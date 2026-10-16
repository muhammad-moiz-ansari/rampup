from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from app.config import get_settings


def postgres_url(raw: str) -> str:
    url = make_url(raw)
    if url.get_backend_name() not in ("postgres", "postgresql"):
        raise ValueError("PostgreSQL is required")
    return url.set(drivername="postgresql+psycopg").render_as_string(
        hide_password=False
    )


@lru_cache
def get_engine():
    return create_engine(
        postgres_url(get_settings().database_url),
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
        pool_recycle=240,
        connect_args={"connect_timeout": 10},
    )


def get_db():
    with sessionmaker(get_engine(), expire_on_commit=False)() as db:
        yield db
