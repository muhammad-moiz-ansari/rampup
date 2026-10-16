from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text

from app.config import get_settings


def create_app() -> FastAPI:
    app = FastAPI(title="RampUp", version="0.1.0")

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.get("/healthz")
    def health():
        return {"status": "ok"}

    @app.get("/readyz")
    def ready():
        try:
            engine = create_engine(get_settings().database_url, connect_args={"connect_timeout": 3})
            try:
                with engine.connect() as connection:
                    revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
                    if revision != "0001":
                        raise ValueError("Schema not ready")
            finally:
                engine.dispose()
        except Exception:
            return JSONResponse(status_code=503, content={"status": "not_ready"})
        return {"status": "ready"}

    @app.get("/api/{path:path}", include_in_schema=False)
    def missing_api(path: str, request: Request):
        return JSONResponse(status_code=404, content={"error": {"code": "NOT_FOUND", "message": "Route not found", "retryable": False, "request_id": request.state.request_id}})

    static = Path(get_settings().static_dir)
    if (static / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if (static / "index.html").is_file():
            return FileResponse(static / "index.html")
        return JSONResponse(status_code=404, content={"detail": "Frontend assets not built"})

    return app


app = create_app()
