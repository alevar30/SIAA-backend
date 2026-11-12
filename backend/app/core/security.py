from datetime import datetime, timedelta, timezone
import secrets
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > 72:
        raise ValueError("La contraseña supera el límite de 72 bytes de bcrypt")
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if len(plain_password.encode("utf-8")) > 72:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def generate_temporary_password(*, short: bool = False) -> str:
    return secrets.token_urlsafe(6 if short else 18)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    now = datetime.now(timezone.utc)
    lifetime = (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {**data, "iat": now, "exp": now + lifetime}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require_exp": True, "require_iat": True, "require_sub": True},
        )
    except JWTError:
        return None
