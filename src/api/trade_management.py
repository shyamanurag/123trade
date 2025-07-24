from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/")
async def get_all_trades() -> List[Dict[str, Any]]:
    """Get all trades"""
    try:
        # ELIMINATED: Dangerous trade hiding that could hide real trading activity
        # ❌ # For now, return empty list - no trades yet
        # ❌ return []
        
        # SAFETY: Return error instead of hiding real trades
        logger.error("CRITICAL: Trade hiding ELIMINATED to prevent hidden trading activity")
        
        raise HTTPException(
            status_code=503, 
            detail="SAFETY: Trade data access disabled - real trade tracking required. Trade hiding eliminated for safety."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trades: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/live")
async def get_live_trades():
    """Get live trades data"""
    try:
        return {
            "status": "success",
            "trades": [],
            "message": "No live trades available",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting live trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/metrics")
async def get_all_user_metrics() -> Dict[str, Dict[str, Any]]:
    """Get metrics for all users"""
    try:
        # Return empty metrics for now
        return {}
    except Exception as e:
        logger.error(f"Error getting user metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{trade_id}")
async def get_trade_details(trade_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific trade"""
    try:
        # Trade not found since we're not persisting yet
        raise HTTPException(status_code=404, detail="Trade not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trade details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}")
async def get_user_trades(user_id: str) -> List[Dict[str, Any]]:
    """Get all trades for a specific user"""
    try:
        # Return empty list for now
        return []
    except Exception as e:
        logger.error(f"Error getting user trades: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}/metrics")
async def get_user_metrics(user_id: str) -> Dict[str, Any]:
    """Get detailed metrics for a specific user"""
    try:
        # Return basic metrics structure
        return {
            "user_id": user_id,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting user metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 