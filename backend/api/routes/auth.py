import smtplib

from fastapi import APIRouter, Cookie, Header, HTTPException, Response
from pydantic import BaseModel, field_validator

from services.auth import (
    AuthToken,
    EmailCodeStore,
    EmailDeliveryError,
    JwtService,
    SmtpEmailSender,
    UserIdentity,
)
from settings import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
code_store = EmailCodeStore()
SESSION_COOKIE_NAME = "strata_session"


class SendCodeRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("invalid email")
        return value.lower()


class SendCodeResponse(BaseModel):
    sent: bool
    dev_code: str | None = None


class VerifyCodeRequest(BaseModel):
    email: str
    code: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("invalid email")
        return value.lower()


@router.post("/send-code", response_model=SendCodeResponse)
async def send_code(request: SendCodeRequest) -> SendCodeResponse:
    settings = get_settings()
    code = code_store.issue_code(str(request.email))
    if settings.app_env == "development":
        return SendCodeResponse(sent=True, dev_code=code)
    try:
        SmtpEmailSender(settings).send_verification_code(str(request.email), code)
    except EmailDeliveryError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (OSError, smtplib.SMTPException) as exc:
        raise HTTPException(status_code=502, detail="failed to send verification email") from exc
    return SendCodeResponse(sent=True)


@router.post("/verify", response_model=AuthToken)
async def verify_code(request: VerifyCodeRequest, response: Response) -> AuthToken:
    settings = get_settings()
    if not code_store.verify_code(str(request.email), request.code):
        raise HTTPException(status_code=401, detail="invalid verification code")
    if not settings.jwt_secret:
        raise HTTPException(status_code=500, detail="JWT_SECRET is not configured")
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


@router.get("/me", response_model=UserIdentity)
async def me(
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> UserIdentity:
    settings = get_settings()
    token = session_token
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="missing bearer token")
    if not settings.jwt_secret:
        raise HTTPException(status_code=500, detail="JWT_SECRET is not configured")
    try:
        return JwtService(settings.jwt_secret).verify(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


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
