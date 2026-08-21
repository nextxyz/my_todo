import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# 동기 연결 문자열 — Alembic과 query_db.py가 쓴다 (환경변수로 덮어쓰기 가능)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./todo.db")


def _to_async_url(url: str) -> str:
    """동기 URL을 같은 DB를 가리키는 async 드라이버 URL로 바꾼다."""
    if "+" in url.split(":", 1)[0]:  # 이미 드라이버가 지정된 경우 그대로
        return url
    if url.startswith("sqlite:"):
        return url.replace("sqlite:", "sqlite+aiosqlite:", 1)
    if url.startswith("postgresql:"):
        return url.replace("postgresql:", "postgresql+asyncpg:", 1)
    return url


# 앱(FastAPI)은 async 드라이버로 같은 DB에 접속한다.
ASYNC_DATABASE_URL = _to_async_url(DATABASE_URL)

# SQLite는 쓰기 시 파일 락을 잡는다. 동시 요청이 겹쳐도 즉시 실패하지 않도록
# 락 대기 시간을 준다(timeout). check_same_thread=False는 aiosqlite가 별도
# 스레드에서 커넥션을 다루기 때문에 필요하다.
connect_args = (
    {"check_same_thread": False, "timeout": 15}
    if ASYNC_DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_async_engine(
    ASYNC_DATABASE_URL, pool_pre_ping=True, connect_args=connect_args
)

# expire_on_commit=False: commit 후에도 객체 속성이 만료되지 않는다.
# async에서는 만료된 속성 접근이 암묵적 IO를 일으켜 MissingGreenlet으로 터진다.
SessionLocal = async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 의존성: 요청마다 세션을 열고 끝나면 닫는다."""
    async with SessionLocal() as db:
        yield db
