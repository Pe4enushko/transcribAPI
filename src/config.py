import os
from dotenv import load_dotenv

load_dotenv()

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "transcribdb")

# Consult Database Configuration
CONSULT_DB_HOST = os.getenv("CONSULT_DB_HOST", "localhost")
CONSULT_DB_PORT = int(os.getenv("CONSULT_DB_PORT", "5432"))
CONSULT_DB_USER = os.getenv("CONSULT_DB_USER", "postgres")
CONSULT_DB_PASSWORD = os.getenv("CONSULT_DB_PASSWORD", "")
CONSULT_DB_NAME = os.getenv("CONSULT_DB_NAME", "")
APP_PORT = int(os.getenv("APP_PORT", "8000"))

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = float(os.getenv("JWT_EXPIRATION_HOURS", "0.5"))  # 30 minutes
JWT_REFRESH_EXPIRATION_HOURS = float(os.getenv("JWT_REFRESH_EXPIRATION_HOURS", "24"))

# Login Credentials (simple hardcoded for MVP)
LOGIN_USERNAME = os.getenv("LOGIN_USERNAME", "admin")
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "SafePass_2026")
