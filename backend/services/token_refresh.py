"""
Token Refresh Service
- Google: a biblioteca google-auth já faz refresh automático via _get_credentials()
- Meta: troca access_token por Long-Lived Token (validade ~60 dias)
          Só renova quando faltam menos de 7 dias para expirar
"""
import httpx
import logging
from datetime import datetime, timedelta
from .token_store import get_token, save_token, list_connected
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def refresh_google_token() -> bool:
    """
    Força verificação/refresh do token Google.
    A biblioteca google-auth cuida do refresh automaticamente quando
    _get_credentials() detecta que o token expirou.
    """
    try:
        from .drive_service import _get_credentials
        creds = _get_credentials()
        if creds is None:
            logger.warning("[Google] Token não encontrado.")
            return False
        # Salva access_token atualizado (caso a lib tenha feito refresh)
        token = get_token("google")
        if token and creds.token != token.get("access_token"):
            save_token("google", {
                **token,
                "access_token": creds.token,
            })
            logger.info("[Google] Token atualizado após refresh automático.")
        else:
            logger.info("[Google] Token ainda válido.")
        return True
    except Exception as e:
        logger.error(f"[Google] Erro ao verificar token: {e}")
        return False


async def refresh_meta_token() -> bool:
    """
    Troca o token do Meta por um Long-Lived Token (~60 dias).
    Só faz a troca se o token estiver com menos de 7 dias de validade
    ou se ainda não tiver data de expiração registrada.
    """
    token = get_token("meta")
    if not token:
        logger.warning("[Meta] Token não encontrado, pulando refresh.")
        return False

    # Verifica validade
    expires_at = token.get("expires_at")
    if expires_at:
        try:
            expires_dt = datetime.fromisoformat(expires_at)
            dias_restantes = (expires_dt - datetime.utcnow()).days
            if dias_restantes > 7:
                logger.info(f"[Meta] Token válido por mais {dias_restantes} dias, sem refresh necessário.")
                return True
            logger.info(f"[Meta] Token vence em {dias_restantes} dias — renovando...")
        except ValueError:
            pass  # formato inválido, força refresh

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://graph.facebook.com/v19.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": settings.meta_app_id,
                    "client_secret": settings.meta_app_secret,
                    "fb_exchange_token": token["access_token"],
                },
            )
            resp.raise_for_status()
            data = resp.json()

        expires_in = data.get("expires_in", 5_184_000)  # padrão: 60 dias
        new_expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()

        save_token("meta", {
            **token,
            "access_token": data["access_token"],
            "expires_at": new_expires_at,
        })
        logger.info(f"[Meta] Token renovado. Novo vencimento: {new_expires_at[:10]}")
        return True

    except Exception as e:
        logger.error(f"[Meta] Erro ao renovar token: {e}")
        return False


async def refresh_all_tokens() -> dict:
    """
    Renova tokens de todas as plataformas conectadas.
    Retorna dict com resultado por plataforma.
    """
    connected = list_connected()
    results = {}

    if "google" in connected:
        results["google"] = await refresh_google_token()

    if "meta" in connected:
        results["meta"] = await refresh_meta_token()

    # TikTok e Hotmart: implementar refresh quando integração for ao ar
    for p in ["tiktok", "hotmart", "shopify"]:
        if p in connected:
            results[p] = True  # tokens desses não expiram no curto prazo

    logger.info(f"Refresh de tokens concluído: {results}")
    return results
