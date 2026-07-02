from datetime import date as date_type
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

# 앞뒤 공백 제거 후 1자 이상 — "   " 같은 공백만 있는 내용은 422로 거부
ContentStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class TodoCreate(BaseModel):
    date: date_type = Field(..., description="할 일 날짜 (YYYY-MM-DD)")
    content: ContentStr = Field(..., description="할 일 내용")


class TodoUpdate(BaseModel):
    # 부분 수정: 보낸 필드만 변경 (content만, date만, 둘 다 모두 가능)
    content: Optional[ContentStr] = Field(None, description="수정할 할 일 내용")
    date: Optional[date_type] = Field(None, description="수정할 날짜 (YYYY-MM-DD)")

    @field_validator("content", "date", mode="before")
    @classmethod
    def reject_explicit_null(cls, v):
        # 기본값(미전송)에는 validator가 실행되지 않으므로,
        # 여기 None이 들어왔다는 건 클라이언트가 명시적으로 null을 보낸 것 → 422
        if v is None:
            raise ValueError("null은 허용되지 않습니다 — 변경하지 않을 필드는 생략하세요")
        return v


class TodoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date_type
    content: str
    done: bool
