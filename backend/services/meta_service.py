"""
Meta Ads Service (Facebook / Instagram Ads)
"""
import httpx
from typing import List, Dict, Any, Optional
from .token_store import get_token
from config import get_settings

settings = get_settings()
GRAPH_API = "https://graph.facebook.com/v19.0"


def _get_access_token() -> Optional[str]:
    token = get_token("meta")
    return token.get("access_token") if token else None


async def get_ad_accounts() -> List[Dict[str, Any]]:
    """Lista contas de anúncio do usuário."""
    access_token = _get_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GRAPH_API}/me/adaccounts",
            params={"fields": "id,name,account_status,currency", "access_token": access_token},
        )
        resp.raise_for_status()
        return resp.json().get("data", [])


async def get_campaign_insights(
    ad_account_id: str,
    date_preset: str = "last_30d",
) -> List[Dict[str, Any]]:
    """
    Retorna insights de campanhas.
    date_preset: today | yesterday | last_7d | last_30d | this_month | last_month
    """
    access_token = _get_access_token()
    params = {
        "access_token": access_token,
        "level": "campaign",
        "date_preset": date_preset,
        "fields": "campaign_name,spend,impressions,clicks,actions,date_start,date_stop",
        "limit": 500,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GRAPH_API}/act_{ad_account_id}/insights",
            params=params,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])

    rows = []
    for d in data:
        # Extrai conversões das actions
        actions = {a["action_type"]: int(a["value"]) for a in d.get("actions", [])}
        purchase_value = next(
            (float(a["value"]) for a in d.get("action_values", []) if a["action_type"] == "purchase"),
            0.0,
        ) if "action_values" in d else 0.0

        rows.append({
            "date": d.get("date_start", ""),
            "campaign": d.get("campaign_name", ""),
            "spend": float(d.get("spend", 0)),
            "impressions": int(d.get("impressions", 0)),
            "clicks": int(d.get("clicks", 0)),
            "conversions": actions.get("purchase", 0),
            "revenue": purchase_value,
        })
    return rows


async def get_user_info() -> Dict[str, str]:
    access_token = _get_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GRAPH_API}/me",
            params={"fields": "id,name,email", "access_token": access_token},
        )
        resp.raise_for_status()
        return resp.json()
