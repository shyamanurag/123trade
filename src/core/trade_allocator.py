"""
Trade Allocator for Trading System
Handles trade allocation, position sizing, and portfolio distribution
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from enum import Enum

logger = logging.getLogger(__name__)

class AllocationMethod(str, Enum):
    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity" 
    MOMENTUM_BASED = "momentum_based"
    VOLATILITY_ADJUSTED = "volatility_adjusted"

class TradeAllocation(BaseModel):
    """Trade allocation result"""
    symbol: str
    allocation_percentage: float
    target_position_size: Decimal
    current_position_size: Decimal
    trade_size: Decimal
    side: str  # BUY or SELL
    priority: int

class AllocationConfig(BaseModel):
    """Allocation configuration"""
    method: AllocationMethod = AllocationMethod.EQUAL_WEIGHT
    max_position_percentage: float = 0.20  # Max 20% per position
    min_position_size: Decimal = Decimal("100")  # Min $100 position
    rebalance_threshold: float = 0.05  # 5% deviation triggers rebalance
    active_symbols: List[str] = []

class TradeAllocator:
    """Handles trade allocation and position sizing"""
    
    def __init__(self):
        self.config = AllocationConfig()
        self.portfolio_value = Decimal("100000")  # Default $100k portfolio
        self.current_positions: Dict[str, Decimal] = {}
        self.symbol_weights: Dict[str, float] = {}
        self.volatilities: Dict[str, float] = {}
        
    async def calculate_allocations(self, symbols: List[str], total_capital: Decimal = None) -> List[TradeAllocation]:
        """Calculate optimal trade allocations"""
        try:
            if total_capital:
                self.portfolio_value = total_capital
                
            allocations = []
            
            if self.config.method == AllocationMethod.EQUAL_WEIGHT:
                allocations = await self._equal_weight_allocation(symbols)
            elif self.config.method == AllocationMethod.RISK_PARITY:
                allocations = await self._risk_parity_allocation(symbols)
            elif self.config.method == AllocationMethod.MOMENTUM_BASED:
                allocations = await self._momentum_allocation(symbols)
            elif self.config.method == AllocationMethod.VOLATILITY_ADJUSTED:
                allocations = await self._volatility_adjusted_allocation(symbols)
                
            return allocations
            
        except Exception as e:
            logger.error(f"Error calculating allocations: {e}")
            return []
    
    async def _equal_weight_allocation(self, symbols: List[str]) -> List[TradeAllocation]:
        """Equal weight allocation method"""
        allocations = []
        
        if not symbols:
            return allocations
            
        weight_per_symbol = min(1.0 / len(symbols), self.config.max_position_percentage)
        
        for i, symbol in enumerate(symbols):
            current_position = self.current_positions.get(symbol, Decimal("0"))
            target_value = self.portfolio_value * Decimal(str(weight_per_symbol))
            trade_size = target_value - current_position
            
            if abs(trade_size) >= self.config.min_position_size:
                allocation = TradeAllocation(
                    symbol=symbol,
                    allocation_percentage=weight_per_symbol * 100,
                    target_position_size=target_value,
                    current_position_size=current_position,
                    trade_size=abs(trade_size),
                    side="BUY" if trade_size > 0 else "SELL",
                    priority=i + 1
                )
                allocations.append(allocation)
                
        return allocations
    
    async def _risk_parity_allocation(self, symbols: List[str]) -> List[TradeAllocation]:
        """Risk parity allocation method"""
        allocations = []
        
        if not symbols:
            return allocations
            
        # Get volatilities (default to 0.02 if not available)
        total_inv_vol = sum(1.0 / self.volatilities.get(symbol, 0.02) for symbol in symbols)
        
        for i, symbol in enumerate(symbols):
            vol = self.volatilities.get(symbol, 0.02)
            weight = (1.0 / vol) / total_inv_vol
            weight = min(weight, self.config.max_position_percentage)
            
            current_position = self.current_positions.get(symbol, Decimal("0"))
            target_value = self.portfolio_value * Decimal(str(weight))
            trade_size = target_value - current_position
            
            if abs(trade_size) >= self.config.min_position_size:
                allocation = TradeAllocation(
                    symbol=symbol,
                    allocation_percentage=weight * 100,
                    target_position_size=target_value,
                    current_position_size=current_position,
                    trade_size=abs(trade_size),
                    side="BUY" if trade_size > 0 else "SELL",
                    priority=i + 1
                )
                allocations.append(allocation)
                
        return allocations
    
    async def _momentum_allocation(self, symbols: List[str]) -> List[TradeAllocation]:
        """Momentum-based allocation method"""
        # Simplified momentum allocation - equal weight for now
        return await self._equal_weight_allocation(symbols)
    
    async def _volatility_adjusted_allocation(self, symbols: List[str]) -> List[TradeAllocation]:
        """Volatility-adjusted allocation method"""
        # Simplified volatility allocation - inverse of risk parity
        return await self._risk_parity_allocation(symbols)
    
    async def update_position(self, symbol: str, position_value: Decimal):
        """Update current position value"""
        self.current_positions[symbol] = position_value
    
    async def update_volatility(self, symbol: str, volatility: float):
        """Update symbol volatility"""
        self.volatilities[symbol] = volatility
    
    async def set_portfolio_value(self, value: Decimal):
        """Set total portfolio value"""
        self.portfolio_value = value
    
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio allocation summary"""
        try:
            total_allocated = sum(self.current_positions.values())
            cash_position = self.portfolio_value - total_allocated
            
            positions = []
            for symbol, value in self.current_positions.items():
                if value > 0:
                    percentage = float(value / self.portfolio_value * 100)
                    positions.append({
                        "symbol": symbol,
                        "value": float(value),
                        "percentage": percentage
                    })
            
            return {
                "total_portfolio_value": float(self.portfolio_value),
                "total_allocated": float(total_allocated),
                "cash_position": float(cash_position),
                "cash_percentage": float(cash_position / self.portfolio_value * 100),
                "positions": positions,
                "position_count": len([p for p in positions if p["value"] > 0]),
                "allocation_method": self.config.method,
                "max_position_percentage": self.config.max_position_percentage * 100
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            return {"error": str(e)}
    
    async def rebalance_needed(self) -> Tuple[bool, List[str]]:
        """Check if rebalancing is needed"""
        needs_rebalance = []
        
        try:
            for symbol, current_value in self.current_positions.items():
                if current_value > 0:
                    current_percentage = float(current_value / self.portfolio_value)
                    target_weight = self.symbol_weights.get(symbol, 0)
                    
                    deviation = abs(current_percentage - target_weight)
                    if deviation > self.config.rebalance_threshold:
                        needs_rebalance.append(symbol)
            
            return len(needs_rebalance) > 0, needs_rebalance
            
        except Exception as e:
            logger.error(f"Error checking rebalance: {e}")
            return False, []

# Global trade allocator instance
trade_allocator = TradeAllocator()

# API Router
router = APIRouter(prefix="/api/v1/allocation", tags=["trade-allocation"])

@router.get("/summary")
async def get_allocation_summary():
    """Get portfolio allocation summary"""
    try:
        summary = await trade_allocator.get_portfolio_summary()
        
        return {
            "status": "success",
            "data": summary
        }
    except Exception as e:
        logger.error(f"Error getting allocation summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get allocation summary")

@router.post("/calculate")
async def calculate_allocations(symbols: List[str], total_capital: float = None):
    """Calculate trade allocations for given symbols"""
    try:
        capital = Decimal(str(total_capital)) if total_capital else None
        allocations = await trade_allocator.calculate_allocations(symbols, capital)
        
        return {
            "status": "success",
            "data": {
                "allocations": [alloc.dict() for alloc in allocations],
                "total_symbols": len(symbols),
                "allocation_method": trade_allocator.config.method
            }
        }
    except Exception as e:
        logger.error(f"Error calculating allocations: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate allocations")

@router.post("/rebalance-check")
async def check_rebalance():
    """Check if portfolio rebalancing is needed"""
    try:
        needs_rebalance, symbols = await trade_allocator.rebalance_needed()
        
        return {
            "status": "success",
            "data": {
                "needs_rebalance": needs_rebalance,
                "symbols_to_rebalance": symbols,
                "rebalance_threshold": trade_allocator.config.rebalance_threshold * 100
            }
        }
    except Exception as e:
        logger.error(f"Error checking rebalance: {e}")
        raise HTTPException(status_code=500, detail="Failed to check rebalance")

@router.put("/config")
async def update_allocation_config(
    method: AllocationMethod = None,
    max_position_percentage: float = None,
    min_position_size: float = None,
    rebalance_threshold: float = None
):
    """Update allocation configuration"""
    try:
        if method:
            trade_allocator.config.method = method
        if max_position_percentage:
            trade_allocator.config.max_position_percentage = max_position_percentage / 100
        if min_position_size:
            trade_allocator.config.min_position_size = Decimal(str(min_position_size))
        if rebalance_threshold:
            trade_allocator.config.rebalance_threshold = rebalance_threshold / 100
            
        return {
            "status": "success",
            "data": {
                "config": trade_allocator.config.dict(),
                "message": "Allocation configuration updated"
            }
        }
    except Exception as e:
        logger.error(f"Error updating allocation config: {e}")
        raise HTTPException(status_code=500, detail="Failed to update allocation config") 