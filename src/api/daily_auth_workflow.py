"""
Daily Authentication Workflow API
Streamlined daily auth process for pre-configured Zerodha broker
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Optional
import logging
import os
import requests
from datetime import datetime, timedelta
from kiteconnect import KiteConnect

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/daily-auth", tags=["daily-auth"])

# Pre-configured Zerodha credentials (from environment or hardcoded)
ZERODHA_API_KEY = "sylcoq492qz6f7ej"
ZERODHA_API_SECRET = "jm3h4iejwnxr4ngmma2qxccpkhevo8sy"
ZERODHA_CLIENT_ID = "QSW899"

class DailyAuthRequest(BaseModel):
    """Daily authentication request"""
    request_token: str

class AuthStatusResponse(BaseModel):
    """Authentication status response"""
    authenticated: bool
    user_id: Optional[str] = None
    expires_at: Optional[str] = None
    trading_ready: bool = False
    message: str

# HTML template for streamlined daily auth
DAILY_AUTH_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Daily Trading Authentication</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            text-align: center;
        }
        h1 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 2.2em;
        }
        .subtitle {
            color: #7f8c8d;
            margin-bottom: 30px;
            font-size: 1.1em;
        }
        .status {
            padding: 20px;
            margin: 20px 0;
            border-radius: 10px;
            font-weight: 500;
        }
        .status.success { 
            background: linear-gradient(135deg, #a8e6cf, #88d8a3);
            color: #2d5a41;
        }
        .status.error { 
            background: linear-gradient(135deg, #ffaaa5, #ff8a80);
            color: #c62828;
        }
        .status.info { 
            background: linear-gradient(135deg, #a8d8ea, #7fcdff);
            color: #1565c0;
        }
        .auth-button {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 15px 40px;
            border: none;
            border-radius: 50px;
            font-size: 1.2em;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            margin: 20px 0;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        .auth-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }
        .manual-section {
            margin-top: 40px;
            padding-top: 30px;
            border-top: 1px solid #ecf0f1;
        }
        .token-input {
            width: 100%;
            padding: 15px;
            border: 2px solid #ecf0f1;
            border-radius: 10px;
            font-size: 1em;
            margin: 15px 0;
            box-sizing: border-box;
        }
        .token-input:focus {
            outline: none;
            border-color: #667eea;
        }
        .submit-button {
            background: linear-gradient(135deg, #56ab2f, #a8e6cf);
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 25px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .submit-button:hover {
            transform: translateY(-1px);
        }
        .info-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: left;
        }
        .step {
            display: flex;
            align-items: center;
            margin: 10px 0;
        }
        .step-number {
            background: #667eea;
            color: white;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 15px;
            font-weight: bold;
        }
        @media (max-width: 768px) {
            body { padding: 10px; }
            .container { padding: 20px; }
            h1 { font-size: 1.8em; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Daily Trading Auth</h1>
        <p class="subtitle">Quick authentication for autonomous trading</p>
        
        {status_html}
        
        <div class="info-card">
            <h3>📋 Simple 3-Step Process:</h3>
            <div class="step">
                <div class="step-number">1</div>
                <div>Click "Authenticate with Zerodha" below</div>
            </div>
            <div class="step">
                <div class="step-number">2</div>
                <div>Enter your Zerodha PIN on their website</div>
            </div>
            <div class="step">
                <div class="step-number">3</div>
                <div>You'll be redirected back automatically</div>
            </div>
        </div>

        <a href="{auth_url}" class="auth-button">
            🔐 Authenticate with Zerodha
        </a>

        <div class="manual-section">
            <h3>📝 Manual Token Entry</h3>
            <p>If redirect fails, paste the request_token from Zerodha URL:</p>
            <form id="tokenForm" onsubmit="submitToken(event)">
                <input type="text" id="requestToken" class="token-input" 
                       placeholder="Paste request_token here..." required>
                <br>
                <button type="submit" class="submit-button">Submit Token</button>
            </form>
        </div>
        
        <div class="info-card" style="margin-top: 30px;">
            <h4>🔧 System Status:</h4>
            <p><strong>API Key:</strong> {api_key_masked}</p>
            <p><strong>Client ID:</strong> {client_id}</p>
            <p><strong>Auth Status:</strong> {auth_status}</p>
            <p><strong>Trading Ready:</strong> {trading_ready}</p>
        </div>
    </div>

    <script>
        async function submitToken(event) {
            event.preventDefault();
            const token = document.getElementById('requestToken').value.trim();
            
            if (!token) {
                alert('Please enter a request token');
                return;
            }

            try {
                const response = await fetch('/daily-auth/submit-token', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({request_token: token})
                });

                const result = await response.json();
                
                if (result.success) {
                    location.reload();
                } else {
                    alert('Authentication failed: ' + result.message);
                }
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }

        // Auto-refresh status every 30 seconds
        setInterval(() => {
            fetch('/daily-auth/status')
                .then(r => r.json())
                .then(data => {
                    if (data.trading_ready) {
                        location.reload();
                    }
                })
                .catch(() => {});
        }, 30000);
    </script>
</body>
</html>
"""

