from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel
from typing import Optional
from src import config
from src.auth import create_access_token, create_refresh_token, rotate_refresh_token, verify_token
from src.database import (
    init_connection_pool, close_all_connections, get_record_by_filename,
    init_consult_connection_pool, get_consult_data_by_org_and_date,
)
from logging import getLogger
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)

logger = getLogger(__name__)


# Initialize FastAPI app
app = FastAPI(
    title="TranscribAPI",
    description="JWT-protected API for querying callsense transcriptions",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://r-d.space"],  # какие origins разрешены
    allow_credentials=True,                  # разрешить куки и авторизацию
    allow_methods=["GET", "POST"],  # какие методы
    allow_headers=["Authorization", "Content-Type"], # какие заголовки
)


# Security scheme
security = HTTPBearer()

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TranscriptionResponse(BaseModel):
    filename: str
    transcription: Optional[str]
    dialogs: Optional[str]


class ConsultRecord(BaseModel):
    id: str
    organization_id: str
    created_at: datetime
    conv_date: date
    dialog: str
    score_1_start_and_relevance: Optional[int]
    score_2_request_understanding_and_relevance: Optional[int]
    score_3_dialog_logic: Optional[int]
    score_4_objection_handling: Optional[int]
    score_5_solution_promotion: Optional[int]
    score_6_cta_and_result_fixation: Optional[int]
    score_7_service_and_wording: Optional[int]
    score_8_niche_constraints: Optional[int]
    score_9_result_and_risk: Optional[int]


class ConsultDataResponse(BaseModel):
    organization_id: str
    date: date
    records: list[ConsultRecord]


# Dependency: JWT token validation
def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify JWT token from Authorization header."""
    token = credentials.credentials
    logger.info("Verifying...")
    
    payload = verify_token(token)
    
    
    if payload is None:
        logger.error("Bad token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload


# Endpoints

@app.on_event("startup")
async def startup():
    """Initialize database connection pool on startup."""
    init_connection_pool()
    init_consult_connection_pool()


@app.on_event("shutdown")
async def shutdown():
    """Close all database connections on shutdown."""
    close_all_connections()


@app.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Login endpoint. Accepts username and password, returns JWT token.
    
    Default credentials: username='admin', password from .env LOGIN_PASSWORD.
    """
    if request.username != config.LOGIN_USERNAME or request.password != config.LOGIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    access_token = create_access_token({"sub": request.username})
    refresh_token = create_refresh_token(request.username)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@app.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(request: RefreshRequest):
    """Issue a new access token and refresh token from a valid refresh token."""
    token_pair = rotate_refresh_token(request.refresh_token)
    if token_pair is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    access_token, refresh_token = token_pair
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@app.get("/query/{filename}", response_model=TranscriptionResponse)
async def query_transcription(
    filename: str,
    payload: dict = Depends(verify_jwt)
):
    """
    Protected endpoint. Query callsense table by filename and return transcription.
    
    Requires valid JWT token in Authorization header: `Authorization: Bearer <token>`
    """
    try:
        result = get_record_by_filename(filename)
        
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No record found for filename: {filename}"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@app.get("/consultdata", response_model=ConsultDataResponse)
async def consult_data(
    organization_id: str,
    date: date,
    payload: dict = Depends(verify_jwt),
):
    """
    Protected endpoint. Returns all rows from the consult table for a given organization_id and date.

    Query params:
    - organization_id: organisation identifier (plain text)
    - date: date in YYYY-MM-DD format

    Requires valid JWT token in Authorization header: `Authorization: Bearer <token>`
    """
    try:
        rows = get_consult_data_by_org_and_date(organization_id, str(date))
        records = [ConsultRecord(**row) for row in rows]
        return ConsultDataResponse(organization_id=organization_id, date=date, records=records)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=config.APP_PORT, log_level=logging.INFO)
