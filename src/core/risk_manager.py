"""
Risk Manager for Trading System
Real-time risk management and position monitoring
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from enum import Enum

logger = logging.getLogger(__name__)

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RiskCheck(BaseModel):
    """Risk check result"""
    passed: bool
    risk_level: RiskLevel
    message: str
    details: Dict[str, Any] = {}

class PositionRisk(BaseModel):
    """Position risk assessment"""
    symbol: str
    position_size: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    risk_percentage: float
    var_1d: Decimal  # Value at Risk 1 day
    max_drawdown: Decimal

class RiskLimits(BaseModel):
    """Risk limits configuration"""
    max_position_size: Decimal = Decimal("10000")  # Max position size
    max_daily_loss: Decimal = Decimal("1000")      # Max daily loss
    max_portfolio_risk: float = 0.02               # Max 2% portfolio risk
    max_positions: int = 10                        # Max open positions
    max_leverage: float = 3.0                      # Max leverage
    stop_loss_percentage: float = 0.05             # 5% stop loss

class RiskManager:
    """Real-time risk management system"""
    
    def __init__(self):
        self.risk_limits = RiskLimits()
        self.daily_pnl = Decimal("0")
        self.positions: Dict[str, PositionRisk] = {}
        self.risk_violations: List[Dict] = []
        self.emergency_stop = False
        
    async def check_pre_trade_risk(self, symbol: str, side: str, quantity: Decimal, price: Decimal) -> RiskCheck:
        """Check risk before placing a trade"""
        try:
            # Calculate trade value
            trade_value = quantity * price
            
            # Check position size limit
            if trade_value > self.risk_limits.max_position_size:
                return RiskCheck(
                    passed=False,
                    risk_level=RiskLevel.HIGH,
                    message=f"Trade value {trade_value} exceeds max position size {self.risk_limits.max_position_size}",
                    details={"trade_value": float(trade_value), "limit": float(self.risk_limits.max_position_size)}
                )
            
            # Check daily loss limit
            if self.daily_pnl < -self.risk_limits.max_daily_loss:
                return RiskCheck(
                    passed=False,
                    risk_level=RiskLevel.CRITICAL,
                    message=f"Daily loss limit exceeded: {self.daily_pnl}",
                    details={"daily_pnl": float(self.daily_pnl), "limit": float(self.risk_limits.max_daily_loss)}
                )
            
            # Check number of positions
            if len(self.positions) >= self.risk_limits.max_positions:
                return RiskCheck(
                    passed=False,
                    risk_level=RiskLevel.MEDIUM,
                    message=f"Maximum positions limit reached: {len(self.positions)}",
                    details={"current_positions": len(self.positions), "limit": self.risk_limits.max_positions}
                )
            
            # Check emergency stop
            if self.emergency_stop:
                return RiskCheck(
                    passed=False,
                    risk_level=RiskLevel.CRITICAL,
                    message="Emergency stop is active - all trading halted",
                    details={"emergency_stop": True}
                )
            
            # All checks passed
            return RiskCheck(
                passed=True,
                risk_level=RiskLevel.LOW,
                message="Pre-trade risk checks passed",
                details={"trade_value": float(trade_value)}
            )
            
        except Exception as e:
            logger.error(f"Error in pre-trade risk check: {e}")
            return RiskCheck(
                passed=False,
                risk_level=RiskLevel.HIGH,
                message=f"Risk check error: {str(e)}",
                details={"error": str(e)}
            )
    
    async def update_position(self, symbol: str, position_size: Decimal, market_value: Decimal, unrealized_pnl: Decimal):
        """Update position risk data"""
        try:
            # Calculate risk metrics
            risk_percentage = float(abs(unrealized_pnl) / market_value * 100) if market_value > 0 else 0
            var_1d = market_value * Decimal("0.02")  # Simplified 2% VaR
            max_drawdown = min(unrealized_pnl, Decimal("0"))
            
            position_risk = PositionRisk(
                symbol=symbol,
                position_size=position_size,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                risk_percentage=risk_percentage,
                var_1d=var_1d,
                max_drawdown=max_drawdown
            )
            
            self.positions[symbol] = position_risk
            
            # Check for stop loss
            if risk_percentage > self.risk_limits.stop_loss_percentage * 100:
                await self.trigger_stop_loss(symbol, position_risk)
                
        except Exception as e:
            logger.error(f"Error updating position risk: {e}")
    
    async def trigger_stop_loss(self, symbol: str, position: PositionRisk):
        """Trigger stop loss for a position"""
        violation = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "stop_loss_triggered",
            "symbol": symbol,
            "risk_percentage": position.risk_percentage,
            "unrealized_pnl": float(position.unrealized_pnl),
            "action": "close_position"
        }
        
        self.risk_violations.append(violation)
        logger.warning(f"Stop loss triggered for {symbol}: {position.risk_percentage}% loss")
    
    async def calculate_portfolio_risk(self) -> Dict[str, Any]:
        """Calculate overall portfolio risk"""
        try:
            total_value = sum(pos.market_value for pos in self.positions.values())
            total_var = sum(pos.var_1d for pos in self.positions.values())
            total_unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
            
            portfolio_risk = float(total_var / total_value * 100) if total_value > 0 else 0
            
            return {
                "total_positions": len(self.positions),
                "total_market_value": float(total_value),
                "total_var_1d": float(total_var),
                "total_unrealized_pnl": float(total_unrealized),
                "portfolio_risk_percentage": portfolio_risk,
                "daily_pnl": float(self.daily_pnl),
                "risk_violations": len(self.risk_violations),
                "emergency_stop": self.emergency_stop
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio risk: {e}")
            return {"error": str(e)}
    
    async def set_emergency_stop(self, enabled: bool, reason: str = ""):
        """Enable/disable emergency stop"""
        self.emergency_stop = enabled
        
        violation = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "emergency_stop",
            "enabled": enabled,
            "reason": reason
        }
        
        self.risk_violations.append(violation)
        logger.warning(f"Emergency stop {'enabled' if enabled else 'disabled'}: {reason}")
    
    async def update_daily_pnl(self, pnl: Decimal):
        """Update daily P&L"""
        self.daily_pnl += pnl

# Global risk manager instance
risk_manager = RiskManager()

# API Router
router = APIRouter(prefix="/api/v1/risk", tags=["risk-management"])

@router.get("/status")
async def get_risk_status():
    """Get current risk status"""
    try:
        portfolio_risk = await risk_manager.calculate_portfolio_risk()
        
        return {
            "status": "success",
            "data": {
                "risk_manager_active": True,
                "emergency_stop": risk_manager.emergency_stop,
                "portfolio_risk": portfolio_risk,
                "risk_limits": risk_manager.risk_limits.dict(),
                "recent_violations": risk_manager.risk_violations[-10:]  # Last 10 violations
            }
        }
    except Exception as e:
        logger.error(f"Error getting risk status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get risk status")

@router.get("/positions")
async def get_position_risks():
    """Get risk assessment for all positions"""
    try:
        positions = [pos.dict() for pos in risk_manager.positions.values()]
        
        return {
            "status": "success", 
            "data": {
                "positions": positions,
                "total_positions": len(positions)
            }
        }
    except Exception as e:
        logger.error(f"Error getting position risks: {e}")
        raise HTTPException(status_code=500, detail="Failed to get position risks")

@router.post("/emergency-stop")
async def toggle_emergency_stop(enabled: bool, reason: str = "Manual override"):
    """Toggle emergency stop"""
    try:
        await risk_manager.set_emergency_stop(enabled, reason)
        
        return {
            "status": "success",
            "data": {
                "emergency_stop": enabled,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error toggling emergency stop: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle emergency stop")

@router.post("/check-trade")
async def check_trade_risk(symbol: str, side: str, quantity: float, price: float):
    """Check if a trade passes risk requirements"""
    try:
        risk_check = await risk_manager.check_pre_trade_risk(
            symbol=symbol,
            side=side,
            quantity=Decimal(str(quantity)),
            price=Decimal(str(price))
        )
        
        return {
            "status": "success",
            "data": risk_check.dict()
        }
    except Exception as e:
        logger.error(f"Error checking trade risk: {e}")
        raise HTTPException(status_code=500, detail="Failed to check trade risk") 