#!/usr/bin/env bash
# .venv의 파이썬으로 query_db.py 실행 (로컬 ./todo.db 조회)
# 사용법: ./query.sh
#   다른 DB를 보고 싶으면 환경변수로: TODO_DB=/경로/다른.db ./query.sh
#   특정 사용자의 할 일만 보려면:  TODO_USER=me@example.com ./query.sh
set -euo pipefail

cd "$(dirname "$0")"

# 호출 시 TODO_DB를 안 주면 이 폴더의 todo.db를 기본 사용
export TODO_DB="${TODO_DB:-./todo.db}"

exec .venv/bin/python query_db.py
