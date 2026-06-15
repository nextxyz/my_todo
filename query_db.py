"""todo.db를 순수 SQL로 직접 조회하는 샘플 (프론트/FastAPI 안 거침)

[중요] named volume 안의 DB(/data/todo.db)는 호스트에서 직접 못 연다.
macOS에서는 named volume이 Docker VM 내부에 있어 호스트 파이썬으로 접근 불가.
→ 컨테이너 안에서 실행해야 한다.

▶ 컨테이너(named volume) DB 조회 — 호스트 스크립트를 stdin으로 넘겨 실행:
    docker compose exec -T app python - < query_db.py
  (지금 컨테이너 이미지엔 이 파일이 없을 수 있어, 파일 복사 없이 stdin 방식이 안전)

▶ 로컬 작업디렉토리 ./todo.db 조회:
    TODO_DB=./todo.db .venv/bin/python query_db.py
"""
import os
import sqlite3

# 기본값은 컨테이너 안의 named volume 경로. 호스트에서 쓰려면 TODO_DB로 덮어쓴다.
DB_PATH = os.getenv("TODO_DB", "/data/todo.db")


def run(conn: sqlite3.Connection, title: str, sql: str, params: tuple = ()):
    """쿼리 하나를 실행하고 결과를 표 형태로 출력."""
    print(f"\n### {title}")
    print(f"SQL> {' '.join(sql.split())}  {params if params else ''}")
    rows = conn.execute(sql, params).fetchall()
    if not rows:
        print("  (결과 없음)")
        return
    cols = rows[0].keys()  # sqlite3.Row 덕분에 컬럼명 접근 가능
    print("  " + " | ".join(cols))
    print("  " + "-" * 50)
    for r in rows:
        print("  " + " | ".join(str(r[c]) for c in cols))


def main():
    print(f"(조회 대상 DB: {DB_PATH})")
    if not os.path.exists(DB_PATH):
        raise SystemExit(
            f"DB 파일이 없습니다: {DB_PATH}\n"
            "  - named volume DB라면 컨테이너 안에서 실행하세요: "
            "docker compose exec -T app python - < query_db.py\n"
            "  - 로컬 DB라면: TODO_DB=./todo.db .venv/bin/python query_db.py"
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 1) 전체 조회 (= select * 와 동일)
    run(conn, "전체 할 일", "SELECT id, date, content, done FROM todos ORDER BY id")

    # #2) 미완료만 (done = 0)
    # run(conn, "미완료만", "SELECT id, date, content FROM todos WHERE done = 0 ORDER BY date")

    # # 3) 특정 날짜 조회 (파라미터 바인딩 — SQL 인젝션 방지)
    # run(conn, "특정 날짜(2026-06-15) 할 일",
    #    "SELECT id, content, done FROM todos WHERE date = ?", ("2026-06-15",))

    # #4) 오늘 이전의 미완료(밀린 할 일)
    # run(conn, "밀린 할 일(오늘 이전 미완료)",
    #    "SELECT id, date, content FROM todos WHERE done = 0 AND date < date('now') ORDER BY date")

    # # 5) 날짜별 집계 (완료/미완료 개수)
    # run(conn, "날짜별 완료/미완료 개수",
    #     """SELECT date,
    #               SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END) AS done_cnt,
    #               SUM(CASE WHEN done = 0 THEN 1 ELSE 0 END) AS todo_cnt
    #        FROM todos GROUP BY date ORDER BY date""")

    conn.close()


if __name__ == "__main__":
    main()
