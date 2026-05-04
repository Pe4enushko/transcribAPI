"""Unit tests for src/auth.py — no DB, no HTTP."""
import time
import pytest
import jwt as pyjwt

from src.auth import (
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_refresh_token,
    rotate_refresh_token,
    refresh_token_store,
)
from src.config import JWT_SECRET, JWT_ALGORITHM


@pytest.fixture(autouse=True)
def clear_store():
    """Wipe the in-memory refresh token store before every test."""
    refresh_token_store.clear()
    yield
    refresh_token_store.clear()


# ---------------------------------------------------------------------------
# create_access_token
# ---------------------------------------------------------------------------

class TestCreateAccessToken:
    def test_returns_decodable_jwt(self):
        token = create_access_token({"sub": "alice"})
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["sub"] == "alice"

    def test_type_is_access(self):
        token = create_access_token({"sub": "alice"})
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["type"] == "access"

    def test_has_jti(self):
        token = create_access_token({"sub": "alice"})
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert "jti" in payload and len(payload["jti"]) == 32

    def test_two_tokens_have_different_jti(self):
        t1 = create_access_token({"sub": "alice"})
        t2 = create_access_token({"sub": "alice"})
        p1 = pyjwt.decode(t1, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        p2 = pyjwt.decode(t2, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert p1["jti"] != p2["jti"]

    def test_extra_claims_preserved(self):
        token = create_access_token({"sub": "alice", "role": "admin"})
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["role"] == "admin"


# ---------------------------------------------------------------------------
# create_refresh_token
# ---------------------------------------------------------------------------

class TestCreateRefreshToken:
    def test_stored_in_store(self):
        token = create_refresh_token("alice")
        assert token in refresh_token_store

    def test_stored_entry_has_correct_sub(self):
        token = create_refresh_token("alice")
        assert refresh_token_store[token]["sub"] == "alice"

    def test_type_is_refresh(self):
        token = create_refresh_token("alice")
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["type"] == "refresh"

    def test_two_tokens_are_unique(self):
        t1 = create_refresh_token("alice")
        t2 = create_refresh_token("alice")
        assert t1 != t2


# ---------------------------------------------------------------------------
# verify_token
# ---------------------------------------------------------------------------

class TestVerifyToken:
    def test_valid_access_token(self):
        token = create_access_token({"sub": "alice"})
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "alice"

    def test_wrong_type_returns_none(self):
        token = create_refresh_token("alice")
        assert verify_token(token, expected_type="access") is None

    def test_correct_refresh_type(self):
        token = create_refresh_token("alice")
        payload = verify_token(token, expected_type="refresh")
        assert payload is not None

    def test_garbage_token_returns_none(self):
        assert verify_token("not.a.token") is None

    def test_tampered_signature_returns_none(self):
        token = create_access_token({"sub": "alice"})
        tampered = token[:-4] + "xxxx"
        assert verify_token(tampered) is None

    def test_expired_token_returns_none(self):
        from datetime import datetime, timedelta, timezone
        payload = {
            "sub": "alice",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
            "type": "access",
            "jti": "abc",
        }
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        assert verify_token(token) is None


# ---------------------------------------------------------------------------
# verify_refresh_token
# ---------------------------------------------------------------------------

class TestVerifyRefreshToken:
    def test_valid_refresh_token(self):
        token = create_refresh_token("alice")
        payload = verify_refresh_token(token)
        assert payload is not None
        assert payload["sub"] == "alice"

    def test_not_in_store_returns_none(self):
        token = create_refresh_token("alice")
        refresh_token_store.clear()
        assert verify_refresh_token(token) is None

    def test_access_token_rejected(self):
        token = create_access_token({"sub": "alice"})
        assert verify_refresh_token(token) is None

    def test_tampered_token_removed_from_store(self):
        token = create_refresh_token("alice")
        tampered = token[:-4] + "xxxx"
        verify_refresh_token(tampered)
        assert tampered not in refresh_token_store


# ---------------------------------------------------------------------------
# rotate_refresh_token
# ---------------------------------------------------------------------------

class TestRotateRefreshToken:
    def test_returns_new_token_pair(self):
        token = create_refresh_token("alice")
        result = rotate_refresh_token(token)
        assert result is not None
        new_access, new_refresh = result
        assert isinstance(new_access, str)
        assert isinstance(new_refresh, str)

    def test_old_token_consumed(self):
        token = create_refresh_token("alice")
        rotate_refresh_token(token)
        assert token not in refresh_token_store

    def test_new_refresh_token_stored(self):
        token = create_refresh_token("alice")
        _, new_refresh = rotate_refresh_token(token)
        assert new_refresh in refresh_token_store

    def test_new_access_token_is_valid(self):
        token = create_refresh_token("alice")
        new_access, _ = rotate_refresh_token(token)
        payload = verify_token(new_access)
        assert payload is not None
        assert payload["sub"] == "alice"

    def test_cannot_reuse_consumed_token(self):
        token = create_refresh_token("alice")
        rotate_refresh_token(token)
        assert rotate_refresh_token(token) is None

    def test_invalid_token_returns_none(self):
        assert rotate_refresh_token("invalid.token.here") is None
