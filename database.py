import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# 연결 문자열은 환경변수로 덮어쓸 수 있음 (기본값은 프로젝트 폴더의 SQLite 파일)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./todo.db")

# SQLite는 기본적으로 한 스레드에서만 커넥션을 쓸 수 있어,
# FastAPI(여러 스레드)에서 쓰려면 check_same_thread=False가 필요하다.
connect_args = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(
    DATABASE_URL, future=True, pool_pre_ping=True, connect_args=connect_args
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 의존성: 요청마다 세션을 열고 끝나면 닫는다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
