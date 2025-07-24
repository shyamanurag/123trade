from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from pydantic import BaseModel
import logging
from datetime import datetime

from ..core.user_tracker import UserTracker
from ..core.risk_manager import RiskManager
from ..core.trade_allocator import TradeAllocator
from ..core.system_evolution import SystemEvolution
from ..core.load_balancer import LoadBalancer
from ..models.schema import UserCreate, UserUpdate, UserResponse
from ..auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate, user_tracker: UserTracker = Depends()):
    """Create a new user"""
    try:
        # Initialize user in system
        await user_tracker.initialize_user(
            user_id=user.user_id,
            initial_capital=user.initial_capital,
            risk_limits=user.risk_limits,
            trading_preferences=user.trading_preferences
        )
        
        # Get user details
        user_details = await user_tracker.get_user_details(user.user_id)
        
        return UserResponse(
            user_id=user.user_id,
            capital=user.initial_capital,
            risk_limits=user.risk_limits,
            trading_preferences=user.trading_preferences,
            is_active=True,
            performance_metrics={}
        )
        
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, user_tracker: UserTracker = Depends()):
    """Get user details"""
    try:
        user_details = await user_tracker.get_user_details(user_id)
        if not user_details:
            raise HTTPException(status_code=404, detail="User not found")
            
        return UserResponse(**user_details)
        
    except Exception as e:
        logger.error(f"Error getting user details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    user_tracker: UserTracker = Depends(),
    risk_manager: RiskManager = Depends(),
    trade_allocator: TradeAllocator = Depends()
):
    """Update user details"""
    try:
        # Update user details
        if user_update.capital is not None:
            await trade_allocator.update_user_capital(user_id, user_update.capital)
            
        if user_update.risk_limits is not None:
            await risk_manager.update_user_risk_limits(user_id, user_update.risk_limits)
            
        if user_update.trading_preferences is not None:
            await user_tracker.update_user_preferences(user_id, user_update.trading_preferences)
            
        if user_update.is_active is not None:
            await user_tracker.update_user_status(user_id, user_update.is_active)
        
        # Get updated user details
        user_details = await user_tracker.get_user_details(user_id)
        
        return UserResponse(**user_details)
        
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    user_tracker: UserTracker = Depends(),
    system_evolution: SystemEvolution = Depends()
):
    """List all users with their performance metrics"""
    try:
        users = await user_tracker.list_users()
        
        # Get performance metrics for each user
        user_responses = []
        for user in users:
            metrics = await system_evolution.get_user_metrics(user['user_id'])
            user['performance_metrics'] = metrics
            user_responses.append(UserResponse(**user))
            
        return user_responses
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user_tracker: UserTracker = Depends(),
    risk_manager: RiskManager = Depends(),
    trade_allocator: TradeAllocator = Depends()
):
    """Delete a user"""
    try:
        # Check if user has active positions
        active_positions = await user_tracker.get_user_positions(user_id)
        if active_positions:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete user with active positions"
            )
        
        # Delete user from all systems
        await user_tracker.delete_user(user_id)
        await risk_manager.delete_user_risk_limits(user_id)
        await trade_allocator.delete_user(user_id)
        
        return {"message": f"User {user_id} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/performance")
async def get_user_performance(
    user_id: str,
    user_tracker: UserTracker = Depends(),
    system_evolution: SystemEvolution = Depends()
):
    """Get user performance analytics"""
    try:
        # Get basic user details
        user_details = await user_tracker.get_user_details(user_id)
        if not user_details:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get performance metrics
        metrics = await system_evolution.get_user_metrics(user_id)
        
        # Get trading history
        try:
            from datetime import date
            from src.core.database import get_db_session
            from sqlalchemy import text
            
            async with get_db_session() as session:
                # Get today's trades
                today = date.today()
                trades_query = text("""
                    SELECT COUNT(*) as total_trades,
                           SUM(CASE WHEN trade_type = 'buy' THEN quantity * price ELSE 0 END) as total_bought,
                           SUM(CASE WHEN trade_type = 'sell' THEN quantity * price ELSE 0 END) as total_sold
                    FROM trades 
                    WHERE user_id = :user_id AND DATE(executed_at) = :today
                """)
                trades_result = await session.execute(trades_query, {"user_id": user_id, "today": today})
                trades_data = trades_result.fetchone()
                
                # Get positions
                positions_query = text("""
                    SELECT COUNT(*) as open_positions,
                           SUM(unrealized_pnl) as unrealized_pnl
                    FROM positions 
                    WHERE user_id = :user_id AND status = 'open'
                """)
                positions_result = await session.execute(positions_query, {"user_id": user_id})
                positions_data = positions_result.fetchone()
                
                performance_data = {
                    "user_id": user_id,
                    "total_trades_today": trades_data.total_trades if trades_data else 0,
                    "total_bought": float(trades_data.total_bought) if trades_data and trades_data.total_bought else 0,
                    "total_sold": float(trades_data.total_sold) if trades_data and trades_data.total_sold else 0,
                    "open_positions": positions_data.open_positions if positions_data else 0,
                    "unrealized_pnl": float(positions_data.unrealized_pnl) if positions_data and positions_data.unrealized_pnl else 0,
                    "win_rate": metrics.get('win_rate', 0),
                    "total_pnl": metrics.get('total_pnl', 0),
                    "sharpe_ratio": metrics.get('sharpe_ratio', 0),
                    "max_drawdown": metrics.get('max_drawdown', 0),
                    "capital": user_details.get('capital', 0),
                    "timestamp": datetime.now().isoformat()
                }
                
                return {
                    "success": True,
                    "data": performance_data,
                    "message": "Performance data retrieved successfully"
                }
                
        except Exception as db_error:
            logger.warning(f"Database query failed: {db_error}")
            # Return default performance data if database fails
            return {
                "success": True,
                "data": {
                    "user_id": user_id,
                    "total_trades_today": 0,
                    "total_bought": 0,
                    "total_sold": 0,
                    "open_positions": 0,
                    "unrealized_pnl": 0,
                    "win_rate": 0,
                    "total_pnl": 0,
                    "sharpe_ratio": 0,
                    "max_drawdown": 0,
                    "capital": user_details.get('capital', 0),
                    "timestamp": datetime.now().isoformat()
                },
                "message": "Default performance data (database unavailable)"
            }
        
    except Exception as e:
        logger.error(f"Error getting user performance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 