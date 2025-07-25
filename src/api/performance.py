from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..models.responses import BaseResponse, TradeResponse, PositionResponse

# Fixed import path
try:
    from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
except ImportError:
    from ..core.sharekhan_orchestrator import ShareKhanTradingOrchestrator

import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/performance/daily-pnl", response_model=BaseResponse)
async def get_daily_pnl(
    date: Optional[datetime] = None,
    orchestrator: ShareKhanTradingOrchestrator = Depends()
):
    """Get daily PnL metrics from ShareKhan"""
    try:
        if not date:
            date = datetime.utcnow()
        
        if orchestrator.metrics_service is None:
            return BaseResponse(
                success=False,
                message="Metrics service not yet initialized",
                data={"error": "Service initializing", "date": date.isoformat()}
            )
        
        metrics = await orchestrator.metrics_service.get_daily_pnl(date)
        return BaseResponse(
            success=True,
            message="Daily PnL retrieved successfully",
            data=metrics
        )
    except Exception as e:
        logger.error(f"Error getting daily PnL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/positions", response_model=List[Dict[str, Any]])
async def get_positions(
    orchestrator: ShareKhanTradingOrchestrator = Depends()
):
    """Get current positions from ShareKhan"""
    try:
        if orchestrator.position_manager is None:
            return []
        
        positions = await orchestrator.position_manager.get_all_positions()
        return positions
    except Exception as e:
        logger.error(f"Error getting positions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/trades", response_model=List[Dict[str, Any]])
async def get_trades(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    orchestrator: ShareKhanTradingOrchestrator = Depends()
):
    """Get trade history from ShareKhan"""
    try:
        if orchestrator.trade_manager is None:
            return []
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        trades = await orchestrator.trade_manager.get_trades(start_date, end_date)
        return trades
    except Exception as e:
        logger.error(f"Error getting trades: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/metrics", response_model=Dict[str, Any])
async def get_performance_metrics(
    orchestrator: ShareKhanTradingOrchestrator = Depends()
):
    """Get comprehensive performance metrics from ShareKhan system"""
    try:
        # Get real system status
        system_status = await orchestrator.get_system_status()
        
        # Get metrics if service is available
        performance_data = {}
        if orchestrator.metrics_service:
            try:
                performance_data = await orchestrator.metrics_service.get_all_metrics()
            except Exception as e:
                logger.warning(f"Could not get performance metrics: {e}")
                performance_data = {"error": str(e)}
        
        return {
            "success": True,
            "message": "Performance metrics retrieved from ShareKhan system",
            "data": {
                "system_status": system_status,
                "performance_metrics": performance_data,
                "services_available": {
                    "metrics_service": orchestrator.metrics_service is not None,
                    "position_manager": orchestrator.position_manager is not None,
                    "trade_manager": orchestrator.trade_manager is not None,
                    "risk_manager": orchestrator.risk_manager is not None
                },
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/risk", response_model=Dict[str, Any])
async def get_risk_metrics(
    orchestrator: ShareKhanTradingOrchestrator = Depends()
):
    """Get risk metrics from ShareKhan"""
    try:
        if orchestrator.risk_manager is None:
            return {
                "success": False,
                "message": "Risk manager not yet initialized",
                "data": {"error": "Service initializing"}
            }
        
        risk_metrics = await orchestrator.risk_manager.get_risk_metrics()
        return {
            "success": True,
            "message": "Risk metrics retrieved successfully",
            "data": risk_metrics
        }
    except Exception as e:
        logger.error(f"Error getting risk metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 