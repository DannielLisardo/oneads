"""
OneAds — Backend Principal
FastAPI + OAuth para Google Drive, Google Ads, Meta Ads, TikTok Ads, Hotmart e Shopify
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import logging

from routers import auth, sync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan: startup + shutdown ──────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from services.scheduler import start_scheduler
    start_scheduler()
    logger.info("OneAds API iniciada.")
    yield
    # Shutdown
    from services.scheduler import stop_scheduler
    stop_scheduler()
    logger.info("OneAds API encerrada.")


app = FastAPI(
    title="OneAds API",
    description="Conecte suas contas de ads e sincronize com seu Google Drive",
    version="1.1.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://oneads-9248.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────
app.include_router(auth.router)
app.include_router(sync.router)

# ── Frontend estático ─────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


# ── Páginas ───────────────────────────────────
@app.get("/")
async def root():
    path = os.path.join(FRONTEND_DIR, "landing.html")
    return FileResponse(path) if os.path.exists(path) else {"message": "OneAds API rodando", "docs": "/docs"}


@app.get("/landing")
async def landing():
    path = os.path.join(FRONTEND_DIR, "landing.html")
    return FileResponse(path) if os.path.exists(path) else {"message": "Landing não encontrada"}


@app.get("/conectar")
async def conectar():
    path = os.path.join(FRONTEND_DIR, "conectar.html")
    return FileResponse(path) if os.path.exists(path) else {"message": "Página de conexão não encontrada"}


@app.get("/dashboard")
async def dashboard():
    path = os.path.join(FRONTEND_DIR, "index.html")
    return FileResponse(path) if os.path.exists(path) else {"message": "Dashboard não encontrado"}


# ── Health + info ─────────────────────────────
@app.get("/health")
async def health():
    from services.scheduler import scheduler
    job = scheduler.get_job("daily_sync")
    return {
        "status": "ok",
        "version": "1.1.0",
        "scheduler": "running" if scheduler.running else "stopped",
        "next_sync": str(job.next_run_time) if job else None,
    }


if __name__ == "__main__":
    import uvicorn
    from config import get_settings
    s = get_settings()
    port = int(os.environ.get("PORT", s.app_port))
    reload = os.environ.get("RENDER") is None  # reload só em dev local
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload)
