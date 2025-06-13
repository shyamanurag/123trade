"""
Centralized Configuration Validation System
"""

import os
import yaml
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, validator, root_validator
# Updated import for newer Pydantic versions
try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic.v1.env_settings import BaseSettings
    except ImportError:
        from pydantic import BaseSettings
from datetime import datetime
from enum import Enum

# Import standard library logging directly to avoid naming conflict
import logging as std_logging
std_logging.basicConfig(level=std_logging.INFO)
logger = std_logging.getLogger(__name__)

class LogLevel(str, Enum):
    """Valid log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Environment(str, Enum):
    """Valid environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"

class DatabaseConfig(BaseModel):
    """Database configuration"""
    host: str = Field(..., description="Database host")
    port: int = Field(default=5432, ge=1, le=65535, description="Database port")
    database: str = Field(..., min_length=1, description="Database name")
    username: str = Field(..., min_length=1, description="Database username")
    password: str = Field(..., min_length=1, description="Database password")
    ssl_mode: str = Field(default="prefer", description="SSL mode")
    pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(default=20, ge=0, le=50, description="Max pool overflow")
    pool_timeout: int = Field(default=30, ge=1, le=300, description="Pool timeout in seconds")
    
    @validator('ssl_mode')
    def validate_ssl_mode(cls, v):
        valid_modes = ['disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full']
        if v not in valid_modes:
            raise ValueError(f"Invalid SSL mode. Must be one of: {valid_modes}")
        return v

class RedisConfig(BaseModel):
    """Redis configuration"""
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    password: Optional[str] = Field(default=None, description="Redis password")
    db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    ssl: bool = Field(default=False, description="Use SSL for Redis connection")
    socket_timeout: float = Field(default=5.0, ge=0.1, le=60.0, description="Socket timeout")
    connection_pool_kwargs: Dict[str, Any] = Field(default_factory=dict, description="Additional connection pool arguments")
    
    @validator('connection_pool_kwargs')
    def validate_pool_kwargs(cls, v):
        # Validate known connection pool parameters
        valid_keys = ['max_connections', 'retry_on_timeout', 'health_check_interval']
        for key in v.keys():
            if key not in valid_keys:
                logger.warning(f"Unknown Redis connection pool parameter: {key}")
        return v

