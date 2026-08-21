from datetime import date as date_type
from typing import Optional

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable
from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class User(SQLAlchemyBaseUserTable[int], Base):
    """사용자 테이블.

    email / hashed_password / is_active / is_superuser / is_verified 는
    SQLAlchemyBaseUserTable이 제공하고, PK만 직접 선언한다(정수 ID).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # 소유자. 인증 도입 전 데이터에는 소유자가 없어 nullable이며,
    # 소유자 없는 행은 어떤 사용자에게도 조회되지 않는다(backfill_owner.py로 귀속).
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    content: Mapped[str] = mapped_column(String, nullable=False)
    done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 할 일 메모(선택)
