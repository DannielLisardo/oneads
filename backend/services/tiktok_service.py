"""
TikTok Ads Service
Business API v1.3
"""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from .token_store import get_token

TIKTOK_API = "https://business-api.tiktok.com/open_api/v1.3"


def _get_access_token() -> Optional[str]:
    token = get_token("tiktok")
    return token.get("access_token") if token else None


async def get_advertisers() -> List[Dict[str, Any]]:
    """Lista anunciantes vinculados à conta."""
    access_token = _get_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{TIKTOK_API}/oauth2/advertiser/get/",
            headers={"Access-Token": access_token},
            params={"app_id": "", "secret": ""},
        )
        resp.raise_for_status()
        return resp.json().get("data", {}).get("list", [])


async def get_campaign_report(
    advertiser_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retorna relatório de campanhas por dia.
    start_date / end_date: 'YYYY-MM-DD'
    """
    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.utcnow().strftime("%Y-%m-%d")

    access_token = _get_access_token()
    params = {
        "advertiser_id": advertiser_id,
        "report_type": "BASIC",
        "dimensions": '["campaign_id","stat_time_day"]',
        "metrics": '["campaign_name","spend","impressions","clicks","conversions","conversion_rate"]',
        "start_date": start_date,
        "end_date": end_date,
        "page_size": 200,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{TIKTOK_API}/report/integrated/get/",
            headers={"Access-Token": access_token},
            params=params,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})

    rows = []
    for item in data.get("list", []):
        dims = item.get("dimensions", {})
        metrics = item.get("metrics", {})
        rows.append({
            "date": dims.get("stat_time_day", "")[:10],
            "campaign": metrics.get("campaign_name", ""),
            "spend": float(metrics.get("spend", 0)),
            "impressions": int(metrics.get("impressions", 0)),
            "clicks": int(metrics.get("clicks", 0)),
            "conversions": int(metrics.get("conversions", 0)),
        })
    return rows
