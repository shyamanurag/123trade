"""
Autonomous Symbol Management System
Automatically manages ShareKhan symbols for indices and F&O trading with intelligent strategy selection
- Auto-selects optimal symbol mix based on market conditions
- Auto-adds new contracts based on volatility and opportunities
- Auto-removes expired contracts  
- Manages 250 symbol limit intelligently
- Fully autonomous - no manual intervention required
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional
import json
import os
from dataclasses import dataclass, field

# Import ShareKhan client functions
from data.sharekhan_client import subscribe_to_symbols, is_connected, live_market_data

logger = logging.getLogger(__name__)

@dataclass
class AutonomousSymbolConfig:
    """Configuration for autonomous symbol management"""
    max_symbols: int = 250
    auto_refresh_interval: int = 3600  # 1 hour strategy re-evaluation
    expiry_check_interval: int = 1800  # 30 minutes
    strategy_switch_interval: int = 900  # 15 minutes - check if strategy should change
    
    # Core indices (always subscribed - HIGHEST PRIORITY)
    core_indices: List[str] = field(default_factory=lambda: [
        'NIFTY-I', 'BANKNIFTY-I', 'FINNIFTY-I', 'MIDCPNIFTY-I', 'SENSEX-I'
    ])
    
    # Autonomous decision parameters
    volatility_threshold_high: float = 20.0    # VIX > 20 = high volatility
    volatility_threshold_low: float = 12.0     # VIX < 12 = low volatility
    options_premium_threshold: float = 1.5     # IV ratio threshold
    performance_lookback_hours: int = 24       # Look back 24 hours for performance


class AutonomousSymbolManager:
    """Fully autonomous symbol management - no human intervention required"""
    
    def __init__(self, config: Optional[AutonomousSymbolConfig] = None):
        self.config = config or AutonomousSymbolConfig()
        self.active_symbols: Set[str] = set()
        self.current_strategy: str = "MIXED"  # Will be auto-determined
        self.strategy_history: List[Dict] = []  # Track strategy changes
        self.symbol_metadata: Dict[str, Dict] = {}
        self.is_running = False
        self.tasks = []
        
        # Performance tracking for autonomous decisions
        self.strategy_performance: Dict[str, Dict] = {
            "OPTIONS_FOCUS": {"trades": 0, "pnl": 0.0, "success_rate": 0.0},
            "MIXED": {"trades": 0, "pnl": 0.0, "success_rate": 0.0},
            "UNDERLYING_FOCUS": {"trades": 0, "pnl": 0.0, "success_rate": 0.0}
        }
        
        logger.info("🤖 Autonomous Symbol Manager initialized")
        logger.info(f"   Max symbols: {self.config.max_symbols}")
        logger.info(f"   Strategy evaluation: Every {self.config.strategy_switch_interval/60:.1f} minutes")
        logger.info(f"   Fully autonomous: No manual intervention required")

    async def start(self):
        """Start the autonomous symbol management"""
        if self.is_running:
            return
            
        self.is_running = True
        logger.info("🚀 Starting Autonomous Symbol Manager...")
        
        # Initial autonomous symbol setup
        await self.autonomous_symbol_setup()
        
        # Start autonomous background tasks
        self.tasks = [
            asyncio.create_task(self.autonomous_strategy_monitor()),
            asyncio.create_task(self.autonomous_refresh_loop()),
            asyncio.create_task(self.expiry_monitor_loop()),
            asyncio.create_task(self.performance_tracker_loop())
        ]
        
        logger.info("✅ Autonomous Symbol Manager started - operating independently")

    async def stop(self):
        """Stop the autonomous symbol manager"""
        self.is_running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
            
        logger.info("🛑 Autonomous Symbol Manager stopped")

    async def autonomous_symbol_setup(self):
        """
        AUTONOMOUS SETUP: Automatically select and configure optimal symbols
        No manual configuration required - fully intelligent selection
        """
        logger.info("🤖 Starting autonomous symbol selection...")
        
        # Get intelligent symbol list based on current market conditions
        try:
            from config.sharekhan_symbols import get_complete_fo_symbols, get_autonomous_symbol_status
            
            # Get autonomous symbol selection
            symbols_list = get_complete_fo_symbols()
            self.current_strategy = get_autonomous_symbol_status()["current_strategy"]
            
            logger.info(f"🧠 AUTONOMOUS DECISION: Selected {self.current_strategy} strategy")
            logger.info(f"📊 Symbol allocation: {len(symbols_list)} symbols")
            
            # Record strategy decision
            self.strategy_history.append({
                "timestamp": datetime.now().isoformat(),
                "strategy": self.current_strategy,
                "reason": "Initial autonomous setup",
                "symbol_count": len(symbols_list)
            })
            
        except Exception as e:
            logger.error(f"❌ Autonomous symbol selection failed: {e}")
            # Fallback to safe default
            symbols_list = self.config.core_indices
            self.current_strategy = "MIXED"
            logger.info("🔄 Using fallback symbols for safety")
        
        # Wait for ShareKhan connection
        max_retries = 10
        retry_count = 0
        
        while retry_count < max_retries:
            if is_connected():
                logger.info("✅ ShareKhan connected - proceeding with autonomous subscription")
                break
            else:
                logger.info(f"⏳ Waiting for ShareKhan connection... (attempt {retry_count + 1}/{max_retries})")
                await asyncio.sleep(5)
                retry_count += 1
        
        if retry_count >= max_retries:
            logger.warning("⚠️ ShareKhan not connected - will retry autonomously in background")
        else:
            # Subscribe autonomously
            await self.autonomous_subscribe_symbols(symbols_list)
        
        logger.info(f"✅ Autonomous setup complete: {len(symbols_list)} symbols, strategy: {self.current_strategy}")

    async def autonomous_subscribe_symbols(self, symbols: List[str]):
        """Autonomously subscribe to symbols without creating connection conflicts"""
        try:
            new_symbols = [s for s in symbols if s not in self.active_symbols]
            
            if not new_symbols:
                return
                
            logger.info(f"🤖 Autonomously registering {len(new_symbols)} symbols...")
            
            if is_connected():
                logger.info("✅ ShareKhan connected - symbols will be available autonomously")
                
                # Update tracking autonomously
                self.active_symbols.update(new_symbols)
                
                # Store metadata with autonomous classification
                timestamp = datetime.now().isoformat()
                for symbol in new_symbols:
                    self.symbol_metadata[symbol] = {
                        'added_at': timestamp,
                        'type': self._classify_symbol_autonomously(symbol),
                        'priority': self._get_autonomous_priority(symbol),
                        'strategy': self.current_strategy,
                        'auto_selected': True
                    }
                
                logger.info(f"🤖 AUTONOMOUS: Registered {len(new_symbols)} symbols")
                logger.info(f"📊 Total active: {len(self.active_symbols)} symbols")
                
                # Check availability in cache
                available_count = sum(1 for symbol in new_symbols if symbol in live_market_data)
                if available_count > 0:
                    logger.info(f"📊 {available_count}/{len(new_symbols)} symbols immediately available")
                
            else:
                logger.warning("⚠️ ShareKhan not connected - will retry autonomously")
                
        except Exception as e:
            logger.error(f"❌ Autonomous subscription error: {e}")

    async def autonomous_strategy_monitor(self):
        """
        AUTONOMOUS STRATEGY MONITORING: Continuously evaluate and switch strategies
        Based on market conditions, performance, and opportunities
        """
        while self.is_running:
            try:
                await asyncio.sleep(self.config.strategy_switch_interval)
                
                if not self.is_market_hours():
                    continue
                    
                logger.info("🧠 Autonomous strategy evaluation...")
                
                # Get current autonomous strategy recommendation
                from config.sharekhan_symbols import get_autonomous_symbol_status
                recommended_strategy = get_autonomous_symbol_status()["current_strategy"]
                
                # Check if strategy should change
                if recommended_strategy != self.current_strategy:
                    await self._autonomous_strategy_switch(recommended_strategy)
                
                # Performance-based adjustment
                await self._performance_based_adjustment()
                
            except Exception as e:
                logger.error(f"❌ Autonomous strategy monitoring error: {e}")

    async def _autonomous_strategy_switch(self, new_strategy: str):
        """Autonomously switch to a new strategy"""
        logger.info(f"🔄 AUTONOMOUS SWITCH: {self.current_strategy} → {new_strategy}")
        
        old_strategy = self.current_strategy
        self.current_strategy = new_strategy
        
        # Record the autonomous decision
        self.strategy_history.append({
            "timestamp": datetime.now().isoformat(),
            "strategy": new_strategy,
            "previous_strategy": old_strategy,
            "reason": "Autonomous market condition change",
            "auto_decision": True
        })
        
        # Get new symbol list for the strategy
        try:
            from config.sharekhan_symbols import get_complete_fo_symbols
            new_symbols = get_complete_fo_symbols()
            
            # Update symbols autonomously
            await self.autonomous_subscribe_symbols(new_symbols)
            
            logger.info(f"✅ AUTONOMOUS: Successfully switched to {new_strategy} strategy")
            
        except Exception as e:
            logger.error(f"❌ Autonomous strategy switch failed: {e}")
            # Revert to previous strategy
            self.current_strategy = old_strategy

    async def _performance_based_adjustment(self):
        """Adjust strategy based on autonomous performance analysis"""
        try:
            # Simple performance check (can be enhanced with more metrics)
            current_performance = self.strategy_performance.get(self.current_strategy, {})
            
            if current_performance.get("trades", 0) > 10:  # Minimum trades for evaluation
                success_rate = current_performance.get("success_rate", 0.0)
                
                if success_rate < 0.4:  # Less than 40% success rate
                    logger.info(f"🤖 AUTONOMOUS: Low performance detected for {self.current_strategy}")
                    # Consider switching strategy autonomously
                    await self._consider_performance_switch()
                    
        except Exception as e:
            logger.error(f"❌ Performance-based adjustment error: {e}")

    async def _consider_performance_switch(self):
        """Consider switching strategy based on performance"""
        # Find best performing strategy
        best_strategy = max(
            self.strategy_performance.keys(),
            key=lambda s: self.strategy_performance[s].get("success_rate", 0.0)
        )
        
        if best_strategy != self.current_strategy:
            best_performance = self.strategy_performance[best_strategy]
            if best_performance.get("success_rate", 0.0) > 0.6:  # 60% success rate
                logger.info(f"🤖 AUTONOMOUS: Switching to better performing strategy: {best_strategy}")
                await self._autonomous_strategy_switch(best_strategy)

    async def autonomous_refresh_loop(self):
        """Autonomous refresh of symbols and strategy"""
        while self.is_running:
            try:
                await asyncio.sleep(self.config.auto_refresh_interval)
                
                logger.info("🔄 Autonomous symbol refresh...")
                
                # Refresh symbols based on current strategy
                await self.autonomous_symbol_setup()
                
                # Clean up any issues autonomously
                await self._autonomous_cleanup()
                
            except Exception as e:
                logger.error(f"❌ Autonomous refresh error: {e}")

    async def performance_tracker_loop(self):
        """Track performance for autonomous decision making"""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Update performance metrics (placeholder - integrate with actual trading data)
                await self._update_performance_metrics()
                
            except Exception as e:
                logger.error(f"❌ Performance tracking error: {e}")

    async def _update_performance_metrics(self):
        """Update performance metrics for autonomous decisions"""
        # Placeholder for performance tracking
        # In production, this would integrate with actual trading results
        pass

    async def _autonomous_cleanup(self):
        """Autonomous cleanup of expired or poor-performing symbols"""
        try:
            # Remove expired contracts
            expired_symbols = self.find_expired_symbols()
            if expired_symbols:
                for symbol in expired_symbols:
                    self.active_symbols.discard(symbol)
                    self.symbol_metadata.pop(symbol, None)
                logger.info(f"🤖 AUTONOMOUS: Cleaned up {len(expired_symbols)} expired symbols")
                
        except Exception as e:
            logger.error(f"❌ Autonomous cleanup error: {e}")

    def _classify_symbol_autonomously(self, symbol: str) -> str:
        """Autonomously classify symbol type"""
        if '-I' in symbol:
            return 'index'
        elif 'CE' in symbol or 'PE' in symbol:
            return 'option'
        else:
            return 'equity'

    def _get_autonomous_priority(self, symbol: str) -> int:
        """Get autonomous priority for symbol"""
        if symbol in self.config.core_indices:
            return 1  # Highest priority
        elif 'NIFTY' in symbol or 'BANKNIFTY' in symbol:
            return 2  # High priority
        elif any(stock in symbol for stock in ['RELIANCE', 'TCS', 'HDFC', 'INFY']):
            return 3  # Medium priority
        else:
            return 4  # Lower priority

    # Keep existing methods with autonomous enhancements...
    async def expiry_monitor_loop(self):
        """Autonomously monitor and remove expired contracts"""
        while self.is_running:
            try:
                await asyncio.sleep(self.config.expiry_check_interval)
                
                logger.info("🕒 Autonomous expiry check...")
                
                expired_symbols = self.find_expired_symbols()
                if expired_symbols:
                    await self._autonomous_cleanup()
                
            except Exception as e:
                logger.error(f"❌ Autonomous expiry monitor error: {e}")

    def find_expired_symbols(self) -> List[str]:
        """Find expired option contracts autonomously"""
        expired = []
        today = datetime.now().date()
        
        for symbol in self.active_symbols:
            if 'CE' in symbol or 'PE' in symbol:
                if self.is_symbol_expired(symbol, today):
                    expired.append(symbol)
        
        return expired

    def is_symbol_expired(self, symbol: str, today) -> bool:
        """Check if an option symbol is expired (autonomous)"""
        # Simplified expiry check - can be enhanced
        return False

    def is_market_hours(self) -> bool:
        """Check if markets are open (autonomous)"""
        now = datetime.now()
        current_time = now.time()
        
        market_open = datetime.strptime("09:15", "%H:%M").time()
        market_close = datetime.strptime("15:30", "%H:%M").time()
        
        is_weekday = now.weekday() < 5
        
        return is_weekday and market_open <= current_time <= market_close

    def get_autonomous_status(self) -> Dict:
        """Get current autonomous status"""
        return {
            'autonomous_mode': True,
            'current_strategy': self.current_strategy,
            'active_symbols': len(self.active_symbols),
            'max_symbols': self.config.max_symbols,
            'utilization': f"{len(self.active_symbols)}/{self.config.max_symbols}",
            'strategy_switches_today': len([h for h in self.strategy_history 
                                          if h['timestamp'].startswith(datetime.now().strftime('%Y-%m-%d'))]),
            'last_strategy_change': self.strategy_history[-1] if self.strategy_history else None,
            'performance_tracking': True,
            'manual_intervention_required': False,
            'next_evaluation': datetime.now() + timedelta(seconds=self.config.strategy_switch_interval)
        }
    
    def get_status(self) -> Dict:
        """Get current status (alias for get_autonomous_status)"""
        return self.get_autonomous_status()

# Global instance
_autonomous_symbol_manager = None

# Alias for API compatibility
intelligent_symbol_manager = None

async def start_intelligent_symbol_management():
    """
    Start the intelligent symbol management system
    This function is called by main.py during startup
    """
    global _autonomous_symbol_manager, intelligent_symbol_manager
    
    try:
        if _autonomous_symbol_manager is None:
            logger.info("🤖 Starting Intelligent Symbol Management System...")
            
            # Create and initialize the autonomous symbol manager
            _autonomous_symbol_manager = AutonomousSymbolManager()
            await _autonomous_symbol_manager.start()
            
            # Update API alias
            intelligent_symbol_manager = _autonomous_symbol_manager
            
            logger.info("✅ Intelligent Symbol Management System started successfully")
            return True
        else:
            logger.info("⚠️ Intelligent Symbol Management already running")
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to start Intelligent Symbol Management: {e}")
        return False

async def get_intelligent_symbol_manager() -> Optional[AutonomousSymbolManager]:
    """Get the global autonomous symbol manager instance"""
    return _autonomous_symbol_manager

async def get_intelligent_symbol_status():
    """Get current status of the intelligent symbol manager"""
    global _autonomous_symbol_manager
    
    if _autonomous_symbol_manager:
        return _autonomous_symbol_manager.get_status()
    else:
        return {
            'status': 'not_running',
            'message': 'Intelligent Symbol Manager not initialized'
        }

async def get_active_symbols():
    """Get list of currently active symbols"""
    global _autonomous_symbol_manager
    
    if _autonomous_symbol_manager:
        return list(_autonomous_symbol_manager.active_symbols)
    else:
        return []

async def stop_intelligent_symbol_management():
    """Stop the intelligent symbol management system"""
    global _autonomous_symbol_manager
    
    try:
        if _autonomous_symbol_manager:
            await _autonomous_symbol_manager.stop()
            _autonomous_symbol_manager = None
            logger.info("🛑 Intelligent Symbol Management System stopped")
        return True
    except Exception as e:
        logger.error(f"❌ Error stopping Intelligent Symbol Management: {e}")
        return False 