from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException
from pydantic import BaseModel

from services.auth import SESSION_COOKIE_NAME, JwtService, user_id_for_email
from settings import get_settings


class CurrentUser(BaseModel):
    email: str
    user_id: UUID


def get_current_user(
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> CurrentUser:
    settings = get_settings()
    token = session_token
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="missing bearer token")
    if not settings.jwt_secret:
        raise HTTPException(status_code=500, detail="JWT_SECRET is not configured")
    try:
        identity = JwtService(settings.jwt_secret).verify(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return CurrentUser(email=identity.email, user_id=user_id_for_email(identity.email))


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
