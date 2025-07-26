"""
Configuration settings for the trading system
"""
from typing import List, Optional, Dict, Any
import os
from pathlib import Path
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from functools import lru_cache
import logging

# Graceful import handling for pydantic_settings
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    PYDANTIC_SETTINGS_AVAILABLE = True
except ImportError:
    # Fallback if pydantic_settings is not available
    try:
        from pydantic import BaseSettings
        # Create a dummy SettingsConfigDict for compatibility
        class SettingsConfigDict(dict):
            pass
        PYDANTIC_SETTINGS_AVAILABLE = False
        logging.warning("pydantic_settings not available, using pydantic BaseSettings fallback")
    except ImportError:
        # Final fallback - create minimal BaseSettings
        class BaseSettings:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        class SettingsConfigDict(dict):
            pass
        
        PYDANTIC_SETTINGS_AVAILABLE = False
        logging.warning("Both pydantic_settings and pydantic not available, using minimal fallback")

from pydantic import Field

logger = logging.getLogger(__name__)

# Check if we're in production environment
IS_PRODUCTION = os.getenv('ENVIRONMENT', '').lower() in ['production', 'prod', 'live']

class Settings(BaseSettings):
    """Application settings"""
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', case_sensitive=True)
    
    # API Settings
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    DEBUG: bool = Field(default=False)
    
    # Database Settings - Check for DigitalOcean DATABASE_URL first
    DATABASE_URL: Optional[str] = Field(default=None, alias='DATABASE_URL')
    DB_HOST: str = Field(default="localhost", alias='DB_HOST')
    DB_PORT: int = Field(default=5432, alias='DB_PORT')
    DB_NAME: str = Field(default="trading", alias='DB_NAME')
    DB_USER: str = Field(default="postgres", alias='DB_USER')
    DB_PASSWORD: str = Field(default="", alias='DB_PASSWORD')
    DB_SSL_MODE: str = Field(default="disable", alias='DB_SSL_MODE')
    DATABASE_SSL: str = Field(default="disable", alias='DATABASE_SSL')
    
    @property
    def database_url(self) -> str:
        """Get the database URL with proper configuration"""
        # If DigitalOcean provides DATABASE_URL, use it but ensure proper SSL handling
        if self.DATABASE_URL:
            # For SQLAlchemy, we need to remove sslmode from the URL and handle it via connect_args
            url = self.DATABASE_URL
            if '?sslmode=' in url:
                # Remove sslmode parameter from URL
                base_url = url.split('?sslmode=')[0]
                return base_url
            return url
        
        # Otherwise, construct from individual settings
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def DATABASE_CONNECT_ARGS(self) -> dict:
        """Get connection arguments for SQLAlchemy"""
        connect_args = {}
        
        # CRITICAL FIX: Only apply SSL settings to PostgreSQL databases, not SQLite
        database_url = self.database_url
        
        # Check if this is a SQLite database
        if database_url.startswith('sqlite:'):
            # SQLite doesn't support SSL - return empty connect_args
            return connect_args
        
        # Only apply SSL settings for PostgreSQL/other databases
        # If using DigitalOcean DATABASE_URL or SSL is required
        if self.DATABASE_URL or self.DATABASE_SSL == 'require':
            connect_args['sslmode'] = 'require'
            
        # DigitalOcean managed databases always require SSL
        if self.DATABASE_URL and 'ondigitalocean.com' in self.DATABASE_URL:
            connect_args['sslmode'] = 'require'
            
        return connect_args
    
    # Redis Settings - Check for DigitalOcean REDIS_URL first
    REDIS_URL: Optional[str] = Field(default=None, alias='REDIS_URL')
    REDIS_HOST: str = Field(default="localhost", alias='REDIS_HOST')
    REDIS_PORT: int = Field(default=6379, alias='REDIS_PORT')
    REDIS_DB: int = Field(default=0, alias='REDIS_DB')
    REDIS_PASSWORD: Optional[str] = Field(default=None, alias='REDIS_PASSWORD')
    REDIS_SSL: bool = Field(default=False, alias='REDIS_SSL')
    
    @property
    def redis_url(self) -> str:
        """Get Redis URL with proper SSL configuration"""
        # If DigitalOcean provides REDIS_URL, use it directly
        if self.REDIS_URL:
            return self.REDIS_URL
        
        # Otherwise, construct from individual settings
        protocol = "rediss" if self.REDIS_SSL else "redis"
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"{protocol}://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # Trading Settings
    DEFAULT_TIMEFRAME: str = Field(default="1h")
    DEFAULT_SYMBOLS: List[str] = Field(default=["BTC/USD", "ETH/USD"])
    MAX_POSITION_SIZE: float = Field(default=1.0)
    RISK_PER_TRADE: float = Field(default=0.02)
    
    # Backtesting Settings
    BACKTEST_START_DATE: str = Field(default="2023-01-01")
    BACKTEST_END_DATE: str = Field(default="2023-12-31")
    INITIAL_CAPITAL: float = Field(default=1000000.0)
    
    # Monitoring Settings
    METRICS_INTERVAL: int = Field(default=60)  # seconds
    
    # File Paths
    BASE_DIR: Path = Field(default=Path(__file__).parent.parent.parent)
    DATA_DIR: Path = Field(default=Path(__file__).parent.parent.parent / "data")
    LOGS_DIR: Path = Field(default=Path(__file__).parent.parent.parent / "logs")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    
    # Zerodha
    ZERODHA_API_KEY: Optional[str] = Field(None, description="Zerodha API key")
    ZERODHA_API_SECRET: Optional[str] = Field(None, description="Zerodha API secret")
    ZERODHA_USER_ID: Optional[str] = Field(None, description="Zerodha user ID")
    
    # TrueData
    TRUEDATA_USERNAME: Optional[str] = Field(None, description="TrueData username")
    TRUEDATA_PASSWORD: Optional[str] = Field(None, description="TrueData password")
    TRUEDATA_LIVE_PORT: int = Field(8084, description="TrueData live port")
    TRUEDATA_IS_SANDBOX: bool = Field(False, description="TrueData sandbox mode")
    
    # Orchestrator
    ORCHESTRATOR_CONFIG: dict = Field(
        default={
            "max_positions": 5,
            "max_risk_per_trade": 0.02,  # 2% per trade
            "max_daily_loss": 0.05,      # 5% daily loss limit
            "default_timeframe": "1m",
            "default_provider": "zerodha"
        },
        description="Trading orchestrator configuration"
    )
    
    # WebSocket
    WS_PING_INTERVAL: int = Field(30, description="WebSocket ping interval in seconds")
    WS_PING_TIMEOUT: int = Field(10, description="WebSocket ping timeout in seconds")
    
    # Logging
    LOG_LEVEL: str = Field("INFO", description="Logging level")
    LOG_FORMAT: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )

