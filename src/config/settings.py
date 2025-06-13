"""
Configuration settings for the trading system.
"""

import os
from typing import Optional
from pydantic import BaseSettings, PostgresDsn, RedisDsn, validator

class Settings(BaseSettings):
    """Application settings."""
    
    # Application settings
    APP_NAME: str = "Trading System"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    LOG_LEVEL: str = "INFO"
    
    # API settings
    API_PREFIX: str = "/api/v1"
    API_TITLE: str = "Trading System API"
    API_DESCRIPTION: str = "API for the automated trading system"
    
    # Security settings
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # Database settings
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: str = "5432"
    DATABASE_URI: Optional[PostgresDsn] = None
    
    @validator("DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql",
            user=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER"),
            port=values.get("POSTGRES_PORT"),
            path=f"/{values.get('POSTGRES_DB') or ''}",
        )
    
    # Redis settings
    REDIS_HOST: str
    REDIS_PORT: str = "6379"
    REDIS_PASSWORD: str
    REDIS_URI: Optional[RedisDsn] = None
    
    @validator("REDIS_URI", pre=True)
    def assemble_redis_connection(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str):
            return v
        return RedisDsn.build(
            scheme="redis",
            host=values.get("REDIS_HOST"),
            port=values.get("REDIS_PORT"),
            password=values.get("REDIS_PASSWORD"),
        )
    
    # Trading settings
    MAX_POSITION_SIZE: float = 100000.0
    MAX_LEVERAGE: float = 10.0
    MAX_DRAWDOWN: float = 0.1
    RISK_FREE_RATE: float = 0.02
    TRADING_FEE: float = 0.001
    
    # Market data settings
    MARKET_DATA_UPDATE_INTERVAL: float = 1.0
    MARKET_DATA_CACHE_TTL: int = 60
    
    # Risk management settings
    RISK_CHECK_INTERVAL: float = 1.0
    RISK_ALERT_THRESHOLD: float = 0.8
    MAX_CORRELATION: float = 0.7
    MAX_VOLATILITY: float = 0.5
    
    # Order execution settings
    ORDER_TIMEOUT: float = 30.0
    ORDER_RETRY_DELAY: float = 1.0
    ORDER_MAX_RETRIES: int = 3
    SLIPPAGE_TOLERANCE: float = 0.001
    
    # Monitoring settings
    METRICS_PORT: int = 8001
    PROMETHEUS_MULTIPROC_DIR: str = "/tmp"
    
    # Backup settings
    BACKUP_INTERVAL: int = 3600
    BACKUP_RETENTION_DAYS: int = 7
    
    # SSL settings
    SSL_ENABLED: bool = True
    SSL_CERT_PATH: Optional[str] = None
    SSL_KEY_PATH: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create global settings instance
settings = Settings() 