@router.get("/", response_class=HTMLResponse)
async def daily_auth_page():
    """Main daily authentication page"""
    try:
        # Check current auth status
        auth_status = await get_auth_status()
        
        # Generate auth URL
        kite = KiteConnect(api_key=ZERODHA_API_KEY)
        auth_url = kite.login_url()
        
        # Determine status HTML
        if auth_status.authenticated and auth_status.trading_ready:
            status_html = f'''
            <div class="status success">
                ✅ <strong>Authenticated & Trading Ready!</strong><br>
                User: {auth_status.user_id}<br>
                Expires: {auth_status.expires_at}<br>
                🚀 Autonomous trading is active
            </div>
            '''
        elif auth_status.authenticated:
            status_html = f'''
            <div class="status info">
                🔐 <strong>Authenticated but starting trading...</strong><br>
                User: {auth_status.user_id}<br>
                Expires: {auth_status.expires_at}
            </div>
            '''
        else:
            status_html = '''
            <div class="status info">
                🔑 <strong>Ready for daily authentication</strong><br>
                Please authenticate to start trading
            </div>
            '''
        
        # Render HTML
        html_content = DAILY_AUTH_HTML.format(
            status_html=status_html,
            auth_url=auth_url,
            api_key_masked=ZERODHA_API_KEY[:6] + "..." + ZERODHA_API_KEY[-4:],
            client_id=ZERODHA_CLIENT_ID,
            auth_status="✅ Valid" if auth_status.authenticated else "❌ Needs Auth",
            trading_ready="✅ Active" if auth_status.trading_ready else "❌ Inactive"
        )
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Error generating daily auth page: {e}")
        return HTMLResponse(content=f"<h1>Error</h1><p>{str(e)}</p>", status_code=500)

@router.get("/status")
async def get_auth_status() -> AuthStatusResponse:
    """Get current authentication and trading status"""
    try:
        # Check if we have a valid access token
        # This would typically check Redis or database
        # For now, we'll check if autonomous trading is active
        
        # Check autonomous trading status
        autonomous_response = requests.get(
            "http://localhost:8000/api/v1/autonomous/status",
            timeout=5
        )
        
        if autonomous_response.status_code == 200:
            autonomous_data = autonomous_response.json()
            trading_data = autonomous_data.get('data', {})
            is_trading_active = trading_data.get('is_active', False)
            
            return AuthStatusResponse(
                authenticated=True,  # Assume authenticated if trading is active
                user_id=ZERODHA_CLIENT_ID,
                expires_at=(datetime.now() + timedelta(hours=8)).isoformat(),
                trading_ready=is_trading_active,
                message="Authentication status retrieved"
            )
        else:
            return AuthStatusResponse(
                authenticated=False,
                trading_ready=False,
                message="Need daily authentication"
            )
            
    except Exception as e:
        logger.error(f"Error checking auth status: {e}")
        return AuthStatusResponse(
            authenticated=False,
            trading_ready=False,
            message=f"Status check failed: {str(e)}"
        )

