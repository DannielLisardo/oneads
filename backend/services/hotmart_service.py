"""
Hotmart Service
API v2 — Vendas, Comissões e Produtos
"""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from .token_store import get_token
from config import get_settings

settings = get_settings()
HOTMART_API = "https://developers.hotmart.com/payments/api/v1"
HOTMART_AUTH = "https://api-sec-vlc.hotmart.com/security/oauth/token"


async def _get_access_token() -> Optional[str]:
    token = get_token("hotmart")
    if not token:
        return None
    # OAuth2 client credentials
    if token.get("access_token"):
        return token["access_token"]
    # Solicita novo token via client_credentials
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            HOTMART_AUTH,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.hotmart_client_id,
                "client_secret": settings.hotmart_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()
        from .token_store import save_token
        save_token("hotmart", {"access_token": data["access_token"]})
        return data["access_token"]


async def get_sales(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retorna vendas do período.
    start_date / end_date: 'YYYY-MM-DD'
    """
    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.utcnow().strftime("%Y-%m-%d")

    access_token = await _get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}

    # Converte para ms (Hotmart usa milissegundos)
    start_ms = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
    end_ms = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)

    rows = []
    page_token = None
    async with httpx.AsyncClient() as client:
        while True:
            params = {
                "start_date": start_ms,
                "end_date": end_ms,
                "max_results": 50,
            }
            if page_token:
                params["page_token"] = page_token

            resp = await client.get(
                f"{HOTMART_API}/sales/history",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("items", []):
                purchase = item.get("purchase", {})
                product = item.get("product", {})
                price = purchase.get("original_offer_price", {})
                rows.append({
                    "date": purchase.get("order_date", "")[:10],
                    "product": product.get("name", ""),
                    "status": purchase.get("status", ""),
                    "revenue": float(price.get("value", 0)),
                    "currency": price.get("currency_value", "BRL"),
                    "transaction": purchase.get("transaction", ""),
                })

            page_token = data.get("page_info", {}).get("next_page_token")
            if not page_token:
                break

    return rows
