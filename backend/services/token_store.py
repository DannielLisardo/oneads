"""
Armazenamento simples de tokens em memória (local).
Em produção SaaS, substitua por banco de dados.
"""
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime

# Em produção (Render), DATA_DIR aponta para o disco persistente montado em /data
# Em desenvolvimento local, usa a pasta do projeto normalmente
_DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), ".."))
TOKENS_FILE = os.path.join(_DATA_DIR, "tokens.json")


def _load() -> Dict[str, Any]:
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, "r") as f:
            return json.load(f)
    return {}


def _save(data: Dict[str, Any]):
    with open(TOKENS_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def save_token(platform: str, token_data: Dict[str, Any]):
    data = _load()
    data[platform] = {**token_data, "saved_at": str(datetime.utcnow())}
    _save(data)


def get_token(platform: str) -> Optional[Dict[str, Any]]:
    return _load().get(platform)


def delete_token(platform: str):
    data = _load()
    data.pop(platform, None)
    _save(data)


def list_connected() -> list[str]:
    return list(_load().keys())
