#!/usr/bin/env python3
"""
FREE CRYPTO TRADING SYSTEM - PRODUCTION READY
Real-time crypto trading with live data - NO SIMULATION

CRITICAL: This system uses REAL data and REAL trading capabilities only.
No mock data, demo mode, or simulation allowed per user guidelines.
"""

import logging
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.quantum_trading_system import QuantumTradingSystem

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProductionCryptoTradingSystem:
    """Production-ready crypto trading system - REAL DATA ONLY"""
    
    def __init__(self):
        self.system = None
        self.is_running = False
        
    async def initialize(self):
        """Initialize production trading system"""
        try:
            logger.info("🚀 Initializing PRODUCTION Crypto Trading System...")
            logger.info("✅ REAL DATA ONLY - No simulation or demo modes")
            
            # Initialize with production configuration
            self.system = QuantumTradingSystem("config/quantum_trading_config.yaml")
            await self.system.initialize()
            
            logger.info("✅ Production system initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Production system initialization failed: {e}")
            raise
    
    async def start_trading(self):
        """Start production trading"""
        try:
            if not self.system:
                raise RuntimeError("System not initialized")
            
            logger.info("🎯 Starting PRODUCTION crypto trading...")
            
            # Get real active symbols from database
            from src.core.database import get_db_session
            async with get_db_session() as session:
                result = await session.execute("""
                    SELECT symbol, name FROM symbols 
                    WHERE is_active = true AND exchange = 'BINANCE'
                    ORDER BY volume_24h DESC
                    LIMIT 10
                """)
                
                active_symbols = result.fetchall()
                if not active_symbols:
                    raise RuntimeError("No active symbols found in database")
            
            symbol_list = [row.symbol for row in active_symbols]
            logger.info(f"   🎯 Active Symbols: {', '.join(symbol_list)}")
            
            # Start real trading
            await self.system.start()
            self.is_running = True
            
            logger.info("✅ Production trading started successfully")
            
            # Monitor real trading performance
            await self._monitor_real_performance()
            
        except Exception as e:
            logger.error(f"❌ Production trading failed: {e}")
            raise
    
    async def _monitor_real_performance(self):
        """Monitor real trading performance"""
        try:
            while self.is_running:
                # Get real performance metrics from database
                performance = await self._get_real_performance_metrics()
                
                if performance:
                    logger.info(f"📊 Real Performance:")
                    logger.info(f"   • Total Trades: {performance.get('total_trades', 0)}")
                    logger.info(f"   • Success Rate: {performance.get('success_rate', 0):.1f}%")
                    logger.info(f"   • Total P&L: ${performance.get('total_pnl', 0):.2f}")
                    logger.info(f"   • Active Positions: {performance.get('active_positions', 0)}")
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
        except Exception as e:
            logger.error(f"Performance monitoring error: {e}")
    
    async def _get_real_performance_metrics(self) -> dict:
        """Get real performance metrics from database"""
        try:
            from src.core.database import get_db_session
            
            async with get_db_session() as session:
                # Get real trading statistics
                result = await session.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        AVG(CASE WHEN pnl > 0 THEN 1.0 ELSE 0.0 END) * 100 as success_rate,
                        SUM(pnl) as total_pnl,
                        COUNT(CASE WHEN status = 'OPEN' THEN 1 END) as active_positions
                    FROM trades 
                    WHERE DATE(created_at) = CURRENT_DATE
                """)
                
                row = result.fetchone()
                if row:
                    return {
                        'total_trades': row.total_trades,
                        'success_rate': float(row.success_rate or 0),
                        'total_pnl': float(row.total_pnl or 0),
                        'active_positions': row.active_positions
                    }
                
            return {}
            
        except Exception as e:
            logger.error(f"Error getting real performance metrics: {e}")
            return {}
    
    async def stop(self):
        """Stop production trading"""
        try:
            self.is_running = False
            if self.system:
                await self.system.stop()
            logger.info("🛑 Production trading stopped")
            
        except Exception as e:
            logger.error(f"Error stopping system: {e}")

async def main():
    """Main entry point for production crypto trading"""
    system = None
    
    try:
        logger.info("=" * 80)
        logger.info("          PRODUCTION CRYPTO TRADING SYSTEM")
        logger.info("=" * 80)
        logger.info("")
        logger.info("⚡ REAL-TIME TRADING - NO SIMULATION")
        logger.info("🔥 LIVE MARKET DATA ONLY")
        logger.info("💰 PRODUCTION TRADING ENVIRONMENT")
        logger.info("")
        
        # Initialize and start production system
        system = ProductionCryptoTradingSystem()
        await system.initialize()
        await system.start_trading()
        
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR: {e}")
        sys.exit(1)
    finally:
        if system:
            await system.stop()

if __name__ == "__main__":
    asyncio.run(main()) 