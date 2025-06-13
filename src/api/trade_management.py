from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from datetime import datetime
import json
from ..core.risk_manager import RiskManager
from ..core.order_manager import OrderManager
from ..models import Trade, User
from ..auth import get_current_user

router = APIRouter()

@router.get("/trades/live")
async def get_live_trades(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get all live trades across users"""
    try:
        # Get all trades from Redis
        trades = []
        async with redis.from_url(current_user.config['redis_url']) as redis_client:
            # Get all trade keys
            trade_keys = await redis_client.keys("trade:*")
            
            for key in trade_keys:
                trade_data = await redis_client.get(key)
                if trade_data:
                    trade = json.loads(trade_data)
                    # Only include open trades
                    if trade['status'] == 'OPEN':
                        trades.append(trade)
        
        return trades
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/metrics")
async def get_user_metrics(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Dict[str, Any]]:
    """Get metrics for all users"""
    try:
        metrics = {}
        async with redis.from_url(current_user.config['redis_url']) as redis_client:
            # Get all user keys
            user_keys = await redis_client.keys("user:*")
            
            for key in user_keys:
                if ":metrics" in key:  # Only get metrics keys
                    user_id = key.split(":")[1]
                    metrics_data = await redis_client.get(key)
                    if metrics_data:
                        metrics[user_id] = json.loads(metrics_data)
        
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trades/{trade_id}")
async def get_trade_details(
    trade_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed information about a specific trade"""
    try:
        async with redis.from_url(current_user.config['redis_url']) as redis_client:
            trade_data = await redis_client.get(f"trade:{trade_id}")
            if not trade_data:
                raise HTTPException(status_code=404, detail="Trade not found")
            
            return json.loads(trade_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}/trades")
async def get_user_trades(
    user_id: str,
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get all trades for a specific user"""
    try:
        trades = []
        async with redis.from_url(current_user.config['redis_url']) as redis_client:
            # Get all trade keys for the user
            trade_keys = await redis_client.keys(f"trade:{user_id}:*")
            
            for key in trade_keys:
                trade_data = await redis_client.get(key)
                if trade_data:
                    trades.append(json.loads(trade_data))
        
        return trades
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}/metrics")
async def get_user_metrics(
    user_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed metrics for a specific user"""
    try:
        async with redis.from_url(current_user.config['redis_url']) as redis_client:
            metrics_data = await redis_client.get(f"user:{user_id}:metrics")
            if not metrics_data:
                raise HTTPException(status_code=404, detail="User metrics not found")
            
            return json.loads(metrics_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 