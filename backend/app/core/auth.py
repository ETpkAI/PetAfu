from __future__ import annotations
from typing import Optional
from datetime import datetime, timedelta, timezone
import jwt
from app.core.config import get_settings

settings = get_settings()

ALGORITHM = settings.algorithm
SECRET = settings.secret_key
EXPIRE_MINUTES = settings.access_token_expire_minutes


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=EXPIRE_MINUTES)
    )
    payload = {"sub": subject, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
