"""Integration tests for API endpoints — DB calls are mocked."""
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport

from src.auth import create_access_token, create_refresh_token, refresh_token_store
from src.main import app


@pytest.fixture(autouse=True)
def clear_store():
    refresh_token_store.clear()
    yield
    refresh_token_store.clear()


@pytest.fixture
def access_token():
    return create_access_token({"sub": "testuser"})


@pytest.fixture
def auth_headers(access_token):
    return {"Authorization": f"Bearer {access_token}"}


# Patch DB init so the app can start without a real database.
@pytest.fixture
async def client():
    with patch("src.main.init_connection_pool"), \
         patch("src.main.init_consult_connection_pool"), \
         patch("src.main.close_all_connections"):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

class TestHealth:
    async def test_returns_ok(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------

class TestLogin:
    async def test_valid_credentials(self, client):
        with patch("src.main.config") as cfg:
            cfg.LOGIN_USERNAME = "admin"
            cfg.LOGIN_PASSWORD = "secret"
            r = await client.post("/login", json={"username": "admin", "password": "secret"})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_wrong_password(self, client):
        with patch("src.main.config") as cfg:
            cfg.LOGIN_USERNAME = "admin"
            cfg.LOGIN_PASSWORD = "secret"
            r = await client.post("/login", json={"username": "admin", "password": "wrong"})
        assert r.status_code == 401

    async def test_wrong_username(self, client):
        with patch("src.main.config") as cfg:
            cfg.LOGIN_USERNAME = "admin"
            cfg.LOGIN_PASSWORD = "secret"
            r = await client.post("/login", json={"username": "hacker", "password": "secret"})
        assert r.status_code == 401

    async def test_missing_body(self, client):
        r = await client.post("/login", json={})
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /refresh
# ---------------------------------------------------------------------------

class TestRefresh:
    async def test_valid_refresh_token(self, client):
        token = create_refresh_token("alice")
        r = await client.post("/refresh", json={"refresh_token": token})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" in body

    async def test_consumed_token_rejected(self, client):
        token = create_refresh_token("alice")
        await client.post("/refresh", json={"refresh_token": token})
        r = await client.post("/refresh", json={"refresh_token": token})
        assert r.status_code == 401

    async def test_garbage_token_rejected(self, client):
        r = await client.post("/refresh", json={"refresh_token": "garbage"})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /query/{filename}
# ---------------------------------------------------------------------------

class TestQueryTranscription:
    async def test_requires_auth(self, client):
        r = await client.get("/query/file.mp3")
        assert r.status_code == 403

    async def test_found(self, client, auth_headers):
        record = {"filename": "file.mp3", "transcription": "hello", "dialogs": "[]"}
        with patch("src.main.get_record_by_filename", return_value=record):
            r = await client.get("/query/file.mp3", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["transcription"] == "hello"

    async def test_not_found(self, client, auth_headers):
        with patch("src.main.get_record_by_filename", return_value=None):
            r = await client.get("/query/missing.mp3", headers=auth_headers)
        assert r.status_code == 404

    async def test_db_error_returns_500(self, client, auth_headers):
        with patch("src.main.get_record_by_filename", side_effect=Exception("db down")):
            r = await client.get("/query/file.mp3", headers=auth_headers)
        assert r.status_code == 500

    async def test_invalid_token_rejected(self, client):
        r = await client.get("/query/file.mp3", headers={"Authorization": "Bearer bad.token"})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /consultdata
# ---------------------------------------------------------------------------

ORG_ID = str(uuid.uuid4())
CONV_ID = str(uuid.uuid4())
ROW_ID = str(uuid.uuid4())

FAKE_ROW = {
    "id": uuid.UUID(ROW_ID),
    "organization_id": uuid.UUID(ORG_ID),
    "conversation_id": uuid.UUID(CONV_ID),
    "created_at": datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
    "dialog": "Hello",
    "score_1_start_and_relevance": 4,
    "score_2_request_understanding_and_relevance": 3,
    "score_3_dialog_logic": 5,
    "score_4_objection_handling": None,
    "score_5_solution_promotion": 2,
    "score_6_cta_and_result_fixation": 4,
    "score_7_service_and_wording": 5,
    "score_8_niche_constraints": None,
    "score_9_result_and_risk": 3,
}


class TestConsultData:
    async def test_requires_auth(self, client):
        r = await client.get("/consultdata", params={"organization_id": ORG_ID, "date": "2024-01-15"})
        assert r.status_code == 403

    async def test_returns_records(self, client, auth_headers):
        with patch("src.main.get_consult_data_by_org_and_date", return_value=[FAKE_ROW]):
            r = await client.get(
                "/consultdata",
                params={"organization_id": ORG_ID, "date": "2024-01-15"},
                headers=auth_headers,
            )
        assert r.status_code == 200
        body = r.json()
        assert body["organization_id"] == ORG_ID
        assert body["date"] == "2024-01-15"
        assert len(body["records"]) == 1
        rec = body["records"][0]
        assert rec["dialog"] == "Hello"
        assert rec["score_1_start_and_relevance"] == 4
        assert rec["score_4_objection_handling"] is None

    async def test_empty_result(self, client, auth_headers):
        with patch("src.main.get_consult_data_by_org_and_date", return_value=[]):
            r = await client.get(
                "/consultdata",
                params={"organization_id": ORG_ID, "date": "2024-01-15"},
                headers=auth_headers,
            )
        assert r.status_code == 200
        assert r.json()["records"] == []

    async def test_db_error_returns_500(self, client, auth_headers):
        with patch("src.main.get_consult_data_by_org_and_date", side_effect=Exception("conn lost")):
            r = await client.get(
                "/consultdata",
                params={"organization_id": ORG_ID, "date": "2024-01-15"},
                headers=auth_headers,
            )
        assert r.status_code == 500

    async def test_missing_params(self, client, auth_headers):
        r = await client.get("/consultdata", headers=auth_headers)
        assert r.status_code == 422
