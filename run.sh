#!/usr/bin/env bash
# TODO 앱 실행 스크립트 (SQLite)
# 사용법: ./run.sh [포트] [호스트]
#   ./run.sh                  → 0.0.0.0:8000 (모든 인터페이스, 외부 접근 허용·기본)
#   ./run.sh 8000 127.0.0.1   → localhost 전용
#
# 인증을 켜려면 실행 전에 환경변수를 설정하세요 (둘 다 있어야 활성화):
#   export BASIC_AUTH_USER=todo
#   export BASIC_AUTH_PASS='원하는비밀번호'
#
# 동작: 1) 마이그레이션 적용(없으면 DB 파일 생성)  2) 서버 실행
set -euo pipefail

cd "$(dirname "$0")"

PORT="${1:-8000}"
HOST="${2:-0.0.0.0}"

echo "▶ 마이그레이션 적용..."
.venv/bin/alembic upgrade head

if [ -n "${BASIC_AUTH_USER:-}" ] && [ -n "${BASIC_AUTH_PASS:-}" ]; then
  echo "▶ Basic 인증: 활성화 (user=${BASIC_AUTH_USER})"
else
  echo "▶ Basic 인증: 비활성화 (BASIC_AUTH_USER/PASS 미설정)"
fi

echo "▶ 서버 시작 → http://${HOST}:${PORT}"
exec .venv/bin/python -m uvicorn main:app --host "$HOST" --port "$PORT"