@lru_cache()
def get_settings() -> Settings:
    return Settings()

# Create settings instance
settings = get_settings()

# Ensure directories exist (only if they are Path objects)
try:
    if hasattr(settings.DATA_DIR, 'mkdir') and callable(settings.DATA_DIR.mkdir):
        settings.DATA_DIR.mkdir(exist_ok=True)
    if hasattr(settings.LOGS_DIR, 'mkdir') and callable(settings.LOGS_DIR.mkdir):
        settings.LOGS_DIR.mkdir(exist_ok=True)
except Exception as e:
    logger.warning(f"Could not create directories: {e}")

# Fail fast if localhost detected in production
if IS_PRODUCTION:
    # Check if we have a proper DATABASE_URL (DigitalOcean provides this)
    # Use environment variable directly to avoid FieldInfo issues
    database_url_env = os.getenv('DATABASE_URL', '')
    db_host_env = os.getenv('DB_HOST', 'localhost')
    
    has_proper_db_url = database_url_env and 'ondigitalocean.com' in database_url_env
    has_proper_db_host = db_host_env != "localhost" and db_host_env != "127.0.0.1"
    
    # Only fail if we don't have either a proper DATABASE_URL or DB_HOST
    if not has_proper_db_url and not has_proper_db_host:
        error_msg = "CRITICAL: No proper database configuration found in production. Set DATABASE_URL or DB_HOST environment variables!"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Check Redis configuration
    # Use environment variables directly to avoid FieldInfo issues
    redis_url_env = os.getenv('REDIS_URL', '')
    redis_host_env = os.getenv('REDIS_HOST', 'localhost')
    
    has_proper_redis_url = redis_url_env and 'ondigitalocean.com' in redis_url_env
    has_proper_redis_host = redis_host_env != "localhost" and redis_host_env != "127.0.0.1"
    
    if not has_proper_redis_url and not has_proper_redis_host:
        error_msg = "CRITICAL: No proper Redis configuration found in production. Set REDIS_URL or REDIS_HOST environment variables!"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Check CORS origins (allow localhost in development origins for testing)
    try:
        cors_origins = settings.CORS_ORIGINS if hasattr(settings.CORS_ORIGINS, '__iter__') and not isinstance(settings.CORS_ORIGINS, str) else []
        localhost_in_cors = any("localhost" in origin for origin in cors_origins)
        if localhost_in_cors:
            logger.warning("CORS_ORIGINS contains localhost in production - consider removing for security")
    except Exception as e:
        logger.warning(f"Could not check CORS origins: {e}")
else:
    # Warn in development
    if settings.DB_HOST == "localhost":
        logger.warning("[DEV WARNING] DB_HOST is set to localhost. This MUST be overridden in production!")
    if settings.REDIS_HOST == "localhost":
        logger.warning("[DEV WARNING] REDIS_HOST is set to localhost. This MUST be overridden in production!")
    try:
        cors_origins = settings.CORS_ORIGINS if hasattr(settings.CORS_ORIGINS, '__iter__') and not isinstance(settings.CORS_ORIGINS, str) else []
        localhost_in_cors = any("localhost" in origin for origin in cors_origins)
        if localhost_in_cors:
            logger.warning("[DEV WARNING] CORS_ORIGINS contains localhost. This MUST be overridden in production!")
    except Exception as e:
        logger.warning(f"Could not check CORS origins: {e}")

# In production, set these via environment variables or config files! 