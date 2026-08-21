#!/usr/bin/env python
"""소유자 없는 기존 할 일을 특정 사용자에게 일괄 귀속시킨다.

인증을 도입하기 전에 쌓인 todos는 user_id가 NULL이어서 어떤 사용자에게도
조회되지 않는다. 먼저 회원가입을 한 뒤 그 이메일을 지정해 실행하면 된다.

  ./.venv/bin/python backfill_owner.py --email me@example.com --dry-run
  ./.venv/bin/python backfill_owner.py --email me@example.com
"""

import argparse
import sys

from sqlalchemy import create_engine, func, select, update
from sqlalchemy.orm import Session

from database import DATABASE_URL  # 동기 URL (Alembic과 동일)
from models import Todo, User


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="귀속시킬 사용자 이메일")
    parser.add_argument(
        "--dry-run", action="store_true", help="실제로 바꾸지 않고 건수만 확인"
    )
    args = parser.parse_args()

    engine = create_engine(DATABASE_URL, future=True)
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.email == args.email))
        if user is None:
            print(f"✗ 사용자를 찾을 수 없습니다: {args.email}", file=sys.stderr)
            print("  먼저 /auth/register 로 회원가입하세요.", file=sys.stderr)
            return 1

        orphans = db.scalar(
            select(func.count()).select_from(Todo).where(Todo.user_id.is_(None))
        )
        if not orphans:
            print("소유자 없는 할 일이 없습니다. 할 일이 없네요.")
            return 0

        if args.dry_run:
            print(f"[dry-run] {orphans}건을 {user.email}(id={user.id})에게 귀속시킵니다.")
            return 0

        db.execute(update(Todo).where(Todo.user_id.is_(None)).values(user_id=user.id))
        db.commit()
        print(f"✔ {orphans}건을 {user.email}(id={user.id})에게 귀속시켰습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
