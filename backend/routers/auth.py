"""
Router de autenticação OAuth para todas as plataformas.
Cada plataforma tem:
  GET /auth/{platform}/connect  → redireciona para o OAuth da plataforma
  GET /auth/{platform}/callback → recebe o code, troca por token, salva
  DELETE /auth/{platform}/disconnect → revoga e remove token
"""
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from urllib.parse import urlencode
from config import get_settings
from services.token_store import save_token, get_token, delete_token, list_connected
from services.drive_service import get_user_info as google_user_info
from services.meta_service import get_user_info as meta_user_info

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

# ──────────────────────────────────────────────
# STATUS GERAL
# ──────────────────────────────────────────────
@router.get("/status")
async def connection_status():
    connected = list_connected()
    platforms = ["google", "meta", "tiktok", "hotmart", "shopify"]
    result = {}
    for p in platforms:
        token = get_token(p)
        result[p] = {"connected": token is not None}
        if token and token.get("account_name"):
            result[p]["account_name"] = token["account_name"]
    return result


# ──────────────────────────────────────────────
# GOOGLE (Drive + Ads — mesmo OAuth)
# ──────────────────────────────────────────────
GOOGLE_SCOPES = " ".join([
    "openid", "email", "profile",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/adwords",
])

@router.get("/google/connect")
async def google_connect():
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(url)

@router.get("/google/callback")
async def google_callback(code: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        token_data = resp.json()

    save_token("google", {
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token"),
    })

    try:
        info = google_user_info()
        token = {"access_token": token_data["access_token"],
                 "refresh_token": token_data.get("refresh_token"),
                 "account_name": info.get("name", ""),
                 "email": info.get("email", "")}
        save_token("google", token)
    except Exception:
        pass

    return RedirectResponse(f"{settings.frontend_base_url}/conectar?connected=google")

@router.delete("/google/disconnect")
async def google_disconnect():
    delete_token("google")
    return {"ok": True}


# ──────────────────────────────────────────────
# META ADS
# ──────────────────────────────────────────────
META_SCOPES = "ads_read,ads_management,pages_read_engagement,email,public_profile"

@router.get("/meta/connect")
async def meta_connect():
    params = {
        "client_id": settings.meta_app_id,
        "redirect_uri": settings.meta_redirect_uri,
        "scope": META_SCOPES,
        "response_type": "code",
    }
    url = "https://www.facebook.com/v19.0/dialog/oauth?" + urlencode(params)
    return RedirectResponse(url)

@router.get("/meta/callback")
async def meta_callback(code: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://graph.facebook.com/v19.0/oauth/access_token",
            params={
                "client_id": settings.meta_app_id,
                "client_secret": settings.meta_app_secret,
                "redirect_uri": settings.meta_redirect_uri,
                "code": code,
            },
        )
        resp.raise_for_status()
        token_data = resp.json()

    save_token("meta", {"access_token": token_data["access_token"]})

    try:
        info = await meta_user_info()
        save_token("meta", {
            "access_token": token_data["access_token"],
            "account_name": info.get("name", ""),
        })
    except Exception:
        pass

    return RedirectResponse(f"{settings.frontend_base_url}/conectar?connected=meta")

@router.delete("/meta/disconnect")
async def meta_disconnect():
    delete_token("meta")
    return {"ok": True}


# ──────────────────────────────────────────────
# TIKTOK ADS
# ──────────────────────────────────────────────
@router.get("/tiktok/connect")
async def tiktok_connect():
    params = {
        "app_id": settings.tiktok_app_id,
        "redirect_uri": settings.tiktok_redirect_uri,
        "state": "oneads",
    }
    url = "https://business-api.tiktok.com/portal/auth?" + urlencode(params)
    return RedirectResponse(url)

@router.get("/tiktok/callback")
async def tiktok_callback(auth_code: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://business-api.tiktok.com/open_api/v1.3/oauth2/access_token/",
            json={
                "app_id": settings.tiktok_app_id,
                "secret": settings.tiktok_app_secret,
                "auth_code": auth_code,
            },
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})

    save_token("tiktok", {
        "access_token": data.get("access_token"),
        "advertiser_ids": data.get("advertiser_ids", []),
        "account_name": data.get("display_name", "TikTok"),
    })
    return RedirectResponse(f"{settings.frontend_base_url}/conectar?connected=tiktok")

@router.delete("/tiktok/disconnect")
async def tiktok_disconnect():
    delete_token("tiktok")
    return {"ok": True}


# ──────────────────────────────────────────────
# HOTMART
# ──────────────────────────────────────────────
@router.get("/hotmart/connect")
async def hotmart_connect():
    params = {
        "client_id": settings.hotmart_client_id,
        "redirect_uri": settings.hotmart_redirect_uri,
        "response_type": "code",
        "scope": "READ_SALES",
    }
    url = "https://api-sec-vlc.hotmart.com/security/oauth/authorize?" + urlencode(params)
    return RedirectResponse(url)

@router.get("/hotmart/callback")
async def hotmart_callback(code: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api-sec-vlc.hotmart.com/security/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.hotmart_redirect_uri,
                "client_id": settings.hotmart_client_id,
                "client_secret": settings.hotmart_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        token_data = resp.json()

    save_token("hotmart", {
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token"),
        "account_name": "Hotmart",
    })
    return RedirectResponse(f"{settings.frontend_base_url}/conectar?connected=hotmart")

@router.delete("/hotmart/disconnect")
async def hotmart_disconnect():
    delete_token("hotmart")
    return {"ok": True}

# ──────────────────────────────────────────────
# SHOPIFY
# ──────────────────────────────────────────────
@router.get("/shopify/connect")
async def shopify_connect(shop: str):
    """
    shop: domínio da loja, ex. minha-loja.myshopify.com
    Redireciona para o OAuth do Shopify.
    """
    scopes = "read_orders,read_products,read_analytics"
    params = {
        "client_id": settings.shopify_api_key,
        "scope": scopes,
        "redirect_uri": settings.shopify_redirect_uri,
        "state": shop,
    }
    url = f"https://{shop}/admin/oauth/authorize?" + urlencode(params)
    return RedirectResponse(url)

@router.get("/shopify/callback")
async def shopify_callback(code: str, shop: str, state: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://{shop}/admin/oauth/access_token",
            json={
                "client_id": settings.shopify_api_key,
                "client_secret": settings.shopify_api_secret,
                "code": code,
            },
        )
        resp.raise_for_status()
        token_data = resp.json()

    save_token("shopify", {
        "access_token": token_data["access_token"],
        "shop_domain": shop,
        "account_name": shop.replace(".myshopify.com", ""),
    })
    return RedirectResponse(f"{settings.frontend_base_url}/conectar?connected=shopify")

@router.delete("/shopify/disconnect")
async def shopify_disconnect():
    delete_token("shopify")
    return {"ok": True}