@router.post("/submit-token")
async def submit_daily_token(
    request: DailyAuthRequest, 
    background_tasks: BackgroundTasks
):
    """Submit daily authentication token"""
    try:
        # Process the token with Zerodha
        kite = KiteConnect(api_key=ZERODHA_API_KEY)
        
        # Generate session
        data = kite.generate_session(
            request_token=request.request_token,
            api_secret=ZERODHA_API_SECRET
        )
        
        access_token = data["access_token"]
        user_id = data["user_id"]
        
        # Store the token properly in Redis (not just environment variables)
        try:
            import redis.asyncio as redis
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            redis_client = redis.from_url(redis_url)
            
            # Calculate proper expiry (6 AM next day)
            from datetime import time
            now = datetime.now()
            tomorrow_6am = datetime.combine(
                now.date() + timedelta(days=1),
                time(6, 0, 0)
            )
            
            if now.time() < time(6, 0, 0):
                expiry = datetime.combine(now.date(), time(6, 0, 0))  # Today 6 AM
            else:
                expiry = tomorrow_6am  # Tomorrow 6 AM
            
            # Store token and expiry in Redis (will replace existing token)
            await redis_client.set(f"zerodha:token:{user_id}", access_token)
            await redis_client.set(f"zerodha:token_expiry:{user_id}", expiry.isoformat())
            
            # Also set environment variables for backward compatibility
            os.environ['ZERODHA_ACCESS_TOKEN'] = access_token
            os.environ['ZERODHA_USER_ID'] = user_id
            
            await redis_client.close()
            
            logger.info(f"Token stored in Redis for user {user_id}, expires at {expiry}")
            
        except Exception as redis_error:
            logger.error(f"Failed to store token in Redis: {redis_error}")
            # Fallback to environment variables only
            os.environ['ZERODHA_ACCESS_TOKEN'] = access_token
            os.environ['ZERODHA_USER_ID'] = user_id
        
        # Start autonomous trading in background
        background_tasks.add_task(start_autonomous_trading_after_auth)
        
        logger.info(f"Daily authentication successful for user: {user_id}")
        
        return {
            "success": True,
            "message": "Authentication successful, starting trading...",
            "user_id": user_id,
            "expires_at": expiry.isoformat() if 'expiry' in locals() else (datetime.now() + timedelta(hours=8)).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Daily authentication failed: {e}")
        return {
            "success": False,
            "message": f"Authentication failed: {str(e)}"
        }

async def start_autonomous_trading_after_auth():
    """Start autonomous trading after successful authentication"""
    try:
        # Wait a moment for token to be processed
        import asyncio
        await asyncio.sleep(2)
        
        # IMPORTANT: Refresh connections to pick up new token from Redis
        logger.info("Refreshing connections after authentication...")
        try:
            # Get the orchestrator instance and refresh Zerodha connection
            from src.core.orchestrator import TradingOrchestrator
            orchestrator = TradingOrchestrator.get_instance()
            
            if orchestrator.connection_manager:
                refresh_success = await orchestrator.connection_manager.refresh_zerodha_connection()
                if refresh_success:
                    logger.info("✅ Zerodha connection refreshed successfully after authentication")
                else:
                    logger.warning("⚠️ Zerodha connection refresh failed, but continuing with trading start")
            
        except Exception as refresh_error:
            logger.error(f"Connection refresh error: {refresh_error}")
            # Continue anyway - the token might still work
        
        # Start autonomous trading
        start_response = requests.post(
            "http://localhost:8000/api/v1/autonomous/start",
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        if start_response.status_code == 200:
            logger.info("Autonomous trading started successfully after authentication")
        else:
            logger.error(f"Failed to start trading after auth: {start_response.text}")
            
    except Exception as e:
        logger.error(f"Error starting trading after auth: {e}")

@router.get("/callback")
async def handle_zerodha_callback(request_token: str, background_tasks: BackgroundTasks):
    """Handle Zerodha authentication callback"""
    try:
        # Process the token
        auth_request = DailyAuthRequest(request_token=request_token)
        result = await submit_daily_token(auth_request, background_tasks)
        
        if result.get("success"):
            return HTMLResponse(content="""
            <html>
                <head>
                    <title>Authentication Successful</title>
                    <meta http-equiv="refresh" content="3;url=/daily-auth">
                </head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>✅ Authentication Successful!</h1>
                    <p>Starting autonomous trading...</p>
                    <p>Redirecting back to dashboard...</p>
                </body>
            </html>
            """)
        else:
            return HTMLResponse(content=f"""
            <html>
                <head><title>Authentication Failed</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>❌ Authentication Failed</h1>
                    <p>{result.get('message', 'Unknown error')}</p>
                    <a href="/daily-auth">Try Again</a>
                </body>
            </html>
            """, status_code=400)
            
    except Exception as e:
        logger.error(f"Callback handling failed: {e}")
        return HTMLResponse(content=f"""
        <html>
            <head><title>Error</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>❌ Error</h1>
                <p>{str(e)}</p>
                <a href="/daily-auth">Try Again</a>
            </body>
        </html>
        """, status_code=500) 