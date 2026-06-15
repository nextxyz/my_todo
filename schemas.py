from datetime import date as date_type

from pydantic import BaseModel, ConfigDict, Field


class TodoCreate(BaseModel):
    date: date_type = Field(..., description="할 일 날짜 (YYYY-MM-DD)")
    content: str = Field(..., min_length=1, description="할 일 내용")


class TodoUpdate(BaseModel):
    content: str = Field(..., min_length=1, description="수정할 할 일 내용")


class TodoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date_type
    content: str
    done: bool
