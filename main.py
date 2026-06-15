"""
main.py — E-Okul OCR FastAPI uygulamasının giriş noktası.

Başlatmak için:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Swagger UI: http://127.0.0.1:8000/docs
ReDoc:       http://127.0.0.1:8000/redoc
"""
from __future__ import annotations
import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

from app.database import init_db
from app.routers import upload, grades, export

# ─── Loglama yapılandırması ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("eokul_ocr.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ─── Uygulama yaşam döngüsü ──────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Başlangıç: DB tablolarını oluştur."""
    logger.info("🚀 E-Okul OCR Backend başlatılıyor…")
    init_db()
    logger.info("✅ Veritabanı hazır (local_eokul.db).")
    # EasyOCR reader'ı arka planda ön-yükle (isteğe bağlı)
    # from app.services.ocr_engine import _get_reader
    # _get_reader()  # İlk istek hızlanır; başlangıç ~30 sn uzar
    yield
    logger.info("🛑 E-Okul OCR Backend kapatılıyor.")


# ─── FastAPI uygulaması ───────────────────────────────────────────────────────

app = FastAPI(
    title="E-Okul OCR Backend",
    description=(
        "Fizik öğretmeni için e-okul ekran görüntülerinden not ayıklayan, "
        "yerelde CPU'da çalışan FastAPI servisi."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — geliştirme ortamında tüm originate izin ver
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Router kayıtları ─────────────────────────────────────────────────────────
app.include_router(upload.router)
app.include_router(grades.router)
app.include_router(export.router)


# ─── Global hata yakalayıcı ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("İşlenmeyen hata: %s %s → %s", request.method, request.url.path, exc,
                 exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Sunucu hatası: {type(exc).__name__}: {exc}"},
    )


# ─── Sağlık kontrolü ─────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
def health_check():
    """Servis canlılık kontrolü."""
    return {"status": "ok", "service": "E-Okul OCR Backend", "version": "1.0.0"}


@app.get("/", tags=["system"])
def root():
    return {
        "message": "E-Okul OCR Backend çalışıyor.",
        "docs": "/docs",
        "health": "/health",
    }
