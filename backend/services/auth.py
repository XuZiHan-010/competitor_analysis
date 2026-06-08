import base64
import hashlib
import hmac
import json
import secrets
import smtplib
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from types import TracebackType
from typing import Any
from uuid import UUID, uuid5

from pydantic import BaseModel, field_validator

from settings import Settings

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


class EmailCodeStore:
    def __init__(self) -> None:
        self._codes: dict[str, tuple[str, datetime]] = {}

    def issue_code(self, email: str) -> str:
        code = f"{secrets.randbelow(1_000_000):06d}"
        self._codes[email.lower()] = (code, datetime.now(UTC) + timedelta(minutes=5))
        return code

    def verify_code(self, email: str, code: str) -> bool:
        stored = self._codes.get(email.lower())
        if stored is None:
            return False
        expected, expires_at = stored
        if expires_at < datetime.now(UTC):
            self._codes.pop(email.lower(), None)
            return False
        if not hmac.compare_digest(expected, code):
            return False
        self._codes.pop(email.lower(), None)
        return True


class EmailDeliveryError(RuntimeError):
    pass


class SmtpEmailSender:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send_verification_code(self, email: str, code: str) -> None:
        if not self._settings.smtp_host or not self._settings.smtp_from_email:
            raise EmailDeliveryError("SMTP_HOST and SMTP_FROM_EMAIL are required")

        message = EmailMessage()
        message["Subject"] = "竞品分析系统登录验证码"
        message["From"] = self._settings.smtp_from_email
        message["To"] = email
        message.set_content(
            f"你的登录验证码是：{code}\n\n"
            "验证码 5 分钟内有效。如果这不是你本人操作，请忽略这封邮件。"
        )

        client: smtplib.SMTP | smtplib.SMTP_SSL
        if self._settings.smtp_use_ssl:
            client = smtplib.SMTP_SSL(
                self._settings.smtp_host,
                self._settings.smtp_port,
                timeout=10,
            )
        else:
            client = smtplib.SMTP(
                self._settings.smtp_host,
                self._settings.smtp_port,
                timeout=10,
            )

        with _smtp_client(client) as smtp:
            if not self._settings.smtp_use_ssl and self._settings.smtp_starttls:
                smtp.starttls()
            if self._settings.smtp_username and self._settings.smtp_password:
                smtp.login(self._settings.smtp_username, self._settings.smtp_password)
            smtp.send_message(message)


class _smtp_client:
    def __init__(self, client: smtplib.SMTP | smtplib.SMTP_SSL) -> None:
        self._client = client

    def __enter__(self) -> smtplib.SMTP | smtplib.SMTP_SSL:
        return self._client

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        with suppress(OSError, smtplib.SMTPException):
            self._client.quit()


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
