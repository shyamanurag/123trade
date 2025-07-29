"""
Frontend API Endpoints for ShareKhan Trading Platform
Provides all necessary endpoints for the static frontend - 100% REAL DATA ONLY
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["frontend"])

# REMOVED: All sample/demo data - real production data only

# Market Data Endpoints - REAL SHAREKHAN DATA ONLY
@router.get("/indices")
async def get_market_indices():
    """Get live market indices data from ShareKhan - NO MOCK DATA"""
    try:
        # Import real ShareKhan client
        from brokers.sharekhan import ShareKhanIntegration
        
        # Get real market data
        sharekhan = ShareKhanIntegration()
        if not sharekhan.is_connected():
            raise HTTPException(
                status_code=503, 
                detail="ShareKhan connection not available - real data required"
            )
        
        # Get real indices data
        indices_data = await sharekhan.get_market_indices()
        
        return {
            "success": True,
            "data": indices_data,
            "source": "sharekhan_live",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"REAL DATA ERROR: {e}")
        raise HTTPException(
            status_code=503, 
            detail=f"Real market data unavailable: {str(e)} - NO FALLBACK ALLOWED"
        )

@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """Get quote for a specific symbol"""
    try:
        # Import real ShareKhan client
        from brokers.sharekhan import ShareKhanIntegration
        
        # Get real quote data
        sharekhan = ShareKhanIntegration()
        if not sharekhan.is_connected():
            raise HTTPException(
                status_code=503,
                detail="ShareKhan connection not available - real data required"
            )
        
        quote_data = await sharekhan.get_quote(symbol)
        
        return {
            "success": True,
            "data": quote_data,
            "source": "sharekhan_live",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"REAL QUOTE ERROR: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Real quote data unavailable: {str(e)} - NO FALLBACK ALLOWED"
        )

@router.get("/market-status")
async def get_market_status():
    """Get current market status"""
    try:
        # Import real ShareKhan client
        from brokers.sharekhan import ShareKhanIntegration
        
        # Get real market status
        sharekhan = ShareKhanIntegration()
        if not sharekhan.is_connected():
            raise HTTPException(
                status_code=503,
                detail="ShareKhan connection not available - real data required"
            )
        
        market_status = await sharekhan.get_market_status()
        
        return {
            "success": True,
            "data": market_status,
            "source": "sharekhan_live",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"REAL MARKET STATUS ERROR: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Real market status unavailable: {str(e)} - NO FALLBACK ALLOWED"
        )

# User Management Endpoints - REAL DATABASE DATA ONLY
@router.get("/users")
async def get_users():
    """Get real user data from database - NO SAMPLE DATA"""
    try:
        # Import real database connection
        from src.core.database import get_database_session
        
        session = get_database_session()
        if not session:
            raise HTTPException(
                status_code=503,
                detail="Database connection not available - real data required"
            )
        
        # Query real users from database
        users_query = "SELECT * FROM users WHERE is_active = true"
        real_users = session.execute(users_query).fetchall()
        
        return {
            "success": True,
            "data": [dict(user) for user in real_users],
            "source": "database_live",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"REAL USER DATA ERROR: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Real user data unavailable: {str(e)} - NO FALLBACK ALLOWED"
        )

@router.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get specific user details"""
    try:
        # Import real database connection
        from src.core.database import get_database_session
        
        session = get_database_session()
        if not session:
            raise HTTPException(
                status_code=503,
                detail="Database connection not available - real data required"
            )
        
        # Query real user by ID
        user_query = "SELECT * FROM users WHERE id = %s"
        user_result = session.execute(user_query, (user_id,))
        user = user_result.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "success": True,
            "data": dict(user),
            "source": "database_live",
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"REAL USER DETAILS ERROR: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Real user details unavailable: {str(e)} - NO FALLBACK ALLOWED"
        )

@router.post("/users")
async def create_user(user_data: Dict[str, Any]):
    """Create a new user"""
    try:
        # Import real database connection
        from src.core.database import get_database_session
        
        session = get_database_session()
        if not session:
            raise HTTPException(
                status_code=503,
                detail="Database connection not available - real data required"
            )
        
        # Insert new user into database
        insert_query = """
            INSERT INTO users (name, email, trading_limit, is_active)
            VALUES (%s, %s, %s, %s)
            RETURNING id, name, email, trading_limit, is_active, created_at, updated_at
        """
        new_user_data = (
            user_data.get("name", "New User"),
            user_data.get("email", "user@trading.com"),
            user_data.get("trading_limit", 50000),
            True # Default to active
        )
        new_user_result = session.execute(insert_query, new_user_data)
        new_user = new_user_result.fetchone()
        
        return {
            "success": True,
            "message": "User created successfully",
            "data": dict(new_user),
            "source": "database_live",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"REAL CREATE USER ERROR: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Real user creation unavailable: {str(e)} - NO FALLBACK ALLOWED"
        )

