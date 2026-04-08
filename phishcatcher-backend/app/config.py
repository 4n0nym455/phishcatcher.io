"""
PhishCatcher Configuration Module

Updated with MinIO-specific settings and production configurations.
"""

from functools import lru_cache
from typing import Optional, List, Set
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator, field_validator
import secrets
import json


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # Application Settings
    APP_NAME: str = Field(default="PhishCatcher API", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    DEBUG: bool = Field(default=False, description="Debug mode")
    ENVIRONMENT: str = Field(default="development", description="Environment (development/staging/production)")
    FRONTEND_URL: str = Field(default="http://localhost:5173", description="Frontend URL for redirects")
    
    # Security Settings
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Secret key for JWT signing"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=120, description="Access token expiry in minutes (2 hours)")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh token expiry in days")
    OTP_EXPIRE_MINUTES: int = Field(default=10, description="OTP expiry in minutes")
    
    # Session Management Settings
    SESSION_INACTIVITY_MINUTES: int = Field(default=60, description="Session inactivity timeout in minutes")
    SESSION_MAX_DURATION_HOURS: int = Field(default=0, description="Maximum session duration in minutes (0 means use SESSION_MAX_DURATION_MINUTES)")
    SESSION_MAX_DURATION_MINUTES: int = Field(default=240, description="Maximum session duration in minutes")
    SESSION_CHECK_INTERVAL_MINUTES: int = Field(default=15, description="Session activity check interval in minutes")
    
    # Password Policy
    MIN_PASSWORD_LENGTH: int = Field(default=12, description="Minimum password length")
    PASSWORD_REQUIRE_UPPERCASE: bool = Field(default=True, description="Require uppercase letters")
    PASSWORD_REQUIRE_LOWERCASE: bool = Field(default=True, description="Require lowercase letters")
    PASSWORD_REQUIRE_NUMBERS: bool = Field(default=True, description="Require numbers")
    PASSWORD_REQUIRE_SPECIAL: bool = Field(default=True, description="Require special characters")
    
    # Database Settings
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/phishcatcher",
        description="PostgreSQL connection URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, description="Database max overflow connections")
    
    # PostgreSQL Credentials (for environment variable construction)
    POSTGRES_USER: Optional[str] = Field(default=None, description="PostgreSQL username")
    POSTGRES_PASSWORD: Optional[str] = Field(default=None, description="PostgreSQL password")
    POSTGRES_DB: Optional[str] = Field(default=None, description="PostgreSQL database name")
    
    # MongoDB Settings
    MONGODB_URL: str = Field(
        default="mongodb://localhost:27017/phishcatcher",
        description="MongoDB connection URL"
    )
    MONGODB_DB_NAME: str = Field(default="phishcatcher", description="MongoDB database name")
    
    # MongoDB Credentials (for environment variable construction)
    MONGO_USER: Optional[str] = Field(default=None, description="MongoDB username")
    MONGO_PASSWORD: Optional[str] = Field(default=None, description="MongoDB password")
    MONGO_DB: Optional[str] = Field(default=None, description="MongoDB database name")
    
    # Redis Settings
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    REDIS_POOL_SIZE: int = Field(default=10, description="Redis connection pool size")
    
    # Redis Credentials (for environment variable construction)
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=100, description="Rate limit per minute")
    RATE_LIMIT_AUTH_REQUESTS_PER_MINUTE: int = Field(default=5, description="Auth rate limit per minute")
    
    # File Storage (MinIO Only)
    MINIO_ENDPOINT: Optional[str] = Field(default=None, description="MinIO endpoint (e.g., minio:9000)")
    MINIO_ACCESS_KEY: Optional[str] = Field(default=None, description="MinIO access key")
    MINIO_SECRET_KEY: Optional[str] = Field(default=None, description="MinIO secret key")
    # Back-compat: older setups used a single MINIO_BUCKET_NAME
    MINIO_BUCKET_NAME: Optional[str] = Field(default=None, description="(Deprecated) Single MinIO bucket name")
    # Bucket strategy: separate buckets per data class (default matches docker-compose.dev.yml)
    MINIO_BUCKET_EMAILS: str = Field(default="phishcatcher-emails", description="Bucket for uploaded emails/attachments")
    MINIO_BUCKET_REPORTS: str = Field(default="phishcatcher-reports", description="Bucket for generated reports/exports")
    MINIO_BUCKET_MODELS: str = Field(default="phishcatcher-models", description="Bucket for ML models/artifacts")
    MINIO_BUCKET_AVATARS: str = Field(default="phishcatcher-avatars", description="Bucket for user profile pictures")
    MINIO_SECURE: bool = Field(default=False, description="Use HTTPS for MinIO")
    MINIO_REGION: str = Field(default="us-east-1", description="MinIO region")
    MINIO_PORT: int = Field(default=9000, description="MinIO port")
    MINIO_CONSOLE_PORT: int = Field(default=9001, description="MinIO console port")
    
    # JWT Configuration
    JWT_SECRET_KEY: str = Field(description="JWT secret key")
    JWT_REFRESH_SECRET_KEY: str = Field(description="JWT refresh secret key")
    
    # File Upload Settings
    MAX_FILE_SIZE_MB: int = Field(default=50, description="Maximum file upload size in MB")
    ALLOWED_FILE_EXTENSIONS: List[str] = Field(
        default=[".eml", ".msg", ".txt", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".png", ".jpg", ".jpeg", ".webp"],
        description="Allowed file extensions for upload"
    )
    
    # Google OAuth Settings
    GOOGLE_CLIENT_ID: Optional[str] = Field(default=None, description="Google OAuth client ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None, description="Google OAuth client secret")
    GOOGLE_REDIRECT_URI: str = Field(
        default="http://localhost:5173/auth/google/callback",
        description="Google OAuth redirect URI"
    )
    
    # Gmail API Settings
    GMAIL_SCOPES: List[str] = Field(
        default=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile"
        ],
        description="Gmail API scopes"
    )
    
    # Email Settings (SMTP)
    SMTP_HOST: Optional[str] = Field(default=None, description="SMTP server host")
    SMTP_PORT: int = Field(default=587, description="SMTP server port")
    SMTP_USER: Optional[str] = Field(default=None, description="SMTP username")
    SMTP_PASSWORD: Optional[str] = Field(default=None, description="SMTP password")
    SMTP_TLS: bool = Field(default=True, description="Use TLS for SMTP")
    FROM_EMAIL: str = Field(default="noreply@phishcatcher.io", description="From email address")
    
    # SendGrid Settings (Optional - falls back to SMTP settings)
    SENDGRID_API_KEY: Optional[str] = Field(default=None, description="SendGrid API key (optional)")
    SENDGRID_FROM_EMAIL: Optional[str] = Field(default=None, description="SendGrid from email (optional, falls back to FROM_EMAIL)")
    SENDGRID_FROM_NAME: str = Field(default="PhishCatcher", description="SendGrid from name")
    
    # Threat Intelligence API Settings
    VIRUSTOTAL_API_KEY: Optional[str] = Field(default=None, description="VirusTotal API key")
    PHISHTANK_API_KEY: Optional[str] = Field(default=None, description="PhishTank API key")
    URLSCAN_API_KEY: Optional[str] = Field(default=None, description="URLScan API key (backup for URLs)")
    ABUSEIPDB_API_KEY: Optional[str] = Field(default=None, description="AbuseIPDB API key (IP/domain reputation)")
    WHOISJSON_API_KEY: Optional[str] = Field(default=None, description="WhoisJSON API key (domain age)")
    
    # ML/Ensemble Settings
    ML_WEIGHT: float = Field(default=0.4, description="ML model weight in ensemble (0.0-1.0)")
    TI_WEIGHT: float = Field(default=0.6, description="Threat intelligence weight in ensemble (0.0-1.0)")
    TI_CACHE_TTL_HOURS: int = Field(default=24, description="Redis cache TTL for TI results in hours")
    ENABLE_URLSCAN_BACKUP: bool = Field(default=True, description="Use URLScan as backup when primary URL checks fail")
    
    # ML Model Settings
    ML_MODEL_PATH: str = Field(default="models/phishing_detector.pkl", description="Path to ML model")
    ML_MODEL_VERSION: str = Field(default="1.0.0", description="ML model version")
    ML_FEATURE_NAMES_PATH: str = Field(default="models/feature_names.json", description="Path to feature names")
    TEXT_CLASSIFIER_PATH: str = Field(default="models/text_classifier.pkl", description="Path to text classifier model")
    TFIDF_VECTORIZER_PATH: str = Field(default="models/tfidf_vectorizer.pkl", description="Path to TF-IDF vectorizer")
    ML_MODELS_DIR: str = Field(default="models", description="Directory containing trained ML models")
    ML_BEST_MODEL: str = Field(default="svm", description="Best performing model (svm, logistic_regression, xgboost)")
    
    # Celery Settings
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0", description="Celery broker URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/0", description="Celery result backend")
    CELERY_TASK_ALWAYS_EAGER: bool = Field(default=False, description="Run tasks synchronously")
    
    # CORS Settings
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173,http://localhost:5174",
        description="Allowed CORS origins"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="Allow CORS credentials")
    CORS_ALLOW_METHODS: str = Field(
        default="GET,POST,PUT,DELETE,OPTIONS",
        description="Allowed CORS methods"
    )
    CORS_ALLOW_HEADERS: str = Field(
        default="*",
        description="Allowed CORS headers"
    )
    
    # Logging Settings
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format (json/text)")
    
    # Data Retention Settings
    DATA_RETENTION_DAYS: int = Field(default=30, description="Data retention period in days")
    ANALYSIS_RETENTION_DAYS: int = Field(default=90, description="Analysis results retention in days")
    
    # Admin Settings
    ADMIN_EMAIL: Optional[str] = Field(default=None, description="Default admin email")
    ADMIN_PASSWORD: Optional[str] = Field(default=None, description="Default admin password")
    
    # Grafana Settings
    GRAFANA_USER: Optional[str] = Field(default=None, description="Grafana username")
    GRAFANA_PASSWORD: Optional[str] = Field(default=None, description="Grafana password")
    
    # Gmail Integration Settings
    GMAIL_CLIENT_ID: Optional[str] = Field(default=None, description="Gmail OAuth client ID")
    GMAIL_CLIENT_SECRET: Optional[str] = Field(default=None, description="Gmail OAuth client secret")
    GMAIL_REDIRECT_URI: str = Field(
        default="http://localhost:5173/gmail/callback",
        description="Gmail OAuth redirect URI"
    )
    
    @validator("SECRET_KEY", pre=True, always=True)
    def validate_secret_key(cls, v):
        """Ensure secret key is sufficiently long for production."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @validator("REDIS_URL", pre=True)
    def validate_redis_url(cls, v):
        """Construct Redis URL from environment variables if needed."""
        # If REDIS_URL is default, construct it from environment variables
        if v == "redis://localhost:6379/0":
            import os
            from urllib.parse import quote
            redis_password = os.getenv("REDIS_PASSWORD", "redis_secret")
            # URL-encode the password to handle special characters
            encoded_password = quote(redis_password, safe='')
            v = f"redis://:{encoded_password}@localhost:6379/0"
        return v
    
    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v):
        """Ensure async driver is used for PostgreSQL."""
        # If DATABASE_URL is not provided or is default, construct it from environment variables
        if v == "postgresql+asyncpg://postgres:postgres@localhost:5432/phishcatcher":
            import os
            postgres_user = os.getenv("POSTGRES_USER", "phishcatcher")
            postgres_password = os.getenv("POSTGRES_PASSWORD", "changeme")
            postgres_db = os.getenv("POSTGRES_DB", "phishcatcher")
            v = f"postgresql+asyncpg://{postgres_user}:{postgres_password}@localhost:5432/{postgres_db}"
        
        # Ensure async driver is used
        if v.startswith("postgresql://") and "asyncpg" not in v:
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    
    @validator("MINIO_ENDPOINT", pre=True)
    def validate_minio_endpoint(cls, v):
        """Use localhost for local development when running outside Docker."""
        if v and v.startswith("minio:"):
            return v.replace("minio:", "localhost:")
        return v
    
    # @validator("CORS_ORIGINS", pre=True)
    # def parse_cors_origins(cls, v):
    #     """Parse CORS origins from string or list."""
    #     if isinstance(v, str):
    #         try:
    #             return json.loads(v)
    #         except json.JSONDecodeError:
    #             return [origin.strip() for origin in v.split(",")]
    #     return v
    
    # @validator("CORS_ALLOW_METHODS", pre=True)
    # def parse_cors_methods(cls, v):
    #     """Parse CORS methods from string or list."""
    #     if isinstance(v, str):
    #         try:
    #             return json.loads(v)
    #         except json.JSONDecodeError:
    #             return [method.strip() for method in v.split(",")]
    #     return v
    
    # @validator("CORS_ALLOW_HEADERS", pre=True)
    # def parse_cors_headers(cls, v):
    #     """Parse CORS headers from string or list."""
    #     if isinstance(v, str):
    #         try:
    #             return json.loads(v)
    #         except json.JSONDecodeError:
    #             return [header.strip() for header in v.split(",")]
    #     return v
    
    @validator("ALLOWED_FILE_EXTENSIONS", pre=True)
    def parse_allowed_extensions(cls, v):
        """Parse allowed extensions from string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [ext.strip() for ext in v.split(",")]
        return v

    @field_validator("MINIO_BUCKET_EMAILS", mode="before")
    @classmethod
    def _default_emails_bucket_from_legacy(cls, v, info):
        # If explicitly set, keep it.
        if v not in (None, ""):
            return v
        legacy = (info.data or {}).get("MINIO_BUCKET_NAME")
        return legacy or "phishcatcher-emails"
    
    @property
    def allowed_extensions_set(self) -> Set[str]:
        """Get allowed extensions as a set for fast lookup."""
        return {ext.lower().lstrip('.') for ext in self.ALLOWED_FILE_EXTENSIONS}
    
    @property
    def max_upload_size(self) -> int:
        """Get max upload size in bytes."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    @property
    def storage_config(self) -> dict:
        """Get MinIO storage configuration."""
        if self.MINIO_ENDPOINT:
            return {
                "endpoint": self.MINIO_ENDPOINT,
                "access_key": self.MINIO_ACCESS_KEY,
                "secret_key": self.MINIO_SECRET_KEY,
                "secure": self.MINIO_SECURE,
                "region": self.MINIO_REGION,
                "type": "minio"
            }
        return None

    # NOTE: pydantic v2 uses `model_config` above (not inner Config)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_database_url() -> str:
    """Get database URL with async driver."""
    settings = get_settings()
    return settings.DATABASE_URL


def get_redis_url() -> str:
    """Get Redis URL."""
    settings = get_settings()
    return settings.REDIS_URL


def get_mongodb_url() -> str:
    """Get MongoDB URL."""
    settings = get_settings()
    return settings.MONGODB_URL