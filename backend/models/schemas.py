from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class TokenData(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None


class ConnectionStatus(BaseModel):
    platform: str
    connected: bool
    account_name: Optional[str] = None
    account_id: Optional[str] = None
    connected_at: Optional[datetime] = None


class MetricRow(BaseModel):
    date: str
    platform: str
    campaign: Optional[str] = None
    spend: float = 0.0
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    revenue: float = 0.0


class SyncResponse(BaseModel):
    success: bool
    message: str
    rows_synced: int = 0
    drive_file_url: Optional[str] = None


class DriveFile(BaseModel):
    id: str
    name: str
    url: str
    modified_at: Optional[str] = None
