from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.config import get_settings
from app.db import get_engine
from app.errors import AppError
from app.model_factory import configured_model
from app.models import Base


def create_app() -> FastAPI:
    app = FastAPI(title="RampUp", version="0.1.0")
    app.state.model = configured_model()

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = (
            "no-store" if request.url.path.startswith("/api") else "no-cache"
        )
        return response

    def error_response(request, status, code, message, retryable=False):
        return JSONResponse(
            status_code=status,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "retryable": retryable,
                    "request_id": getattr(request.state, "request_id", str(uuid4())),
                }
            },
        )

    @app.exception_handler(AppError)
    async def application_error(request, error):
        return error_response(
            request, error.status, error.code, error.message, error.retryable
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        return error_response(
            request,
            422,
            "VALIDATION_ERROR",
            "Invalid request body, path, query or required header.",
        )

    @app.exception_handler(HTTPException)
    async def http_error(request, error):
        return error_response(
            request,
            error.status_code,
            "NOT_FOUND" if error.status_code == 404 else "HTTP_ERROR",
            "Route not found" if error.status_code == 404 else "Request rejected",
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, error):
        return error_response(
            request,
            503,
            "DATABASE_UNAVAILABLE",
            "Database operation failed. Retry shortly.",
            True,
        )

    from app.routes import router

    app.include_router(router)

    @app.get("/healthz")
    def health():
        return {"status": "ok"}

    @app.get("/readyz")
    def ready():
        try:
            migration_dir = Path(__file__).resolve().parents[1] / "migrations"
            config = Config()
            config.set_main_option("script_location", str(migration_dir))
            expected = ScriptDirectory.from_config(config).get_current_head()
            with get_engine().connect() as connection:
                revision = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar()
                if revision != expected:
                    raise ValueError("Schema not ready")
                if not set(Base.metadata.tables) <= set(
                    inspect(connection).get_table_names()
                ):
                    raise ValueError("Schema tables missing")
        except Exception:
            return JSONResponse(status_code=503, content={"status": "not_ready"})
        return {"status": "ready"}

    @app.api_route(
        "/api",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        include_in_schema=False,
    )
    @app.api_route(
        "/api/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        include_in_schema=False,
    )
    def missing_api(request: Request, path: str = ""):
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Route not found",
                    "retryable": False,
                    "request_id": request.state.request_id,
                }
            },
        )

    static = Path(get_settings().static_dir)
    if (static / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if (static / "index.html").is_file():
            return FileResponse(static / "index.html")
        return JSONResponse(
            status_code=404, content={"detail": "Frontend assets not built"}
        )

    return app


app = create_app()
