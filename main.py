"""
ShareKhan Trading System - Main Application Entry Point
Complete replacement for TrueData + Zerodha with unified ShareKhan API
Multi-user trading system with comprehensive market data and trading capabilities
"""

import os
import sys
from pathlib import Path
import asyncio
import logging
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import time

from fastapi import FastAPI, APIRouter, Request, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.staticfiles import StaticFiles
import uvicorn
from dotenv import load_dotenv

# Add project root to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables
env_file = os.getenv('ENV_FILE', 'config/production.env')
if os.getenv('ENVIRONMENT') == 'production':
    load_dotenv(env_file)
else:
    load_dotenv()

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/sharekhan_app.log', mode='a') if os.path.exists('logs') else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)

# Global orchestrator instance
global_orchestrator = None
app_startup_complete = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    global global_orchestrator, app_startup_complete
    
    try:
        logger.info("🚀 Starting ShareKhan Trading System...")
        
        # Validate environment variables
        required_env_vars = [
            'SHAREKHAN_API_KEY',
            'SHAREKHAN_SECRET_KEY',
            'REDIS_URL'
        ]
        
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"❌ Missing required environment variables: {missing_vars}")
            raise RuntimeError(f"Missing environment variables: {missing_vars}")
        
        # Initialize ShareKhan orchestrator
        logger.info("🔧 Initializing ShareKhan Trading Orchestrator...")
        from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
        
        config = {
            'paper_trading': os.getenv('PAPER_TRADING', 'true').lower() == 'true',
            'max_position_size': float(os.getenv('MAX_POSITION_SIZE', '100000')),
            'max_daily_loss': float(os.getenv('MAX_DAILY_LOSS', '10000')),
            'email_notifications': os.getenv('EMAIL_NOTIFICATIONS', 'false').lower() == 'true',
            'sms_notifications': os.getenv('SMS_NOTIFICATIONS', 'false').lower() == 'true',
            'database_url': os.getenv('DATABASE_URL', 'sqlite:///sharekhan_trading.db')
        }
        
        global_orchestrator = await ShareKhanTradingOrchestrator.get_instance(config)
        
        if global_orchestrator and global_orchestrator.is_initialized:
            logger.info("✅ ShareKhan Trading Orchestrator initialized successfully!")
            
            # Create default admin user if none exists
            try:
                admin_user_id = os.getenv('ADMIN_USER_ID', 'admin')
                admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
                admin_email = os.getenv('ADMIN_EMAIL', 'admin@tradingsystem.com')
                
                admin_data = {
                    'user_id': admin_user_id,
                    'password': admin_password,
                    'email': admin_email,
                    'role': 'admin',
                    'max_position_size': config['max_position_size'],
                    'max_daily_loss': config['max_daily_loss']
                }
                
                # Try to create admin user if the orchestrator supports it
                if hasattr(global_orchestrator, 'user_manager'):
                    await global_orchestrator.user_manager.create_or_update_user(admin_data)
                    logger.info(f"✅ Admin user ensured: {admin_email}")
                else:
                    logger.info("ℹ️ User manager not available in orchestrator")
                
            except Exception as e:
                logger.warning(f"⚠️ Admin user creation warning: {e}")
            
            # Start orchestrator if supported
            try:
                if hasattr(global_orchestrator, 'start_trading'):
                    await global_orchestrator.start_trading()
                    logger.info("✅ Trading orchestrator started!")
            except Exception as e:
                logger.warning(f"⚠️ Trading start warning: {e}")
        else:
            logger.error("❌ Failed to initialize ShareKhan Trading Orchestrator")
        
        app_startup_complete = True
        logger.info("🎉 Application startup completed successfully!")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        yield
    finally:
        # Cleanup
        if global_orchestrator:
            try:
                if hasattr(global_orchestrator, 'stop_trading'):
                    await global_orchestrator.stop_trading()
                if hasattr(global_orchestrator, 'cleanup'):
                    await global_orchestrator.cleanup()
                logger.info("✅ Orchestrator cleanup completed")
            except Exception as e:
                logger.error(f"❌ Cleanup error: {e}")

# Create FastAPI application
app = FastAPI(
    title="ShareKhan Trading System",
    description="Unified trading system with ShareKhan integration - Complete replacement for TrueData + Zerodha",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security middleware disabled to prevent host header issues in production
# TrustedHostMiddleware can cause "Invalid host header" errors in cloud deployments
logger.info("TrustedHostMiddleware disabled for cloud deployment compatibility")

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "Validation error",
            "details": exc.errors()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "message": str(exc) if os.getenv('DEBUG') == 'true' else "An unexpected error occurred"
        }
    )

