"""
Configuration settings for the trading system - PRODUCTION READY
"""
from typing import List, Optional, Dict, Any
import os
from pathlib import Path
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from functools import lru_cache
import logging

# Comprehensive Pydantic import handling
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import Field
    PYDANTIC_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ Using pydantic_settings")
except ImportError:
    try:
        from pydantic import BaseSettings, Field
        # Create dummy SettingsConfigDict for compatibility
        class SettingsConfigDict(dict):
            pass
        PYDANTIC_AVAILABLE = True
        logger = logging.getLogger(__name__)
        logger.warning("⚠️ Using pydantic fallback (no pydantic_settings)")
    except ImportError:
        # Final fallback - create minimal settings class
        logger = logging.getLogger(__name__)
        logger.error("❌ No pydantic available, using environment-only config")
        
        class BaseSettings:
            def __init__(self, **kwargs):
                # Load from environment variables directly
                for key, default in kwargs.items():
                    setattr(self, key.upper(), os.getenv(key.upper(), default))
        
        def Field(default=None, **kwargs):
            return default
        
        class SettingsConfigDict(dict):
            pass
        
        PYDANTIC_AVAILABLE = False

# Check if we're in production environment
IS_PRODUCTION = os.getenv('ENVIRONMENT', '').lower() in ['production', 'prod', 'live']

# Robust settings class that works with or without pydantic
class Settings(BaseSettings):
    """Application settings - Production Ready"""
    
    if PYDANTIC_AVAILABLE:
        model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', case_sensitive=True)
    
    # API Settings
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    DEBUG: bool = Field(default=False)
    
    # Database Settings - Production Ready
    DATABASE_URL: Optional[str] = Field(default=None)
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=5432)
    DB_NAME: str = Field(default="trading")
    DB_USER: str = Field(default="postgres")
    DB_PASSWORD: str = Field(default="")
    DB_SSL_MODE: str = Field(default="disable")
    DATABASE_SSL: str = Field(default="disable")
    
    # Redis Settings
    REDIS_URL: Optional[str] = Field(default=None)
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: str = Field(default="")
    REDIS_USERNAME: str = Field(default="default")
    REDIS_SSL: str = Field(default="false")
    REDIS_DB: str = Field(default="0")
    
    # ShareKhan Settings
    SHAREKHAN_API_KEY: str = Field(default="")
    SHAREKHAN_SECRET_KEY: str = Field(default="")
    SHAREKHAN_CUSTOMER_ID: str = Field(default="")
    SHAREKHAN_BASE_URL: str = Field(default="https://api.sharekhan.com")
    SHAREKHAN_WS_URL: str = Field(default="wss://wspush.sharekhan.com")
    
    # Security Settings
    JWT_SECRET: str = Field(default="dev-secret-key")
    SECRET_KEY: str = Field(default="dev-secret-key")
    ENCRYPTION_KEY: str = Field(default="")
    
    # CORS and Host Settings
    CORS_ORIGINS: str = Field(default='["*"]')
    TRUSTED_HOSTS: str = Field(default='["*"]')
    ENABLE_CORS: str = Field(default="true")
    
    # Application Settings
    LOG_LEVEL: str = Field(default="INFO")
    ENVIRONMENT: str = Field(default="development")
    TRADING_MODE: str = Field(default="paper")
    PAPER_TRADING: str = Field(default="true")
    
    # Directory Settings
    DATA_DIR: Optional[Path] = Field(default=None)
    LOGS_DIR: Optional[Path] = Field(default=None)
    
    def __init__(self, **kwargs):
        if PYDANTIC_AVAILABLE:
            super().__init__(**kwargs)
        else:
            # Manual initialization for fallback mode
            for field_name in ['API_HOST', 'API_PORT', 'DEBUG', 'DATABASE_URL', 'DB_HOST', 'DB_PORT', 
                              'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'REDIS_URL', 'REDIS_HOST', 'REDIS_PORT',
                              'SHAREKHAN_API_KEY', 'SHAREKHAN_SECRET_KEY', 'CORS_ORIGINS', 'TRUSTED_HOSTS',
                              'LOG_LEVEL', 'ENVIRONMENT', 'TRADING_MODE']:
                env_value = os.getenv(field_name, getattr(self.__class__, field_name, None))
                if hasattr(env_value, 'default'):  # Handle Field objects
                    env_value = env_value.default
                setattr(self, field_name, env_value)
        
        # Set directory paths
        self._setup_directories()
    
    def _setup_directories(self):
        """Setup directory paths safely"""
        try:
            if not self.DATA_DIR:
                self.DATA_DIR = Path("data")
            if not self.LOGS_DIR:
                self.LOGS_DIR = Path("logs")
        except Exception as e:
            logger.warning(f"Could not setup directories: {e}")
            self.DATA_DIR = Path("data")
            self.LOGS_DIR = Path("logs")
    
    @property
    def database_url(self) -> str:
        """Get the database URL with proper configuration"""
        # Use environment variable directly to avoid FieldInfo issues
        database_url_env = os.getenv('DATABASE_URL')
        if database_url_env:
            # For SQLAlchemy, remove sslmode from URL if present
            if '?sslmode=' in database_url_env:
                base_url = database_url_env.split('?sslmode=')[0]
                return base_url
            return database_url_env
        
        # Construct from individual settings using environment variables
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', '')
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'trading')
        
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    @property
    def redis_url(self) -> str:
        """Get the Redis URL"""
        redis_url_env = os.getenv('REDIS_URL')
        if redis_url_env:
            return redis_url_env
        
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = os.getenv('REDIS_PORT', '6379')
        redis_db = os.getenv('REDIS_DB', '0')
        redis_password = os.getenv('REDIS_PASSWORD', '')
        
        if redis_password:
            return f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
        return f"redis://{redis_host}:{redis_port}/{redis_db}"

