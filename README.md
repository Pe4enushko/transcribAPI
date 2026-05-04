# TranscribAPI

A minimal FastAPI application with JWT authentication for querying PostgreSQL callsense transcriptions.

## Setup

### 1. Install Dependencies
```bash
uv pip install --python .venv/bin/python -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and update with your database credentials:
```bash
cp .env.example .env
```

Edit `.env` with:
- Your PostgreSQL host, port, user, password, and database name
- A strong `JWT_SECRET` for token signing
- Login credentials (`LOGIN_USERNAME`, `LOGIN_PASSWORD`)

### 3. Start the Server
```bash
.venv/bin/python main.py
```

The API will be available at `http://localhost:<APP_PORT>`.

## API Endpoints

### 1. Login (Unauthenticated)
Get a JWT token using credentials.

**Request:**
```bash
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "SafePass_2026"}'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. Refresh Tokens (Unauthenticated)
Issue a new access token and refresh token using the refresh token.

**Request:**
```bash
curl -X POST "http://localhost:8000/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<your_refresh_token_here>"}'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3. Query Transcription (Authenticated)
Get transcription by filename. Requires valid JWT token.

**Request:**
```bash
curl -X GET "http://localhost:8000/query/1770351837.398605.mp3" \
  -H "Authorization: Bearer <your_token_here>"
```

**Response (Success):**
```json
{
  "filename": "1770351837.398605.mp3",
  "transcription": "Your transcription text here..."
}
```

**Response (Not Found):**
```json
{
  "detail": "No record found for filename: 1770351837.398605.mp3"
}
```

### 4. Health Check (Unauthenticated)
Check if the API is running.

**Request:**
```bash
curl -X GET "http://localhost:8000/health"
```

**Response:**
```json
{
  "status": "ok"
}
```

## Database Schema

The API queries the `callsense` table:
```sql
CREATE TABLE public.callsense (
    id bigint PRIMARY KEY,
    filename text,
    transcription text,
    -- ... other columns
);
```

Currently, only the `transcription` column is returned.

## Error Responses

- **401 Unauthorized**: Invalid or expired token, or invalid login credentials
- **404 Not Found**: No record with the given filename
- **500 Internal Server Error**: Database connection error

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | localhost | PostgreSQL host |
| `DB_PORT` | 5432 | PostgreSQL port |
| `DB_USER` | postgres | PostgreSQL user |
| `DB_PASSWORD` | (empty) | PostgreSQL password |
| `DB_NAME` | transcribdb | PostgreSQL database |
| `APP_PORT` | 8000 | FastAPI listen port |
| `JWT_SECRET` | your-secret-key-change-me | Secret key for JWT signing |
| `JWT_EXPIRATION_HOURS` | 0.5 | Token expiration time (in hours) |
| `JWT_REFRESH_EXPIRATION_HOURS` | 24 | Refresh token expiration time (in hours) |
| `LOGIN_USERNAME` | admin | Username for login |
| `LOGIN_PASSWORD` | SafePass_2026 | Password for login |

## Testing Workflow

1. **Start the API:**
   ```bash
  .venv/bin/python main.py
   ```

2. **Get a token:**
   ```bash
  TOKENS=$(curl -s -X POST "http://localhost:8000/login" \
     -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "SafePass_2026"}')
  TOKEN=$(echo "$TOKENS" | jq -r '.access_token')
  REFRESH_TOKEN=$(echo "$TOKENS" | jq -r '.refresh_token')
   ```

3. **Refresh tokens (optional):**
  ```bash
  TOKENS=$(curl -s -X POST "http://localhost:8000/refresh" \
    -H "Content-Type: application/json" \
    -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}")
  TOKEN=$(echo "$TOKENS" | jq -r '.access_token')
  REFRESH_TOKEN=$(echo "$TOKENS" | jq -r '.refresh_token')
  ```

4. **Query a transcription:**
   ```bash
   curl -X GET "http://localhost:8000/query/1770351837.398605.mp3" \
     -H "Authorization: Bearer $TOKEN"
   ```

5. **Test without token (should fail):**
   ```bash
   curl -X GET "http://localhost:8000/query/1770351837.398605.mp3"
   # Returns 403 Forbidden
   ```

## Project Structure

```
transcribAPI/
├── main.py           # FastAPI application and endpoints
├── config.py         # Environment variable configuration
├── auth.py           # JWT token generation and validation
├── database.py       # PostgreSQL connection and query functions
├── requirements.txt  # Python dependencies
├── .env.example      # Environment variable template
├── .env              # Actual environment variables (not committed)
├── .gitignore        # Git ignore patterns
└── README.md         # This file
```

## Notes

- The default login credentials are `admin:SafePass_2026`. Change these in `.env`.
- The JWT token expires after 30 minutes (configurable via `JWT_EXPIRATION_HOURS`).
- Refresh tokens are stored in memory and rotated on every `/refresh` call.
- Database connection pooling is implemented for better performance.
- Only the `transcription` column is returned; modify `database.py` to return additional columns.

## Future Enhancements

- Add more query endpoints (by ID, date range, etc.)
- Implement user database-backed authentication
- Add pagination and filtering
- Add request logging and monitoring
- Containerize with Docker
