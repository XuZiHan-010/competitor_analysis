import asyncio
import threading

import structlog
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, field_validator

from api.auth_deps import CurrentUser, CurrentUserDep
from services.auth import (
    SESSION_COOKIE_NAME,
    AuthToken,
    JwtService,
)
from settings import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = structlog.get_logger(__name__)


def _schedule_user_upsert(email: str) -> None:
    """Fire-and-forget the best-effort user upsert on a detached thread.

    The DB write talks to a remote (Neon) Postgres whose cold-start connection
    takes seconds, and psycopg's connect handshake synchronously blocks the
    event loop it runs on. Running it inline — or via BackgroundTasks /
    create_task on the request loop — therefore stalls login until the DB
    responds. Spawning a daemon thread with its own event loop fully isolates
    the write so verify can return the JWT immediately.
    """

    def _run() -> None:
        try:
            asyncio.run(_upsert_user_best_effort(email))
        except Exception:
            logger.warning("user_upsert_thread_failed", exc_info=True)

    threading.Thread(target=_run, daemon=True, name="user-upsert").start()


class LoginRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("invalid email")
        return value.lower()


@router.post("/login", response_model=AuthToken)
async def login(request: LoginRequest, response: Response) -> AuthToken:
    settings = get_settings()
    if not settings.jwt_secret:
        raise HTTPException(status_code=500, detail="JWT_SECRET is not configured")
    # The users-table upsert is bookkeeping only — auth derives user_id from the
    # email (auth_deps.user_id_for_email), so it is not needed for login or
    # account isolation. Skip it in development, where the remote DB's cold-start
    # connection would otherwise dominate (and block) login latency.
    if settings.app_env != "development":
        _schedule_user_upsert(str(request.email))
    token = JwtService(settings.jwt_secret).issue(str(request.email))
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.app_env != "development",
        samesite="lax" if settings.app_env == "development" else "none",
        max_age=12 * 60 * 60,
        path="/",
    )
    return AuthToken(access_token=token)


@router.get("/me", response_model=CurrentUser)
async def me(current_user: CurrentUserDep) -> CurrentUser:
    return current_user


@router.post("/logout", status_code=204)
async def logout(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.app_env != "development",
        samesite="lax" if settings.app_env == "development" else "none",
    )


async def _upsert_user_best_effort(email: str) -> None:
    settings = get_settings()
    if not settings.database_url:
        return
    try:
        from db.persistence import SqlRunPersistence
        from db.session import create_engine, create_sessionmaker

        engine = create_engine()
        try:
            persistence = SqlRunPersistence(create_sessionmaker(engine))
            await persistence.upsert_user(email)
        finally:
            await engine.dispose()
    except Exception:
        logger.warning("user_upsert_failed_login_continues", exc_info=True)