# Dependency to get orchestrator
async def get_orchestrator():
    """Dependency to get the global orchestrator instance"""
    global global_orchestrator
    if not global_orchestrator or not global_orchestrator.is_initialized:
        raise HTTPException(status_code=503, detail="Trading system not initialized")
    return global_orchestrator

# =============================================================================
# API ROUTERS - COMPREHENSIVE FRONTEND-BACKEND INTEGRATION
# =============================================================================

# Authentication API (NEW for React frontend)
try:
    from src.api.auth_api import router as auth_router
    app.include_router(auth_router, tags=["authentication"])
    logger.info("✅ Authentication API loaded")
except Exception as e:
    logger.warning(f"⚠️ Authentication API not loaded: {e}")

# Dashboard API v1 (NEW for React frontend)
try:
    from src.api.dashboard_api_v1 import router as dashboard_v1_router
    app.include_router(dashboard_v1_router, tags=["dashboard-v1"])
    logger.info("✅ Dashboard API v1 loaded")
except Exception as e:
    logger.warning(f"⚠️ Dashboard API v1 not loaded: {e}")

# Token Management API (NEW for React frontend)
try:
    from src.api.token_management_api import router as token_mgmt_router
    app.include_router(token_mgmt_router, tags=["token-management"])
    logger.info("✅ Token Management API loaded")
except Exception as e:
    logger.warning(f"⚠️ Token Management API not loaded: {e}")

# Multi-User API (NEW for React frontend)
try:
    from src.api.multi_user_api import router as multi_user_router
    app.include_router(multi_user_router, tags=["multi-user-api"])
    logger.info("✅ Multi-User API loaded")
except Exception as e:
    logger.warning(f"⚠️ Multi-User API not loaded: {e}")

# Users API v1 (NEW for React frontend)
try:
    from src.api.users_api_v1 import router as users_v1_router
    app.include_router(users_v1_router, tags=["users-v1"])
    logger.info("✅ Users API v1 loaded")
except Exception as e:
    logger.warning(f"⚠️ Users API v1 not loaded: {e}")

# Market Data API (existing, compatible with frontend)
try:
    from src.api.market import router as market_router
    app.include_router(market_router, tags=["market-data"])
    logger.info("✅ Market Data API loaded")
except Exception as e:
    logger.warning(f"⚠️ Market Data API not loaded: {e}")

# ShareKhan API routes (existing)
try:
    from src.api.sharekhan_api import router as sharekhan_router
    from src.api.sharekhan_auth_callback import router as sharekhan_auth_router
    from src.api.sharekhan_webhooks import router as sharekhan_webhook_router
    
    app.include_router(sharekhan_router, tags=["sharekhan-api"])
    app.include_router(sharekhan_auth_router, tags=["sharekhan-auth"])
    app.include_router(sharekhan_webhook_router, tags=["sharekhan-webhooks"])
    logger.info("✅ ShareKhan API routes loaded")
except Exception as e:
    logger.warning(f"⚠️ ShareKhan API routes not loaded: {e}")

# Frontend API (fallback compatibility)
try:
    from src.api.frontend_api import router as frontend_router
    app.include_router(frontend_router, tags=["frontend-compat"])
    logger.info("✅ Frontend compatibility API loaded")
except Exception as e:
    logger.warning(f"⚠️ Frontend compatibility API not loaded: {e}")

# =============================================================================
# HEALTH CHECK ENDPOINTS
# =============================================================================

@app.get("/health")
async def health_check():
    """Basic health check"""
    global app_startup_complete, global_orchestrator
    
    status = "healthy"
    checks = {
        "startup_complete": app_startup_complete,
        "orchestrator_initialized": bool(global_orchestrator and global_orchestrator.is_initialized),
        "orchestrator_running": bool(global_orchestrator and global_orchestrator.is_running)
    }
    
    if not all(checks.values()):
        status = "unhealthy"
    
    return {
        "status": status,
        "timestamp": datetime.now(),
        "checks": checks,
        "version": "2.0.0",
        "system": "ShareKhan Trading System"
    }

