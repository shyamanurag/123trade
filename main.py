# main.py
"""
Main Application Entry Point with OpenAPI Documentation
Updated: 2025-06-07 - FORCE DEPLOYMENT WITH ALL TRADING FEATURES
INCLUDES: Authentication, Trading APIs, Autonomous Trading, Risk Management
"""

import asyncio
import logging
from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
import uvicorn
import yaml
from pathlib import Path
import redis.asyncio as redis
from datetime import datetime, timedelta
import json
from typing import Dict, Optional, Annotated
import os
import random
import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordRequestForm
from pydantic import BaseModel
from contextlib import asynccontextmanager
from prometheus_client import CONTENT_TYPE_LATEST
from src.utils.metrics import get_metrics, setup_metrics
from middleware.security_middleware import SecurityMiddleware, get_security_config_from_env

# Import unified systems
from common.logging import setup_logging, get_logger
from common.health_checker import HealthChecker
from security import SecurityManager
from monitoring.security_monitor import SecurityMonitor
from utils.backup_manager import BackupManager
from scripts.shutdown import GracefulShutdown

# Import WebSocket manager
from websocket_manager import init_websocket_manager, get_websocket_manager, WebSocketManager

# Import database operations at the top with other imports
from database_manager import get_database_operations, get_database_manager

# Import new API routers
from src.api.market_data import router as market_data_router
from src.api.elite_recommendations import router as recommendations_router
from src.api.auth import router as auth_router
from src.api.monitoring import router as monitoring_router
from src.api.autonomous_trading import router as autonomous_router
from src.api.error_monitoring import router as error_monitoring_router
from src.api.database_health import router as database_health_router
from src.api.market_indices import router as market_indices_router
from src.api.dashboard_api import router as dashboard_router
from src.api.trading_control import router as trading_control_router

# Import error handler
from src.core.error_handler import error_handler, ErrorRecoveryMiddleware

# Import DI provider
from core.providers import get_orchestrator

# Setup unified logging first
setup_logging(level="INFO")
logger = get_logger(__name__)

# Create orchestrator singleton
orchestrator_singleton = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global config, redis_client, security_manager, security_monitor, health_checker, backup_manager, shutdown_handler, websocket_manager, orchestrator_singleton
    
    # Startup
    try:
        logger.info("Starting trading system application...")
        
        # Load configuration
        config = await load_config()
        
        # Initialize Redis
        redis_client = await init_redis()

        # Add security middleware once Redis is available
        app.add_middleware(
            SecurityMiddleware,
            redis_client=redis_client,
            config=get_security_config_from_env()
        )

        # Initialize Prometheus metrics
        setup_metrics()
        
        # Initialize database manager
        database_manager = None
        try:
            from database_manager import get_database_manager, init_database_manager
            database_manager = await init_database_manager()
            if database_manager:
                logger.info("✅ Database manager initialized successfully")
            else:
                logger.warning("❌ Database manager initialization failed - continuing without database")
        except Exception as e:
            logger.warning(f"❌ Database unavailable, continuing in API-only mode: {e}")
        
        # Initialize health checker
        health_checker = await init_health_checker()
        
        # Initialize security (if Redis is available)
        if redis_client:
            security_manager, security_monitor = await init_security()
        else:
            logger.warning("Redis unavailable, skipping security components")
        
        # Initialize backup
        backup_manager = await init_backup()
        
        # Initialize shutdown handler
        shutdown_handler = await init_shutdown()
        
        # Initialize websocket manager
        if redis_client:
            websocket_manager = init_websocket_manager(redis_client)
            await websocket_manager.start()
        else:
            logger.warning("Redis unavailable, skipping WebSocket manager")
        
        # Initialize orchestrator singleton
        orchestrator_singleton = await get_orchestrator()
        
        # Register components for shutdown
        components_to_register = [comp for comp in [
            security_manager, security_monitor, health_checker, backup_manager, orchestrator_singleton
        ] if comp is not None]
        
        for component in components_to_register:
            await shutdown_handler.register_component(component)
        
        logger.info("Application started successfully")
        
        yield  # Application runs here
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    
    # Shutdown
    try:
        logger.info("Shutting down application...")
        if shutdown_handler:
            await shutdown_handler.shutdown()
        
        # Close WebSocket manager
        if websocket_manager:
            await websocket_manager.stop()
        
        # Close database connections
        try:
            from database_manager import get_database_manager
            db_manager = get_database_manager()
            if db_manager:
                await db_manager.close()
                logger.info("✅ Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")
        
        # Close Redis connection
        if redis_client:
            await redis_client.close()
            
        logger.info("Application shutdown completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# Initialize FastAPI app with lifespan

# Import new API routers
from src.api.market_data import router as market_data_router
from src.api.elite_recommendations import router as recommendations_router
from src.api.auth import router as auth_router
from src.api.monitoring import router as monitoring_router
from src.api.autonomous_trading import router as autonomous_router

app = FastAPI(
    title="Trading System API",
    description="""
    ## Comprehensive Trading System API
    
    A production-ready automated trading system with real-time market data,
    risk management, and multi-broker support.
    
    ### Features
    * **Real-time Market Data**: Live feeds from TrueData and Zerodha
    * **Risk Management**: Advanced position sizing and drawdown protection
    * **Multi-Broker Support**: Zerodha KiteConnect integration
    * **WebSocket Streaming**: Real-time updates via WebSocket
    * **Compliance**: SEBI regulatory compliance and audit trails
    * **Security**: JWT authentication, rate limiting, and encryption
    
    ### Authentication
    This API uses JWT tokens for authentication. Include the token in the Authorization header:
    ```
    Authorization: Bearer <your_jwt_token>
    ```
    
    ### Rate Limiting
    - API endpoints: 100 requests per minute
    - WebSocket connections: 1000 concurrent connections
    - Market data: 500 requests per minute
    
    ### Support
    For technical support, contact: support@yourdomain.com
    """,
    version="2.0.0",
    terms_of_service="https://yourdomain.com/terms",
    contact={
        "name": "Trading System Support",
        "url": "https://yourdomain.com/support",
        "email": "support@yourdomain.com",
    },
    license_info={
        "name": "Proprietary License",
        "url": "https://yourdomain.com/license",
    },
    servers=[
        {
            "url": "https://api.yourdomain.com",
            "description": "Production server"
        },
        {
            "url": "https://staging-api.yourdomain.com", 
            "description": "Staging server"
        },
        {
            "url": "http://localhost:8001",
            "description": "Development server"
        }
    ],
    lifespan=lifespan,  # Use lifespan instead of on_event
    openapi_tags=[
        {
            "name": "health",
            "description": "System health and status monitoring"
        },
        {
            "name": "auth",
            "description": "Authentication and authorization"
        },
        {
            "name": "trading",
            "description": "Trading operations and order management"
        },
        {
            "name": "market-data",
            "description": "Real-time and historical market data"
        },
        {
            "name": "positions",
            "description": "Position management and tracking"
        },
        {
            "name": "risk",
            "description": "Risk management and monitoring"
        },
        {
            "name": "analytics",
            "description": "Performance analytics and reporting"
        },
        {
            "name": "compliance",
            "description": "Regulatory compliance and audit trails"
        },
        {
            "name": "admin",
            "description": "Administrative operations (admin only)"
        },
        {
            "name": "users",
            "description": "User management and trading data"
        },
        {
            "name": "monitoring",
            "description": "System monitoring and alerts"
        },
        {
            "name": "autonomous",
            "description": "Autonomous trading operations"
        }
    ]
)

# Setup global error handlers
environment = os.getenv("ENVIRONMENT", "production")
error_handler.environment = environment
error_handler.setup_exception_handlers(app)

# Add error recovery middleware
app.add_middleware(ErrorRecoveryMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:3000"),  # Primary frontend URL
        os.getenv("APP_URL", "http://localhost:8000"),      # App URL
        "http://localhost:3000",  # Development frontend
        "http://0.0.0.0:3000",    # Alternate development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["X-Total-Count", "X-Page-Count"],
    max_age=3600,
)

# Include new API routers
app.include_router(market_data_router, prefix="/market-data", tags=["market-data"])
app.include_router(recommendations_router, prefix="/recommendations", tags=["recommendations"])
app.include_router(recommendations_router, prefix="/scan", tags=["scanning"])
app.include_router(recommendations_router, prefix="/backtest", tags=["backtesting"])
app.include_router(monitoring_router, prefix="/monitoring", tags=["monitoring"])
app.include_router(monitoring_router, prefix="/performance", tags=["performance"])
app.include_router(autonomous_router, prefix="/autonomous", tags=["autonomous"])
app.include_router(auth_router, prefix="/v1/auth", tags=["authentication"])
app.include_router(error_monitoring_router, prefix="/errors", tags=["error-monitoring"])
app.include_router(database_health_router, prefix="/database", tags=["database"])
app.include_router(market_indices_router, prefix="/market", tags=["market-data"])
app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])
app.include_router(trading_control_router, prefix="/api", tags=["trading-control"])

