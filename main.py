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
                    'name': 'System Administrator',
                    'email': admin_email,
                    'password': admin_password,
                    'role': 'admin',
                    'trading_enabled': True,
                    'max_position_size': 1000000.0,
                    'max_daily_loss': 100000.0
                }
                
                await global_orchestrator.create_user(admin_data)
                logger.info("✅ Default admin user created")
                
            except Exception as e:
                logger.info(f"ℹ️ Admin user already exists or creation failed: {e}")
        
        else:
            logger.error("❌ Failed to initialize ShareKhan orchestrator")
            raise RuntimeError("ShareKhan orchestrator initialization failed")
        
        app_startup_complete = True
        logger.info("🎯 ShareKhan Trading System started successfully!")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    finally:
        # Cleanup
        logger.info("🔄 Shutting down ShareKhan Trading System...")
        
        if global_orchestrator:
            try:
                await global_orchestrator.cleanup()
                logger.info("✅ ShareKhan orchestrator cleanup completed")
            except Exception as e:
                logger.error(f"❌ Orchestrator cleanup failed: {e}")
        
        app_startup_complete = False
        logger.info("✅ ShareKhan Trading System shutdown complete")

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

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP error {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
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

# Include ShareKhan API routes
from src.api.sharekhan_api import router as sharekhan_router
from src.api.sharekhan_auth_callback import router as sharekhan_auth_router
from src.api.sharekhan_webhooks import router as sharekhan_webhook_router

app.include_router(sharekhan_router)
app.include_router(sharekhan_auth_router, tags=["sharekhan-auth"])
app.include_router(sharekhan_webhook_router, tags=["sharekhan-webhooks"])

# Health check endpoints
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

@app.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive", "timestamp": datetime.now()}

# REMOVED: Root endpoint to allow React frontend to handle root path
# This was conflicting with the frontend static site deployment
# DigitalOcean ingress will now route "/" to the frontend component

@app.get("/api/system/config")
async def get_system_config():
    """Get system configuration information"""
    return {
        "trading_mode": "paper",
        "autonomous_enabled": True,
        "version": "2.0.0",
        "status": "active"
    }

# System management endpoints
@app.post("/system/restart")
async def restart_system():
    """Restart the trading system (admin only)"""
    global global_orchestrator
    
    try:
        if global_orchestrator:
            await global_orchestrator.stop_trading()
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

# Static files (if frontend exists)
if os.path.exists("src/frontend/static"):
    app.mount("/static", StaticFiles(directory="src/frontend/static"), name="static")

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
    
    uvicorn.run(
        "main_sharekhan:app",
        host=host,
        port=port,
        reload=os.getenv('ENVIRONMENT') != 'production',
        log_level=log_level.lower(),
        access_log=True
    ) 