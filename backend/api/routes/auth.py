from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, field_validator

from services.auth import AuthToken, EmailCodeStore, JwtService, UserIdentity
from settings import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
code_store = EmailCodeStore()


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
    return SendCodeResponse(sent=True, dev_code=code if settings.app_env == "development" else None)


@router.post("/verify", response_model=AuthToken)
async def verify_code(request: VerifyCodeRequest) -> AuthToken:
    settings = get_settings()
    if not code_store.verify_code(str(request.email), request.code):
        raise HTTPException(status_code=401, detail="invalid verification code")
    if not settings.jwt_secret:
        raise HTTPException(status_code=500, detail="JWT_SECRET is not configured")
    token = JwtService(settings.jwt_secret).issue(str(request.email))
    return AuthToken(access_token=token)


@router.get("/me", response_model=UserIdentity)
async def me(authorization: str | None = Header(default=None)) -> UserIdentity:
    settings = get_settings()
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    if not settings.jwt_secret:
        raise HTTPException(status_code=500, detail="JWT_SECRET is not configured")
    try:
        return JwtService(settings.jwt_secret).verify(authorization.split(" ", 1)[1])
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
