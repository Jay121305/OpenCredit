"""
Application Configuration
=========================

Centralized configuration using Pydantic Settings with environment variable support.
All settings can be overridden via .env file or environment variables.

Environment Variables:
    All settings can be set via environment variables with UPPER_CASE names.
    Example: jwt_secret → JWT_SECRET

Configuration Categories:
    - Application: Basic app settings (name, env, API prefix)
    - Security: JWT token configuration
    - Database: SQLAlchemy database URL
    - Redis: Stream messaging configuration
    - Fraud Detection: ML thresholds and weights
    - Rate Limiting: Per-endpoint rate limits
    - External Services: Email, SMS, KYC providers
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings have sensible defaults for development.
    For production, override via .env file or environment variables.
    """
    
    # ─────────────────────────────────────────────────────────────────────────
    # Application Settings
    # ─────────────────────────────────────────────────────────────────────────
    app_name: str = "OpenCredit"
    env: str = "dev"
    api_prefix: str = "/api/v1"

    # ─────────────────────────────────────────────────────────────────────────
    # Security
    # ─────────────────────────────────────────────────────────────────────────
    jwt_secret: str = Field(default="change-me-in-prod", min_length=16)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # ─────────────────────────────────────────────────────────────────────────
    # Database
    # ─────────────────────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./opencredit.db"

    # ─────────────────────────────────────────────────────────────────────────
    # Redis (Optional - app will work without it)
    # ─────────────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    stream_name: str = "opencredit.transactions"
    stream_max_len: int = 10000

    # ─────────────────────────────────────────────────────────────────────────
    # Idempotency
    # ─────────────────────────────────────────────────────────────────────────
    idempotency_ttl_seconds: int = 3600

    # ─────────────────────────────────────────────────────────────────────────
    # Credit & Business Rules
    # ─────────────────────────────────────────────────────────────────────────
    default_credit_limit: float = 5000.0
    max_transaction_amount: float = 10000.0

    # ─────────────────────────────────────────────────────────────────────────
    # Fraud Detection
    # ─────────────────────────────────────────────────────────────────────────
    high_value_threshold: float = 5000.0
    velocity_window_seconds: int = 60
    velocity_max_txn_count: int = 5

    # Fraud score weights
    fraud_weight_high_value: float = 0.45
    fraud_weight_velocity: float = 0.25
    fraud_weight_geo_mismatch: float = 0.10
    fraud_weight_ml_max: float = 0.30

    # Fraud decision thresholds
    fraud_threshold_reject: float = 0.75
    fraud_threshold_flag: float = 0.50

    # ─────────────────────────────────────────────────────────────────────────
    # Rate Limiting
    # ─────────────────────────────────────────────────────────────────────────
    rate_limit_auth: str = "5/minute"
    rate_limit_payments: str = "100/minute"
    rate_limit_default: str = "60/minute"

    # ─────────────────────────────────────────────────────────────────────────
    # CORS
    # ─────────────────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    # ─────────────────────────────────────────────────────────────────────────
    # Email Configuration (Resend)
    # ─────────────────────────────────────────────────────────────────────────
    email_provider: str = "resend"
    resend_api_key: str = ""
    email_from: str = "OpenCredit <noreply@opencredit.io>"

    # ─────────────────────────────────────────────────────────────────────────
    # SMS Configuration (Twilio)
    # ─────────────────────────────────────────────────────────────────────────
    sms_provider: str = "twilio"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # ─────────────────────────────────────────────────────────────────────────
    # Currency Exchange (ExchangeRate-API)
    # ─────────────────────────────────────────────────────────────────────────
    fx_provider: str = "exchangerate_api"
    exchangerate_api_key: str = ""
    fx_base_currency: str = "USD"

    # ─────────────────────────────────────────────────────────────────────────
    # KYC Configuration
    # ─────────────────────────────────────────────────────────────────────────
    kyc_provider: str = "manual"

    # ─────────────────────────────────────────────────────────────────────────
    # Sanctions Screening
    # ─────────────────────────────────────────────────────────────────────────
    sanctions_provider: str = "ofac_sdn"

    # ─────────────────────────────────────────────────────────────────────────
    # 2FA Configuration
    # ─────────────────────────────────────────────────────────────────────────
    totp_issuer: str = "OpenCredit"
    otp_expiry_seconds: int = 300  # 5 minutes

    # ─────────────────────────────────────────────────────────────────────────
    # Webhooks
    # ─────────────────────────────────────────────────────────────────────────
    WEBHOOK_TIMEOUT: int = 30
    WEBHOOK_MAX_RETRIES: int = 3

    # ─────────────────────────────────────────────────────────────────────────
    # Backup & Disaster Recovery
    # ─────────────────────────────────────────────────────────────────────────
    BACKUP_DIR: str = "backups"
    BACKUP_RETENTION_DAYS: int = 30
    BACKUP_RETENTION_COUNT: int = 10

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
