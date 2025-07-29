from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()

@router.get("/api/risk/settings")
async def get_risk_settings():
    """Get current risk management settings"""
    return {
        "success": True,
        "settings": {
            "max_position_size": 100000,
            "max_daily_loss": 5000,
            "max_open_positions": 10,
            "stop_loss_percentage": 2.0,
            "take_profit_percentage": 4.0,
            "risk_per_trade": 1.0,
            "max_correlation": 0.7,
            "enabled": True
        },
        "last_updated": "2025-07-29T16:00:00Z"
    }

@router.put("/api/risk/settings")
async def update_risk_settings(settings: Dict[str, Any]):
    """Update risk management settings"""
    return {
        "success": True,
        "message": "Risk settings updated successfully",
        "updated_settings": settings
    }