@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with component status"""
    global global_orchestrator
    
    if not global_orchestrator:
        return {
            "status": "unhealthy",
            "error": "Orchestrator not available",
            "timestamp": datetime.now()
        }
    
    try:
        system_status = await global_orchestrator.get_system_status()
        return {
            "status": "healthy",
            "timestamp": datetime.now(),
            "system_status": system_status
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now()
        }

@app.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    global app_startup_complete, global_orchestrator
    
    if not app_startup_complete or not global_orchestrator or not global_orchestrator.is_initialized:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return {"status": "ready", "timestamp": datetime.now()}

@app.get("/health/ready/json")
async def readiness_check_json():
    """JSON readiness check for deployment scripts"""
    global app_startup_complete, global_orchestrator
    
    ready = app_startup_complete and global_orchestrator and global_orchestrator.is_initialized
    
    return {
        "ready": ready,
        "timestamp": datetime.now().isoformat(),
        "status": "ready" if ready else "not_ready",
        "components": {
            "startup_complete": app_startup_complete,
            "orchestrator_available": bool(global_orchestrator),
            "orchestrator_initialized": bool(global_orchestrator and global_orchestrator.is_initialized)
        }
    }

@app.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive", "timestamp": datetime.now()}

# =============================================================================
# SYSTEM MANAGEMENT ENDPOINTS
# =============================================================================

@app.get("/api/system/config")
async def get_system_config():
    """Get system configuration information"""
    return {
        "trading_mode": "paper",
        "autonomous_enabled": True,
        "version": "2.0.0",
        "status": "active",
        "features": [
            "authentication",
            "dashboard",
            "live-indices", 
            "analytics",
            "multi-user-api",
            "token-management",
            "user-management"
        ]
    }

@app.post("/system/restart")
async def restart_system():
    """Restart the trading system (admin only)"""
    global global_orchestrator
    
    try:
        if global_orchestrator:
            if hasattr(global_orchestrator, 'stop_trading'):
                await global_orchestrator.stop_trading()
            if hasattr(global_orchestrator, 'cleanup'):
                await global_orchestrator.cleanup()
        
        # Reinitialize
        config = {
            'paper_trading': os.getenv('PAPER_TRADING', 'true').lower() == 'true',
            'max_position_size': float(os.getenv('MAX_POSITION_SIZE', '100000')),
            'max_daily_loss': float(os.getenv('MAX_DAILY_LOSS', '10000'))
        }
        
        from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
        global_orchestrator = await ShareKhanTradingOrchestrator.get_instance(config)
        
        return {"success": True, "message": "System restarted successfully"}
        
    except Exception as e:
        logger.error(f"System restart failed: {e}")
        return {"success": False, "error": str(e)}

# =============================================================================
# STATIC FILES & FRONTEND SERVING
# =============================================================================

# Serve React frontend static files
if os.path.exists("src/frontend/dist"):
    app.mount("/static", StaticFiles(directory="src/frontend/dist/assets"), name="static")
    logger.info("✅ React frontend static files mounted")

# Serve React frontend (catch-all route for client-side routing)
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    """Serve React frontend for all unmatched routes"""
    
    # Skip API routes and known endpoints
    if (full_path.startswith("api/") or 
        full_path.startswith("docs") or 
        full_path.startswith("redoc") or
        full_path.startswith("health") or
        full_path.startswith("auth/") or
        full_path.startswith("sharekhan/") or
        full_path.startswith("v1/")):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # Serve React app index.html for all other routes
    react_index_path = "src/frontend/dist/index.html"
    if os.path.exists(react_index_path):
        with open(react_index_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    else:
        # Fallback if React build doesn't exist
        return HTMLResponse(
            content="""
            <html>
                <head><title>Trade123 - Setup Required</title></head>
                <body>
                    <h1>🚀 Trade123 Trading System</h1>
                    <p>React frontend is being built. Please run:</p>
                    <pre>cd src/frontend && npm install && npm run build</pre>
                    <p><a href="/docs">📚 API Documentation</a></p>
                </body>
            </html>
            """
        )

# Development server configuration
if __name__ == "__main__":
    # Development server
    port = int(os.getenv('PORT', 8000))
    host = os.getenv('HOST', '0.0.0.0')
    
    logger.info(f"🚀 Starting ShareKhan Trading System on {host}:{port}")
    logger.info("📋 Environment Configuration:")
    logger.info(f"   - Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"   - Paper Trading: {os.getenv('PAPER_TRADING', 'true')}")
    logger.info(f"   - Log Level: {os.getenv('LOG_LEVEL', 'INFO')}")
    logger.info(f"   - ShareKhan API Key: {os.getenv('SHAREKHAN_API_KEY', 'Not Set')[:8]}...")
    logger.info(f"   - Frontend: {'React Build Available' if os.path.exists('src/frontend/dist') else 'React Build Required'}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv('ENVIRONMENT') != 'production',
        log_level=log_level.lower(),
        access_log=True
    ) 