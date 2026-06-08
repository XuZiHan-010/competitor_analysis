import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid5

from pydantic import BaseModel, field_validator

SESSION_COOKIE_NAME = "strata_session"
USER_NAMESPACE = UUID("6f3ee5d8-19d6-4a60-aef3-91c76b1b2f7c")


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserIdentity(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("invalid email")
        return value.lower()


def user_id_for_email(email: str) -> UUID:
    return uuid5(USER_NAMESPACE, email.strip().lower())


class JwtService:
    def __init__(self, secret: str) -> None:
        if not secret:
            raise ValueError("JWT_SECRET is required")
        self._secret = secret.encode("utf-8")

    def issue(self, email: str, expires_delta: timedelta = timedelta(hours=12)) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        now = datetime.now(UTC)
        payload = {
            "sub": email.lower(),
            "iat": int(now.timestamp()),
            "exp": int((now + expires_delta).timestamp()),
        }
        signing_input = ".".join([_b64_json(header), _b64_json(payload)])
        signature = _b64_bytes(
            hmac.new(self._secret, signing_input.encode("utf-8"), hashlib.sha256).digest()
        )
        return f"{signing_input}.{signature}"

    def verify(self, token: str) -> UserIdentity:
        try:
            header_b64, payload_b64, signature = token.split(".")
        except ValueError as exc:
            raise ValueError("invalid token") from exc
        signing_input = f"{header_b64}.{payload_b64}"
        expected = _b64_bytes(
            hmac.new(self._secret, signing_input.encode("utf-8"), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(expected, signature):
            raise ValueError("invalid token signature")
        payload = _from_b64_json(payload_b64)
        if int(payload.get("exp", 0)) < int(datetime.now(UTC).timestamp()):
            raise ValueError("token expired")
        return UserIdentity(email=payload["sub"])


def _b64_json(value: dict[str, Any]) -> str:
    return _b64_bytes(json.dumps(value, separators=(",", ":")).encode("utf-8"))


def _b64_bytes(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _from_b64_json(value: str) -> dict[str, Any]:
    padded = value + "=" * (-len(value) % 4)
    return json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
