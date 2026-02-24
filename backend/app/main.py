from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi.encoders import jsonable_encoder
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.responses import error_response, success_response
from app.db.session import init_db


def _build_lifespan(init_default_db: bool):
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if init_default_db:
            init_db()
        yield

    return lifespan


def create_app(*, init_default_db: bool = True) -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Todo List API", version="0.1.0", lifespan=_build_lifespan(init_default_db))

    origins = settings.cors_origins_list or ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException):
        message = exc.detail if isinstance(exc.detail, str) else "요청 처리 중 오류가 발생했습니다."
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(message, code=f"HTTP_{exc.status_code}", details=None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=error_response(
                "입력값 검증에 실패했습니다.",
                code="VALIDATION_ERROR",
                details=jsonable_encoder(exc.errors()),
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=error_response("서버 내부 오류가 발생했습니다.", code="INTERNAL_SERVER_ERROR", details=None),
        )

    @app.get("/health")
    def health_check():
        return success_response({"ok": True})

    app.include_router(api_router, prefix="/api/v1")

    static_dir = (Path(__file__).resolve().parents[2] / "static").resolve()
    index_file = static_dir / "index.html"
    assets_dir = static_dir / "assets"

    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    if index_file.exists():
        @app.get("/", include_in_schema=False)
        def serve_index():
            return FileResponse(index_file)

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa_fallback(full_path: str):
            reserved_prefixes = ("api/", "docs", "redoc", "openapi.json", "health", "assets/")
            if full_path == "" or full_path.startswith(reserved_prefixes):
                raise HTTPException(status_code=404, detail="Not Found")
            return FileResponse(index_file)

    return app


app = create_app()
