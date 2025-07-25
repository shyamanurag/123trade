"""
ShareKhan Authentication Callback Endpoint
Handles the redirect from ShareKhan API authentication flow
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/auth/sharekhan/callback")
async def sharekhan_auth_callback(request: Request, code: str = None, error: str = None):
    """
    Handle ShareKhan authentication callback
    This endpoint receives the authorization code from ShareKhan
    """
    try:
        if error:
            logger.error(f"ShareKhan authentication error: {error}")
            return HTMLResponse(f"""
            <html>
                <body>
                    <h2>❌ ShareKhan Authentication Failed</h2>
                    <p>Error: {error}</p>
                    <p>Please try authenticating again.</p>
                    <a href="/auth/sharekhan">Retry Authentication</a>
                </body>
            </html>
            """)
        
        if not code:
            logger.error("No authorization code received from ShareKhan")
            raise HTTPException(status_code=400, detail="Authorization code not received")
        
        logger.info(f"✅ Received ShareKhan authorization code: {code[:10]}...")
        
        # Store the authorization code for session generation
        # You'll use this code to generate access token
        
        return HTMLResponse(f"""
        <html>
            <body>
                <h2>✅ ShareKhan Authentication Successful!</h2>
                <p>Authorization code received successfully.</p>
                <p>Code: <code>{code}</code></p>
                <p>You can now close this window and return to your application.</p>
                <script>
                    // Auto-close window after 3 seconds
                    setTimeout(() => window.close(), 3000);
                </script>
            </body>
        </html>
        """)
        
    except Exception as e:
        logger.error(f"Error in ShareKhan callback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/auth/sharekhan")
async def sharekhan_auth_redirect():
    """
    Redirect user to ShareKhan authentication
    """
    try:
        # ShareKhan authentication URL
        api_key = os.getenv('SHAREKHAN_API_KEY')
        if not api_key:
            raise HTTPException(status_code=500, detail="ShareKhan API key not configured")
        
        # Build ShareKhan auth URL
        redirect_uri = "http://127.0.0.1:8000/auth/sharekhan/callback"
        sharekhan_auth_url = f"https://newtrade.sharekhan.com/authorize?api_key={api_key}&redirect_uri={redirect_uri}"
        
        return HTMLResponse(f"""
        <html>
            <body>
                <h2>🔐 ShareKhan Authentication</h2>
                <p>Click the button below to authenticate with ShareKhan:</p>
                <a href="{sharekhan_auth_url}" target="_blank" 
                   style="display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">
                   Authenticate with ShareKhan
                </a>
                <p><small>You will be redirected to ShareKhan's secure login page.</small></p>
            </body>
        </html>
        """)
        
    except Exception as e:
        logger.error(f"Error initiating ShareKhan auth: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 