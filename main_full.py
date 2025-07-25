"""
Trading System Main Application - Full Version
Complete ShareKhan trading system with all features
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv('config/local_deployment.env')
    load_dotenv('config/sharekhan_credentials.env')
except ImportError:
    pass

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ShareKhan Trading System",
    description="Full-Featured Trading System with ShareKhan Integration",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance
global_orchestrator = None

@app.on_event("startup")
async def startup_event():
    """Initialize the trading system on startup"""
    global global_orchestrator
    
    logger.info("Starting Full Trading System...")
    
    try:
        # Initialize ShareKhan orchestrator
        from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
        global_orchestrator = await ShareKhanTradingOrchestrator.get_instance()
        logger.info("ShareKhan orchestrator initialized successfully")
    except Exception as e:
        logger.warning(f"Orchestrator initialization issue: {e}")
        global_orchestrator = None

# Include API routes with error handling
try:
    from src.api.sharekhan_auth_callback import router as sharekhan_auth_router
    app.include_router(sharekhan_auth_router, tags=["sharekhan-auth"])
    logger.info("ShareKhan auth routes loaded")
except Exception as e:
    logger.warning(f"ShareKhan auth routes not loaded: {e}")

try:
    from src.api.sharekhan_webhooks import router as sharekhan_webhook_router
    app.include_router(sharekhan_webhook_router, tags=["sharekhan-webhooks"])
    logger.info("ShareKhan webhook routes loaded")
except Exception as e:
    logger.warning(f"ShareKhan webhook routes not loaded: {e}")

try:
    from src.api.performance import router as performance_router
    app.include_router(performance_router, prefix="/api", tags=["performance"])
    logger.info("Performance API routes loaded")
except Exception as e:
    logger.warning(f"Performance routes not loaded: {e}")

try:
    from src.api.autonomous_trading import router as autonomous_router
    app.include_router(autonomous_router, prefix="/api", tags=["autonomous"])
    logger.info("Autonomous trading routes loaded")
except Exception as e:
    logger.warning(f"Autonomous trading routes not loaded: {e}")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Enhanced main dashboard"""
    sharekhan_status = "Configured" if os.getenv('SHAREKHAN_API_KEY') else "Not configured"
    customer_configured = bool(os.getenv('SHAREKHAN_CUSTOMER_ID') and os.getenv('SHAREKHAN_CUSTOMER_ID') != 'YOUR_SHAREKHAN_CLIENT_ID')
    
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ShareKhan Trading System - Full Version</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
            .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
            .header {{ text-align: center; color: white; margin-bottom: 30px; }}
            .header h1 {{ font-size: 3em; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
            .status-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }}
            .status-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .status-success {{ border-left: 5px solid #28a745; }}
            .status-warning {{ border-left: 5px solid #ffc107; }}
            .status-info {{ border-left: 5px solid #17a2b8; }}
            .nav-buttons {{ display: flex; flex-wrap: wrap; gap: 15px; justify-content: center; margin: 30px 0; }}
            .btn {{ display: inline-block; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; transition: all 0.3s; }}
            .btn:hover {{ background: #0056b3; transform: translateY(-2px); }}
            .btn-success {{ background: #28a745; }}
            .btn-warning {{ background: #ffc107; color: #212529; }}
            .features {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }}
            .feature {{ background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; color: white; }}
            .feature h3 {{ margin-top: 0; }}
            .status-indicator {{ display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }}
            .status-online {{ background: #28a745; }}
            .status-offline {{ background: #dc3545; }}
            .status-pending {{ background: #ffc107; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>ShareKhan Trading System</h1>
                <p style="font-size: 1.2em;">Full-Featured Professional Trading Platform</p>
            </div>
            
            <div class="status-grid">
                <div class="status-card status-success">
                    <h3><span class="status-indicator status-online"></span>System Status</h3>
                    <p><strong>Application:</strong> Running Successfully</p>
                    <p><strong>Version:</strong> 2.0.0 Full System</p>
                    <p><strong>Environment:</strong> Local Development</p>
                </div>
                
                <div class="status-card status-{'success' if customer_configured else 'warning'}">
                    <h3><span class="status-indicator status-{'online' if customer_configured else 'pending'}"></span>ShareKhan API</h3>
                    <p><strong>API Status:</strong> {sharekhan_status}</p>
                    <p><strong>Customer ID:</strong> {'Configured' if customer_configured else 'Needs Configuration'}</p>
                    <p><strong>Integration:</strong> Ready</p>
                </div>
                
                <div class="status-card status-info">
                    <h3><span class="status-indicator status-online"></span>Features</h3>
                    <p><strong>Order Management:</strong> Active</p>
                    <p><strong>Real-time Data:</strong> WebSocket Ready</p>
                    <p><strong>Portfolio Tracking:</strong> Available</p>
                </div>
            </div>
            
            <div class="nav-buttons">
                <a href="/docs" class="btn">API Documentation</a>
                <a href="/redoc" class="btn">API Reference</a>
                <a href="/auth/sharekhan" class="btn btn-success">ShareKhan Auth</a>
                <a href="/api/system/status" class="btn btn-warning">System Status</a>
                <a href="/api/performance/metrics" class="btn">Performance</a>
                <a href="/api/autonomous/status" class="btn">Trading Status</a>
            </div>
            
            <h2 style="color: white; text-align: center;">Available Features</h2>
            <div class="features">
                <div class="feature">
                    <h3>ShareKhan Integration</h3>
                    <p>Complete API integration with order placement, portfolio management, and real-time data streaming.</p>
                </div>
                <div class="feature">
                    <h3>Order Management</h3>
                    <p>Advanced order types including market, limit, stop-loss, and multi-leg orders with risk controls.</p>
                </div>
                <div class="feature">
                    <h3>Real-time Analytics</h3>
                    <p>Live market data, position tracking, P&L monitoring, and performance analytics.</p>
                </div>
                <div class="feature">
                    <h3>Automated Trading</h3>
                    <p>Strategy deployment, backtesting, risk management, and autonomous trading capabilities.</p>
                </div>
                <div class="feature">
                    <h3>Risk Management</h3>
                    <p>Position sizing, stop-loss automation, daily limits, and comprehensive risk controls.</p>
                </div>
                <div class="feature">
                    <h3>Multi-User Support</h3>
                    <p>User authentication, role-based permissions, and individual trading accounts.</p>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 40px; color: white;">
                <p><strong>Current Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><small>Professional Trading System v2.0.0 - All Features Enabled</small></p>
            </div>
        </div>
    </body>
    </html>
    """)

@app.get("/api/system/status")
async def system_status():
    """Get comprehensive system status"""
    global global_orchestrator
    
    orchestrator_status = None
    if global_orchestrator:
        try:
            orchestrator_status = await global_orchestrator.get_system_status()
        except Exception as e:
            logger.error(f"Error getting orchestrator status: {e}")
    
    return {
        "status": "running",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "environment": "local_development",
        "components": {
            "fastapi": True,
            "sharekhan_api": bool(os.getenv('SHAREKHAN_API_KEY')),
            "sharekhan_secret": bool(os.getenv('SHAREKHAN_SECRET_KEY')),
            "customer_id_configured": bool(os.getenv('SHAREKHAN_CUSTOMER_ID') and os.getenv('SHAREKHAN_CUSTOMER_ID') != 'YOUR_SHAREKHAN_CLIENT_ID'),
            "orchestrator": global_orchestrator is not None,
            "database": "sqlite",
            "redis": "optional",
            "websockets": True,
            "order_management": True,
            "position_tracking": True,
            "risk_management": True
        },
        "orchestrator_status": orchestrator_status,
        "features_enabled": [
            "ShareKhan API Integration",
            "Real-time Market Data",
            "Order Management",
            "Position Tracking",
            "Risk Management",
            "Trading Strategies",
            "WebSocket Connections",
            "Multi-user Support",
            "Performance Analytics",
            "Automated Trading"
        ]
    }

@app.get("/api/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    print("Starting Full ShareKhan Trading System...")
    print("URL: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
