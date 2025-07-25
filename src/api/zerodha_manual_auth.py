"""
Zerodha Manual Authentication - LEGACY MODULE  
This module is kept for historical purposes but is NOT USED in production.
The system now uses ShareKhan exclusively via src/api/sharekhan_api.py
"""

from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import os
import logging
from typing import Optional

# NOTE: All KiteConnect functionality removed - using ShareKhan exclusively
# This module is disabled and kept for reference only

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_class=HTMLResponse)  
async def zerodha_manual_auth_disabled():
    """Zerodha manual auth disabled - redirects to ShareKhan"""
    return """
    <html>
        <head><title>Zerodha Manual Auth Disabled</title></head>
        <body>
            <h1>⚠️ Zerodha Manual Authentication Disabled</h1>
            <p>This system now uses ShareKhan exclusively.</p>
            <p><a href="/auth/sharekhan">→ Use ShareKhan Authentication</a></p>
        </body>
    </html>
    """ 