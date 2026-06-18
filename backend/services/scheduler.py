"""
Scheduler de sincronização diária — OneAds
==========================================
- Roda às 08:30 BRT (America/Sao_Paulo) todos os dias
- Coleta dados do DIA ANTERIOR de cada plataforma conectada
- Retry automático (3 tentativas com backoff exponencial: 2s, 4s, 8s)
- Rate limiting: pausa entre requisições para evitar bloqueio de API
- Uma plataforma com erro NÃO cancela as outras
"""
import asyncio
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .token_refresh import refresh_all_tokens
from .token_store import list_connected
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Instância global do scheduler
scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def _yesterday() -> str:
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


async def _with_retry(label: str, coro_fn, max_attempts: int = 3):
    """
    Executa coro_fn() com até max_attempts tentativas.
    Backoff: 2s → 4s → 8s entre falhas.
    Retorna o resultado ou None se todas as tentativas falharem.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            result = await coro_fn()
            logger.info(f"[{label}] OK — {result}")
            return result
        except Exception as e:
            wait = 2 ** attempt
            if attempt < max_attempts:
                logger.warning(
                    f"[{label}] Tentativa {attempt}/{max_attempts} falhou: {e}. "
                    f"Retentando em {wait}s..."
                )
                await asyncio.sleep(wait)
            else:
                logger.error(f"[{label}] Falhou após {max_attempts} tentativas: {e}")
                return None


# ──────────────────────────────────────────────
# SYNC FUNCTIONS (cada uma retorna {rows, url})
# ──────────────────────────────────────────────

async def _sync_meta(yesterday: str):
    from . import meta_service, drive_service

    accounts = await meta_service.get_ad_accounts()
    if not accounts:
        return {"rows": 0, "msg": "Nenhuma conta Meta encontrada"}

    folder_id = drive_service.get_or_create_folder(settings.drive_root_folder_name)
    file_info = drive_service.get_or_create_spreadsheet("Meta Ads - Métricas", folder_id)
    header = ["Data", "Conta", "Campanha", "Gasto (R$)", "Impressões", "Cliques", "Conversões", "Receita"]
    drive_service.write_header_if_empty(file_info["id"], "Dados", header)

    total = 0
    for account in accounts:
        await asyncio.sleep(1)  # respeita rate limit: 1s entre contas
        rows = await meta_service.get_campaign_insights(
            account["id"].replace("act_", ""),
            date_preset="yesterday",
        )
        for r in rows:
            drive_service.append_rows_to_sheet(
                file_info["id"], "Dados",
                [[yesterday, account.get("name", ""), r["campaign"],
                  r["spend"], r["impressions"], r["clicks"],
                  r["conversions"], r["revenue"]]]
            )
            total += 1

    return {"rows": total, "url": file_info["url"]}


async def _sync_google_ads(yesterday: str):
    from . import google_ads_service, drive_service

    customers = await google_ads_service.list_customers()
    if not customers:
        return {"rows": 0, "msg": "Nenhuma conta Google Ads encontrada"}

    folder_id = drive_service.get_or_create_folder(settings.drive_root_folder_name)
    file_info = drive_service.get_or_create_spreadsheet("Google Ads - Métricas", folder_id)
    header = ["Data", "Campanha", "Status", "Gasto (R$)", "Impressões", "Cliques", "Conversões"]
    drive_service.write_header_if_empty(file_info["id"], "Dados", header)

    total = 0
    for cid_resource in customers:
        await asyncio.sleep(0.5)  # respeita rate limit do Google Ads
        cid = cid_resource.split("/")[-1]
        rows = await google_ads_service.get_campaign_metrics(cid, "YESTERDAY")
        for r in rows:
            drive_service.append_rows_to_sheet(
                file_info["id"], "Dados",
                [[r["date"], r["campaign"], r["status"],
                  r["spend"], r["impressions"], r["clicks"], r["conversions"]]]
            )
            total += 1

    return {"rows": total, "url": file_info["url"]}


async def _sync_shopify(yesterday: str):
    from . import shopify_service, drive_service

    rows = await shopify_service.get_orders(yesterday, yesterday, status="paid")
    folder_id = drive_service.get_or_create_folder(settings.drive_root_folder_name)
    file_info = drive_service.get_or_create_spreadsheet("Shopify - Pedidos", folder_id)
    header = ["Data", "Pedido ID", "Receita", "Subtotal", "Imposto",
              "Status Pagamento", "Status Envio", "Origem", "Desconto"]
    drive_service.write_header_if_empty(file_info["id"], "Pedidos", header)

    for r in rows:
        drive_service.append_rows_to_sheet(
            file_info["id"], "Pedidos",
            [[r["date"], r["order_id"], r["revenue"], r["subtotal"],
              r["tax"], r["financial_status"], r["fulfillment_status"],
              r["source"], r["discount"]]]
        )

    return {"rows": len(rows), "url": file_info["url"]}


async def _sync_hotmart(yesterday: str):
    from . import hotmart_service, drive_service

    rows = await hotmart_service.get_sales(yesterday, yesterday)
    folder_id = drive_service.get_or_create_folder(settings.drive_root_folder_name)
    file_info = drive_service.get_or_create_spreadsheet("Hotmart - Vendas", folder_id)
    header = ["Data", "Produto", "Status", "Receita", "Moeda", "Transação"]
    drive_service.write_header_if_empty(file_info["id"], "Vendas", header)

    for r in rows:
        drive_service.append_rows_to_sheet(
            file_info["id"], "Vendas",
            [[r["date"], r["product"], r["status"],
              r["revenue"], r["currency"], r["transaction"]]]
        )

    return {"rows": len(rows), "url": file_info["url"]}


# ──────────────────────────────────────────────
# JOB PRINCIPAL
# ──────────────────────────────────────────────

async def daily_sync_job():
    """
    Job diário — executa às 08:30 BRT.
    Coleta dados de ontem de todas as plataformas conectadas.
    """
    yesterday = _yesterday()
    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"╔══ Sync diário iniciado [{started_at}] | Alvo: {yesterday} ══╗")

    # 1. Renova tokens antes de qualquer chamada de API
    try:
        await refresh_all_tokens()
    except Exception as e:
        logger.error(f"Erro no refresh de tokens: {e}")
    await asyncio.sleep(1)

    connected = list_connected()
    logger.info(f"Plataformas conectadas: {connected}")

    if not connected:
        logger.info("Nenhuma plataforma conectada. Sync encerrado.")
        return {}

    results = {}

    # 2. Meta Ads
    if "meta" in connected:
        results["meta"] = await _with_retry(
            "Meta Ads", lambda: _sync_meta(yesterday)
        )
        await asyncio.sleep(2)  # pausa entre plataformas

    # 3. Google Ads (via token Google já conectado)
    if "google" in connected:
        results["google_ads"] = await _with_retry(
            "Google Ads", lambda: _sync_google_ads(yesterday)
        )
        await asyncio.sleep(2)

    # 4. Shopify
    if "shopify" in connected:
        results["shopify"] = await _with_retry(
            "Shopify", lambda: _sync_shopify(yesterday)
        )
        await asyncio.sleep(1)

    # 5. Hotmart
    if "hotmart" in connected:
        results["hotmart"] = await _with_retry(
            "Hotmart", lambda: _sync_hotmart(yesterday)
        )

    finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"╚══ Sync diário concluído [{finished_at}] | Resultados: {results} ══╝")
    return results


# ──────────────────────────────────────────────
# INICIALIZAÇÃO
# ──────────────────────────────────────────────

def start_scheduler():
    """
    Registra o job diário e inicia o scheduler.
    Chamado no startup do FastAPI via lifespan.
    """
    scheduler.add_job(
        daily_sync_job,
        trigger=CronTrigger(hour=8, minute=30, timezone="America/Sao_Paulo"),
        id="daily_sync",
        name="Sync diário 08:30 BRT",
        replace_existing=True,
        misfire_grace_time=3600,  # aceita até 1h de atraso (ex: cold start do Render)
    )
    scheduler.start()

    next_run = scheduler.get_job("daily_sync").next_run_time
    logger.info(f"Scheduler iniciado. Próximo sync: {next_run}")


def stop_scheduler():
    """Para o scheduler no shutdown do FastAPI."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler encerrado.")