# Trading Endpoints - REAL ORCHESTRATOR DATA ONLY
@router.get("/portfolio")
async def get_portfolio(user_id: Optional[int] = None):
    """Get portfolio information"""
    try:
        # Import real ShareKhan client
        from brokers.sharekhan import ShareKhanIntegration
        
        # Get real portfolio data
        sharekhan = ShareKhanIntegration()
        if not sharekhan.is_connected():
            raise HTTPException(
                status_code=503,
                detail="ShareKhan connection not available - real data required"
            )
        
        portfolio_data = await sharekhan.get_portfolio(user_id)
        
        return {
            "success": True,
            "data": portfolio_data,
            "source": "sharekhan_live",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"REAL PORTFOLIO ERROR: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Real portfolio data unavailable: {str(e)} - NO FALLBACK ALLOWED"
        )

@router.get("/trades")
async def get_trades(
    user_id: Optional[int] = None,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Get trading history"""
    try:
        # Import real ShareKhan client
        from brokers.sharekhan import ShareKhanIntegration
        
        # Get real trades data
        sharekhan = ShareKhanIntegration()
        if not sharekhan.is_connected():
            raise HTTPException(
                status_code=503,
                detail="ShareKhan connection not available - real data required"
            )
        
        trades_data = await sharekhan.get_trades(user_id, start_date, end_date)
        
        return {
            "success": True,
            "data": trades_data,
            "source": "sharekhan_live",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"REAL TRADES ERROR: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Real trades data unavailable: {str(e)} - NO FALLBACK ALLOWED"
        )

# Analytics Endpoints - REAL ORCHESTRATOR DATA ONLY
@router.get("/analytics")
async def get_analytics(user_id: Optional[int] = None):
    """Get trading analytics"""
    try:
        # Import real ShareKhan client
        from brokers.sharekhan import ShareKhanIntegration
        
        # Get real analytics data
        sharekhan = ShareKhanIntegration()
        if not sharekhan.is_connected():
            raise HTTPException(
                status_code=503,
                detail="ShareKhan connection not available - real data required"
            )
        
        analytics_data = await sharekhan.get_analytics(user_id)
        
        return {
            "success": True,
            "data": analytics_data,
            "source": "sharekhan_live",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"REAL ANALYTICS ERROR: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Real analytics data unavailable: {str(e)} - NO FALLBACK ALLOWED"
        )

@router.get("/performance/metrics")
async def get_performance_metrics(
    user_id: Optional[int] = None,
    period: str = Query("1M", regex="^(1D|1W|1M|3M|6M|1Y)$")
):
    """Get performance metrics for specified period"""
    try:
        # Import real ShareKhan client
        from brokers.sharekhan import ShareKhanIntegration
        
        # Get real performance metrics
        sharekhan = ShareKhanIntegration()
        if not sharekhan.is_connected():
            raise HTTPException(
                status_code=503,
                detail="ShareKhan connection not available - real data required"
            )
        
        metrics_data = await sharekhan.get_performance_metrics(user_id, period)
        
        return {
            "success": True,
            "data": metrics_data,
            "source": "sharekhan_live",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"REAL PERFORMANCE METRICS ERROR: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Real performance metrics unavailable: {str(e)} - NO FALLBACK ALLOWED"
        )

# Configuration Endpoints - REAL ORCHESTRATOR DATA ONLY
@router.get("/config")
async def get_config():
    """Get system configuration"""
    try:
        # Import real ShareKhan client
        from brokers.sharekhan import ShareKhanIntegration
        
        # Get real config data
        sharekhan = ShareKhanIntegration()
        if not sharekhan.is_connected():
            raise HTTPException(
                status_code=503,
                detail="ShareKhan connection not available - real data required"
            )
        
        config_data = await sharekhan.get_config()
        
        return {
            "success": True,
            "data": config_data,
            "source": "sharekhan_live",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"REAL CONFIG ERROR: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Real config data unavailable: {str(e)} - NO FALLBACK ALLOWED"
        )

@router.get("/debug/status")
async def get_debug_status():
    """Get detailed debug status for troubleshooting"""
    try:
        # Import real ShareKhan client
        from brokers.sharekhan import ShareKhanIntegration
        
        # Get real debug status
        sharekhan = ShareKhanIntegration()
        if not sharekhan.is_connected():
            raise HTTPException(
                status_code=503,
                detail="ShareKhan connection not available - real data required"
            )
        
        debug_info = await sharekhan.get_debug_status()
        
        return {
            "success": True,
            "data": debug_info,
            "source": "sharekhan_live",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"REAL DEBUG STATUS ERROR: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Real debug status unavailable: {str(e)} - NO FALLBACK ALLOWED"
        ) 