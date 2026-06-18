"""
Google Drive Service
- Autentica com a conta Google do CLIENTE (não da agência)
- Cria/lê a pasta 'OneAds Data' no Drive do cliente
- Salva métricas em planilhas Google Sheets dentro dessa pasta
"""
import os
from typing import Optional, List, Dict, Any
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .token_store import get_token, save_token
from config import get_settings

settings = get_settings()

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
    "openid",
    "email",
    "profile",
]


def _get_credentials() -> Optional[Credentials]:
    token = get_token("google")
    if not token:
        return None

    creds = Credentials(
        token=token.get("access_token"),
        refresh_token=token.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        save_token("google", {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
        })

    return creds


def get_or_create_folder(folder_name: str, parent_id: Optional[str] = None) -> str:
    """Busca ou cria uma pasta no Drive do cliente."""
    creds = _get_credentials()
    service = build("drive", "v3", credentials=creds)

    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def get_or_create_spreadsheet(name: str, folder_id: str) -> Dict[str, str]:
    """Busca ou cria uma planilha dentro da pasta OneAds Data."""
    creds = _get_credentials()
    drive_service = build("drive", "v3", credentials=creds)

    query = (
        f"name='{name}' and mimeType='application/vnd.google-apps.spreadsheet' "
        f"and '{folder_id}' in parents and trashed=false"
    )
    results = drive_service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
    files = results.get("files", [])

    if files:
        return {"id": files[0]["id"], "url": files[0].get("webViewLink", "")}

    # Cria nova planilha
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.spreadsheet",
        "parents": [folder_id],
    }
    file = drive_service.files().create(body=metadata, fields="id, webViewLink").execute()
    return {"id": file["id"], "url": file.get("webViewLink", "")}


def append_rows_to_sheet(spreadsheet_id: str, sheet_name: str, rows: List[List[Any]]):
    """Adiciona linhas em uma aba da planilha."""
    creds = _get_credentials()
    sheets_service = build("sheets", "v4", credentials=creds)

    # Garante que a aba existe
    spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    existing_sheets = [s["properties"]["title"] for s in spreadsheet.get("sheets", [])]

    if sheet_name not in existing_sheets:
        body = {"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}
        sheets_service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

    range_notation = f"{sheet_name}!A1"
    body = {"values": rows}
    sheets_service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=range_notation,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()


def write_header_if_empty(spreadsheet_id: str, sheet_name: str, header: List[str]):
    """Escreve o cabeçalho somente se a planilha estiver vazia."""
    creds = _get_credentials()
    sheets_service = build("sheets", "v4", credentials=creds)

    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A1:Z1"
    ).execute()

    if not result.get("values"):
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption="USER_ENTERED",
            body={"values": [header]},
        ).execute()


def get_user_info() -> Dict[str, str]:
    """Retorna nome e email da conta Google conectada."""
    creds = _get_credentials()
    service = build("oauth2", "v2", credentials=creds)
    info = service.userinfo().get().execute()
    return {"name": info.get("name", ""), "email": info.get("email", "")}