class SecurityConfig(BaseModel):
    """Security configuration"""
    jwt_secret: str = Field(..., min_length=32, description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(default=24, ge=1, le=168, description="JWT expiration in hours")
    api_key_length: int = Field(default=32, ge=16, le=64, description="API key length")
    password_hash_rounds: int = Field(default=12, ge=10, le=15, description="Password hash rounds")
    max_login_attempts: int = Field(default=5, ge=1, le=10, description="Max login attempts")
    lockout_duration_minutes: int = Field(default=30, ge=1, le=1440, description="Account lockout duration")
    require_2fa: bool = Field(default=False, description="Require 2FA for authentication")
    
    @validator('jwt_secret')
    def validate_jwt_secret(cls, v):
        if v == 'development-secret-key' and os.getenv('ENVIRONMENT', 'development') == 'production':
            raise ValueError("Development JWT secret cannot be used in production")
        return v
    
    @validator('jwt_algorithm')
    def validate_jwt_algorithm(cls, v):
        valid_algorithms = ['HS256', 'HS384', 'HS512', 'RS256', 'RS384', 'RS512']
        if v not in valid_algorithms:
            raise ValueError(f"Invalid JWT algorithm. Must be one of: {valid_algorithms}")
        return v

class BrokerConfig(BaseModel):
    """Broker configuration"""
    name: str = Field(..., description="Broker name")
    api_key: str = Field(..., min_length=1, description="Broker API key")
    api_secret: str = Field(..., min_length=1, description="Broker API secret")
    base_url: str = Field(..., description="Broker API base URL")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Request timeout")
    rate_limit_per_minute: int = Field(default=60, ge=1, le=1000, description="Rate limit per minute")
    sandbox_mode: bool = Field(default=False, description="Use sandbox/test environment")
    
    @validator('base_url')
    def validate_base_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError("Base URL must start with http:// or https://")
        return v

class TradingConfig(BaseModel):
    """Trading configuration"""
    max_daily_trades: int = Field(default=100, ge=1, le=1000, description="Maximum daily trades")
    max_position_size_percent: float = Field(default=10.0, ge=0.1, le=50.0, description="Max position size as % of capital")
    default_stop_loss_percent: float = Field(default=2.0, ge=0.1, le=10.0, description="Default stop loss %")
    max_drawdown_percent: float = Field(default=20.0, ge=1.0, le=50.0, description="Maximum allowed drawdown %")
    risk_per_trade_percent: float = Field(default=1.0, ge=0.1, le=5.0, description="Risk per trade as % of capital")
    min_order_value: float = Field(default=1000.0, ge=1.0, description="Minimum order value")
    max_order_value: float = Field(default=1000000.0, ge=1000.0, description="Maximum order value")
    
    @root_validator
    def validate_order_values(cls, values):
        min_val = values.get('min_order_value')
        max_val = values.get('max_order_value')
        if min_val and max_val and min_val >= max_val:
            raise ValueError("min_order_value must be less than max_order_value")
        return values

class MonitoringConfig(BaseModel):
    """Monitoring configuration"""
    prometheus_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    prometheus_port: int = Field(default=8001, ge=1024, le=65535, description="Prometheus metrics port")
    health_check_interval_seconds: int = Field(default=30, ge=5, le=300, description="Health check interval")
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    log_format: str = Field(default="json", description="Log format")
    metrics_retention_days: int = Field(default=30, ge=1, le=365, description="Metrics retention period")
    alert_webhook_url: Optional[str] = Field(default=None, description="Webhook URL for alerts")
    
    @validator('log_format')
    def validate_log_format(cls, v):
        valid_formats = ['json', 'text', 'structured']
        if v not in valid_formats:
            raise ValueError(f"Invalid log format. Must be one of: {valid_formats}")
        return v

class WebSocketConfig(BaseModel):
    """WebSocket configuration"""
    port: int = Field(default=8002, ge=1024, le=65535, description="WebSocket server port")
    max_connections: int = Field(default=1000, ge=1, le=10000, description="Maximum concurrent connections")
    ping_interval: int = Field(default=30, ge=5, le=300, description="Ping interval in seconds")
    ping_timeout: int = Field(default=10, ge=1, le=60, description="Ping timeout in seconds")
    message_queue_size: int = Field(default=1000, ge=100, le=10000, description="Message queue size per connection")
    compression_enabled: bool = Field(default=True, description="Enable WebSocket compression")

class ComplianceConfig(BaseModel):
    """Compliance configuration"""
    sebi_reporting_enabled: bool = Field(default=True, description="Enable SEBI reporting")
    audit_trail_retention_days: int = Field(default=2555, ge=365, le=3650, description="Audit trail retention (7 years default)")
    trade_reporting_endpoint: Optional[str] = Field(default=None, description="Trade reporting endpoint URL")
    max_position_value: float = Field(default=50000000.0, ge=1000.0, description="Maximum position value for compliance")
    foreign_investment_limit_percent: float = Field(default=49.0, ge=0.0, le=100.0, description="Foreign investment limit %")
    
    @validator('audit_trail_retention_days')
    def validate_retention_days(cls, v):
        if v < 2555:  # 7 years
            logger.warning("SEBI requires minimum 7 years audit trail retention")
        return v

class TradingSystemConfig(BaseSettings):
    """Main trading system configuration"""
    
    # Environment settings
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Current environment")
    debug: bool = Field(default=False, description="Enable debug mode")
    version: str = Field(default="2.0.0", description="System version")
    
    # Component configurations
    database: DatabaseConfig = Field(..., description="Database configuration")
    redis: RedisConfig = Field(default_factory=RedisConfig, description="Redis configuration")
    security: SecurityConfig = Field(..., description="Security configuration")
    trading: TradingConfig = Field(default_factory=TradingConfig, description="Trading configuration")
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig, description="Monitoring configuration")
    websocket: WebSocketConfig = Field(default_factory=WebSocketConfig, description="WebSocket configuration")
    compliance: ComplianceConfig = Field(default_factory=ComplianceConfig, description="Compliance configuration")
    
    # Broker configurations
    brokers: Dict[str, BrokerConfig] = Field(default_factory=dict, description="Broker configurations")
    
    # Additional settings
    timezone: str = Field(default="Asia/Kolkata", description="System timezone")
    max_workers: int = Field(default=4, ge=1, le=16, description="Maximum worker processes")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    @root_validator
    def validate_production_settings(cls, values):
        """Validate production-specific settings"""
        env = values.get('environment')
        if env == Environment.PRODUCTION:
            # Production validation
            security = values.get('security')
            if security and security.jwt_secret == 'development-secret-key':
                raise ValueError("Development JWT secret cannot be used in production")
                
            if values.get('debug'):
                raise ValueError("Debug mode cannot be enabled in production")
                
            # Ensure essential brokers are configured
            brokers = values.get('brokers', {})
            if not brokers:
                raise ValueError("At least one broker must be configured for production")
                
        return values
    
    @validator('timezone')
    def validate_timezone(cls, v):
        # Basic timezone validation without pytz
        valid_timezones = [
            'Asia/Kolkata', 'UTC', 'America/New_York', 'Europe/London',
            'Asia/Tokyo', 'Asia/Shanghai', 'Australia/Sydney'
        ]
        if v not in valid_timezones:
            logger.warning(f"Timezone {v} not in common list, proceeding anyway")
        return v

