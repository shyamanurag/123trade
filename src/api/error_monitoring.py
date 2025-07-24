"""
Error Monitoring API
Provides endpoints for monitoring errors and system health
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from src.core.error_handler import error_handler

router = APIRouter()

@router.get("/errors/stats")
async def get_error_statistics():
    """
    Get error statistics
    
    Returns error counts, types, and recent errors
    """
    try:
        stats = error_handler.error_tracker.get_error_stats()
        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get error stats: {str(e)}")

@router.get("/errors/recent")
async def get_recent_errors(limit: int = 10):
    """
    Get recent errors
    
    Args:
        limit: Maximum number of errors to return (default: 10, max: 100)
    """
    try:
        limit = min(limit, 100)  # Cap at 100
        recent_errors = error_handler.error_tracker.error_history[-limit:]
        
        return {
            "status": "success",
            "data": {
                "errors": recent_errors,
                "count": len(recent_errors),
                "total_errors": sum(error_handler.error_tracker.error_counts.values())
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent errors: {str(e)}")

@router.get("/errors/types")
async def get_error_types():
    """
    Get error types and their counts
    
    Returns a breakdown of errors by type
    """
    try:
        error_counts = error_handler.error_tracker.error_counts
        
        # Sort by count descending
        sorted_errors = sorted(
            error_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            "status": "success",
            "data": {
                "error_types": [
                    {"type": error_type, "count": count}
                    for error_type, count in sorted_errors
                ],
                "total_types": len(error_counts),
                "total_errors": sum(error_counts.values())
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get error types: {str(e)}")

@router.post("/errors/clear")
async def clear_error_history():
    """
    Clear error history (admin only)
    
    Resets error counts and history
    """
    try:
        # Clear error tracking data
        error_handler.error_tracker.error_counts.clear()
        error_handler.error_tracker.error_history.clear()
        
        return {
            "status": "success",
            "message": "Error history cleared",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear error history: {str(e)}")

@router.get("/errors/health")
async def get_error_health():
    """
    Get error health status
    
    Returns health status based on error rates
    """
    try:
        total_errors = sum(error_handler.error_tracker.error_counts.values())
        error_types = len(error_handler.error_tracker.error_counts)
        
        # Calculate error rate (last hour)
        recent_errors = [
            error for error in error_handler.error_tracker.error_history
            if datetime.fromisoformat(error["timestamp"]) > datetime.now() - timedelta(hours=1)
        ]
        
        error_rate = len(recent_errors)
        
        # Determine health status
        if error_rate == 0:
            health_status = "healthy"
        elif error_rate < 10:
            health_status = "good"
        elif error_rate < 50:
            health_status = "warning"
        else:
            health_status = "critical"
        
        return {
            "status": "success",
            "data": {
                "health_status": health_status,
                "error_rate_per_hour": error_rate,
                "total_errors": total_errors,
                "error_types": error_types,
                "recent_errors": len(recent_errors)
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get error health: {str(e)}") 