#!/usr/bin/env bash
set -e

PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}

echo "⚡ Starting VibeSplit Web Application on http://${HOST}:${PORT} ..."
exec uvicorn backend.main:app --host "${HOST}" --port "${PORT}"
