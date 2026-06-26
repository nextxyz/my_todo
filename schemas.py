from datetime import date as date_type
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TodoCreate(BaseModel):
    date: date_type = Field(..., description="할 일 날짜 (YYYY-MM-DD)")
    content: str = Field(..., min_length=1, description="할 일 내용")


class TodoUpdate(BaseModel):
    # 부분 수정: 보낸 필드만 변경 (content만, date만, 둘 다 모두 가능)
    content: Optional[str] = Field(None, min_length=1, description="수정할 할 일 내용")
    date: Optional[date_type] = Field(None, description="수정할 날짜 (YYYY-MM-DD)")


class TodoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date_type
    content: str
    done: bool
