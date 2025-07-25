"""
Zerodha Multi-User Authentication - LEGACY MODULE
This module is kept for historical purposes but is NOT USED in production.
The system now uses ShareKhan exclusively via src/core/multi_user_sharekhan_manager.py
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
async def zerodha_multi_user_auth_disabled():
    """Zerodha multi-user auth disabled - redirects to ShareKhan"""
    return """
    <html>
        <head><title>Zerodha Multi-User Auth Disabled</title></head>
        <body>
            <h1>⚠️ Zerodha Multi-User Authentication Disabled</h1>
            <p>This system now uses ShareKhan exclusively.</p>
            <p><a href="/auth/sharekhan">→ Use ShareKhan Authentication</a></p>
        </body>
    </html>
    """ 