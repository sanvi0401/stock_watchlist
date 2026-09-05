import base64
import hashlib
import hmac
import secrets
import struct
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.errors import AppError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
MAX_PASSWORD_BYTES = 72
TOTP_DIGITS = 6
TOTP_PERIOD = 30


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


def new_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _totp_secret_bytes(secret: str) -> bytes:
    padded = secret.upper().replace(" ", "") + "=" * ((8 - len(secret) % 8) % 8)
    return base64.b32decode(padded, casefold=True)


def totp_code(secret: str, timestamp: int | None = None) -> str:
    counter = int((timestamp if timestamp is not None else datetime.now(UTC).timestamp()) // TOTP_PERIOD)
    digest = hmac.new(_totp_secret_bytes(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(value % (10**TOTP_DIGITS)).zfill(TOTP_DIGITS)


def verify_totp(secret: str, code: str, timestamp: int | None = None) -> bool:
    normalized = "".join(ch for ch in code if ch.isdigit())
    if len(normalized) != TOTP_DIGITS:
        return False
    now = int(timestamp if timestamp is not None else datetime.now(UTC).timestamp())
    for offset in (-TOTP_PERIOD, 0, TOTP_PERIOD):
        if hmac.compare_digest(totp_code(secret, now + offset), normalized):
            return True
    return False


def _totp_fernet():
    from cryptography.fernet import Fernet

    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_totp_secret(secret: str) -> str:
    return _totp_fernet().encrypt(secret.encode("utf-8")).decode("ascii")


def decrypt_totp_secret(encrypted: str) -> str:
    return _totp_fernet().decrypt(encrypted.encode("ascii")).decode("utf-8")


def totp_uri(secret: str, email: str) -> str:
    from urllib.parse import quote

    issuer = "Market Watch"
    label = f"{issuer}:{email}"
    return (
        f"otpauth://totp/{quote(label)}?secret={secret}"
        f"&issuer={quote(issuer)}&algorithm=SHA1&digits={TOTP_DIGITS}&period={TOTP_PERIOD}"
    )


def decode_token_payload(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload if isinstance(payload, dict) else None
    except JWTError:
        return None