class ConfigValidator:
    """Configuration validation and management"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self.config: Optional[TradingSystemConfig] = None
        
    def load_and_validate_sync(self) -> TradingSystemConfig:
        """Synchronous version for CLI usage"""
        try:
            # Load YAML configuration
            if not self.config_path.exists():
                logger.info("Configuration file not found, creating sample config...")
                self.create_sample_config()
                return self.load_and_validate_sync()
                
            with open(self.config_path, 'r') as f:
                raw_config = yaml.safe_load(f)
                
            # Validate configuration
            self.config = TradingSystemConfig(**raw_config)
            
            logger.info("Configuration validated successfully")
            return self.config
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
    
    def get_config(self) -> TradingSystemConfig:
        """Get validated configuration"""
        if not self.config:
            raise RuntimeError("Configuration not loaded. Call load_and_validate() first.")
        return self.config
    
    def create_sample_config(self, output_path: str = "config/config.yaml"):
        """Create a sample configuration file"""
        sample_config = {
            "environment": "development",
            "debug": True,
            "version": "2.0.0",
            "database": {
                "host": "localhost",
                "port": 5432,
                "database": "trading_system",
                "username": "trading_user",
                "password": "change_me_in_production",
                "ssl_mode": "prefer",
                "pool_size": 10
            },
            "redis": {
                "host": "localhost",
                "port": 6379,
                "password": None,
                "db": 0,
                "ssl": False
            },
            "security": {
                "jwt_secret": "your-super-secret-jwt-key-change-in-production-minimum-32-chars",
                "jwt_algorithm": "HS256",
                "jwt_expiration_hours": 24,
                "password_hash_rounds": 12,
                "max_login_attempts": 5,
                "require_2fa": False
            },
            "trading": {
                "max_daily_trades": 100,
                "max_position_size_percent": 10.0,
                "default_stop_loss_percent": 2.0,
                "max_drawdown_percent": 20.0,
                "risk_per_trade_percent": 1.0,
                "min_order_value": 1000.0,
                "max_order_value": 1000000.0
            },
            "monitoring": {
                "prometheus_enabled": True,
                "prometheus_port": 8001,
                "health_check_interval_seconds": 30,
                "log_level": "INFO",
                "log_format": "json",
                "metrics_retention_days": 30
            },
            "websocket": {
                "port": 8002,
                "max_connections": 1000,
                "ping_interval": 30,
                "compression_enabled": True
            },
            "compliance": {
                "sebi_reporting_enabled": True,
                "audit_trail_retention_days": 2555,
                "max_position_value": 50000000.0,
                "foreign_investment_limit_percent": 49.0
            },
            "brokers": {
                "zerodha": {
                    "name": "zerodha",
                    "api_key": "your_zerodha_api_key",
                    "api_secret": "your_zerodha_api_secret",
                    "base_url": "https://api.kite.trade",
                    "timeout_seconds": 30,
                    "rate_limit_per_minute": 60,
                    "sandbox_mode": False
                }
            },
            "timezone": "Asia/Kolkata",
            "max_workers": 4
        }
        
        # Create output directory if it doesn't exist
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            yaml.dump(sample_config, f, default_flow_style=False, indent=2)
            
        logger.info(f"Sample configuration created at: {output_path}")

# Singleton instance
config_validator = ConfigValidator()

def get_validated_config_sync() -> TradingSystemConfig:
    """Synchronous version for CLI usage"""
    return config_validator.load_and_validate_sync()

if __name__ == "__main__":
    # CLI for configuration management
    def main():
        if len(sys.argv) > 1:
            command = sys.argv[1]
            
            if command == "validate":
                try:
                    config = get_validated_config_sync()
                    print("✅ Configuration is valid")
                    print(f"Environment: {config.environment}")
                    print(f"Debug mode: {config.debug}")
                    print(f"Configured brokers: {list(config.brokers.keys())}")
                except Exception as e:
                    print(f"❌ Configuration validation failed: {e}")
                    sys.exit(1)
                    
            elif command == "sample":
                output_path = sys.argv[2] if len(sys.argv) > 2 else "config/sample_config.yaml"
                config_validator.create_sample_config(output_path)
                print(f"✅ Sample configuration created at: {output_path}")
                
            else:
                print(f"Unknown command: {command}")
                print("Available commands: validate, sample")
                sys.exit(1)
        else:
            print("Usage: python config_validator.py [validate|sample] [output_path]")
            sys.exit(1)
    
    main() 