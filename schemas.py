from datetime import date as date_type
from typing import Annotated, Optional

from fastapi_users import schemas as fu_schemas
from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

# 앞뒤 공백 제거 후 1자 이상 — "   " 같은 공백만 있는 내용은 422로 거부
ContentStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class TodoCreate(BaseModel):
    date: date_type = Field(..., description="할 일 날짜 (YYYY-MM-DD)")
    content: ContentStr = Field(..., description="할 일 내용")


class TodoUpdate(BaseModel):
    # 부분 수정: 보낸 필드만 변경 (content / date / memo 각각·함께 가능)
    content: Optional[ContentStr] = Field(None, description="수정할 할 일 내용")
    date: Optional[date_type] = Field(None, description="수정할 날짜 (YYYY-MM-DD)")
    # memo는 빈 문자열("")로 지우기가 가능해야 하므로 공백 제약을 두지 않음
    memo: Optional[str] = Field(None, description="할 일 메모 (빈 문자열이면 메모 삭제)")

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
    memo: Optional[str] = None


# --- 사용자(인증) 스키마 ---
class UserRead(fu_schemas.BaseUser[int]):
    """응답용 사용자 정보 (비밀번호 해시는 절대 포함되지 않음)"""


class UserCreate(fu_schemas.BaseUserCreate):
    """fastapi-users가 사용자 생성 시 받는 스키마 (email + password)"""


class UserUpdate(fu_schemas.BaseUserUpdate):
    """본인 정보 수정용 (이메일/비밀번호 변경)"""


class RegisterRequest(BaseModel):
    """회원가입 요청 — 초대 코드가 설정된 서버에서는 code가 필수"""

    email: EmailStr = Field(..., description="로그인에 쓸 이메일")
    password: str = Field(..., description="비밀번호 (8자 이상)")
    code: Optional[str] = Field(None, description="초대 코드 (REGISTER_CODE 설정 시 필수)")
