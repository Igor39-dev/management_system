#!/bin/sh
set -e

alembic -c backend/alembic.ini upgrade head

exec uvicorn backend.src.main:app --host 0.0.0.0 --port 8000
