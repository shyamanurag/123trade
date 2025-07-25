"""
Daily Authentication Workflow - LEGACY MODULE
This module is kept for historical purposes but is NOT USED in production.
The system now uses ShareKhan exclusively via src/api/sharekhan_api.py
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import os
import logging

# NOTE: All KiteConnect functionality removed - using ShareKhan exclusively
# This module is disabled and kept for reference only

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/")
async def daily_auth_workflow_disabled():
    """Daily auth workflow disabled - use ShareKhan instead"""
    return JSONResponse({
        "success": False, 
        "message": "Zerodha authentication disabled - using ShareKhan exclusively",
        "redirect": "/auth/sharekhan"
    }) 