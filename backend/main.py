"""
OneAds — Backend Principal
FastAPI + OAuth para Google Drive, Google Ads, Meta Ads, TikTok Ads e Hotmart
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from routers import auth, sync

app = FastAPI(
    title="OneAds API",
    description="Conecte suas contas de ads e sincronize com seu Google Drive",
    version="1.0.0",
)

# ── CORS (permite frontend local e futuro domínio SaaS) ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000",
                   "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──
app.include_router(auth.router)
app.include_router(sync.router)

# ── Serve o frontend estático (pasta ../frontend) ──
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

@app.get("/")
async def root():
    landing_path = os.path.join(FRONTEND_DIR, "landing.html")
    if os.path.exists(landing_path):
        return FileResponse(landing_path)
    return {"message": "OneAds API está rodando!", "docs": "/docs"}

@app.get("/landing")
async def landing():
    landing_path = os.path.join(FRONTEND_DIR, "landing.html")
    if os.path.exists(landing_path):
        return FileResponse(landing_path)
    return {"message": "Landing page não encontrada"}

@app.get("/conectar")
async def conectar():
    conectar_path = os.path.join(FRONTEND_DIR, "conectar.html")
    if os.path.exists(conectar_path):
        return FileResponse(conectar_path)
    return {"message": "Página de conexão não encontrada"}

@app.get("/dashboard")
async def dashboard():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Dashboard não encontrado"}

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    from config import get_settings
    s = get_settings()
    port = int(os.environ.get("PORT", s.app_port))
    reload = os.environ.get("RAILWAY_ENVIRONMENT") is None  # reload só em dev local
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload)
