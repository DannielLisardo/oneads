"""
Router de sincronização: puxa dados de cada plataforma e salva no Drive do cliente.
POST /sync/{platform}  → sincroniza dados da plataforma no Google Drive
GET  /sync/history     → lista arquivos na pasta OneAds Data do Drive
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from config import get_settings
from services import drive_service, google_ads_service, meta_service, hotmart_service, tiktok_service
from services.token_store import get_token

router = APIRouter(prefix="/sync", tags=["sync"])
settings = get_settings()


def _require_google():
    if not get_token("google"):
        raise HTTPException(400, "Google Drive não conectado. Conecte primeiro.")


# ──────────────────────────────────────────────
# META ADS → Drive
# ──────────────────────────────────────────────
@router.post("/meta")
async def sync_meta(date_preset: str = Query("last_30d")):
    _require_google()
    if not get_token("meta"):
        raise HTTPException(400, "Meta Ads não conectado.")

    accounts = await meta_service.get_ad_accounts()
    if not accounts:
        raise HTTPException(404, "Nenhuma conta de anúncio encontrada no Meta.")

    total_rows = 0
    folder_id = drive_service.get_or_create_folder(settings.drive_root_folder_name)
    file_info = drive_service.get_or_create_spreadsheet("Meta Ads - Métricas", folder_id)

    header = ["Data", "Conta", "Campanha", "Gasto (R$)", "Impressões", "Cliques", "Conversões", "Receita"]
    drive_service.write_header_if_empty(file_info["id"], "Dados", header)

    for account in accounts:
        rows = await meta_service.get_campaign_insights(
            account["id"].replace("act_", ""), date_preset
        )
        for r in rows:
            drive_service.append_rows_to_sheet(
                file_info["id"], "Dados",
                [[r["date"], account.get("name", ""), r["campaign"],
                  r["spend"], r["impressions"], r["clicks"],
                  r["conversions"], r["revenue"]]]
            )
            total_rows += 1

    return {"success": True, "rows_synced": total_rows, "drive_file_url": file_info["url"]}


# ──────────────────────────────────────────────
# GOOGLE ADS → Drive
# ──────────────────────────────────────────────
@router.post("/google-ads")
async def sync_google_ads(date_range: str = Query("LAST_30_DAYS")):
    _require_google()
    if not get_token("google"):
        raise HTTPException(400, "Google Ads não conectado.")

    customers = await google_ads_service.list_customers()
    if not customers:
        raise HTTPException(404, "Nenhuma conta Google Ads encontrada.")

    total_rows = 0
    folder_id = drive_service.get_or_create_folder(settings.drive_root_folder_name)
    file_info = drive_service.get_or_create_spreadsheet("Google Ads - Métricas", folder_id)

    header = ["Data", "Campanha", "Status", "Gasto (R$)", "Impressões", "Cliques", "Conversões"]
    drive_service.write_header_if_empty(file_info["id"], "Dados", header)

    for customer_resource in customers:
        customer_id = customer_resource.split("/")[-1]
        rows = await google_ads_service.get_campaign_metrics(customer_id, date_range)
        for r in rows:
            drive_service.append_rows_to_sheet(
                file_info["id"], "Dados",
                [[r["date"], r["campaign"], r["status"],
                  r["spend"], r["impressions"], r["clicks"], r["conversions"]]]
            )
            total_rows += 1

    return {"success": True, "rows_synced": total_rows, "drive_file_url": file_info["url"]}


# ──────────────────────────────────────────────
# HOTMART → Drive
# ──────────────────────────────────────────────
@router.post("/hotmart")
async def sync_hotmart(start_date: Optional[str] = None, end_date: Optional[str] = None):
    _require_google()
    if not get_token("hotmart"):
        raise HTTPException(400, "Hotmart não conectado.")

    rows = await hotmart_service.get_sales(start_date, end_date)
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

    return {"success": True, "rows_synced": len(rows), "drive_file_url": file_info["url"]}


# ──────────────────────────────────────────────
# TIKTOK ADS → Drive
# ──────────────────────────────────────────────
@router.post("/tiktok")
async def sync_tiktok(start_date: Optional[str] = None, end_date: Optional[str] = None):
    _require_google()
    token = get_token("tiktok")
    if not token:
        raise HTTPException(400, "TikTok Ads não conectado.")

    advertiser_ids = token.get("advertiser_ids", [])
    if not advertiser_ids:
        raise HTTPException(404, "Nenhuma conta de anunciante TikTok encontrada.")

    folder_id = drive_service.get_or_create_folder(settings.drive_root_folder_name)
    file_info = drive_service.get_or_create_spreadsheet("TikTok Ads - Métricas", folder_id)

    header = ["Data", "Campanha", "Gasto (R$)", "Impressões", "Cliques", "Conversões"]
    drive_service.write_header_if_empty(file_info["id"], "Dados", header)

    total_rows = 0
    for adv_id in advertiser_ids:
        rows = await tiktok_service.get_campaign_report(adv_id, start_date, end_date)
        for r in rows:
            drive_service.append_rows_to_sheet(
                file_info["id"], "Dados",
                [[r["date"], r["campaign"], r["spend"],
                  r["impressions"], r["clicks"], r["conversions"]]]
            )
            total_rows += 1

    return {"success": True, "rows_synced": total_rows, "drive_file_url": file_info["url"]}


# ──────────────────────────────────────────────
# HISTÓRICO — lista planilhas no Drive
# ──────────────────────────────────────────────
@router.get("/history")
async def sync_history():
    _require_google()
    from googleapiclient.discovery import build
    from services.drive_service import _get_credentials
    creds = _get_credentials()
    service = build("drive", "v3", credentials=creds)

    folder_id = drive_service.get_or_create_folder(settings.drive_root_folder_name)
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id, name, webViewLink, modifiedTime)",
        orderBy="modifiedTime desc",
    ).execute()

    return {"files": results.get("files", [])}

# ──────────────────────────────────────────────
# SHOPIFY → Drive
# ──────────────────────────────────────────────
@router.post("/shopify")
async def sync_shopify(start_date: Optional[str] = None, end_date: Optional[str] = None):
    _require_google()
    if not get_token("shopify"):
        raise HTTPException(400, "Shopify não conectado.")

    from services import shopify_service
    rows = await shopify_service.get_orders(start_date, end_date, status="paid")

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

    return {"success": True, "rows_synced": len(rows), "drive_file_url": file_info["url"]}


# ──────────────────────────────────────────────
# RUN NOW — dispara o sync completo manualmente
# ──────────────────────────────────────────────
@router.post("/run-now")
async def run_now():
    """
    Dispara o sync diário imediatamente (para testes e uso manual).
    Equivale ao job das 08:30 BRT, mas roda na hora que for chamado.
    """
    import datetime as dt
    from services.scheduler import daily_sync_job
    results = await daily_sync_job()
    return {
        "success": True,
        "triggered_at": dt.datetime.now().isoformat(),
        "results": results,
    }

