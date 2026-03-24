from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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
    # Redis
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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