# Create settings instance
@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()

# Create directories safely
try:
    if hasattr(settings, 'DATA_DIR') and settings.DATA_DIR:
        settings.DATA_DIR.mkdir(exist_ok=True)
    if hasattr(settings, 'LOGS_DIR') and settings.LOGS_DIR:
        settings.LOGS_DIR.mkdir(exist_ok=True)
except Exception as e:
    logger.warning(f"Could not create directories: {e}")

# Production validation - USE ENVIRONMENT VARIABLES DIRECTLY
if IS_PRODUCTION:
    logger.info("🚀 Production environment detected - validating configuration...")
    
    # Database validation using environment variables directly
    database_url_env = os.getenv('DATABASE_URL', '')
    db_host_env = os.getenv('DB_HOST', 'localhost')
    
    has_proper_db_url = database_url_env and 'ondigitalocean.com' in database_url_env
    has_proper_db_host = db_host_env not in ["localhost", "127.0.0.1"]
    
    if not has_proper_db_url and not has_proper_db_host:
        logger.warning("⚠️ No production database configuration detected")
    else:
        logger.info("✅ Database configuration validated")
    
    # Redis validation using environment variables directly
    redis_url_env = os.getenv('REDIS_URL', '')
    redis_host_env = os.getenv('REDIS_HOST', 'localhost')
    
    has_proper_redis_url = redis_url_env and 'ondigitalocean.com' in redis_url_env
    has_proper_redis_host = redis_host_env not in ["localhost", "127.0.0.1"]
    
    if not has_proper_redis_url and not has_proper_redis_host:
        logger.warning("⚠️ No production Redis configuration detected")
    else:
        logger.info("✅ Redis configuration validated")
    
    logger.info("✅ Production configuration validation complete")
else:
    logger.info("🔧 Development environment detected")

# Export settings
__all__ = ['settings', 'get_settings', 'Settings', 'IS_PRODUCTION'] 