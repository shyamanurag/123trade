from fastapi import APIRouter
import time
import asyncio
from datetime import datetime

router = APIRouter()

@router.get("/api/system/api-health")
async def get_api_health():
    """Get API health status"""
    start_time = time.time()
    
    # Simulate some processing
    await asyncio.sleep(0.01)
    
    response_time = (time.time() - start_time) * 1000  # Convert to ms
    
    return {
        "success": True,
        "status": "healthy",
        "response_time_ms": round(response_time, 2),
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "environment": "production"
    }