# Mount static files for frontend
static_dir = Path("dist/frontend")
if static_dir.exists():
    # Mount the assets directory for JS/CSS files
    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend_assets")
    
    # Mount the entire frontend directory for other static files
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token for authentication"
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for service-to-service authentication"
        }
    }
    
    # Add global security requirement
    openapi_schema["security"] = [{"BearerAuth": []}]
    
    # Add common response schemas
    openapi_schema["components"]["schemas"].update({
        "ErrorResponse": {
            "type": "object",
            "properties": {
                "error": {"type": "string", "description": "Error message"},
                "code": {"type": "string", "description": "Error code"},
                "timestamp": {"type": "string", "format": "date-time"},
                "path": {"type": "string", "description": "Request path"}
            },
            "required": ["error", "code", "timestamp"]
        },
        "SuccessResponse": {
            "type": "object", 
            "properties": {
                "message": {"type": "string", "description": "Success message"},
                "data": {"type": "object", "description": "Response data"},
                "timestamp": {"type": "string", "format": "date-time"}
            },
            "required": ["message", "timestamp"]
        },
        "HealthStatus": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["healthy", "degraded", "unhealthy"]},
                "timestamp": {"type": "string", "format": "date-time"},
                "components": {
                    "type": "object",
                    "additionalProperties": {"type": "boolean"}
                },
                "uptime": {"type": "number", "description": "System uptime in seconds"}
            }
        }
    })
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Global variables
config: Dict = {}
redis_client: Optional[redis.Redis] = None
security_manager: Optional[SecurityManager] = None
security_monitor: Optional[SecurityMonitor] = None
health_checker: Optional[HealthChecker] = None
backup_manager: Optional[BackupManager] = None
shutdown_handler: Optional[GracefulShutdown] = None
websocket_manager: Optional[WebSocketManager] = None
orchestrator_singleton: Optional = None

