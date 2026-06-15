#!/usr/bin/env bash
# TODO 앱 실행 스크립트 (SQLite)
# 사용법: ./run.sh [포트]  (기본 포트: 8000)
#  1) 마이그레이션 적용(없으면 DB 파일 생성)  2) 서버 실행
set -euo pipefail

cd "$(dirname "$0")"

PORT="${1:-8000}"

echo "▶ 마이그레이션 적용..."
.venv/bin/alembic upgrade head

echo "▶ 서버 시작 → http://localhost:${PORT}"
exec .venv/bin/python -m uvicorn main:app --reload --port "$PORT"
