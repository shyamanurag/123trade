"""
Autonomous Trading API
Handles automated trading operations
"""
import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = str(Path(__file__).parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from datetime import datetime
import logging
from src.models.responses import (
    BaseResponse,
    TradingStatusResponse,
    PositionResponse,
    PerformanceMetricsResponse,
    StrategyResponse,
    RiskMetricsResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/autonomous")

# Lazy import to avoid circular dependency
async def get_orchestrator():
    """Get orchestrator instance with lazy import"""
    from src.core.orchestrator import get_orchestrator as get_orchestrator_instance
    return await get_orchestrator_instance()

@router.get("/status", response_model=TradingStatusResponse)
async def get_status(
    orchestrator: Any = Depends(get_orchestrator)
):
    """Get current autonomous trading status"""
    try:
        status = await orchestrator.get_trading_status()
        return TradingStatusResponse(
            success=True,
            message="Trading status retrieved successfully",
            data={
                "is_active": status["is_active"],
                "session_id": status["session_id"],
                "start_time": status["start_time"],
                "last_heartbeat": status["last_heartbeat"],
                "active_strategies": status["active_strategies"],
                "active_positions": status["active_positions"],
                "total_trades": status["total_trades"],
                "daily_pnl": status["daily_pnl"],
                "risk_status": status["risk_status"],
                "market_status": status["market_status"],
                "timestamp": datetime.utcnow()
            }
        )
    except Exception as e:
        logger.error(f"Error getting trading status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start", response_model=BaseResponse)
async def start_trading(
    orchestrator: Any = Depends(get_orchestrator)
):
    """Start autonomous trading with forced initialization for deployment"""
    try:
        logger.info("🚀 Starting autonomous trading system...")
        
        # FORCE COMPLETE SYSTEM INITIALIZATION regardless of flags
        # This fixes the deployment issue where orchestrator isn't properly initialized
        logger.info("🔄 Forcing complete system initialization...")
        
        # Clear any existing state that might be interfering
        orchestrator.is_initialized = False
        orchestrator.is_running = False
        orchestrator.components.clear()
        orchestrator.strategies.clear()
        orchestrator.active_strategies.clear()
        
        # Force full initialization
        init_success = await orchestrator.initialize()
        
        if not init_success:
            logger.error("❌ System initialization failed")
            raise HTTPException(status_code=500, detail="Failed to initialize trading system")
        
        logger.info(f"✅ System initialized with {len(orchestrator.strategies)} strategies")
        
        # Force trading start
        trading_enabled = await orchestrator.start_trading()
        
        if not trading_enabled:
            logger.error("❌ Trading start failed")
            raise HTTPException(status_code=500, detail="Failed to start trading")
        
        logger.info("🚀 Autonomous trading started successfully")
        
        # Verify the system is actually running
        final_status = await orchestrator.get_trading_status()
        if not final_status.get('is_active', False):
            logger.error("❌ Trading system not active after start")
            raise HTTPException(status_code=500, detail="Trading system not active after start")
        
        logger.info(f"✅ Verified: {len(final_status.get('active_strategies', []))} strategies active")
        
        return BaseResponse(
            success=True,
            message=f"Autonomous trading started successfully with {len(orchestrator.strategies)} strategies"
        )
            
    except Exception as e:
        logger.error(f"Error starting trading: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start autonomous trading: {str(e)}")

@router.post("/stop", response_model=BaseResponse)
async def stop_trading(
    orchestrator: Any = Depends(get_orchestrator)
):
    """Stop autonomous trading"""
    try:
        await orchestrator.disable_trading()
        return BaseResponse(
            success=True,
            message="Autonomous trading stopped successfully"
        )
    except Exception as e:
        logger.error(f"Error stopping trading: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions", response_model=PositionResponse)
async def get_positions(
    orchestrator: Any = Depends(get_orchestrator)
):
    """Get current positions"""
    try:
        # Handle case where position_tracker isn't fully initialized
        if hasattr(orchestrator, 'position_tracker') and hasattr(orchestrator.position_tracker, 'get_all_positions'):
            positions = await orchestrator.position_tracker.get_all_positions()
        else:
            positions = []  # Return empty list if not initialized
        
        return PositionResponse(
            success=True,
            message="Positions retrieved successfully",
            data=positions
        )
    except Exception as e:
        logger.error(f"Error getting positions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance", response_model=PerformanceMetricsResponse)
async def get_performance(
    orchestrator: Any = Depends(get_orchestrator)
):
    """Get trading performance metrics"""
    try:
        # Return basic metrics for now
        metrics = {
            "total_trades": getattr(orchestrator, 'total_trades', 0),
            "daily_pnl": getattr(orchestrator, 'daily_pnl', 0.0),
            "active_positions": len(getattr(orchestrator, 'active_positions', [])),
            "win_rate": 0.0,
            "sharpe_ratio": 0.0
        }
        return PerformanceMetricsResponse(
            success=True,
            message="Performance metrics retrieved successfully",
            data=metrics
        )
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies", response_model=StrategyResponse)
async def get_strategies(
    orchestrator: Any = Depends(get_orchestrator)
):
    """Get active trading strategies"""
    try:
        # Fix: Use strategies dictionary instead of strategy_engine
        if hasattr(orchestrator, 'strategies') and orchestrator.strategies:
            strategies = {key: {
                'name': info.get('name', key),
                'active': info.get('active', False),
                'last_signal': info.get('last_signal', None)
            } for key, info in orchestrator.strategies.items()}
        else:
            strategies = {}
        return StrategyResponse(
            success=True,
            message="Strategies retrieved successfully",
            data=strategies
        )
    except Exception as e:
        logger.error(f"Error getting strategies: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/risk", response_model=RiskMetricsResponse)
async def get_risk_metrics(
    orchestrator: Any = Depends(get_orchestrator)
):
    """Get current risk metrics"""
    try:
        # Fix: Check if risk_manager is properly initialized
        if hasattr(orchestrator, 'risk_manager') and orchestrator.risk_manager is not None:
            risk_metrics = await orchestrator.risk_manager.get_risk_metrics()
        else:
            # Return default risk metrics if not initialized
            risk_metrics = {
                "max_daily_loss": 50000,
                "current_exposure": 0,
                "available_capital": 0,
                "risk_score": 0,
                "status": "risk_manager_not_initialized"
            }
        return RiskMetricsResponse(
            success=True,
            message="Risk metrics retrieved successfully",
            data=risk_metrics
        )
    except Exception as e:
        logger.error(f"Error getting risk metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orders")
async def get_orders(
    orchestrator: Any = Depends(get_orchestrator)
):
    """Get today's orders"""
    try:
        # Get today's orders from database
        from datetime import date
        today = date.today()
        
        # Try to get orders from database
        try:
            from src.core.database import get_db_session
            async with get_db_session() as session:
                # Get orders for today
                from sqlalchemy import text
                query = text("""
                    SELECT order_id, symbol, order_type, side, quantity, price, status, 
                           strategy_name, created_at, filled_at
                    FROM orders 
                    WHERE DATE(created_at) = :today
                    ORDER BY created_at DESC
                """)
                result = await session.execute(query, {"today": today})
                orders = []
                for row in result:
                    orders.append({
                        "order_id": row.order_id,
                        "symbol": row.symbol,
                        "order_type": row.order_type,
                        "side": row.side,
                        "quantity": row.quantity,
                        "price": float(row.price) if row.price else None,
                        "status": row.status,
                        "strategy_name": row.strategy_name,
                        "created_at": row.created_at.isoformat(),
                        "filled_at": row.filled_at.isoformat() if row.filled_at else None
                    })
                
                return {
                    "success": True,
                    "message": f"Found {len(orders)} orders for today",
                    "data": orders,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as db_error:
            logger.warning(f"Database query failed: {db_error}")
            # Return empty list if database fails
            return {
                "success": True,
                "message": "No orders found (database unavailable)",
                "data": [],
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting orders: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trades")
async def get_trades(
    orchestrator: Any = Depends(get_orchestrator)
):
    """Get today's trades"""
    try:
        # Get today's trades from database
        from datetime import date
        today = date.today()
        
        # Try to get trades from database
        try:
            from src.core.database import get_db_session
            async with get_db_session() as session:
                # Get trades for today
                from sqlalchemy import text
                query = text("""
                    SELECT trade_id, symbol, trade_type, quantity, price, 
                           strategy, commission, executed_at
                    FROM trades 
                    WHERE DATE(executed_at) = :today
                    ORDER BY executed_at DESC
                """)
                result = await session.execute(query, {"today": today})
                trades = []
                for row in result:
                    trades.append({
                        "trade_id": row.trade_id,
                        "symbol": row.symbol,
                        "trade_type": row.trade_type,
                        "quantity": row.quantity,
                        "price": float(row.price),
                        "strategy": row.strategy,
                        "commission": float(row.commission) if row.commission else 0,
                        "executed_at": row.executed_at.isoformat()
                    })
                
                return {
                    "success": True,
                    "message": f"Found {len(trades)} trades for today",
                    "data": trades,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as db_error:
            logger.warning(f"Database query failed: {db_error}")
            # Return empty list if database fails
            return {
                "success": True,
                "message": "No trades found (database unavailable)",
                "data": [],
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting trades: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 