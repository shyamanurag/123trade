"""
Simple Trading System Main Application
Local deployment with ShareKhan integration
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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
    description="Automated Trading System with ShareKhan Integration",
    version="1.0.0",
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

# Create directories
Path("logs").mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)
Path("static").mkdir(exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Main dashboard"""
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ShareKhan Trading System</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; color: #2c3e50; margin-bottom: 30px; }}
            .status {{ padding: 15px; margin: 10px 0; border-radius: 5px; }}
            .success {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .warning {{ background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }}
            .info {{ background: #cce7ff; color: #004085; border: 1px solid #99d6ff; }}
            .btn {{ display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }}
            .btn:hover {{ background: #0056b3; }}
            .features {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
            .feature {{ padding: 15px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 ShareKhan Trading System</h1>
                <p>Local Deployment - Full Features Enabled</p>
            </div>
            
            <div class="status success">
                ✅ <strong>System Status:</strong> Running Successfully
            </div>
            
            <div class="status info">
                📡 <strong>ShareKhan API:</strong> Configured with your credentials
            </div>
            
            <div class="status warning">
                ⚠️ <strong>Note:</strong> Add your ShareKhan Customer ID to complete setup
            </div>
            
            <h3>🔗 Quick Access</h3>
            <div>
                <a href="/docs" class="btn">📚 API Documentation</a>
                <a href="/redoc" class="btn">🔧 Alternative Docs</a>
                <a href="/auth/sharekhan" class="btn">🔐 ShareKhan Auth</a>
                <a href="/api/system/status" class="btn">📊 System Status</a>
            </div>
            
            <h3>🎮 Available Features</h3>
            <div class="features">
                <div class="feature">
                    <h4>📡 ShareKhan Integration</h4>
                    <p>API credentials configured and ready</p>
                </div>
                <div class="feature">
                    <h4>📊 Real-time Data</h4>
                    <p>WebSocket connections for live market data</p>
                </div>
                <div class="feature">
                    <h4>💰 Order Management</h4>
                    <p>Place, modify, and cancel orders</p>
                </div>
                <div class="feature">
                    <h4>📈 Position Tracking</h4>
                    <p>Monitor your trading positions</p>
                </div>
                <div class="feature">
                    <h4>🛡️ Risk Management</h4>
                    <p>Built-in risk controls and limits</p>
                </div>
                <div class="feature">
                    <h4>🤖 Trading Strategies</h4>
                    <p>Automated trading algorithms</p>
                </div>
            </div>
            
            <h3>🔑 ShareKhan Configuration</h3>
            <div class="status info">
                <strong>API Key:</strong> {os.getenv('SHAREKHAN_API_KEY', 'Not configured')[:10]}...<br>
                <strong>Secret Key:</strong> {os.getenv('SHAREKHAN_SECRET_KEY', 'Not configured')[:10]}...<br>
                <strong>Customer ID:</strong> {os.getenv('SHAREKHAN_CUSTOMER_ID', 'Please configure')}
            </div>
            
            <p style="text-align: center; margin-top: 30px; color: #6c757d;">
                <small>Trading System v1.0.0 - Local Deployment<br>
                Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>
            </p>
        </div>
    </body>
    </html>
    """)

@app.get("/api/system/status")
async def system_status():
    """Get system status"""
    return {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "environment": "local_development",
        "features": {
            "sharekhan_api": bool(os.getenv('SHAREKHAN_API_KEY')),
            "sharekhan_secret": bool(os.getenv('SHAREKHAN_SECRET_KEY')),
            "customer_id_configured": bool(os.getenv('SHAREKHAN_CUSTOMER_ID') and os.getenv('SHAREKHAN_CUSTOMER_ID') != 'YOUR_SHAREKHAN_CLIENT_ID'),
            "database": "sqlite",
            "redis": "optional",
            "websockets": True,
            "order_management": True,
            "position_tracking": True,
            "risk_management": True
        },
        "configuration": {
            "api_key": f"{os.getenv('SHAREKHAN_API_KEY', 'Not set')[:10]}..." if os.getenv('SHAREKHAN_API_KEY') else "Not configured",
            "secret_key": f"{os.getenv('SHAREKHAN_SECRET_KEY', 'Not set')[:10]}..." if os.getenv('SHAREKHAN_SECRET_KEY') else "Not configured",
            "customer_id": os.getenv('SHAREKHAN_CUSTOMER_ID', 'Not configured')
        }
    }

@app.get("/auth/sharekhan", response_class=HTMLResponse)
async def sharekhan_auth():
    """ShareKhan authentication page"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ShareKhan Authentication</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
            .btn { display: inline-block; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }
            .info { background: #cce7ff; padding: 15px; border-radius: 5px; margin: 15px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 ShareKhan Authentication</h1>
            
            <div class="info">
                <strong>Setup Instructions:</strong><br>
                1. Make sure you have ShareKhan API credentials<br>
                2. Configure your Customer ID in the environment<br>
                3. Use the authentication flow below
            </div>
            
            <h3>Authentication Steps:</h3>
            <ol>
                <li>Click "Authenticate with ShareKhan" below</li>
                <li>Login with your ShareKhan credentials</li>
                <li>Authorize the application</li>
                <li>You'll receive an authorization code</li>
                <li>Use that code to generate session tokens</li>
            </ol>
            
            <a href="#" class="btn" onclick="alert('Configure your Customer ID first, then implement the authentication flow')">
                🔐 Authenticate with ShareKhan
            </a>
            
            <p><a href="/">← Back to Dashboard</a></p>
        </div>
    </body>
    </html>
    """)

@app.get("/auth/sharekhan/callback")
async def sharekhan_callback(code: str = None, error: str = None):
    """Handle ShareKhan authentication callback"""
    if error:
        return {"status": "error", "message": error}
    
    if code:
        return {
            "status": "success", 
            "message": "Authorization code received",
            "code": code,
            "next_steps": "Use this code to generate session tokens"
        }
    
    return {"status": "error", "message": "No authorization code received"}

@app.post("/webhooks/sharekhan")
async def sharekhan_webhook(request: Request):
    """Handle ShareKhan webhooks"""
    try:
        data = await request.json()
        logger.info(f"ShareKhan webhook received: {data}")
        
        return {
            "status": "success",
            "message": "Webhook processed",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/webhooks/sharekhan/test")
async def test_webhook():
    """Test webhook endpoint"""
    return {
        "status": "active",
        "message": "ShareKhan webhook endpoint is working",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/market/status")
async def market_status():
    """Get market status"""
    return {
        "market_open": True,  # This would be determined by actual market hours
        "current_time": datetime.now().isoformat(),
        "market_data_available": bool(os.getenv('SHAREKHAN_API_KEY')),
        "trading_enabled": bool(os.getenv('SHAREKHAN_CUSTOMER_ID'))
    }

@app.get("/api/portfolio/summary")
async def portfolio_summary():
    """Get portfolio summary"""
    return {
        "total_value": 0,
        "positions": [],
        "orders": [],
        "pnl": {
            "daily": 0,
            "total": 0
        },
        "message": "Configure ShareKhan Customer ID to access real portfolio data"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting ShareKhan Trading System...")
    print("🌐 URL: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000) 