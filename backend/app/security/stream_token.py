from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import uuid

from jose import jwt, JWTError

from app.core.config import settings
from app.utils.redis_client import get_redis


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stream_secret() -> str:
    # fallback to main jwt secret if specific stream secret isn't set
    return settings.security.stream_token_secret or (settings.security.jwt_secret_key or "change-me")


async def mint_stream_token(camera_id: str, user_id: Optional[str] = None,
                            expires_in: Optional[int] = None) -> Tuple[str, str, datetime]:
    """
    Create a short-lived signed token for HLS access.
    Returns tuple of (token, jti, exp_dt)
    """
    jti = str(uuid.uuid4())
    exp_seconds = int(expires_in or settings.security.stream_token_expire_seconds)
    exp_dt = _now() + timedelta(seconds=exp_seconds)
    payload = {
        "sub": "stream",
        "cid": camera_id,
        "uid": user_id,
        "jti": jti,
        "exp": int(exp_dt.timestamp()),
        "iat": int(_now().timestamp()),
        "typ": "hls",
    }
    token = jwt.encode(payload, _stream_secret(), algorithm=settings.security.stream_token_algorithm)

    # store jti in Redis for allow-list while valid
    redis = get_redis()
    await redis.set(f"stream:token:{jti}", camera_id, ex=exp_seconds)

    return token, jti, exp_dt


async def validate_stream_token(token: str) -> dict:
    """
    Validate token signature, expiry, and jti presence in Redis.
    Returns decoded payload on success, else raises ValueError.
    """
    try:
        payload = jwt.decode(token, _stream_secret(), algorithms=[settings.security.stream_token_algorithm])
    except JWTError as e:
        raise ValueError("invalid_token") from e

    jti = payload.get("jti")
    cid = payload.get("cid")
    if not jti or not cid:
        raise ValueError("invalid_claims")

    redis = get_redis()
    val = await redis.get(f"stream:token:{jti}")
    if val != cid:
        # jti not present or mismatched -> expired or revoked
        raise ValueError("token_revoked_or_expired")
    return payload


async def revoke_stream_token(jti: str):
    redis = get_redis()
    await redis.delete(f"stream:token:{jti}")
