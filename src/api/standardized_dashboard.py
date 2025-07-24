"""
Standardized Dashboard API
Real-time trading dashboard with PRODUCTION DATA ONLY
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# CRITICAL: NO MOCK DATA GENERATORS - ALL REMOVED
# Real data fetching functions only

async def get_real_trading_metrics() -> Dict[str, Any]:
    """Get real trading metrics from database"""
    try:
        from ..core.database import get_db_session
        
        async with get_db_session() as session:
            result = await session.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    AVG(CASE WHEN pnl > 0 THEN 1.0 ELSE 0.0 END) * 100 as success_rate,
                    SUM(pnl) as total_pnl,
                    COUNT(CASE WHEN status = 'OPEN' THEN 1 END) as active_positions
                FROM trades 
                WHERE DATE(created_at) = CURRENT_DATE
            """)
            
            row = result.fetchone()
            if row:
                return {
                    "total_trades": row.total_trades,
                    "success_rate": float(row.success_rate or 0),
                    "total_pnl": float(row.total_pnl or 0),
                    "active_positions": row.active_positions,
                    "source": "real_database"
                }
            
        return {"message": "No trades today", "source": "real_database"}
        
    except Exception as e:
        logger.error(f"Error getting real trading metrics: {e}")
        raise HTTPException(status_code=503, detail="Real trading metrics unavailable")

async def get_real_strategy_performance() -> List[Dict[str, Any]]:
    """Get real strategy performance from database"""
    try:
        from ..core.database import get_db_session
        
        async with get_db_session() as session:
            result = await session.execute("""
                SELECT 
                    strategy_name,
                    COUNT(*) as trades,
                    AVG(CASE WHEN pnl > 0 THEN 1.0 ELSE 0.0 END) * 100 as win_rate,
                    SUM(pnl) as total_pnl
                FROM trades 
                WHERE strategy_name IS NOT NULL
                GROUP BY strategy_name
                ORDER BY total_pnl DESC
            """)
            
            strategies = []
            for row in result:
                strategies.append({
                    "name": row.strategy_name,
                    "trades": row.trades,
                    "win_rate": float(row.win_rate or 0),
                    "pnl": float(row.total_pnl or 0),
                    "source": "real_database"
                })
            
            return strategies
            
    except Exception as e:
        logger.error(f"Error getting real strategy performance: {e}")
        raise HTTPException(status_code=503, detail="Real strategy data unavailable")

@router.get("/overview")
async def get_dashboard_overview():
    """Get complete dashboard overview - REAL DATA ONLY"""
    try:
        trading_metrics = await get_real_trading_metrics()
        strategy_performance = await get_real_strategy_performance()
        
        return {
            "success": True,
            "data": {
                "trading_metrics": trading_metrics,
                "strategy_performance": strategy_performance,
                "timestamp": datetime.now().isoformat(),
                "data_source": "production_database"
            }
        }
        
    except Exception as e:
        logger.error(f"Dashboard overview error: {e}")
        raise HTTPException(status_code=503, detail="Real dashboard data unavailable")

@router.get("/metrics")
async def get_trading_metrics():
    """Get real trading metrics"""
    try:
        return {
            "success": True,
            "data": await get_real_trading_metrics()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail="Real metrics unavailable")

@router.get("/strategies")
async def get_strategy_performance():
    """Get real strategy performance"""
    try:
        return {
            "success": True,
            "data": await get_real_strategy_performance()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail="Real strategy data unavailable") 