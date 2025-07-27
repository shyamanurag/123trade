"""
Dashboard API v1 Endpoints for React Frontend
Provides dashboard data, analytics, and system metrics
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
from .auth_api import get_current_user

router = APIRouter(prefix="/api", tags=["dashboard"])

@router.get("/dashboard")
async def get_dashboard_data(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get comprehensive dashboard data including:
    - Portfolio metrics
    - Recent trades
    - System alerts
    - Performance data
    """
    try:
        # Import orchestrator to get real data
        from ..main import global_orchestrator
        
        # Get real portfolio metrics
        portfolio_data = {}
        if hasattr(global_orchestrator, 'get_portfolio_summary'):
            portfolio_data = await global_orchestrator.get_portfolio_summary(current_user.id)
        
        # Get real trading metrics
        trading_metrics = {}
        if hasattr(global_orchestrator, 'get_trading_metrics'):
            trading_metrics = await global_orchestrator.get_trading_metrics(current_user.id)
        
        # Get recent trades
        recent_trades = []
        if hasattr(global_orchestrator, 'get_recent_trades'):
            recent_trades = await global_orchestrator.get_recent_trades(current_user.id, limit=10)
        
        # Get system alerts
        alerts = []
        if hasattr(global_orchestrator, 'get_system_alerts'):
            alerts = await global_orchestrator.get_system_alerts(current_user.id)
        
        # Get performance data
        performance_data = []
        if hasattr(global_orchestrator, 'get_performance_history'):
            performance_data = await global_orchestrator.get_performance_history(
                current_user.id, 
                days=7
            )
        
        # Compile comprehensive dashboard response
        dashboard_data = {
            "metrics": {
                "portfolio_value": portfolio_data.get("total_value", 0),
                "portfolio_change": portfolio_data.get("day_change_percent", 0),
                "todays_pnl": trading_metrics.get("todays_pnl", 0),
                "pnl_percentage": trading_metrics.get("pnl_percentage", 0),
                "active_positions": portfolio_data.get("active_positions", 0),
                "positions_change": trading_metrics.get("positions_change", 0),
                "connected_users": global_orchestrator.get_connected_users_count() if hasattr(global_orchestrator, 'get_connected_users_count') else 0
            },
            "recent_trades": recent_trades,
            "alerts": alerts,
            "performance_data": performance_data,
            "last_updated": datetime.utcnow().isoformat(),
            "user_info": {
                "id": current_user.id,
                "username": current_user.username,
                "role": current_user.role
            }
        }
        
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard data: {str(e)}"
        )

@router.get("/market/data")
async def get_market_data(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Get real-time market data"""
    try:
        from ..main import global_orchestrator
        
        market_data = {}
        if hasattr(global_orchestrator, 'get_market_data'):
            market_data = await global_orchestrator.get_market_data()
        
        return {
            "market_data": market_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch market data: {str(e)}"
        )

@router.get("/market/indices")
async def get_live_indices(current_user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """Get live market indices data"""
    try:
        from ..main import global_orchestrator
        
        indices = []
        if hasattr(global_orchestrator, 'get_live_indices'):
            indices = await global_orchestrator.get_live_indices()
        
        return indices
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch live indices: {str(e)}"
        )

@router.get("/trades")
async def get_trades(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get user's trading history"""
    try:
        from ..main import global_orchestrator
        
        trades = []
        total_count = 0
        
        if hasattr(global_orchestrator, 'get_user_trades'):
            trades, total_count = await global_orchestrator.get_user_trades(
                current_user.id, 
                limit=limit, 
                offset=offset
            )
        
        return {
            "trades": trades,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch trades: {str(e)}"
        )

@router.post("/trades")
async def create_trade(
    trade_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Submit a new trade"""
    try:
        from ..main import global_orchestrator
        
        if not hasattr(global_orchestrator, 'submit_trade'):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Trading service not available"
            )
        
        # Submit trade through orchestrator
        trade_result = await global_orchestrator.submit_trade(
            user_id=current_user.id,
            trade_data=trade_data
        )
        
        return {
            "trade": trade_result,
            "status": "submitted",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit trade: {str(e)}"
        )

@router.get("/analytics")
async def get_analytics(
    timeframe: str = "1d",
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get trading analytics and performance metrics"""
    try:
        from ..main import global_orchestrator
        
        analytics = {}
        if hasattr(global_orchestrator, 'get_user_analytics'):
            analytics = await global_orchestrator.get_user_analytics(
                current_user.id, 
                timeframe=timeframe
            )
        
        return {
            "analytics": analytics,
            "timeframe": timeframe,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch analytics: {str(e)}"
        )

@router.get("/analytics/performance")
async def get_performance_metrics(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Get detailed performance metrics"""
    try:
        from ..main import global_orchestrator
        
        performance = {}
        if hasattr(global_orchestrator, 'get_performance_metrics'):
            performance = await global_orchestrator.get_performance_metrics(current_user.id)
        
        return performance
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch performance metrics: {str(e)}"
        ) 