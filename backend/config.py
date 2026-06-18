from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Servidor
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_secret_key: str = "dev-secret-change-me"

    # Google
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # Meta
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_redirect_uri: str = "http://localhost:8000/auth/meta/callback"

    # TikTok
    tiktok_app_id: str = ""
    tiktok_app_secret: str = ""
    tiktok_redirect_uri: str = "http://localhost:8000/auth/tiktok/callback"

    # Hotmart
    hotmart_client_id: str = ""
    hotmart_client_secret: str = ""
    hotmart_redirect_uri: str = "http://localhost:8000/auth/hotmart/callback"

    # Shopify
    shopify_api_key: str = ""
    shopify_api_secret: str = ""
    shopify_redirect_uri: str = "http://localhost:8000/auth/shopify/callback"

    # Drive
    drive_root_folder_name: str = "OneAds Data"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
