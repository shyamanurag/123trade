from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
from datetime import datetime
import logging

from ..models.schema import RiskMetrics, RiskLimits
from ..core.risk_manager import RiskManager
from ..core.capital_manager import CapitalManager
from ..auth import get_current_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/risk/limits", response_model=RiskLimits)
async def get_risk_limits(
    risk_manager: RiskManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Get risk limits for the current user"""
    try:
        limits = await risk_manager.get_user_risk_limits(current_user.user_id)
        return limits

    except Exception as e:
        logger.error(f"Error getting risk limits: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/risk/limits", response_model=RiskLimits)
async def update_risk_limits(
    limits: RiskLimits,
    risk_manager: RiskManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Update risk limits for the current user"""
    try:
        # Validate new limits
        validation = await risk_manager.validate_risk_limits(limits)
        if not validation['valid']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid risk limits: {validation['reason']}"
            )

        # Update limits
        updated_limits = await risk_manager.update_user_risk_limits(
            user_id=current_user.user_id,
            limits=limits
        )
        return updated_limits

    except Exception as e:
        logger.error(f"Error updating risk limits: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/risk/metrics", response_model=RiskMetrics)
async def get_risk_metrics(
    risk_manager: RiskManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Get current risk metrics for the user"""
    try:
        metrics = await risk_manager.get_user_risk_metrics(current_user.user_id)
        return metrics

    except Exception as e:
        logger.error(f"Error getting risk metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}/risk", response_model=RiskMetrics)
async def get_user_risk_profile(
    user_id: str,
    risk_manager: RiskManager = Depends(),
    current_user = Depends(require_admin)
):
    """Get detailed risk profile for a user (admin only)"""
    try:
        profile = await risk_manager.get_user_risk_profile(user_id)
        logger.info(f"Admin {current_user.user_id} accessed risk profile for user {user_id}")
        return profile

    except Exception as e:
        logger.error(f"Error getting user risk profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/risk/hard-stop/reset")
async def reset_hard_stop(
    risk_manager: RiskManager = Depends(),
    capital_manager: CapitalManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Reset hard stop status for the user"""
    try:
        # Check if user meets recovery criteria
        recovery_check = await risk_manager.check_hard_stop_recovery(
            user_id=current_user.user_id
        )
        if not recovery_check['allowed']:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot reset hard stop: {recovery_check['reason']}"
            )

        # Reset hard stop
        await risk_manager.reset_hard_stop(current_user.user_id)
        
        # Update capital
        await capital_manager.reset_daily_metrics(current_user.user_id)
        
        return {"message": "Hard stop reset successfully"}

    except Exception as e:
        logger.error(f"Error resetting hard stop: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/risk/alerts")
async def get_risk_alerts(
    risk_manager: RiskManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Get active risk alerts for the user"""
    try:
        alerts = await risk_manager.get_user_risk_alerts(current_user.user_id)
        return alerts

    except Exception as e:
        logger.error(f"Error getting risk alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/risk/history")
async def get_risk_history(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    risk_manager: RiskManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Get risk history for the user"""
    try:
        history = await risk_manager.get_user_risk_history(
            user_id=current_user.user_id,
            start_date=start_date,
            end_date=end_date
        )
        return history

    except Exception as e:
        logger.error(f"Error getting risk history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 