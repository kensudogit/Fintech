from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import get_settings
from app.db.session import SessionLocal, init_db
from app.rag.pipeline import rag_service

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    try:
        async with SessionLocal() as session:
            await rag_service.build_index(session)
    except Exception as exc:  # noqa: BLE001
        # Allow API to start even if DB is temporarily unavailable
        print(f"[startup] RAG index skipped: {exc}")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    origins = settings.cors_origin_list
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if origins == ["*"] else origins,
        allow_credentials=origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api/v1")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def root() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api")
    async def api_info() -> dict:
        return {
            "name": settings.app_name,
            "docs": "/docs",
            "health": "/api/v1/health",
            "chat": "/api/v1/chat",
            "ui": "/",
        }

    return app


app = create_app()
