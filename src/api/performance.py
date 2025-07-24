from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from datetime import datetime, timedelta
from ..models.responses import BaseResponse, TradeResponse, PositionResponse
from ..core.orchestrator import TradingOrchestrator
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/performance/daily-pnl", response_model=BaseResponse)
async def get_daily_pnl(
    date: datetime = None,
    orchestrator: TradingOrchestrator = Depends()
):
    """Get daily PnL metrics"""
    try:
        if not date:
            date = datetime.utcnow()
        
        metrics = await orchestrator.metrics_service.get_daily_pnl(date)
        return BaseResponse(
            success=True,
            message="Daily PnL retrieved successfully",
            data=metrics
        )
    except Exception as e:
        logger.error(f"Error getting daily PnL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/positions", response_model=List[PositionResponse])
async def get_positions(
    orchestrator: TradingOrchestrator = Depends()
):
    """Get current positions"""
    try:
        positions = await orchestrator.position_manager.get_all_positions()
        return [
            PositionResponse(
                success=True,
                message="Position retrieved successfully",
                position_id=pos.position_id,
                symbol=pos.symbol,
                quantity=pos.quantity,
                average_price=pos.average_price,
                current_price=pos.current_price,
                unrealized_pnl=pos.unrealized_pnl,
                realized_pnl=pos.realized_pnl,
                status=pos.status,
                metadata=pos.metadata
            )
            for pos in positions
        ]
    except Exception as e:
        logger.error(f"Error getting positions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/trades", response_model=List[TradeResponse])
async def get_trades(
    start_date: datetime = None,
    end_date: datetime = None,
    orchestrator: TradingOrchestrator = Depends()
):
    """Get trade history"""
    try:
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        trades = await orchestrator.trade_manager.get_trades(start_date, end_date)
        return [
            TradeResponse(
                success=True,
                message="Trade retrieved successfully",
                trade_id=trade.trade_id,
                symbol=trade.symbol,
                quantity=trade.quantity,
                price=trade.price,
                side=trade.side,
                status=trade.status,
                execution_time=trade.execution_time,
                fees=trade.fees,
                metadata=trade.metadata
            )
            for trade in trades
        ]
    except Exception as e:
        logger.error(f"Error getting trades: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/metrics", response_model=Dict[str, Any])
async def get_performance_metrics(
    orchestrator: TradingOrchestrator = Depends()
):
    """Get comprehensive performance metrics"""
    try:
        metrics = await orchestrator.metrics_service.get_all_metrics()
        return {
            "success": True,
            "message": "Performance metrics retrieved successfully",
            "data": metrics
        }
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/risk", response_model=Dict[str, Any])
async def get_risk_metrics(
    orchestrator: TradingOrchestrator = Depends()
):
    """Get risk metrics"""
    try:
        risk_metrics = await orchestrator.risk_manager.get_risk_metrics()
        return {
            "success": True,
            "message": "Risk metrics retrieved successfully",
            "data": risk_metrics
        }
    except Exception as e:
        logger.error(f"Error getting risk metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 