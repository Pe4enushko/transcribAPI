import jwt
from datetime import datetime, timedelta, timezone
import secrets
from typing import Optional
from src.config import (
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRATION_HOURS,
    JWT_REFRESH_EXPIRATION_HOURS,
)


# In-memory refresh token store: {refresh_token: {"sub": str, "exp": datetime}}
refresh_token_store = {}


def create_access_token(data: dict) -> str:
    """Generate a JWT token with the provided data."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire, "type": "access", "jti": secrets.token_hex(16)})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: str) -> str:
    """Generate and store a refresh token for a user subject."""
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_REFRESH_EXPIRATION_HOURS)
    payload = {
        "sub": subject,
        "exp": expire,
        "type": "refresh",
        "jti": secrets.token_hex(16),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    refresh_token_store[token] = {"sub": subject, "exp": expire}
    return token


def verify_token(token: str, expected_type: str = "access") -> Optional[dict]:
    """Verify and decode a JWT token. Returns payload if valid and type matches."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def verify_refresh_token(token: str) -> Optional[dict]:
    """Validate a refresh token against JWT signature/expiry and in-memory store."""
    payload = verify_token(token, expected_type="refresh")
    if payload is None:
        refresh_token_store.pop(token, None)
        return None

    stored = refresh_token_store.get(token)
    if stored is None:
        return None

    if stored.get("exp") < datetime.now(timezone.utc):
        refresh_token_store.pop(token, None)
        return None

    if stored.get("sub") != payload.get("sub"):
        refresh_token_store.pop(token, None)
        return None

    return payload


def rotate_refresh_token(token: str) -> Optional[tuple[str, str]]:
    """Consume a refresh token and return a new access/refresh token pair."""
    payload = verify_refresh_token(token)
    if payload is None:
        return None

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        refresh_token_store.pop(token, None)
        return None

    refresh_token_store.pop(token, None)
    new_access_token = create_access_token({"sub": subject})
    new_refresh_token = create_refresh_token(subject)
    return new_access_token, new_refresh_token
