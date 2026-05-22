from datetime import datetime, timedelta
from typing import Optional

import bcrypt as _bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return _bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    """Hash a plain-text password with bcrypt."""
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.security.jwt_access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    secret = settings.security.jwt_secret_key or "changeme"
    encoded_jwt = jwt.encode(to_encode, secret, algorithm=settings.security.jwt_algorithm)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=7))
    to_encode.update({"exp": expire})
    secret = settings.security.jwt_secret_key or "changeme"
    encoded_jwt = jwt.encode(to_encode, secret, algorithm=settings.security.jwt_algorithm)
    return encoded_jwt


def decode_token(token: str) -> dict:
    try:
        secret = settings.security.jwt_secret_key or "changeme"
        payload = jwt.decode(token, secret, algorithms=[settings.security.jwt_algorithm])
        return payload
    except JWTError:
        return {}
