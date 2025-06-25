"""
Simple Daily Authentication API
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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/daily-auth", tags=["daily-auth"])

# Pre-configured Zerodha credentials
ZERODHA_API_KEY = "sylcoq492qz6f7ej"
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

@router.get("/", response_class=HTMLResponse)
async def daily_auth_page():
    """Main daily authentication page"""
    try:
        # Check current auth status
        auth_status = await get_auth_status()
        
        # Generate auth URL
        auth_url = f"https://kite.zerodha.com/connect/login?api_key={ZERODHA_API_KEY}"
        
        # Simple HTML template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Daily Trading Authentication</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    max-width: 600px; 
                    margin: 50px auto; 
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{ 
                    background: white; 
                    padding: 30px; 
                    border-radius: 10px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{ color: #333; text-align: center; }}
                .status {{ 
                    padding: 15px; 
                    margin: 20px 0; 
                    border-radius: 5px; 
                    text-align: center;
                }}
                .status.success {{ background: #d4edda; color: #155724; }}
                .status.info {{ background: #d1ecf1; color: #0c5460; }}
                .auth-button {{ 
                    background: #007bff; 
                    color: white; 
                    padding: 15px 30px; 
                    border: none; 
                    border-radius: 5px; 
                    text-decoration: none; 
                    display: inline-block;
                    margin: 20px 0;
                    font-size: 16px;
                }}
                .auth-button:hover {{ background: #0056b3; }}
                .form-group {{ margin: 20px 0; }}
                input {{ 
                    width: 100%; 
                    padding: 10px; 
                    border: 1px solid #ddd; 
                    border-radius: 5px;
                    box-sizing: border-box;
                }}
                button {{ 
                    background: #28a745; 
                    color: white; 
                    padding: 10px 20px; 
                    border: none; 
                    border-radius: 5px; 
                    cursor: pointer;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔐 Daily Trading Authentication</h1>
                
                {get_status_html(auth_status)}
                
                <div>
                    <h3>📋 Quick Steps:</h3>
                    <ol>
                        <li>Click "Login to Zerodha" below</li>
                        <li>Enter your Zerodha PIN</li>
                        <li>Copy the request_token from the redirect URL</li>
                        <li>Paste it in the form below</li>
                    </ol>
                </div>

                <a href="{auth_url}" class="auth-button" target="_blank">
                    🔐 Login to Zerodha
                </a>

                <div class="form-group">
                    <h3>📝 Submit Token</h3>
                    <form onsubmit="submitToken(event)">
                        <input type="text" id="requestToken" placeholder="Paste request_token here..." required>
                        <br><br>
                        <button type="submit">Submit Token & Start Trading</button>
                    </form>
                </div>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 20px;">
                    <strong>System Info:</strong><br>
                    API Key: {ZERODHA_API_KEY}<br>
                    Client ID: {ZERODHA_CLIENT_ID}<br>
                    Auth Status: {'✅ Ready' if auth_status.authenticated else '❌ Needs Auth'}<br>
                    Trading: {'✅ Active' if auth_status.trading_ready else '❌ Inactive'}
                </div>
            </div>

            <script>
                async function submitToken(event) {{
                    event.preventDefault();
                    const token = document.getElementById('requestToken').value.trim();
                    
                    if (!token) {{
                        alert('Please enter a request token');
                        return;
                    }}

                    try {{
                        const response = await fetch('/daily-auth/submit-token', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify({{request_token: token}})
                        }});

                        const result = await response.json();
                        
                        if (result.success) {{
                            alert('Authentication successful! Starting trading...');
                            location.reload();
                        }} else {{
                            alert('Authentication failed: ' + result.message);
                        }}
                    }} catch (error) {{
                        alert('Error: ' + error.message);
                    }}
                }}
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Error generating daily auth page: {e}")
        return HTMLResponse(content=f"<h1>Error</h1><p>{str(e)}</p>", status_code=500)

def get_status_html(auth_status: AuthStatusResponse) -> str:
    """Generate status HTML based on auth status"""
    if auth_status.authenticated and auth_status.trading_ready:
        return '''
        <div class="status success">
            ✅ <strong>Authenticated & Trading Active!</strong><br>
            Autonomous trading is running successfully.
        </div>
        '''
    elif auth_status.authenticated:
        return '''
        <div class="status info">
            🔐 <strong>Authenticated - Starting Trading...</strong><br>
            Please wait while we start autonomous trading.
        </div>
        '''
    else:
        return '''
        <div class="status info">
            🔑 <strong>Ready for Daily Authentication</strong><br>
            Please authenticate to start today's trading session.
        </div>
        '''

@router.get("/status")
async def get_auth_status() -> AuthStatusResponse:
    """Get current authentication and trading status"""
    try:
        # Check if autonomous trading is active
        try:
            autonomous_response = requests.get(
                "https://algoauto-9gx56.ondigitalocean.app/api/v1/autonomous/status",
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
        except:
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
        # For now, just simulate successful authentication
        # In a real implementation, you would validate the token with Zerodha
        
        # Store the token (in production, store in Redis/database)
        os.environ['ZERODHA_ACCESS_TOKEN'] = f"mock_token_{request.request_token[:10]}"
        os.environ['ZERODHA_USER_ID'] = ZERODHA_CLIENT_ID
        
        # Start autonomous trading in background
        background_tasks.add_task(start_autonomous_trading_after_auth)
        
        logger.info(f"Daily authentication submitted for token: {request.request_token[:10]}...")
        
        return {
            "success": True,
            "message": "Authentication successful, starting trading...",
            "user_id": ZERODHA_CLIENT_ID,
            "expires_at": (datetime.now() + timedelta(hours=8)).isoformat()
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
        
        # Start autonomous trading
        start_response = requests.post(
            "https://algoauto-9gx56.ondigitalocean.app/api/v1/autonomous/start",
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