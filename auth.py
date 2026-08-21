import os
import secrets
from collections.abc import AsyncGenerator
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, IntegerIDMixin, InvalidPasswordException
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from schemas import UserCreate

# JWT 서명 키. 운영에서는 반드시 설정할 것 — 없으면 프로세스마다 새 키를 만들어
# 서버를 재시작하는 순간 발급된 토큰이 전부 무효가 된다(= 전원 로그아웃).
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    JWT_SECRET = secrets.token_urlsafe(32)
    print("⚠ JWT_SECRET 미설정 — 임시 키 생성 (재시작하면 전원 로그아웃됩니다)")

JWT_LIFETIME_SECONDS = 60 * 60 * 24 * 7  # 7일

# 회원가입 초대 코드. 설정되어 있으면 /auth/register에서 일치해야 가입할 수 있다.
# 미설정이면 누구나 가입 가능 — 로컬 개발용이며 외부 공개 시에는 반드시 설정할 것.
REGISTER_CODE = os.getenv("REGISTER_CODE")

MIN_PASSWORD_LENGTH = 8


async def get_user_db(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[SQLAlchemyUserDatabase, None]:
    yield SQLAlchemyUserDatabase(db, User)


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    reset_password_token_secret = JWT_SECRET
    verification_token_secret = JWT_SECRET

    async def validate_password(self, password: str, user: UserCreate | User) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise InvalidPasswordException(
                f"비밀번호는 최소 {MIN_PASSWORD_LENGTH}자 이상이어야 합니다"
            )
        if user.email.lower() in password.lower():
            raise InvalidPasswordException("비밀번호에 이메일을 포함할 수 없습니다")

    async def on_after_register(self, user: User, request: Optional[Request] = None) -> None:
        print(f"▶ 회원가입: {user.email} (id={user.id})")


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db)


# 쿠키가 아닌 Bearer 토큰으로 자격증명을 주고받는다.
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=JWT_SECRET, lifetime_seconds=JWT_LIFETIME_SECONDS)


auth_backend = AuthenticationBackend(
    name="jwt", transport=bearer_transport, get_strategy=get_jwt_strategy
)

fastapi_users = FastAPIUsers[User, int](get_user_manager, [auth_backend])

# 모든 todo 엔드포인트가 쓰는 의존성: 유효한 JWT + 활성 사용자만 통과
current_active_user = fastapi_users.current_user(active=True)
