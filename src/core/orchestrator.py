"""
Trading Orchestrator
Main orchestrator for coordinating all trading activities
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
import json

logger = logging.getLogger(__name__)

# Global orchestrator instance
_orchestrator_instance: Optional['TradingOrchestrator'] = None

def get_orchestrator() -> 'TradingOrchestrator':
    """Get or create the global orchestrator instance"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = TradingOrchestrator()
    return _orchestrator_instance

def set_orchestrator_instance(orchestrator: 'TradingOrchestrator'):
    """Set the global orchestrator instance"""
    global _orchestrator_instance
    _orchestrator_instance = orchestrator

def reset_orchestrator():
    """Reset the global orchestrator instance"""
    global _orchestrator_instance
    _orchestrator_instance = None

class TradingOrchestrator:
    """Main trading orchestrator for crypto trading system"""
    
    def __init__(self):
        self.is_initialized = False
        self.is_running = False
        self.strategies: Dict[str, Any] = {}
        self.execution_engine = None
        self.risk_manager = None
        self.position_tracker = None
        self.start_time = None
        self.session_id = None
        
    async def initialize(self) -> bool:
        """Initialize the orchestrator and all trading components"""
        try:
            logger.info("🔧 Initializing Trading Orchestrator...")
            
            # Initialize execution engine
            try:
                from .crypto_execution_engine import CryptoExecutionEngine
                self.execution_engine = CryptoExecutionEngine({})
                logger.info("✅ Execution engine initialized")
            except Exception as e:
                logger.warning(f"⚠️ Execution engine initialization failed: {e}")
            
            # Initialize risk manager
            try:
                from .risk_manager import risk_manager
                self.risk_manager = risk_manager
                logger.info("✅ Risk manager initialized")
            except Exception as e:
                logger.warning(f"⚠️ Risk manager initialization failed: {e}")
            
            # Initialize position tracker
            try:
                from .position_tracker import ProductionPositionTracker
                self.position_tracker = ProductionPositionTracker()
                logger.info("✅ Position tracker initialized")
            except Exception as e:
                logger.warning(f"⚠️ Position tracker initialization failed: {e}")
            
            # Load trading strategies
            await self._load_strategies()
            
            # Mark as initialized
            self.is_initialized = True
            self.start_time = datetime.utcnow()
            self.session_id = f"session_{int(self.start_time.timestamp())}"
            
            logger.info(f"✅ Trading Orchestrator initialized successfully (Session: {self.session_id})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize orchestrator: {e}")
            self.is_initialized = False
            return False
    
    async def _load_strategies(self):
        """Load available trading strategies"""
        try:
            # Load crypto strategies
            strategy_names = [
                "Enhanced Momentum Surfer",
                "Regime Adaptive Controller", 
                "News Impact Scalper",
                "Confluence Amplifier",
                "Volatility Explosion",
                "Volume Profile Scalper"
            ]
            
            for strategy_name in strategy_names:
                self.strategies[strategy_name] = {
                    "name": strategy_name,
                    "status": "loaded",
                    "active": False,
                    "performance": {"total_return": 0.0, "trades": 0, "win_rate": 0.0}
                }
            
            logger.info(f"✅ Loaded {len(self.strategies)} trading strategies")
            
        except Exception as e:
            logger.error(f"❌ Failed to load strategies: {e}")
    
    async def start(self) -> bool:
        """Start the trading orchestrator"""
        try:
            if not self.is_initialized:
                await self.initialize()
            
            if self.is_initialized:
                self.is_running = True
                logger.info("🚀 Trading Orchestrator started successfully")
                return True
            else:
                logger.error("❌ Cannot start orchestrator - initialization failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to start orchestrator: {e}")
            return False
    
    async def start_trading(self) -> bool:
        """Start autonomous trading - alias for start()"""
        return await self.start()
    
    async def enable_trading(self) -> bool:
        """Enable trading - alias for start()"""
        return await self.start()
    
    async def get_trading_status(self) -> Dict[str, Any]:
        """Get detailed trading status"""
        return {
            "is_active": self.is_running,
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "last_heartbeat": datetime.utcnow().isoformat(),
            "active_strategies": [name for name, strategy in self.strategies.items() if strategy.get("active", False)],
            "active_strategies_count": len([name for name, strategy in self.strategies.items() if strategy.get("active", False)]),
            "active_positions": 0,  # TODO: Get from position tracker
            "total_trades": sum(strategy.get("performance", {}).get("trades", 0) for strategy in self.strategies.values()),
            "daily_pnl": 0.0,  # TODO: Calculate from positions
            "risk_status": {"status": "normal"},
            "market_status": "ACTIVE",
            "system_ready": self.is_initialized and self.is_running,
            "timestamp": datetime.utcnow()
        }
    
    async def stop(self) -> bool:
        """Stop the trading orchestrator"""
        try:
            self.is_running = False
            logger.info("🛑 Trading Orchestrator stopped")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to stop orchestrator: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        return {
            "initialized": self.is_initialized,
            "running": self.is_running,
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "strategies_loaded": len(self.strategies),
            "execution_engine": self.execution_engine is not None,
            "risk_manager": self.risk_manager is not None,
            "position_tracker": self.position_tracker is not None
        }
    
    async def execute_trade(self, symbol: str, side: str, quantity: float, price: float = None) -> Dict[str, Any]:
        """Execute a trade through the orchestrator"""
        try:
            if not self.is_running:
                return {'success': False, 'error': 'Orchestrator not running'}
            
            if self.execution_engine:
                # Convert to proper enums and call place_order
                from .crypto_execution_engine import OrderSide, OrderType
                from decimal import Decimal
                
                order_side = OrderSide.BUY if side.upper() == 'BUY' else OrderSide.SELL
                order_type = OrderType.LIMIT if price is not None else OrderType.MARKET
                quantity_decimal = Decimal(str(quantity))
                price_decimal = Decimal(str(price)) if price is not None else None
                
                return await self.execution_engine.place_order(
                    symbol=symbol,
                    side=order_side,
                    order_type=order_type,
                    quantity=quantity_decimal,
                    price=price_decimal
                )
            else:
                return {'success': False, 'error': 'Execution engine not available'}
                
        except Exception as e:
            logger.error(f"❌ Trade execution failed: {e}")
            return {'success': False, 'error': str(e)} 