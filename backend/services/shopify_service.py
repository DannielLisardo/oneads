"""
Shopify Service
Admin REST API 2024-04 — Pedidos, Produtos e relatório de vendas
Autenticação: OAuth (para apps públicos/parceiros) ou Private App Token
"""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from .token_store import get_token

SHOPIFY_API_VERSION = "2024-04"


def _get_credentials() -> Optional[Dict[str, Any]]:
    return get_token("shopify")


def _base_url(shop_domain: str) -> str:
    """shop_domain: ex. minha-loja.myshopify.com"""
    return f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}"


async def get_shop_info() -> Dict[str, Any]:
    creds = _get_credentials()
    if not creds:
        return {}
    shop_domain = creds.get("shop_domain", "")
    access_token = creds.get("access_token", "")
    headers = {"X-Shopify-Access-Token": access_token}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{_base_url(shop_domain)}/shop.json", headers=headers)
        resp.raise_for_status()
        return resp.json().get("shop", {})


async def get_orders(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: str = "any",
) -> List[Dict[str, Any]]:
    """
    Retorna pedidos do período.
    start_date / end_date: 'YYYY-MM-DD'
    """
    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.utcnow().strftime("%Y-%m-%d")

    creds = _get_credentials()
    if not creds:
        return []

    shop_domain = creds.get("shop_domain", "")
    access_token = creds.get("access_token", "")
    headers = {"X-Shopify-Access-Token": access_token}

    rows = []
    url = f"{_base_url(shop_domain)}/orders.json"
    params = {
        "status": status,
        "created_at_min": f"{start_date}T00:00:00Z",
        "created_at_max": f"{end_date}T23:59:59Z",
        "limit": 250,
        "fields": "id,created_at,total_price,subtotal_price,total_tax,financial_status,fulfillment_status,source_name,discount_codes",
    }

    async with httpx.AsyncClient() as client:
        while url:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            orders = resp.json().get("orders", [])
            for o in orders:
                rows.append({
                    "date": o.get("created_at", "")[:10],
                    "order_id": o.get("id", ""),
                    "revenue": float(o.get("total_price", 0)),
                    "subtotal": float(o.get("subtotal_price", 0)),
                    "tax": float(o.get("total_tax", 0)),
                    "financial_status": o.get("financial_status", ""),
                    "fulfillment_status": o.get("fulfillment_status", "") or "unfulfilled",
                    "source": o.get("source_name", ""),
                    "discount": ", ".join(d.get("code", "") for d in o.get("discount_codes", [])),
                })
            # Paginação via Link header
            link = resp.headers.get("Link", "")
            next_url = None
            if 'rel="next"' in link:
                for part in link.split(","):
                    if 'rel="next"' in part:
                        next_url = part.split(";")[0].strip().strip("<>")
            url = next_url
            params = {}  # params já estão na URL do next

    return rows


async def get_sales_by_source(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, float]:
    """Agrupa receita por fonte de tráfego (utm_source / source_name)."""
    orders = await get_orders(start_date, end_date, status="paid")
    by_source: Dict[str, float] = {}
    for o in orders:
        src = o.get("source", "direct") or "direct"
        by_source[src] = by_source.get(src, 0.0) + o.get("revenue", 0.0)
    return by_source
