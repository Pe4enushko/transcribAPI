# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run the app** (from project root):
```bash
.venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

**Install dependencies:**
```bash
uv pip install --python .venv/bin/python -r requirements.txt
```

**Docker:**
```bash
docker build .
docker-compose up
```

**Manual testing scripts** (run from project root or any directory):
```bash
./scripts/test.sh        # Full workflow: login → refresh → query
./scripts/check.sh       # Quick login endpoint check (port 12121)
./scripts/checkrefresh.sh  # Refresh token test
```

There is no automated test framework; testing is done via shell scripts using curl.

## Architecture

This is a FastAPI REST API that authenticates clients with JWT and proxies queries to a PostgreSQL table of call transcriptions.

**Request flow:**
```
Client → CORS middleware → FastAPI endpoint → JWT verification → PostgreSQL query
```

**Key files:**
- [src/main.py](src/main.py) — 5 endpoints: `POST /login`, `POST /refresh`, `GET /query/{filename}`, `GET /health`, plus CORS config
- [src/auth.py](src/auth.py) — JWT lifecycle: `create_access_token()` (30 min), `create_refresh_token()` (24 hr, stored in-memory), `rotate_refresh_token()` (consumes old token, issues new pair)
- [src/database.py](src/database.py) — `SimpleConnectionPool` (1–20 connections), queries `public.callsense` table, returns `transcription` and `dialogs` columns
- [src/config.py](src/config.py) — loads all config from `.env` via python-dotenv

**Auth model:** Stateful refresh tokens stored in-memory (`valid_refresh_tokens` set in auth.py). App restart invalidates all refresh tokens. Access tokens are stateless JWT (HS256).

**CORS:** Hardcoded to `http://193.42.127.209` in [src/main.py](src/main.py).

**Deployment:** Runs on port 12121 (Docker), connects to PostgreSQL via external Docker network `n8n_net` (shared with n8n automation).

## Environment Variables

All loaded from `.env`. Required:

| Variable | Purpose |
|---|---|
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | PostgreSQL connection |
| `APP_PORT` | Uvicorn listen port |
| `JWT_SECRET` | HMAC signing key |
| `JWT_EXPIRATION_HOURS` | Access token TTL (0.5 = 30 min) |
| `JWT_REFRESH_EXPIRATION_HOURS` | Refresh token TTL (24) |
| `LOGIN_USERNAME`, `LOGIN_PASSWORD` | Single hardcoded user credential |
