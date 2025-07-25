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
from fastapi.middleware.trustedhost import TrustedHostMiddleware
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

# Security middleware for production
if os.getenv('ENVIRONMENT') == 'production':
    allowed_hosts = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

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
app.include_router(sharekhan_router)

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

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with system information"""
    global global_orchestrator, app_startup_complete
    
    orchestrator_status = "Not Available"
    if global_orchestrator:
        if global_orchestrator.is_initialized:
            orchestrator_status = "Running" if global_orchestrator.is_running else "Initialized"
        else:
            orchestrator_status = "Initializing"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ShareKhan Trading System</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
            .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .status {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
            .status.healthy {{ background: #d4edda; color: #155724; }}
            .status.warning {{ background: #fff3cd; color: #856404; }}
            .status.error {{ background: #f8d7da; color: #721c24; }}
            .feature {{ background: #e3f2fd; padding: 15px; margin: 10px 0; border-radius: 5px; }}
            .api-links {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
            .api-link {{ background: #007bff; color: white; padding: 15px; text-align: center; border-radius: 5px; text-decoration: none; }}
            .api-link:hover {{ background: #0056b3; }}
            .highlight {{ background: #fff3cd; padding: 20px; border-radius: 5px; border-left: 4px solid #ffc107; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 ShareKhan Trading System</h1>
            
            <div class="highlight">
                <h2>🎯 Complete Architecture Replacement</h2>
                <p><strong>Old:</strong> TrueData (Market Data) + Zerodha (Trading) = Dual provider complexity</p>
                <p><strong>New:</strong> ShareKhan API only = Unified simplicity</p>
                <ul>
                    <li>✅ Single API for trading and market data</li>
                    <li>✅ Multi-user support with individual permissions</li>
                    <li>✅ Real-time WebSocket data streaming</li>
                    <li>✅ Comprehensive risk management</li>
                    <li>✅ Autonomous trading strategies</li>
                </ul>
            </div>
            
            <div class="status {'healthy' if app_startup_complete else 'warning'}">
                <h3>System Status</h3>
                <p><strong>Startup:</strong> {'Complete' if app_startup_complete else 'In Progress'}</p>
                <p><strong>Orchestrator:</strong> {orchestrator_status}</p>
                <p><strong>Timestamp:</strong> {datetime.now()}</p>
            </div>
            
            <h2>🔧 Key Features</h2>
            
            <div class="feature">
                <h3>Multi-User Trading</h3>
                <p>Role-based access control with individual trading limits and permissions</p>
            </div>
            
            <div class="feature">
                <h3>Unified ShareKhan Integration</h3>
                <p>Single API for all trading operations and market data - no more dual provider complexity</p>
            </div>
            
            <div class="feature">
                <h3>Real-time Market Data</h3>
                <p>WebSocket streaming with Redis caching for high-performance data delivery</p>
            </div>
            
            <div class="feature">
                <h3>Autonomous Trading</h3>
                <p>Multiple strategies with risk management and performance analytics</p>
            </div>
            
            <h2>📡 API Access</h2>
            
            <div class="api-links">
                <a href="/api/v1/sharekhan/auth/login-page" class="api-link">🔐 Login Interface</a>
                <a href="/docs" class="api-link">📚 API Documentation</a>
                <a href="/health/detailed" class="api-link">🏥 System Health</a>
                <a href="/api/v1/sharekhan/system/status" class="api-link">📊 System Status</a>
            </div>
            
            <h2>🚀 Getting Started</h2>
            <ol>
                <li><strong>Authenticate:</strong> Use the login interface to get an access token</li>
                <li><strong>Setup ShareKhan:</strong> Configure your ShareKhan API credentials</li>
                <li><strong>Subscribe to Data:</strong> Subscribe to market data for your instruments</li>
                <li><strong>Start Trading:</strong> Place orders or enable autonomous trading</li>
            </ol>
            
            <h2>🔗 Environment Configuration</h2>
            <div class="feature">
                <h4>Required Environment Variables:</h4>
                <ul>
                    <li><code>SHAREKHAN_API_KEY</code> - Your ShareKhan API key</li>
                    <li><code>SHAREKHAN_SECRET_KEY</code> - Your ShareKhan secret key</li>
                    <li><code>REDIS_URL</code> - Redis connection URL</li>
                    <li><code>ADMIN_USER_ID</code> - Default admin username (optional)</li>
                    <li><code>ADMIN_PASSWORD</code> - Default admin password (optional)</li>
                </ul>
            </div>
            
            <div class="feature">
                <h4>Migration from Old System:</h4>
                <p>This replaces the entire TrueData + Zerodha architecture. All previous endpoints are now unified under ShareKhan API.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

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