import secrets
from datetime import date as date_type
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi_users import exceptions as fu_exceptions
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import (
    REGISTER_CODE,
    UserManager,
    auth_backend,
    current_active_user,
    fastapi_users,
    get_user_manager,
)
from database import get_db
from models import Todo, User
from schemas import (
    RegisterRequest,
    TodoCreate,
    TodoRead,
    TodoUpdate,
    UserCreate,
    UserRead,
    UserUpdate,
)

app = FastAPI(title="TODO API")


# --- 인증 라우터 ---
# 로그인: POST /auth/jwt/login (form: username=이메일, password=...) → access_token
# 로그아웃: POST /auth/jwt/logout  |  본인 정보: GET/PATCH /users/me
app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"])
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"])


@app.post("/auth/register", response_model=UserRead, status_code=201, tags=["auth"])
async def register(
    body: RegisterRequest,
    user_manager: UserManager = Depends(get_user_manager),
):
    """회원가입.

    fastapi-users의 기본 register 라우터 대신 직접 만든 이유는 초대 코드 검사 때문이다.
    REGISTER_CODE 환경변수가 설정된 서버에서는 코드가 일치해야 가입할 수 있다.
    """
    if REGISTER_CODE:
        # 타이밍 공격 방지를 위해 compare_digest 사용.
        # str끼리 비교하면 비ASCII 문자(한글 등)에서 TypeError가 나므로 바이트로 변환한다.
        if not secrets.compare_digest(
            (body.code or "").encode("utf-8"), REGISTER_CODE.encode("utf-8")
        ):
            raise HTTPException(status_code=403, detail="초대 코드가 올바르지 않습니다")

    try:
        return await user_manager.create(
            UserCreate(email=body.email, password=body.password), safe=True
        )
    except fu_exceptions.UserAlreadyExists:
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다")
    except fu_exceptions.InvalidPasswordException as e:
        raise HTTPException(status_code=400, detail=str(e.reason))


@app.get("/auth/config", tags=["auth"])
async def auth_config():
    """프론트엔드가 회원가입 화면에 초대 코드 입력란을 띄울지 판단하는 용도.
    코드 값 자체는 절대 내려보내지 않는다."""
    return {"register_code_required": bool(REGISTER_CODE)}


# --- 내부 헬퍼 ---
async def get_owned_todo(db: AsyncSession, todo_id: int, user: User) -> Todo:
    """본인 소유의 할 일을 가져온다.

    남의 id를 찔러봐도 403이 아니라 404를 주는 이유: 403은 "그 id는 존재하지만
    네 것이 아니다"를 알려주는 정보 노출이므로, 존재 여부 자체를 감춘다.
    """
    todo = await db.get(Todo, todo_id)
    if todo is None or todo.user_id != user.id:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


# --- 엔드포인트 ---
@app.post("/todos", response_model=TodoRead, status_code=201)
async def create_todo(
    body: TodoCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """할 일 추가: 날짜 + 내용으로 등록 (로그인한 사용자 소유로 저장)"""
    todo = Todo(date=body.date, content=body.content, user_id=user.id)
    db.add(todo)
    await db.commit()
    await db.refresh(todo)
    return todo


@app.patch("/todos/{todo_id}", response_model=TodoRead)
async def update_todo(
    todo_id: int,
    body: TodoUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """할 일 수정 (부분 수정): 보낸 필드만 변경 — content, date 각각/함께 가능"""
    todo = await get_owned_todo(db, todo_id, user)
    data = body.model_dump(exclude_unset=True)  # 실제로 보낸 필드만
    if "content" in data:
        todo.content = data["content"]
    if "date" in data:
        todo.date = data["date"]
    if "memo" in data:
        todo.memo = data["memo"]
    await db.commit()
    await db.refresh(todo)
    return todo


@app.patch("/todos/{todo_id}/done", response_model=TodoRead)
async def mark_done(
    todo_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """완료 표시: 특정 할 일을 '했다' 처리"""
    todo = await get_owned_todo(db, todo_id, user)
    todo.done = True
    await db.commit()
    await db.refresh(todo)
    return todo


@app.patch("/todos/{todo_id}/undone", response_model=TodoRead)
async def mark_undone(
    todo_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """완료 취소: 완료 처리한 할 일을 다시 '안 함' 상태로 되돌림"""
    todo = await get_owned_todo(db, todo_id, user)
    todo.done = False
    await db.commit()
    await db.refresh(todo)
    return todo


@app.delete("/todos/{todo_id}", status_code=204)
async def delete_todo(
    todo_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """할 일 삭제: 완료/미완료 상관없이 DB에서 row를 제거"""
    todo = await get_owned_todo(db, todo_id, user)
    await db.delete(todo)
    await db.commit()


@app.get("/todos", response_model=list[TodoRead])
async def list_todos(
    date: Optional[date_type] = Query(None, description="특정 날짜 조회 (YYYY-MM-DD)"),
    start: Optional[date_type] = Query(None, description="기간 시작일(포함, YYYY-MM-DD)"),
    end: Optional[date_type] = Query(None, description="기간 종료일(포함, YYYY-MM-DD)"),
    done: Optional[bool] = Query(None, description="완료 여부 필터 (true/false)"),
    q: Optional[str] = Query(None, description="할 일 내용 검색어 (content LIKE %q%)"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """전체/날짜별/기간별/완료여부/검색 조회 (항상 본인 데이터만)

    - GET /todos                                   → 전체 조회
    - GET /todos?date=2026-06-12                   → 특정 날짜
    - GET /todos?start=2026-06-16&end=2026-06-22   → 기간 조회(양끝 포함)
    - GET /todos?q=회의                             → 내용에 '회의' 포함
    - GET /todos?start=2026-06-01&end=2026-06-30&q=회의 → 기간 + 검색어
    - GET /todos?done=false                        → 전체 미완료
    """
    stmt = select(Todo).where(Todo.user_id == user.id)  # 사용자 격리 (항상 적용)
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
    result = await db.execute(stmt)
    return result.scalars().all()


# 프론트엔드 서빙 (API 라우트가 우선 매칭되고, 나머지는 static/으로)
# 로그인 화면 자체는 인증 없이 받아야 하므로 정적 파일은 보호하지 않는다.
app.mount("/", StaticFiles(directory="static", html=True), name="static")
