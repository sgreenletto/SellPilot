from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.config import Settings
from sellpilot.core.exceptions import (
    DuplicateOperationError,
    ParameterError,
    UnauthenticatedError,
)
from sellpilot.core.security import create_access_token, hash_password, verify_password
from sellpilot.db.models.user import User
from sellpilot.repositories.user import UserRepository


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.users = UserRepository(session)
        self.settings = settings

    async def authenticate(self, username: str, password: str) -> tuple[User, str]:
        user = await self.users.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthenticatedError("Invalid username or password")
        if not user.is_active:
            raise UnauthenticatedError("User is disabled")
        token = create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            settings=self.settings,
        )
        return user, token

    async def change_password(self, user: User, old_password: str, new_password: str) -> User:
        if not verify_password(old_password, user.password_hash):
            raise ParameterError("Old password is incorrect")
        if old_password == new_password:
            raise ParameterError("New password must differ from the old password")
        user.password_hash = hash_password(new_password)
        return user

    async def create_admin(self, username: str, password: str) -> User:
        if await self.users.get_by_username(username):
            raise DuplicateOperationError(f"Username '{username}' already exists")
        user = User(username=username, password_hash=hash_password(password), role="ADMIN")
        return await self.users.add(user)

    async def get_user(self, user_id: UUID) -> User | None:
        return await self.users.get_by_id(user_id)
