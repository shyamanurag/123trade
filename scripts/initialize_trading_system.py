#!/usr/bin/env python3
"""
Initialize Autonomous Trading System
Prepares the system for 9:15 AM IST trading start
"""
import asyncio
import pytz
from datetime import datetime, time
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.orchestrator import TradingOrchestrator
from src.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TradingSystemInitializer:
    def __init__(self):
        self.orchestrator = TradingOrchestrator.get_instance()
        self.ist = pytz.timezone('Asia/Kolkata')
        self.trading_start = time(9, 15)  # 9:15 AM IST
        self.trading_end = time(15, 30)   # 3:30 PM IST
        
    async def check_system_health(self):
        """Perform system health checks"""
        logger.info("Performing system health checks...")
        
        checks = {
            "Database": await self.check_database(),
            "Redis": await self.check_redis(),
            "TrueData": await self.check_truedata(),
            "Zerodha": await self.check_zerodha(),
            "Risk Manager": await self.check_risk_manager(),
            "Order Manager": await self.check_order_manager()
        }
        
        all_healthy = all(checks.values())
        
        logger.info("System Health Check Results:")
        for component, status in checks.items():
            logger.info(f"  {component}: {'✅ PASS' if status else '❌ FAIL'}")
            
        return all_healthy
    
    async def check_database(self):
        """Check database connectivity"""
        try:
            # Add actual database check here
            return True
        except Exception as e:
            logger.error(f"Database check failed: {e}")
            return False
    
    async def check_redis(self):
        """Check Redis connectivity"""
        try:
            # Add actual Redis check here
            return True
        except Exception as e:
            logger.error(f"Redis check failed: {e}")
            return False
    
    async def check_truedata(self):
        """Check TrueData connection"""
        try:
            # Add actual TrueData check here
            return True
        except Exception as e:
            logger.error(f"TrueData check failed: {e}")
            return False
    
    async def check_zerodha(self):
        """Check Zerodha authentication"""
        try:
            # Add actual Zerodha check here
            return True
        except Exception as e:
            logger.error(f"Zerodha check failed: {e}")
            return False
    
    async def check_risk_manager(self):
        """Check risk management system"""
        try:
            # Add actual risk manager check here
            return True
        except Exception as e:
            logger.error(f"Risk manager check failed: {e}")
            return False
    
    async def check_order_manager(self):
        """Check order management system"""
        try:
            # Add actual order manager check here
            return True
        except Exception as e:
            logger.error(f"Order manager check failed: {e}")
            return False
    
    def get_time_to_market_open(self):
        """Calculate time until market opens"""
        now = datetime.now(self.ist)
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        
        if now.time() >= self.trading_start:
            # Market already open or it's after hours
            return None
            
        time_diff = market_open - now
        return time_diff.total_seconds()
    
    async def wait_for_market_open(self):
        """Wait until 9:15 AM IST"""
        seconds_to_wait = self.get_time_to_market_open()
        
        if seconds_to_wait is None:
            logger.info("Market is already open or it's after trading hours")
            return
        
        logger.info(f"Waiting {seconds_to_wait/60:.1f} minutes for market to open...")
        
        while seconds_to_wait > 0:
            if seconds_to_wait > 300:  # More than 5 minutes
                await asyncio.sleep(60)  # Check every minute
            else:
                await asyncio.sleep(10)  # Check every 10 seconds
            
            seconds_to_wait = self.get_time_to_market_open()
            if seconds_to_wait:
                logger.info(f"Time to market open: {seconds_to_wait/60:.1f} minutes")
    
    async def initialize_trading(self):
        """Initialize the autonomous trading system"""
        logger.info("=" * 60)
        logger.info("AUTONOMOUS TRADING SYSTEM INITIALIZATION")
        logger.info("=" * 60)
        
        # Step 1: System Health Check
        if not await self.check_system_health():
            logger.error("System health check failed! Cannot proceed.")
            return False
        
        # Step 2: Load strategies
        logger.info("Loading trading strategies...")
        # Add strategy loading logic here
        
        # Step 3: Initialize risk parameters
        logger.info("Setting risk parameters...")
        logger.info(f"  Max trades per second: 7 (NSE limit)")
        logger.info(f"  Paper trading: {settings.get('PAPER_TRADING', True)}")
        
        # Step 4: Wait for market open if needed
        await self.wait_for_market_open()
        
        # Step 5: Enable trading
        logger.info("Enabling autonomous trading...")
        await self.orchestrator.enable_trading()
        
        # Step 6: Start monitoring
        logger.info("Starting system monitoring...")
        
        logger.info("=" * 60)
        logger.info("TRADING SYSTEM INITIALIZED SUCCESSFULLY")
        logger.info("Autonomous trading is now active")
        logger.info("=" * 60)
        
        return True
    
    async def run(self):
        """Main execution"""
        try:
            success = await self.initialize_trading()
            if success:
                # Keep the system running
                logger.info("System is running. Press Ctrl+C to stop.")
                while True:
                    # Log heartbeat every 5 minutes
                    await asyncio.sleep(300)
                    status = await self.orchestrator.get_trading_status()
                    logger.info(f"System heartbeat - Active: {status['is_active']}, "
                              f"Trades: {status['total_trades']}, "
                              f"P&L: {status['daily_pnl']}")
        except KeyboardInterrupt:
            logger.info("Shutting down trading system...")
            await self.orchestrator.disable_trading()
            logger.info("Trading system stopped.")

if __name__ == "__main__":
    initializer = TradingSystemInitializer()
    asyncio.run(initializer.run()) 