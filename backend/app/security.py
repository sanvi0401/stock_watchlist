import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.errors import AppError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
MAX_PASSWORD_BYTES = 72


def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")


def validate_password_length(password: str) -> None:
    if len(_password_bytes(password)) > MAX_PASSWORD_BYTES:
        raise AppError(
            400,
            "password_too_long",
            f"Password must be at most {MAX_PASSWORD_BYTES} bytes. Shorten it — we do not truncate.",
        )


def hash_password(password: str) -> str:
    validate_password_length(password)
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if len(_password_bytes(password)) > MAX_PASSWORD_BYTES:
        return False
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, email: str | None = None, token_version: int = 0) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict = {"sub": subject, "exp": expire, "ver": int(token_version)}
    if email:
        payload["email"] = email.lower()
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def hash_reset_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_reset_token() -> str:
    return secrets.token_urlsafe(32)


def decode_token_payload(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload if isinstance(payload, dict) else None
    except JWTError:
        return None