# JWT Security
security = HTTPBearer()

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_info: dict

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    
    # Get JWT secret from environment or config
    jwt_secret = os.getenv('JWT_SECRET')
    if not jwt_secret and hasattr(config, 'get') and callable(config.get):
        jwt_secret = config.get('security', {}).get('jwt_secret')
    if not jwt_secret:
        logger.warning("JWT_SECRET not configured, using fallback (NOT SECURE for production)")
        jwt_secret = "INSECURE_FALLBACK_FOR_DEVELOPMENT_ONLY"
    
    encoded_jwt = jwt.encode(to_encode, jwt_secret, algorithm="HS256")
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify JWT token"""
    try:
        # Get JWT secret from environment or config
        jwt_secret = os.getenv('JWT_SECRET')
        if not jwt_secret and hasattr(config, 'get') and callable(config.get):
            jwt_secret = config.get('security', {}).get('jwt_secret')
        if not jwt_secret:
            logger.warning("JWT_SECRET not configured, using fallback (NOT SECURE for production)")
            jwt_secret = "INSECURE_FALLBACK_FOR_DEVELOPMENT_ONLY"
        
        payload = jwt.decode(credentials.credentials, jwt_secret, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Optional auth dependency for development
def optional_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[dict]:
    """Optional authentication for development mode"""
    if not credentials:
        return None
    try:
        # Get JWT secret from environment or config
        jwt_secret = os.getenv('JWT_SECRET')
        if not jwt_secret and hasattr(config, 'get') and callable(config.get):
            jwt_secret = config.get('security', {}).get('jwt_secret')
        if not jwt_secret:
            logger.warning("JWT_SECRET not configured, using fallback (NOT SECURE for production)")
            jwt_secret = "INSECURE_FALLBACK_FOR_DEVELOPMENT_ONLY"
            
        payload = jwt.decode(credentials.credentials, jwt_secret, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        return None

async def load_config():
    """Load configuration from file and environment variables"""
    try:
        # Load environment variables from production.env first
        env_file_path = Path('config/production.env')
        if env_file_path.exists():
            logger.info("Loading environment variables from production.env")
            with open(env_file_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
            logger.info("✅ Environment variables loaded from production.env")
        
        config_path = Path('config/config.yaml')
        if not config_path.exists():
            # Create a basic config using DigitalOcean environment variables
            redis_port = os.getenv('REDIS_PORT', '25061')  # DigitalOcean Redis port
            db_port = os.getenv('DATABASE_PORT', '25060')   # DigitalOcean DB port
            
            # Use environment variables without hardcoded defaults for security
            basic_config = {
                'redis': {
                    'host': os.getenv('REDIS_HOST'),
                    'port': int(redis_port) if redis_port else 6379,
                    'password': os.getenv('REDIS_PASSWORD'),
                    'username': os.getenv('REDIS_USERNAME', 'default'),
                    'ssl': os.getenv('REDIS_SSL', 'false').lower() == 'true'
                },
                'database': {
                    'host': os.getenv('DATABASE_HOST'),
                    'port': int(db_port) if db_port else 5432,
                    'name': os.getenv('DATABASE_NAME', 'defaultdb'),
                    'user': os.getenv('DATABASE_USER'),
                    'password': os.getenv('DATABASE_PASSWORD')
                },
                'security': {'jwt_secret': os.getenv('JWT_SECRET')},
                'monitoring': {'enabled': True}
            }
            logger.info("✅ Using DigitalOcean environment configuration")
            return basic_config
            
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Override with environment variables if present
        if os.getenv('REDIS_HOST'):
            config.setdefault('redis', {})['host'] = os.getenv('REDIS_HOST')
        redis_port_env = os.getenv('REDIS_PORT')
        if redis_port_env:
            config.setdefault('redis', {})['port'] = int(redis_port_env)
        if os.getenv('DATABASE_HOST'):
            config.setdefault('database', {})['host'] = os.getenv('DATABASE_HOST')
        # Use DigitalOcean defaults for database
        if os.getenv('DATABASE_NAME'):
            config.setdefault('database', {})['name'] = os.getenv('DATABASE_NAME')
        if os.getenv('DATABASE_USER'):
            config.setdefault('database', {})['user'] = os.getenv('DATABASE_USER')
            
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise

async def init_redis():
    """Initialize Redis connection with dedicated server and SSL support"""
    # Check if Redis is disabled for development
    if os.getenv('DISABLE_REDIS', 'false').lower() == 'true':
        logger.warning("Redis is disabled for development mode")
        return None
        
    try:
        import ssl
        
        # Load environment variables for production - prioritize REDIS_URL
        redis_url = os.getenv('REDIS_URL')
        redis_host = os.getenv('REDIS_HOST')
        redis_port = os.getenv('REDIS_PORT')
        redis_password = os.getenv('REDIS_PASSWORD')
        redis_username = os.getenv('REDIS_USERNAME', 'default')
        redis_ssl = os.getenv('REDIS_SSL', 'false').lower() == 'true'
        
        # Build Redis connection - prioritize REDIS_URL for DigitalOcean
        if redis_url:
            # Use Redis URL directly (DigitalOcean format: rediss://default:password@host:port)
            logger.info(f"✅ Using REDIS_URL from DigitalOcean: {redis_url[:60]}...")
            
            # DigitalOcean provides rediss:// URL with SSL already configured
            client = redis.from_url(
                redis_url, 
                decode_responses=True,
                ssl_cert_reqs=None,
                ssl_check_hostname=False,
                ssl_ca_certs=None,
                socket_timeout=10,
                socket_connect_timeout=10,
                socket_keepalive=True,
                retry_on_timeout=True
            )
                
        elif redis_host:
            # Build connection from individual components
            logger.info(f"Building Redis connection to: {redis_host}:{redis_port} (SSL: {redis_ssl})")
            
            if redis_ssl:
                # DigitalOcean managed Redis with SSL
                client = redis.Redis(
                    host=redis_host,
                    port=int(redis_port),
                    password=redis_password,
                    decode_responses=True,
                    ssl=True,
                    ssl_cert_reqs=None,
                    ssl_ca_certs=None,
                    ssl_check_hostname=False
                )
            else:
                # Regular Redis connection
                client = redis.Redis(
                    host=redis_host,
                    port=int(redis_port),
                    password=redis_password,
                    decode_responses=True
                )
        else:
            # Fallback to config
            config_redis = config.get('redis', {})
            config_host = config_redis.get('host', 'localhost')
            config_port = config_redis.get('port', 6379)
            config_password = config_redis.get('password')
            
            client = redis.Redis(
                host=config_host,
                port=config_port,
                password=config_password,
                decode_responses=True
            )
            logger.info(f"Using Redis from config: {config_host}:{config_port}")
        
        # Test connection with timeout for SSL handshake
        await asyncio.wait_for(client.ping(), timeout=10.0)
        logger.info("✅ Redis connection successful!")
        
        # Test basic operations
        await client.set("health_check", "ok", ex=60)
        health_check = await client.get("health_check")
        if health_check == "ok":
            logger.info("✅ Redis read/write operations successful!")
        
        return client
        
    except asyncio.TimeoutError:
        logger.error(f"❌ Redis connection timeout - SSL handshake may have failed")
        logger.error("💡 Check: 1) SSL configuration, 2) Network connectivity, 3) Firewall rules")
        return None
    except redis.ConnectionError as e:
        logger.error(f"❌ Redis connection error: {e}")
        logger.error("📋 Check: 1) Redis server IP/hostname, 2) SSL requirements, 3) Password authentication")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected Redis error: {e}")
        return None

async def init_security():
    """Initialize security components"""
    try:
        from security.auth_manager import AuthConfig, AuthManager as SecurityManager
        from monitoring.security_monitor import SecurityMonitor
        
        # Create proper auth config
        auth_config = AuthConfig()
        
        # Initialize security manager with proper config
        try:
            if redis_client:
                security_manager = SecurityManager(auth_config, redis_client)
            else:
                logger.warning("Redis client not available, skipping security manager")
                security_manager = None
        except Exception as e:
            logger.warning(f"Security manager initialization error: {e}, using fallback")
            security_manager = None
        
        # Initialize security monitor  
        try:
            if redis_client:
                security_monitor = SecurityMonitor(config, redis_client)
                # Check if security monitor has start method
                if hasattr(security_monitor, 'start'):
                    await security_monitor.start()
            else:
                logger.warning("Redis client not available, skipping security monitor")
                security_monitor = None
        except Exception as e:
            logger.warning(f"Security monitor initialization error: {e}, using fallback")
            security_monitor = None
        
        logger.info("Security components initialized successfully")
        return security_manager, security_monitor
    except Exception as e:
        logger.error(f"Error initializing security: {e}")
        # Return None values to allow app to continue without security
        logger.warning("Continuing without security components")
        return None, None

async def init_health_checker():
    """Initialize unified health checker"""
    try:
        health_checker = HealthChecker(config)
        await health_checker.start()
        return health_checker
    except Exception as e:
        logger.error(f"Error initializing health checker: {e}")
        raise

async def init_backup():
    """Initialize backup manager"""
    try:
        backup_manager = BackupManager(config)
        await backup_manager.start()
        return backup_manager
    except Exception as e:
        logger.error(f"Error initializing backup: {e}")
        raise

async def init_shutdown():
    """Initialize shutdown handler"""
    try:
        shutdown_handler = GracefulShutdown()
        await shutdown_handler.start()
        return shutdown_handler
    except Exception as e:
        logger.error(f"Error initializing shutdown handler: {e}")
        raise

@app.get(
    "/",
    tags=["health"],
    summary="Root endpoint", 
    description="Basic health check endpoint that returns system status or serves frontend",
    responses={
        200: {
            "description": "System is operational or frontend served",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "version": "2.0.0"
                    }
                }
            }
        }
    }
)
async def root(request: Request):
    """Root endpoint - serves frontend or JSON based on request"""
    return {
        "status": "ok", 
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "service": "Trading System API"
    }

@app.get(
    "/health",
    tags=["health"],
    summary="Comprehensive health check",
    description="""
    Comprehensive health check that monitors all system components including:
    - Database connectivity
    - Redis cache
    - External API connections
    - Memory and CPU usage
    - Background services
    """,
    responses={
        200: {
            "description": "System health status",
            "model": None,  # Will use HealthStatus schema
        },
        503: {
            "description": "Service unavailable",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "message": "Multiple components failing",
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                }
            }
        }
    }
)
async def get_health_status():
    """Unified health check endpoint"""
    global health_checker
    if not health_checker:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "message": "Health checker not initialized",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    try:
        health_status = await health_checker.get_health_status()
        status_code = 200 if health_status["overall_status"] == "healthy" else 503
        return JSONResponse(status_code=status_code, content=health_status)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy", 
                "message": f"Health check error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        )

@app.get(
    "/health/alive",
    tags=["health"],
    summary="Basic liveness check",
    description="Minimal liveness check that responds immediately without any dependency checks.",
    responses={
        200: {
            "description": "Application is alive",
            "content": {
                "application/json": {
                    "example": {
                        "status": "alive",
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                }
            }
        }
    }
)
async def liveness_check():
    """Minimal liveness check - responds immediately"""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat()
    }

@app.get(
    "/health/ready",
    tags=["health"],
    summary="Simple readiness check for deployments",
    description="""
    Simple readiness check that verifies the application is ready to receive traffic.
    This endpoint is optimized for deployment health checks and does not require database connectivity.
    
    Used by:
    - DigitalOcean App Platform health checks
    - Load balancer health probes
    - Container orchestration readiness probes
    """,
    responses={
        200: {
            "description": "Application is ready",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ready",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "version": "2.0.0"
                    }
                }
            }
        },
        503: {
            "description": "Application not ready",
            "content": {
                "application/json": {
                    "example": {
                        "status": "not_ready",
                        "message": "Application still initializing",
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                }
            }
        }
    }
)
async def readiness_check():
    """Simple readiness check for deployments - database independent"""
    try:
        # Basic checks that don't require database
        checks = {
            "app_initialized": True,  # If we reach here, FastAPI is running
            "redis_available": False
        }
        
        # Quick Redis check (non-blocking)
        if redis_client:
            try:
                # Use a very short timeout to avoid blocking
                await asyncio.wait_for(redis_client.ping(), timeout=2.0)
                checks["redis_available"] = True
            except (asyncio.TimeoutError, Exception):
                # Redis not available, but app can still serve traffic
                pass
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "ready",
                "timestamp": datetime.now().isoformat(),
                "version": "2.0.0",
                "checks": checks
            }
        )
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "message": f"Application error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        )

@app.post(
    "/webhook",
    tags=["integration"],
    summary="Webhook endpoint for external integrations",
    description="""
    Webhook endpoint for receiving real-time updates from external systems:
    - Market data providers (TrueData, Zerodha)
    - n8n workflow automation
    - Third-party trading signals
    - Regulatory notifications
    """,
    responses={
        200: {"description": "Webhook processed successfully"},
        400: {"description": "Invalid webhook data"},
        401: {"description": "Unauthorized webhook"},
        500: {"description": "Internal processing error"}
    }
)
async def webhook(request: Request):
    """Webhook endpoint for external integrations"""
    global security_manager
    if not security_manager:
        raise HTTPException(status_code=503, detail="Security manager not initialized")
        
    try:
        # Get webhook data
        data = await request.json()
        
        # Validate webhook data
        if not data:
            raise HTTPException(status_code=400, detail="Empty webhook data")
        
        # Log webhook received
        logger.info("Webhook received", extra={"webhook_data": data})
        
        # Process webhook based on type
        webhook_type = data.get('type')
        if not webhook_type:
            raise HTTPException(status_code=400, detail="Missing webhook type")
        
        # Route to appropriate handler
        if webhook_type == 'market_data':
            # Handle market data updates
            pass
        elif webhook_type == 'order_update':
            # Handle order status updates
            pass
        elif webhook_type == 'n8n_workflow':
            # Handle n8n workflow events
            pass
        else:
            logger.warning(f"Unknown webhook type: {webhook_type}")
        
        return {"status": "success", "message": "Webhook processed"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/webhook")
async def webhook(request: Request):
    try:
        # Log the raw request body
        body = await request.body()
        print(f"Raw webhook data: {body.decode()}")
        
        # Log headers
        headers = dict(request.headers)
        print(f"Webhook headers: {headers}")
        
        # Try to parse JSON
        try:
            data = await request.json()
            print(f"Parsed webhook data: {data}")
        except Exception as json_error:
            print(f"Could not parse JSON data: {str(json_error)}")
        
        return {"status": "success", "message": "Webhook received and logged"}
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.post(
    "/control",
    tags=["admin"],
    summary="System control operations",
    description="""
    Administrative endpoint for system control operations.
    Requires admin privileges.
    
    Available actions:
    - start: Start trading operations
    - stop: Stop all trading activities
    - pause: Pause trading temporarily
    - resume: Resume paused trading
    - restart: Restart system components
    """,
    dependencies=[],  # Add admin dependency here when available
    responses={
        200: {"description": "Control command executed successfully"},
        400: {"description": "Invalid action parameter"},
        403: {"description": "Insufficient permissions"},
        500: {"description": "Command execution failed"}
    }
)
async def control_system(request: Request):
    """System control operations (admin only)"""
    try:
        data = await request.json()
        action = data.get('action')
        
        if not action:
            raise HTTPException(status_code=400, detail="Missing action parameter")
        
        if action not in ['start', 'stop', 'pause', 'resume', 'restart']:
            raise HTTPException(status_code=400, detail="Invalid action parameter")
        
        logger.info(f"System control action: {action}")
        
        # TODO: Implement system control logic
        return {"status": "success", "message": f"System {action} command received"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in system control: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Custom docs endpoint
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    openapi_url = app.openapi_url or "/openapi.json"
    return get_swagger_ui_html(
        openapi_url=openapi_url,
        title=f"{app.title} - Interactive API Documentation",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui.css",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )

@app.get(
    "/api/recommendations/elite",
    tags=["trading"],
    summary="Get elite trading recommendations",
    description="Fetch AI-powered elite trading recommendations with entry/exit points and risk management"
)
async def get_elite_recommendations():
    """Get elite trading recommendations"""
    try:
        # Get database operations
        db_ops = get_database_operations()
        if not db_ops:
            raise HTTPException(status_code=503, detail="Database service unavailable")
        
        # Query active recommendations from database
        recommendations = await db_ops.db.execute_query("""
            SELECT r.*, u.username as created_by
            FROM recommendations r
            LEFT JOIN users u ON r.created_by = u.user_id
            WHERE r.status = 'ACTIVE' AND r.validity_end > NOW()
            ORDER BY r.confidence DESC, r.created_at DESC
            LIMIT 20
        """)
        
        return {
            "success": True,
            "recommendations": recommendations,
            "scan_timestamp": datetime.now().isoformat(),
            "total_count": len(recommendations)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching elite recommendations: {e}")
        # Return empty state instead of mock data
        return {
            "success": True,
            "recommendations": [],
            "scan_timestamp": datetime.now().isoformat(),
            "total_count": 0,
            "message": "No active recommendations available"
        }

@app.get(
    "/api/performance/elite-trades",
    tags=["analytics"],
    summary="Get elite trades performance",
    description="Fetch performance data for elite trading recommendations"
)
async def get_elite_performance():
    """Get elite trades performance data"""
    try:
        db_ops = get_database_operations()
        if not db_ops:
            raise HTTPException(status_code=503, detail="Database service unavailable")
        
        # Get performance metrics from database
        total_recommendations = await db_ops.db.execute_scalar(
            "SELECT COUNT(*) FROM recommendations WHERE created_at >= NOW() - INTERVAL '1 year'"
        )
        
        active_recommendations = await db_ops.db.execute_scalar(
            "SELECT COUNT(*) FROM recommendations WHERE status = 'ACTIVE'"
        )
        
        # Calculate success rate from closed positions
        success_stats = await db_ops.db.execute_one("""
            SELECT 
                COUNT(*) as total_closed,
                COUNT(CASE WHEN realized_pnl > 0 THEN 1 END) as profitable,
                AVG(CASE WHEN realized_pnl > 0 THEN (realized_pnl / (entry_price * quantity)) * 100 END) as avg_return,
                SUM(realized_pnl) as total_profit
            FROM positions 
            WHERE status = 'closed' AND created_at >= NOW() - INTERVAL '1 year'
        """)
        
        success_rate = 0.0
        avg_return = 0.0
        total_profit = 0.0
        
        if success_stats and success_stats['total_closed'] > 0:
            success_rate = (success_stats['profitable'] / success_stats['total_closed']) * 100
            avg_return = success_stats['avg_return'] or 0.0
            total_profit = success_stats['total_profit'] or 0.0
        
        # Get best performer
        best_performer = await db_ops.db.execute_one("""
            SELECT symbol, realized_pnl as profit,
                   (realized_pnl / (entry_price * quantity)) * 100 as return_pct
            FROM positions 
            WHERE status = 'closed' AND realized_pnl > 0
            ORDER BY realized_pnl DESC
            LIMIT 1
        """)
        
        # Get recent closed trades
        recent_closed = await db_ops.db.execute_query("""
            SELECT symbol, entry_price as entry, 
                   (entry_price + (realized_pnl / quantity)) as exit,
                   (realized_pnl / (entry_price * quantity)) * 100 as return,
                   EXTRACT(DAYS FROM (exit_time - entry_time)) as days
            FROM positions 
            WHERE status = 'closed' AND exit_time IS NOT NULL
            ORDER BY exit_time DESC
            LIMIT 5
        """)
        
        performance_data = {
            "total_recommendations": total_recommendations or 0,
            "active_recommendations": active_recommendations or 0,
            "success_rate": round(success_rate, 1),
            "avg_return": round(avg_return, 1),
            "total_profit": round(total_profit, 2),
            "best_performer": best_performer,
            "recent_closed": recent_closed or []
        }
        
        return {
            "success": True,
            "data": performance_data,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching elite performance: {e}")
        return {
            "success": True,
            "data": {
                "total_recommendations": 0,
                "active_recommendations": 0,
                "success_rate": 0.0,
                "avg_return": 0.0,
                "total_profit": 0.0,
                "best_performer": None,
                "recent_closed": []
            },
            "timestamp": datetime.now().isoformat(),
            "message": "Performance data unavailable"
        }

@app.get(
    "/api/users",
    tags=["users"],
    summary="Get all users",
    description="Fetch all registered trading users with their basic information"
)
def get_users():
    """Get all trading users"""
    try:
        # Import the trading control module to access broker users
        from src.api.trading_control import broker_users
        
        # Convert to list format expected by frontend
        users_list = []
        for user_id, user in broker_users.items():
            users_list.append({
                "user_id": user["user_id"],
                "name": user["name"],
                "username": user["user_id"],
                "avatar": user["name"][0].upper() if user["name"] else "U",
                "initial_capital": user["initial_capital"],
                "current_capital": user["current_capital"],
                "total_pnl": user["total_pnl"],
                "daily_pnl": user["daily_pnl"],
                "total_trades": user["total_trades"],
                "win_rate": user["win_rate"],
                "is_active": user["is_active"],
                "open_trades": user["open_trades"]
            })
        
        return {
            "success": True,
            "users": users_list
        }
        
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return {
            "success": True,
            "users": []  # Return empty list on error
        }

@app.get(
    "/api/users/{user_id}/performance",
    tags=["analytics"],
    summary="Get user performance",
    description="Fetch detailed performance analytics for a specific user"
)
async def get_user_performance(user_id: str):
    """Get detailed user performance"""
    try:
        db_ops = get_database_operations()
        if not db_ops:
            raise HTTPException(status_code=503, detail="Database service unavailable")
        
        # Use the database operations method
        performance = await db_ops.get_user_analytics(user_id, days=30)
        
        if not performance:
            return {
                "success": True,
                "performance": {
                    "daily_performance": [],
                    "recent_trades": [],
                    "risk_metrics": {
                        "sharpe_ratio": 0.0,
                        "max_drawdown": 0.0,
                        "volatility": 0.0,
                        "var_95": 0.0,
                        "correlation_to_market": 0.0
                    },
                    "strategy_breakdown": []
                },
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "message": "No performance data available"
            }
        
        # Get additional data for complete performance view
        recent_trades = await db_ops.db.execute_query("""
            SELECT symbol, entry_time as entry_date, exit_time as exit_date,
                   realized_pnl as pnl, status
            FROM positions 
            WHERE user_id = $1 
            ORDER BY COALESCE(exit_time, entry_time) DESC
            LIMIT 10
        """, user_id)
        
        # Get strategy breakdown
        strategy_breakdown = await db_ops.db.execute_query("""
            SELECT 
                strategy,
                COUNT(*) as trades,
                COUNT(CASE WHEN realized_pnl > 0 THEN 1 END) * 100.0 / COUNT(*) as win_rate,
                AVG(CASE WHEN realized_pnl IS NOT NULL THEN (realized_pnl / (entry_price * quantity)) * 100 END) as avg_return
            FROM positions 
            WHERE user_id = $1 AND strategy IS NOT NULL
            GROUP BY strategy
            ORDER BY trades DESC
        """, user_id)
        
        performance["recent_trades"] = recent_trades or []
        performance["strategy_breakdown"] = strategy_breakdown or []
        performance["risk_metrics"] = {
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "volatility": 0.0,
            "var_95": 0.0,
            "correlation_to_market": 0.0
        }
        
        return {
            "success": True,
            "performance": performance,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user performance: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user performance")

@app.get(
    "/api/performance/daily-pnl",
    tags=["analytics"],
    summary="Get daily P&L data",
    description="Fetch system-wide daily P&L performance data"
)
async def get_daily_pnl():
    """Get daily P&L data"""
    try:
        db_ops = get_database_operations()
        if not db_ops:
            raise HTTPException(status_code=503, detail="Database service unavailable")
        
        # Get actual daily P&L from database
        daily_pnl = await db_ops.db.execute_query("""
            WITH daily_stats AS (
                SELECT 
                    DATE(COALESCE(exit_time, entry_time)) as date,
                    SUM(COALESCE(realized_pnl, 0)) as total_pnl,
                    COUNT(DISTINCT user_id) as user_count,
                    COUNT(*) as trades_count,
                    COUNT(CASE WHEN realized_pnl > 0 THEN 1 END) as winning_trades
                FROM positions 
                WHERE COALESCE(exit_time, entry_time) >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(COALESCE(exit_time, entry_time))
            )
            SELECT *,
                   CASE 
                       WHEN trades_count > 0 THEN (winning_trades::float / trades_count * 100)
                       ELSE 0 
                   END as win_rate
            FROM daily_stats
            ORDER BY date
        """)
        
        return {
            "success": True,
            "daily_pnl": daily_pnl or [],
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching daily P&L: {e}")
        return {
            "success": True,
            "daily_pnl": [],
            "timestamp": datetime.now().isoformat(),
            "message": "Daily P&L data unavailable"
        }

@app.post(
    "/api/users",
    tags=["users"],
    summary="Add new user",
    description="Onboard a new user to the trading system"
)
async def add_user(user_data: dict):
    """Add a new user to the trading system"""
    try:
        # Get database operations
        db_ops = get_database_operations()
        if not db_ops:
            raise HTTPException(status_code=503, detail="Database service unavailable")
        
        # Validate required fields
        required_fields = ['username', 'email', 'password', 'full_name']
        for field in required_fields:
            if field not in user_data or not user_data[field]:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Generate user ID
        user_id = f"user_{user_data['username']}_{datetime.now().strftime('%Y%m%d')}"
        
        # Hash password
        import hashlib
        password_hash = hashlib.sha256(user_data['password'].encode()).hexdigest()
        
        # Prepare user data for database
        user_record = {
            'user_id': user_id,
            'username': user_data['username'],
            'email': user_data['email'],
            'password_hash': password_hash,
            'full_name': user_data['full_name'],
            'initial_capital': user_data.get('initial_capital', 50000),
            'risk_tolerance': user_data.get('risk_tolerance', 'medium'),
            'zerodha_client_id': user_data.get('zerodha_client_id')
        }
        
        # Create user in database
        success = await db_ops.create_user(user_record)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create user")
        
        return {
            "success": True,
            "message": f"User {user_data['username']} created successfully",
            "user_id": user_id,
            "user": {
                "user_id": user_id,
                "username": user_data['username'],
                "email": user_data['email'],
                "full_name": user_data['full_name'],
                "initial_capital": user_record['initial_capital'],
                "risk_tolerance": user_record['risk_tolerance']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete(
    "/api/users/{user_id}",
    tags=["users"],
    summary="Remove user",
    description="Remove a user from the trading system"
)
async def remove_user(user_id: str):
    """Remove a user from the trading system"""
    try:
        db_ops = get_database_operations()
        if not db_ops:
            raise HTTPException(status_code=503, detail="Database service unavailable")
        
        # Check if user exists
        user = await db_ops.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Close all open positions
        await db_ops.db.execute_command("""
            UPDATE positions 
            SET status = 'closed', exit_time = NOW(), 
                realized_pnl = COALESCE(unrealized_pnl, 0)
            WHERE user_id = $1 AND status = 'open'
        """, user_id)
        
        # Deactivate user instead of deleting (for audit trail)
        await db_ops.db.execute_command("""
            UPDATE users 
            SET is_active = false, updated_at = NOW()
            WHERE user_id = $1
        """, user_id)
        
        logger.info(f"User deactivated: {user_id}")
        
        return {
            "success": True,
            "message": "User removed successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing user: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove user")

@app.get(
    "/api/users/{user_id}/positions",
    tags=["users"],
    summary="Get user positions",
    description="Get real-time positions for a specific user"
)
async def get_user_positions(user_id: str):
    """Get real-time positions for a specific user"""
    try:
        db_ops = get_database_operations()
        if not db_ops:
            raise HTTPException(status_code=503, detail="Database service unavailable")
        
        # Get user positions from database
        positions = await db_ops.get_user_positions(user_id)
        
        total_unrealized_pnl = sum(p.get("unrealized_pnl", 0) for p in positions)
        
        return {
            "success": True,
            "user_id": user_id,
            "positions": positions,
            "total_unrealized_pnl": total_unrealized_pnl,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user positions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user positions")

@app.get(
    "/api/users/{user_id}/trades",
    tags=["users"],
    summary="Get user trades",
    description="Get recent trades for a specific user"
)
async def get_user_trades(user_id: str, limit: int = 10):
    """Get recent trades for a specific user"""
    try:
        db_ops = get_database_operations()
        if not db_ops:
            raise HTTPException(status_code=503, detail="Database service unavailable")
        
        # Get recent trades from database
        trades = await db_ops.db.execute_query("""
            SELECT 
                position_id as trade_id,
                symbol,
                quantity,
                entry_price,
                current_price,
                realized_pnl as pnl,
                strategy,
                entry_time,
                exit_time,
                status
            FROM positions 
            WHERE user_id = $1 
            ORDER BY COALESCE(exit_time, entry_time) DESC
            LIMIT $2
        """, user_id, limit)
        
        return {
            "success": True,
            "user_id": user_id,
            "trades": trades or [],
            "total_trades": len(trades or []),
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user trades: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user trades")

@app.get(
    "/api/users/{user_id}/analytics",
    tags=["users"],
    summary="Get user analytics",
    description="Get comprehensive analytics for a specific user"
)
async def get_user_analytics(user_id: str):
    """Get comprehensive analytics for a specific user"""
    try:
        db_ops = get_database_operations()
        if not db_ops:
            raise HTTPException(status_code=503, detail="Database service unavailable")
        
        # Get comprehensive analytics from database
        analytics = await db_ops.get_user_analytics(user_id, days=180)  # 6 months
        
        if not analytics:
            analytics = {
                "monthly_pnl": [],
                "strategy_breakdown": [],
                "performance_metrics": {
                    "total_pnl": 0,
                    "win_rate": 0,
                    "avg_trade_pnl": 0,
                    "max_drawdown": 0,
                    "sharpe_ratio": 0,
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0
                }
            }
        
        # Calculate additional metrics
        total_trades = analytics["performance_metrics"].get("total_trades", 0)
        winning_trades = len([p for p in analytics.get("daily_pnl", []) if p.get("pnl", 0) > 0])
        losing_trades = total_trades - winning_trades
        
        analytics["performance_metrics"].update({
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "max_drawdown": 0.0,  # Calculate from daily P&L if needed
            "sharpe_ratio": 0.0   # Calculate from returns if needed
        })
        
        return {
            "success": True,
            "user_id": user_id,
            "analytics": analytics,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user analytics")

@app.put(
    "/api/users/{user_id}/status",
    tags=["users"],
    summary="Update user status",
    description="Activate or deactivate a user"
)
async def update_user_status(user_id: str, status_data: dict):
    """Update user status (active/inactive)"""
    try:
        new_status = status_data.get("status")
        
        # Mock implementation - replace with real status update logic
        # Here you would:
        # 1. Update user status in database
        # 2. If deactivating: close positions, cancel orders
        # 3. Update Redis cache
        # 4. Log status change
        
        logger.info(f"User {user_id} status changed to: {new_status}")
        
        return {
            "success": True,
            "message": f"User status updated to {new_status}",
            "user_id": user_id,
            "new_status": new_status
        }
    except Exception as e:
        logger.error(f"Error updating user status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user status")

# WebSocket endpoints for real-time data
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time trading data"""
    global websocket_manager
    
    if not websocket_manager:
        await websocket.close(code=1011, reason="WebSocket service unavailable")
        return
    
    connection_id = None
    try:
        # Connect user
        connection_id = await websocket_manager.connection_manager.connect(websocket, user_id)
        
        # Send welcome message
        await websocket.send_json({
            'type': 'welcome',
            'connection_id': connection_id,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'available_rooms': [
                'market_data_all',
                'market_data_RELIANCE',
                'market_data_TCS',
                'market_data_HDFC',
                'market_data_INFY',
                'user_positions',
                'system_alerts'
            ]
        })
        
        # Auto-subscribe to general rooms
        await websocket_manager.connection_manager.subscribe_to_room(connection_id, 'market_data_all')
        await websocket_manager.connection_manager.subscribe_to_room(connection_id, 'system_alerts')
        
        # Handle incoming messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()
                
                # Process message
                response = await websocket_manager.handle_client_message(connection_id, data)
                
                # Send response if any
                if response:
                    await websocket.send_json(response)
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in WebSocket message handling: {e}")
                await websocket.send_json({
                    'type': 'error',
                    'message': 'Message processing error'
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user: {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        # Clean up connection
        if connection_id and websocket_manager:
            await websocket_manager.connection_manager.disconnect(connection_id)

@app.get(
    "/api/websocket/stats",
    tags=["monitoring"],
    summary="Get WebSocket connection statistics",
    description="Get real-time statistics about WebSocket connections and subscriptions"
)
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    global websocket_manager
    
    if not websocket_manager:
        raise HTTPException(status_code=503, detail="WebSocket service unavailable")
    
    try:
        stats = websocket_manager.connection_manager.get_connection_stats()
        return {
            'success': True,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting WebSocket stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get WebSocket statistics")

@app.post(
    "/api/websocket/broadcast",
    tags=["admin"],
    summary="Broadcast message to all WebSocket connections",
    description="Send a message to all connected WebSocket clients (admin only)"
)
async def broadcast_message(message_data: dict):
    """Broadcast message to all WebSocket connections"""
    global websocket_manager
    
    if not websocket_manager:
        raise HTTPException(status_code=503, detail="WebSocket service unavailable")
    
    try:
        message = {
            'type': 'admin_broadcast',
            'data': message_data,
            'timestamp': datetime.now().isoformat()
        }
        
        sent_count = await websocket_manager.connection_manager.broadcast(message)
        
        return {
            'success': True,
            'message': 'Broadcast sent successfully',
            'recipients': sent_count,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error broadcasting message: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast message")

@app.post(
    "/api/websocket/alert/{user_id}",
    tags=["trading"],
    summary="Send alert to specific user",
    description="Send a trading alert to a specific user via WebSocket"
)
async def send_user_alert(user_id: str, alert_data: dict):
    """Send alert to specific user"""
    global websocket_manager
    
    if not websocket_manager:
        raise HTTPException(status_code=503, detail="WebSocket service unavailable")
    
    try:
        message = {
            'type': 'user_alert',
            'data': alert_data,
            'timestamp': datetime.now().isoformat()
        }
        
        sent_count = await websocket_manager.connection_manager.send_to_user(user_id, message)
        
        return {
            'success': True,
            'message': f'Alert sent to user {user_id}',
            'connections_reached': sent_count,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error sending user alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to send user alert")

# Prometheus metrics endpoint (excluded from OpenAPI docs)
@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    """Expose Prometheus metrics for scraping"""
    return Response(get_metrics(), media_type=CONTENT_TYPE_LATEST)

# Catch-all route for SPA (MUST be defined LAST - after all API routes)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str, request: Request):
    """Serve React SPA for all non-API routes"""
    # List of API prefixes that should NOT be handled by the SPA
    api_prefixes = (
        "api/", "docs", "health", "webhook", "control", "openapi.json", 
        "market/", "ws/", "v1/", "errors/", "database/", "monitoring/", 
        "performance/", "autonomous/", "trading/", "recommendations/", 
        "scan/", "backtest/", "static/", "assets/"
    )
    
    # If this is an API route, return 404 instead of serving HTML
    if full_path.startswith(api_prefixes):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # Check if this is an API request based on headers
    accept_header = request.headers.get("accept", "")
    is_api_request = "application/json" in accept_header
    
    # For root path with API request, return API response
    if full_path == "" and is_api_request:
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "service": "Trading System API"
        }
    
    # Check if it's a static file request
    static_dir = Path("dist/frontend")
    if static_dir.exists():
        # If it's an empty path or root, serve index.html
        if not full_path or full_path == "":
            index_file = static_dir / "index.html"
            if index_file.exists():
                return FileResponse(index_file, media_type="text/html")
        
        # Try to serve the requested file
        file_path = static_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        
        # For all other routes (SPA routing), fallback to index.html
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file, media_type="text/html")
    
    # Ultimate fallback - serve static HTML file directly
    static_frontend = Path("static-frontend.html")
    if static_frontend.exists():
        return FileResponse(static_frontend, media_type="text/html")
    
    # If no frontend found, return JSON for root or 404 for others
    if not full_path or full_path == "":
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "service": "Trading System API",
            "message": "Frontend not built - API only mode"
        }
    
    raise HTTPException(status_code=404, detail="Frontend not found")

@app.post(
    "/api/security/mfa/setup-totp",
    tags=["security"],
    summary="Setup TOTP (Time-based One-Time Password)",
    description="Initialize TOTP-based multi-factor authentication for a user"
)
async def setup_totp_mfa(user_data: dict):
    """Setup TOTP MFA for user"""
    try:
        from security.mfa_manager import get_mfa_manager
        
        mfa_manager = get_mfa_manager()
        if not mfa_manager:
            raise HTTPException(status_code=503, detail="MFA service unavailable")
        
        user_id = user_data.get("user_id")
        user_email = user_data.get("email")
        
        if not user_id or not user_email:
            raise HTTPException(status_code=400, detail="Missing user_id or email")
        
        # Setup TOTP
        totp_data = await mfa_manager.setup_totp(user_id, user_email)
        
        return {
            "success": True,
            "message": "TOTP setup initiated",
            "qr_code": totp_data["qr_code"],
            "backup_codes": totp_data["backup_codes"],
            "secret": totp_data["secret"]  # Remove in production
        }
        
    except Exception as e:
        logger.error(f"Error setting up TOTP: {e}")
        raise HTTPException(status_code=500, detail="Failed to setup TOTP")

@app.post(
    "/api/security/mfa/verify-totp",
    tags=["security"],
    summary="Verify TOTP setup",
    description="Verify TOTP setup with user-provided token"
)
async def verify_totp_setup(verification_data: dict):
    """Verify TOTP setup"""
    try:
        from security.mfa_manager import get_mfa_manager
        
        mfa_manager = get_mfa_manager()
        if not mfa_manager:
            raise HTTPException(status_code=503, detail="MFA service unavailable")
        
        user_id = verification_data.get("user_id")
        token = verification_data.get("token")
        
        if not user_id or not token:
            raise HTTPException(status_code=400, detail="Missing user_id or token")
        
        # Verify TOTP
        is_valid = await mfa_manager.verify_totp_setup(user_id, token)
        
        if is_valid:
            return {
                "success": True,
                "message": "TOTP verified and activated successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Invalid TOTP token")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying TOTP: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify TOTP")

@app.post(
    "/api/security/mfa/verify",
    tags=["security"],
    summary="Verify MFA token",
    description="Verify multi-factor authentication token for login"
)
async def verify_mfa_token(verification_data: dict):
    """Verify MFA token"""
    try:
        from security.mfa_manager import get_mfa_manager
        
        mfa_manager = get_mfa_manager()
        if not mfa_manager:
            raise HTTPException(status_code=503, detail="MFA service unavailable")
        
        user_id = verification_data.get("user_id")
        token = verification_data.get("token")
        method = verification_data.get("method", "auto")
        
        if not user_id or not token:
            raise HTTPException(status_code=400, detail="Missing user_id or token")
        
        # Verify MFA
        is_valid = await mfa_manager.verify_mfa(user_id, token, method)
        
        if is_valid:
            return {
                "success": True,
                "message": "MFA verification successful"
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid MFA token")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying MFA: {e}")
        raise HTTPException(status_code=500, detail="MFA verification failed")

@app.get(
    "/api/security/mfa/status/{user_id}",
    tags=["security"],
    summary="Get MFA status",
    description="Get user's multi-factor authentication status"
)
async def get_mfa_status(user_id: str):
    """Get user's MFA status"""
    try:
        from security.mfa_manager import get_mfa_manager
        
        mfa_manager = get_mfa_manager()
        if not mfa_manager:
            raise HTTPException(status_code=503, detail="MFA service unavailable")
        
        # Get MFA status
        mfa_status = await mfa_manager.get_user_mfa_status(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "mfa_status": mfa_status
        }
        
    except Exception as e:
        logger.error(f"Error getting MFA status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get MFA status")

@app.get(
    "/api/security/encryption/status",
    tags=["security"],
    summary="Get encryption status",
    description="Get system encryption status and key information"
)
async def get_encryption_status():
    """Get encryption system status"""
    try:
        from security.encryption_manager import get_encryption_manager
        
        encryption_manager = get_encryption_manager()
        if not encryption_manager:
            return {
                "success": True,
                "encryption_enabled": False,
                "message": "Encryption service not available"
            }
        
        # Get encryption status
        encryption_status = await encryption_manager.get_encryption_status()
        
        return {
            "success": True,
            "encryption_status": encryption_status
        }
        
    except Exception as e:
        logger.error(f"Error getting encryption status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get encryption status")

@app.post(
    "/api/security/encryption/rotate-keys",
    tags=["security"],
    summary="Rotate encryption keys",
    description="Manually trigger encryption key rotation (admin only)"
)
async def rotate_encryption_keys():
    """Rotate encryption keys"""
    try:
        from security.encryption_manager import get_encryption_manager
        
        encryption_manager = get_encryption_manager()
        if not encryption_manager:
            raise HTTPException(status_code=503, detail="Encryption service unavailable")
        
        # Rotate keys
        success = await encryption_manager.rotate_keys()
        
        if success:
            return {
                "success": True,
                "message": "Encryption keys rotated successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Key rotation failed")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rotating keys: {e}")
        raise HTTPException(status_code=500, detail="Failed to rotate encryption keys")

@app.get(
    "/api/security/audit/events",
    tags=["security"],
    summary="Get security audit events",
    description="Get recent security events and audit logs"
)
async def get_security_events(limit: int = 100):
    """Get security audit events"""
    try:
        # Get security events from Redis or database
        if redis_client:
            # Get recent security events
            events = await redis_client.lrange("security_events", 0, limit - 1)
            
            security_events = []
            for event in events:
                try:
                    event_data = json.loads(event.decode())
                    security_events.append(event_data)
                except (json.JSONDecodeError, AttributeError):
                    continue
            
            return {
                "success": True,
                "events": security_events,
                "total_events": len(security_events)
            }
        else:
            return {
                "success": True,
                "events": [],
                "message": "Security monitoring not available"
            }
        
    except Exception as e:
        logger.error(f"Error getting security events: {e}")
        raise HTTPException(status_code=500, detail="Failed to get security events")

@app.get(
    "/api/security/system/status",
    tags=["security"],
    summary="Get comprehensive security status",
    description="Get overall security system status including all components"
)
async def get_security_system_status():
    """Get comprehensive security system status"""
    try:
        security_status = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "components": {}
        }
        
        # Check MFA status
        try:
            from security.mfa_manager import get_mfa_manager
            mfa_manager = get_mfa_manager()
            security_status["components"]["mfa"] = {
                "enabled": mfa_manager is not None,
                "status": "healthy" if mfa_manager else "disabled"
            }
        except Exception as e:
            security_status["components"]["mfa"] = {
                "enabled": False,
                "status": "error",
                "error": str(e)
            }
        
        # Check encryption status
        try:
            from security.encryption_manager import get_encryption_manager
            encryption_manager = get_encryption_manager()
            if encryption_manager:
                enc_status = await encryption_manager.get_encryption_status()
                security_status["components"]["encryption"] = {
                    "enabled": enc_status.get("encryption_enabled", False),
                    "status": "healthy",
                    "details": enc_status
                }
            else:
                security_status["components"]["encryption"] = {
                    "enabled": False,
                    "status": "disabled"
                }
        except Exception as e:
            security_status["components"]["encryption"] = {
                "enabled": False,
                "status": "error",
                "error": str(e)
            }
        
        # Check security monitoring
        security_status["components"]["monitoring"] = {
            "enabled": security_monitor is not None,
            "status": "healthy" if security_monitor else "disabled"
        }
        
        # Check Redis security
        security_status["components"]["redis_security"] = {
            "enabled": redis_client is not None,
            "status": "healthy" if redis_client else "disabled"
        }
        
        # Determine overall status
        component_statuses = [comp["status"] for comp in security_status["components"].values()]
        if "error" in component_statuses:
            security_status["overall_status"] = "degraded"
        elif all(status in ["healthy", "disabled"] for status in component_statuses):
            security_status["overall_status"] = "healthy"
        else:
            security_status["overall_status"] = "unknown"
        
        return {
            "success": True,
            "security_status": security_status
        }
        
    except Exception as e:
        logger.error(f"Error getting security system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get security system status")

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv('APP_PORT', os.getenv('PORT', '8000')))
    
    # For production, don't check port availability as DigitalOcean manages this
    is_production = os.getenv('ENVIRONMENT') == 'production' or os.getenv('NODE_ENV') == 'production'
    
    if not is_production:
        # Check if port is available (only in development)
        import socket
        def check_port_available(port):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                result = sock.bind(('0.0.0.0', port))
                sock.close()
                return True
            except OSError:
                sock.close()
                return False
        
        # Find available port if default is in use
        if not check_port_available(port):
            logger.warning(f"Port {port} is in use, trying alternative ports...")
            for alt_port in [8001, 8002, 8003, 8004, 8005]:
                if check_port_available(alt_port):
                    port = alt_port
                    logger.info(f"Using alternative port: {port}")
                    break
            else:
                logger.error("No available ports found in range 8001-8005")
                exit(1)
    
    logger.info(f"Starting server on http://0.0.0.0:{port}")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Production mode: {is_production}")
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Never reload in production
        log_level="info",
        access_log=True,
    )
