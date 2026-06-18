"""
Google Ads Service
Busca campanhas e métricas via Google Ads API (REST)
"""
import httpx
from typing import List, Dict, Any, Optional
from .token_store import get_token, save_token
from config import get_settings

settings = get_settings()

ADS_API_BASE = "https://googleads.googleapis.com/v16"


async def _get_access_token() -> Optional[str]:
    token = get_token("google_ads")
    if token:
        return token.get("access_token")
    # Fallback: usa o token do Google Drive se for a mesma conta
    google_token = get_token("google")
    return google_token.get("access_token") if google_token else None


async def list_customers() -> List[Dict[str, Any]]:
    """Lista contas de cliente acessíveis."""
    access_token = await _get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": settings.google_ads_developer_token if hasattr(settings, 'google_ads_developer_token') else "",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{ADS_API_BASE}/customers:listAccessibleCustomers", headers=headers)
        resp.raise_for_status()
        return resp.json().get("resourceNames", [])


async def get_campaign_metrics(customer_id: str, date_range: str = "LAST_30_DAYS") -> List[Dict[str, Any]]:
    """
    Retorna métricas de campanhas para um cliente.
    date_range: LAST_7_DAYS | LAST_30_DAYS | THIS_MONTH | LAST_MONTH
    """
    access_token = await _get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": settings.google_ads_developer_token if hasattr(settings, 'google_ads_developer_token') else "",
        "login-customer-id": customer_id,
        "Content-Type": "application/json",
    }
    query = f"""
        SELECT
            campaign.name,
            campaign.status,
            metrics.cost_micros,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions,
            segments.date
        FROM campaign
        WHERE segments.date DURING {date_range}
        ORDER BY segments.date DESC
    """
    body = {"query": query}
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{ADS_API_BASE}/customers/{customer_id}/googleAds:search",
            headers=headers,
            json=body,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])

    rows = []
    for r in results:
        metrics = r.get("metrics", {})
        campaign = r.get("campaign", {})
        rows.append({
            "date": r.get("segments", {}).get("date", ""),
            "campaign": campaign.get("name", ""),
            "status": campaign.get("status", ""),
            "spend": round(int(metrics.get("costMicros", 0)) / 1_000_000, 2),
            "impressions": int(metrics.get("impressions", 0)),
            "clicks": int(metrics.get("clicks", 0)),
            "conversions": float(metrics.get("conversions", 0)),
        })
    return rows
