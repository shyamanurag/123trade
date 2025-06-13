from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
import logging

from ..models.schema import Position
from ..core.position_manager import PositionManager
from ..core.risk_manager import RiskManager
from ..auth import get_current_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/positions", response_model=List[Position])
async def get_all_positions(
    position_manager: PositionManager = Depends(),
    current_user = Depends(require_admin)  # Require admin role
):
    """Get all positions (admin only)"""
    try:
        positions = await position_manager.get_all_positions()
        logger.info(f"Admin {current_user.user_id} retrieved {len(positions)} positions")
        return positions

    except Exception as e:
        logger.error(f"Error getting all positions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}/positions", response_model=List[Position])
async def get_user_positions(
    user_id: str,
    position_manager: PositionManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Get all positions for a user"""
    try:
        # Verify user is requesting their own positions
        if user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view these positions")
            
        positions = await position_manager.get_user_positions(user_id)
        return positions

    except Exception as e:
        logger.error(f"Error getting user positions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions/{position_id}", response_model=Position)
async def get_position(
    position_id: str,
    position_manager: PositionManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Get position details"""
    try:
        position = await position_manager.get_position(position_id)
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
            
        # Verify user owns the position
        if position.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view this position")
            
        return position

    except Exception as e:
        logger.error(f"Error getting position: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/positions/{position_id}", response_model=Position)
async def update_position(
    position_id: str,
    position_update: dict,
    position_manager: PositionManager = Depends(),
    risk_manager: RiskManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Update position details"""
    try:
        # Get existing position
        position = await position_manager.get_position(position_id)
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
            
        # Verify user owns the position
        if position.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this position")
            
        # Check risk limits if updating quantity
        if 'quantity' in position_update:
            risk_check = await risk_manager.check_position_risk(
                user_id=current_user.user_id,
                symbol=position.symbol,
                quantity=position_update['quantity']
            )
            if not risk_check['allowed']:
                raise HTTPException(
                    status_code=400,
                    detail=f"Position update rejected: {risk_check['reason']}"
                )
            
        # Update position
        updated_position = await position_manager.update_position(
            position_id=position_id,
            **position_update
        )
        
        return updated_position

    except Exception as e:
        logger.error(f"Error updating position: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 