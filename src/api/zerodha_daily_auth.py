"""
Zerodha Daily Authentication API - LEGACY MODULE
This module is kept for historical purposes but is NOT USED in production.
The system now uses ShareKhan exclusively via src/api/sharekhan_api.py
"""

from fastapi import APIRouter, HTTPException, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional
import os
import logging
import asyncio
import json
from datetime import datetime

# NOTE: KiteConnect removed - using ShareKhan exclusively
# This module is disabled and kept for reference only

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def zerodha_auth_disabled():
    """Zerodha authentication disabled - redirects to ShareKhan"""
    return """
    <html>
        <head><title>Zerodha Authentication Disabled</title></head>
        <body>
            <h1>⚠️ Zerodha Authentication Disabled</h1>
            <p>This system now uses ShareKhan exclusively.</p>
            <p><a href="/auth/sharekhan">→ Use ShareKhan Authentication</a></p>
        </body>
    </html>
    """ 