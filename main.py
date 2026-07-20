import base64
import os
import secrets
from datetime import date as date_type
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Todo
from schemas import TodoCreate, TodoRead, TodoUpdate

app = FastAPI(title="TODO API")

# HTTP Basic 인증: 두 환경변수가 모두 설정된 경우에만 활성화된다.
# (로컬 개발은 env 없이 그대로, 외부 공개 시에만 켜서 씀. 비밀번호는 코드에 두지 않음)
BASIC_AUTH_USER = os.getenv("BASIC_AUTH_USER")
BASIC_AUTH_PASS = os.getenv("BASIC_AUTH_PASS")


@app.middleware("http")
async def basic_auth(request, call_next):
    if BASIC_AUTH_USER and BASIC_AUTH_PASS:
        ok = False
        header = request.headers.get("Authorization", "")
        if header.startswith("Basic "):
            try:
                user, _, pw = base64.b64decode(header[6:]).decode("utf-8").partition(":")
                # 타이밍 공격 방지를 위해 compare_digest 사용
                ok = secrets.compare_digest(user, BASIC_AUTH_USER) and secrets.compare_digest(
                    pw, BASIC_AUTH_PASS
                )
            except Exception:
                ok = False
        if not ok:
            return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="TODO"'})
    return await call_next(request)


# --- 엔드포인트 ---
@app.post("/todos", response_model=TodoRead, status_code=201)
def create_todo(body: TodoCreate, db: Session = Depends(get_db)):
    """할 일 추가: 날짜 + 내용으로 등록"""
    todo = Todo(date=body.date, content=body.content)
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo


@app.patch("/todos/{todo_id}", response_model=TodoRead)
def update_todo(todo_id: int, body: TodoUpdate, db: Session = Depends(get_db)):
    """할 일 수정 (부분 수정): 보낸 필드만 변경 — content, date 각각/함께 가능"""
    todo = db.get(Todo, todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    data = body.model_dump(exclude_unset=True)  # 실제로 보낸 필드만
    if "content" in data:
        todo.content = data["content"]
    if "date" in data:
        todo.date = data["date"]
    if "memo" in data:
        todo.memo = data["memo"]
    db.commit()
    db.refresh(todo)
    return todo


@app.patch("/todos/{todo_id}/done", response_model=TodoRead)
def mark_done(todo_id: int, db: Session = Depends(get_db)):
    """완료 표시: 특정 할 일을 '했다' 처리"""
    todo = db.get(Todo, todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    todo.done = True
    db.commit()
    db.refresh(todo)
    return todo


@app.patch("/todos/{todo_id}/undone", response_model=TodoRead)
def mark_undone(todo_id: int, db: Session = Depends(get_db)):
    """완료 취소: 완료 처리한 할 일을 다시 '안 함' 상태로 되돌림"""
    todo = db.get(Todo, todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    todo.done = False
    db.commit()
    db.refresh(todo)
    return todo


@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    """할 일 삭제: 완료/미완료 상관없이 DB에서 row를 제거"""
    todo = db.get(Todo, todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    db.delete(todo)
    db.commit()


@app.get("/todos", response_model=list[TodoRead])
def list_todos(
    date: Optional[date_type] = Query(None, description="특정 날짜 조회 (YYYY-MM-DD)"),
    start: Optional[date_type] = Query(None, description="기간 시작일(포함, YYYY-MM-DD)"),
    end: Optional[date_type] = Query(None, description="기간 종료일(포함, YYYY-MM-DD)"),
    done: Optional[bool] = Query(None, description="완료 여부 필터 (true/false)"),
    q: Optional[str] = Query(None, description="할 일 내용 검색어 (content LIKE %q%)"),
    db: Session = Depends(get_db),
):
    """전체/날짜별/기간별/완료여부/검색 조회

    - GET /todos                                   → 전체 조회
    - GET /todos?date=2026-06-12                   → 특정 날짜
    - GET /todos?start=2026-06-16&end=2026-06-22   → 기간 조회(양끝 포함)
    - GET /todos?q=회의                             → 내용에 '회의' 포함
    - GET /todos?start=2026-06-01&end=2026-06-30&q=회의 → 기간 + 검색어
    - GET /todos?done=false                        → 전체 미완료
    """
    stmt = select(Todo)
    if date is not None:
        stmt = stmt.where(Todo.date == date)
    if start is not None:
        stmt = stmt.where(Todo.date >= start)
    if end is not None:
        stmt = stmt.where(Todo.date <= end)
    if done is not None:
        stmt = stmt.where(Todo.done == done)
    if q:
        stmt = stmt.where(Todo.content.ilike(f"%{q}%"))  # 대소문자 무시 부분일치
    stmt = stmt.order_by(Todo.date, Todo.id)
    return db.execute(stmt).scalars().all()


# 프론트엔드 서빙 (API 라우트가 우선 매칭되고, 나머지는 static/으로)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
