#!/usr/bin/env bash
# TODO 앱 실행 스크립트 (SQLite)
# 사용법: ./run.sh [포트] [호스트]
#   ./run.sh                  → 0.0.0.0:8000 (모든 인터페이스, 외부 접근 허용·기본)
#   ./run.sh 8000 127.0.0.1   → localhost 전용
#
# 인증: 이메일 + 비밀번호 회원가입/로그인 (JWT, 유효기간 7일)
# 설정값은 이 폴더의 .env 파일에 적어두면 실행할 때 자동으로 읽는다 (.env.example 참고).
#   JWT_SECRET     — JWT 서명키. 값이 바뀌면 발급된 토큰이 모두 무효(= 재로그인 필요)
#   REGISTER_CODE  — 설정하면 회원가입 시 이 초대 코드가 필요
#
# 동작: 1) 마이그레이션 적용(없으면 DB 파일 생성)  2) 서버 실행
set -euo pipefail

cd "$(dirname "$0")"

# .env가 있으면 읽어서 환경변수로 내보낸다 (set -a: 이후 대입을 자동 export)
# Docker Compose도 같은 .env를 자동으로 읽으므로 로컬/도커 설정이 한 파일로 통일된다.
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
  echo "▶ .env 로드"
fi

PORT="${1:-8000}"
HOST="${2:-0.0.0.0}"

echo "▶ 마이그레이션 적용..."
.venv/bin/alembic upgrade head

if [ -n "${JWT_SECRET:-}" ]; then
  echo "▶ JWT 서명키: 환경변수 사용"
else
  echo "▶ JWT 서명키: 미설정 — 임시 키 생성 (재시작하면 전원 로그아웃)"
fi

if [ -n "${REGISTER_CODE:-}" ]; then
  echo "▶ 회원가입: 초대 코드 필요"
else
  echo "▶ 회원가입: 개방 (누구나 가입 가능 — 외부 공개 시 REGISTER_CODE 설정 권장)"
fi

echo "▶ 서버 시작 → http://${HOST}:${PORT}"
exec .venv/bin/python -m uvicorn main:app --host "$HOST" --port "$PORT"
