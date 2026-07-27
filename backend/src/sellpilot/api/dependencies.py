from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.config import Settings, get_settings
from sellpilot.core.exceptions import UnauthenticatedError
from sellpilot.core.security import decode_access_token
from sellpilot.db.models.user import User
from sellpilot.db.session import get_db_session
from sellpilot.repositories.user import UserRepository

SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: SessionDependency,
    settings: SettingsDependency,
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthenticatedError()
    payload = decode_access_token(credentials.credentials, settings)
    try:
        user_id = UUID(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise UnauthenticatedError("Invalid access token subject") from exc

    user = await UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise UnauthenticatedError("User is unavailable or disabled")
    return user


CurrentUserDependency = Annotated[User, Depends(get_current_user)]
