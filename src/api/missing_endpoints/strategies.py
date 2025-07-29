from fastapi import APIRouter
from typing import List, Dict

router = APIRouter()

@router.get("/api/strategies")
async def get_strategies():
    """Get available trading strategies"""
    strategies = [
        {
            "id": "momentum_surfer",
            "name": "Momentum Surfer",
            "description": "Rides momentum waves with trend confirmation",
            "status": "active",
            "performance": {"return": 12.5, "sharpe": 1.8}
        },
        {
            "id": "volatility_explosion",
            "name": "Volatility Explosion",
            "description": "Captures volatility breakouts",
            "status": "active", 
            "performance": {"return": 15.2, "sharpe": 2.1}
        },
        {
            "id": "volume_profile_scalper",
            "name": "Volume Profile Scalper",
            "description": "Scalps based on volume profile analysis",
            "status": "active",
            "performance": {"return": 8.7, "sharpe": 1.5}
        },
        {
            "id": "news_impact_scalper",
            "name": "News Impact Scalper", 
            "description": "Reacts to news-driven price movements",
            "status": "active",
            "performance": {"return": 10.3, "sharpe": 1.6}
        }
    ]
    
    return {
        "success": True,
        "strategies": strategies,
        "total": len(strategies)
    }
