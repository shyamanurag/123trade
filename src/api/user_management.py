from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from pydantic import BaseModel
import logging

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