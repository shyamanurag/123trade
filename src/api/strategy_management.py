from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
from datetime import datetime
import logging

from ..models.schema import StrategyConfig, TradingSignal
from ..core.strategy_manager import StrategyManager
from ..core.risk_manager import RiskManager
from ..auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/strategies", response_model=StrategyConfig)
async def create_strategy(
    strategy: StrategyConfig,
    strategy_manager: StrategyManager = Depends(),
    risk_manager: RiskManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Create a new trading strategy"""
    try:
        # Validate strategy parameters
        validation = await strategy_manager.validate_strategy(strategy)
        if not validation['valid']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid strategy: {validation['reason']}"
            )

        # Create strategy
        created_strategy = await strategy_manager.create_strategy(
            user_id=current_user.user_id,
            strategy=strategy
        )
        return created_strategy

    except Exception as e:
        logger.error(f"Error creating strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies", response_model=List[StrategyConfig])
async def list_strategies(
    strategy_manager: StrategyManager = Depends(),
    current_user = Depends(get_current_user)
):
    """List all strategies for the user"""
    try:
        strategies = await strategy_manager.get_user_strategies(current_user.user_id)
        return strategies

    except Exception as e:
        logger.error(f"Error listing strategies: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies/{strategy_id}", response_model=StrategyConfig)
async def get_strategy(
    strategy_id: str,
    strategy_manager: StrategyManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Get strategy details"""
    try:
        strategy = await strategy_manager.get_strategy(strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
            
        # Verify user owns the strategy
        if strategy.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view this strategy")
            
        return strategy

    except Exception as e:
        logger.error(f"Error getting strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/strategies/{strategy_id}", response_model=StrategyConfig)
async def update_strategy(
    strategy_id: str,
    strategy_update: StrategyConfig,
    strategy_manager: StrategyManager = Depends(),
    risk_manager: RiskManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Update strategy details"""
    try:
        # Get existing strategy
        strategy = await strategy_manager.get_strategy(strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
            
        # Verify user owns the strategy
        if strategy.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this strategy")
            
        # Validate updated strategy
        validation = await strategy_manager.validate_strategy(strategy_update)
        if not validation['valid']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid strategy update: {validation['reason']}"
            )
            
        # Update strategy
        updated_strategy = await strategy_manager.update_strategy(
            strategy_id=strategy_id,
            strategy=strategy_update
        )
        return updated_strategy

    except Exception as e:
        logger.error(f"Error updating strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/strategies/{strategy_id}")
async def delete_strategy(
    strategy_id: str,
    strategy_manager: StrategyManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Delete a strategy"""
    try:
        # Get existing strategy
        strategy = await strategy_manager.get_strategy(strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
            
        # Verify user owns the strategy
        if strategy.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this strategy")
            
        # Delete strategy
        await strategy_manager.delete_strategy(strategy_id)
        
        return {"message": f"Strategy {strategy_id} deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies/{strategy_id}/enable")
async def enable_strategy(
    strategy_id: str,
    strategy_manager: StrategyManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Enable a strategy"""
    try:
        # Get existing strategy
        strategy = await strategy_manager.get_strategy(strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
            
        # Verify user owns the strategy
        if strategy.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to enable this strategy")
            
        # Enable strategy
        await strategy_manager.enable_strategy(strategy_id)
        
        return {"message": f"Strategy {strategy_id} enabled successfully"}

    except Exception as e:
        logger.error(f"Error enabling strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies/{strategy_id}/disable")
async def disable_strategy(
    strategy_id: str,
    strategy_manager: StrategyManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Disable a strategy"""
    try:
        # Get existing strategy
        strategy = await strategy_manager.get_strategy(strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
            
        # Verify user owns the strategy
        if strategy.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to disable this strategy")
            
        # Disable strategy
        await strategy_manager.disable_strategy(strategy_id)
        
        return {"message": f"Strategy {strategy_id} disabled successfully"}

    except Exception as e:
        logger.error(f"Error disabling strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies/{strategy_id}/signals", response_model=List[TradingSignal])
async def get_strategy_signals(
    strategy_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    strategy_manager: StrategyManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Get signals generated by a strategy"""
    try:
        # Get existing strategy
        strategy = await strategy_manager.get_strategy(strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
            
        # Verify user owns the strategy
        if strategy.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view these signals")
            
        # Get signals
        signals = await strategy_manager.get_strategy_signals(
            strategy_id=strategy_id,
            start_date=start_date,
            end_date=end_date
        )
        return signals

    except Exception as e:
        logger.error(f"Error getting strategy signals: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 