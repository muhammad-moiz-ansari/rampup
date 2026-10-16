#!/bin/sh
set -eu
if [ -n "${DATABASE_URL:-}" ] && [ -f alembic.ini ]; then
  alembic upgrade head
fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
