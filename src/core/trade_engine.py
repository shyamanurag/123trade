"""
Trade Engine - Handles order execution and management
"""

import asyncio
import logging
import time
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

from src.core.paper_trading_user_manager import PaperTradingUserManager
from src.core.database_schema_manager import DatabaseSchemaManager
from sqlalchemy import text

class TradeEngine:
    """Enhanced trade engine with paper trading support"""
    
    def __init__(self, db_config, order_manager, position_tracker, performance_tracker, notification_manager, config=None):
        """Initialize trade engine with all required components and configuration"""
        self.db_config = db_config
        self.order_manager = order_manager
        self.position_tracker = position_tracker
        self.performance_tracker = performance_tracker
        self.notification_manager = notification_manager
        self.logger = logging.getLogger(__name__)
        
        # Handle configuration with defaults
        self.config = config or {}
        
        # CRITICAL FIX: Initialize paper trading mode from configuration  
        self.paper_trading_enabled = self.config.get('paper_trading', False)  # Default to LIVE TRADING for real money
        
        # CRITICAL FIX: Initialize all missing attributes
        self.paper_orders = {}  # Store paper trading orders
        self.pending_signals = []  # Store pending signals
        self.signal_rate_limit = 10.0  # Max 10 signals per second
        self.last_signal_time = 0.0  # Last signal processing time
        
        # Initialize additional required attributes
        self.sharekhan_client = None  # Will be set by orchestrator
        self.risk_manager = None  # Will be set by orchestrator
        
        # Ensure precise database schema
        self._ensure_database_schema()
        
        # Initialize paper trading user manager (no arguments needed - it uses static methods)
        self.paper_user_manager = PaperTradingUserManager()
        
        # Initialize statistics
        self.statistics = {
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_pnl': 0.0,
            'last_trade_time': None
        }
        
        # Status tracking
        self.is_active = True
        self.last_error = None
        
        self.logger.info(f"✅ TradeEngine initialized - Paper trading: {self.paper_trading_enabled}")
    
    def _ensure_database_schema(self):
        """Ensure database has precise schema - this is the definitive approach"""
        try:
            schema_manager = DatabaseSchemaManager(self.db_config.database_url)
            result = schema_manager.ensure_precise_schema()
            
            if result['status'] == 'success':
                self.logger.info("Trade engine: Database schema verified")
            else:
                self.logger.error(f"Trade engine: Database schema issues: {result['errors']}")
                
        except Exception as e:
            self.logger.error(f"Trade engine: Error ensuring database schema: {e}")
    
    async def initialize(self):
        """Initialize trade engine"""
        try:
            self.logger.info("✅ Trade Engine initialized")
            return True
        except Exception as e:
            self.logger.error(f"❌ Trade Engine initialization failed: {e}")
            return False
    
    async def process_signal(self, signal: Dict):
        """Process trading signal with paper trading support"""
        try:
            # Check if paper trading is enabled
            if self.paper_trading_enabled:
                return await self._process_paper_signal(signal)
            else:
                return await self._process_live_signal(signal)
                
        except Exception as e:
            self.logger.error(f"❌ Error processing signal: {e}")
            return None
    
    async def process_signals(self, signals: List[Dict]):
        """Process trading signals and track execution results"""
        if not signals:
            return []
        
        self.logger.info(f"🔍 Processing {len(signals)} signals for execution")
        execution_results = []
        
        for signal in signals:
            try:
                if self.paper_trading_enabled:
                    result = await self._process_paper_signal(signal)
                else:
                    result = await self._process_live_signal(signal)
                
                if result:
                    execution_results.append(result)
                    # TRACK: Signal executed successfully
                    self._track_signal_executed(signal)
                    self.logger.info(f"✅ Signal executed: {signal.get('symbol')} {signal.get('action')}")
                else:
                    execution_results.append(None)
                    # TRACK: Signal execution failed
                    self._track_signal_execution_failed(signal, "Execution returned None")
                    self.logger.error(f"❌ Signal execution failed: {signal.get('symbol')} {signal.get('action')}")
                    
            except Exception as e:
                execution_results.append(None)
                # TRACK: Signal execution failed with exception
                self._track_signal_execution_failed(signal, str(e))
                self.logger.error(f"❌ Signal processing failed: {signal.get('symbol')} {signal.get('action')} - {e}")
        
        # Update pending signals list
        if hasattr(self, 'pending_signals'):
            self.pending_signals.extend([s for s, r in zip(signals, execution_results) if r is None])
        
        return execution_results
    
    def _track_signal_executed(self, signal: Dict):
        """Track successful signal execution"""
        try:
            # Get orchestrator instance to update stats
            from src.core.orchestrator import get_orchestrator_instance
            orchestrator = get_orchestrator_instance()
            
            if orchestrator and hasattr(orchestrator, 'signal_stats'):
                orchestrator.signal_stats['executed'] += 1
                
                strategy = signal.get('strategy', 'unknown')
                if strategy in orchestrator.signal_stats['by_strategy']:
                    orchestrator.signal_stats['by_strategy'][strategy]['executed'] += 1
                
                self.logger.info(f"📊 EXECUTION TRACKED: Total executed: {orchestrator.signal_stats['executed']}")
                
        except Exception as e:
            self.logger.error(f"Error tracking signal execution: {e}")
    
    def _track_signal_execution_failed(self, signal: Dict, reason: str):
        """Track failed signal execution"""
        try:
            # Get orchestrator instance to update stats
            from src.core.orchestrator import get_orchestrator_instance
            orchestrator = get_orchestrator_instance()
            
            if orchestrator and hasattr(orchestrator, '_track_signal_failed'):
                orchestrator._track_signal_failed(signal, reason)
            else:
                self.logger.error(f"📊 EXECUTION FAILED: {signal.get('symbol')} - {reason}")
                
        except Exception as e:
            self.logger.error(f"Error tracking signal execution failure: {e}")
    
    async def _try_get_sharekhan_client_from_orchestrator(self):
        """Try to get ShareKhan client from orchestrator if not set"""
        try:
            # CRITICAL FIX: Use correct function name
            from src.core.orchestrator import get_orchestrator_instance
            orchestrator = get_orchestrator_instance()
            
            if orchestrator and hasattr(orchestrator, 'sharekhan_client') and orchestrator.sharekhan_client:
                self.sharekhan_client = orchestrator.sharekhan_client
                self.logger.info("✅ Successfully retrieved ShareKhan client from orchestrator")
                return True
            else:
                self.logger.error("❌ No ShareKhan client available in orchestrator")
                # CRITICAL DEBUG: Log orchestrator state
                if orchestrator:
                    self.logger.error(f"❌ Orchestrator exists but sharekhan_client is: {getattr(orchestrator, 'sharekhan_client', 'MISSING')}")
                else:
                    self.logger.error("❌ No orchestrator instance found")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error getting ShareKhan client from orchestrator: {e}")
            return False
    
    async def _process_paper_signal(self, signal: Dict):
        """Process signal in paper trading mode with REAL ShareKhan API and P&L tracking"""
        try:
            self.logger.info(f"📊 Processing paper signal for {signal.get('symbol', 'UNKNOWN')}")
            
            # CRITICAL FIX: Attempt to get ShareKhan client if not available
            if not self.sharekhan_client:
                self.logger.warning("⚠️ ShareKhan client not set, attempting to retrieve from orchestrator")
                await self._try_get_sharekhan_client_from_orchestrator()
            
            # CRITICAL FIX: Use real ShareKhan API even in paper mode
            if self.sharekhan_client:
                # CRITICAL FIX: Map signal 'action' to order 'action' correctly
                signal_action = signal.get('action', 'BUY').upper()
                
                # Create order for ShareKhan API (sandbox mode)
                order_data = {
                    'symbol': signal.get('symbol'),
                    'quantity': signal.get('quantity', 50),
                    'action': signal_action,  # ✅ FIXED: Use 'action' from signal
                    'transaction_type': signal_action,  # ✅ FIXED: Backup field  
                    'side': signal_action,  # ✅ FIXED: Another backup field
                    'order_type': 'MARKET',
                    'product': self._get_product_type_for_symbol(signal.get('symbol', '')),  # FIXED: Dynamic product type
                    'validity': 'DAY'
                }
                
                self.logger.info(f"🔄 Signal: {signal.get('symbol')} {signal_action} → Order: {signal.get('symbol')} {signal_action}")
                
                # Place order through ShareKhan (sandbox)
                result = await self.sharekhan_client.place_order(order_data)
                
                # CRITICAL FIX: Handle string order_id returned by ShareKhanIntegration  
                if result and isinstance(result, str):
                    # ShareKhanIntegration returns order_id string directly
                    order_id = result
                    execution_price = signal.get('entry_price', 0)
                    
                    # CRITICAL FIX: Never store trades with zero or invalid prices
                    if not execution_price or execution_price <= 0:
                        self.logger.error(f"❌ INVALID EXECUTION PRICE: {execution_price} for {signal.get('symbol')}")
                        self.logger.error("❌ REJECTED: Cannot store trade with zero/invalid price - violates no-mock-data policy")
                        return None
                    
                    # Create trade record with real execution data  
                    trade_record = {
                        'trade_id': order_id,
                        'symbol': signal.get('symbol'),
                        'side': signal_action,  # ✅ FIXED: Use correct action
                        'quantity': signal.get('quantity', 50),
                        'price': execution_price,
                        'strategy': signal.get('strategy', 'unknown'),
                        'status': 'EXECUTED',
                        'executed_at': datetime.now(),
                        'user_id': 'PAPER_TRADER_001'
                    }
                    
                    # Update position tracker
                    if self.position_tracker:
                        await self.position_tracker.update_position(
                            symbol=trade_record['symbol'],
                            quantity=trade_record['quantity'],
                            price=execution_price,
                            side=trade_record['side'].lower()
                        )
                    
                    # CRITICAL FIX: Calculate real P&L and store to database
                    await self._calculate_and_store_trade_pnl(trade_record)
                    
                    self.logger.info(f"✅ Paper trade executed via ShareKhan API: {order_id}")
                    return trade_record
                elif result and isinstance(result, dict) and result.get('success'):
                    # Handle dict format (backward compatibility)
                    order_id = result.get('order_id', f"PAPER_{int(time.time())}")
                    execution_price = result.get('price', signal.get('entry_price', 0))
                    
                    # Similar processing as above for dict format...
                    trade_record = {
                        'trade_id': order_id,
                        'symbol': signal.get('symbol'),
                        'side': signal_action,
                        'quantity': signal.get('quantity', 50),
                        'price': execution_price,
                        'strategy': signal.get('strategy', 'unknown'),
                        'status': 'EXECUTED',
                        'executed_at': datetime.now(),
                        'user_id': 'PAPER_TRADER_001'
                    }
                    
                    if self.position_tracker:
                        await self.position_tracker.update_position(
                            symbol=trade_record['symbol'],
                            quantity=trade_record['quantity'],
                            price=execution_price,
                            side=trade_record['side'].lower()
                        )
                    
                    await self._calculate_and_store_trade_pnl(trade_record)
                    self.logger.info(f"✅ Paper trade executed via ShareKhan API: {order_id}")
                    return trade_record
                
            # ENHANCED SAFETY: Handle ShareKhan failures with graceful degradation
            self.logger.error("❌ CRITICAL: ShareKhan client not available - NO FALLBACK EXECUTION")
            
            # RULE #8: Don't suggest bypasses—fix root causes
            # RULE #1: Never put mock/demo data in production trading system
            self.logger.error("❌ NO FALLBACK EXECUTION - Real broker required for all trades")
            self.logger.error(f"❌ Signal REJECTED: {signal.get('symbol')} {signal.get('side')} {signal.get('quantity')}")
            self.logger.error("🚨 SYSTEM DESIGNED TO FAIL WHEN BROKER UNAVAILABLE - FIX SHAREKHAN CONNECTION")
            
            # Track failed execution
            self._track_signal_execution_failed(signal, "ShareKhan client unavailable - NO FALLBACK ALLOWED")
            
            # CRITICAL: Raise exception to make failure visible
            raise Exception(f"BROKER CONNECTION FAILED: {signal.get('symbol')} - No fallback execution allowed per Rule #8")
                
        except Exception as e:
            self.logger.error(f"❌ Error processing paper signal: {e}")
            return None

    async def _calculate_and_store_trade_pnl(self, trade_record: Dict):
        """Calculate real-time P&L and store trade to database"""
        try:
            symbol = trade_record['symbol']
            entry_price = float(trade_record['price'])
            quantity = trade_record['quantity']
            side = trade_record['side']
            
            # CRITICAL FIX: Get REAL current market price from ShareKhan
            current_price = await self._get_current_market_price(symbol)
            if not current_price or current_price <= 0:
                self.logger.warning(f"⚠️ No real-time price for {symbol}, using entry price as fallback")
                current_price = entry_price  # Fallback only
            
            # Calculate P&L based on real market movement
            if side.upper() == 'BUY':
                pnl = (current_price - entry_price) * quantity
            else:  # SELL
                pnl = (entry_price - current_price) * quantity
            
            # Calculate P&L percentage
            position_value = entry_price * quantity
            pnl_percent = (pnl / position_value) * 100 if position_value > 0 else 0
            
            # Update trade record with REAL market data
            trade_record['pnl'] = round(pnl, 2)
            trade_record['pnl_percent'] = round(pnl_percent, 2)
            trade_record['current_price'] = current_price
            trade_record['entry_price'] = entry_price  # Keep original entry
            
            # Store to database
            await self._store_trade_to_database(trade_record)
            
            # Start background price monitoring for this trade
            asyncio.create_task(self._monitor_trade_price_updates(trade_record))
            
            self.logger.info(f"💰 P&L calculated for {symbol}: Entry ₹{entry_price:.2f} → Current ₹{current_price:.2f} = ₹{pnl:.2f} ({pnl_percent:.2f}%)")
            
        except Exception as e:
            self.logger.error(f"❌ Error calculating and storing P&L: {e}")
    
    async def _monitor_trade_price_updates(self, trade_record: Dict):
        """Background task to continuously update trade prices and P&L"""
        symbol = trade_record['symbol']
        trade_id = trade_record['trade_id']
        
        try:
            while True:
                # Get fresh market price
                current_price = await self._get_current_market_price(symbol)
                
                if current_price and current_price > 0:
                    # Recalculate P&L with new price
                    entry_price = float(trade_record['price'])
                    quantity = trade_record['quantity']
                    side = trade_record['side']
                    
                    if side.upper() == 'BUY':
                        pnl = (current_price - entry_price) * quantity
                    else:  # SELL
                        pnl = (entry_price - current_price) * quantity
                    
                    position_value = entry_price * quantity
                    pnl_percent = (pnl / position_value) * 100 if position_value > 0 else 0
                    
                    # Update database with new P&L
                    await self._update_trade_pnl_in_database(trade_id, current_price, pnl, pnl_percent)
                    
                    self.logger.debug(f"📊 Updated {symbol}: ₹{current_price:.2f} | P&L: ₹{pnl:.2f} ({pnl_percent:.2f}%)")
                
                # Update every 30 seconds during market hours
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            self.logger.info(f"⏹️ Stopped price monitoring for {symbol}")
        except Exception as e:
            self.logger.error(f"❌ Error in price monitoring for {symbol}: {e}")
    
    async def _update_trade_pnl_in_database(self, trade_id: str, current_price: float, pnl: float, pnl_percent: float):
        """Update trade P&L in database with real-time data"""
        try:
            from src.config.database import get_db
            db_session = next(get_db())
            
            if db_session:
                from sqlalchemy import text
                update_query = text("""
                    UPDATE trades 
                    SET current_price = :current_price, 
                        pnl = :pnl, 
                        pnl_percent = :pnl_percent,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE order_id = :trade_id
                """)
                
                db_session.execute(update_query, {
                    'current_price': current_price,
                    'pnl': pnl,
                    'pnl_percent': pnl_percent,
                    'trade_id': trade_id
                })
                db_session.commit()
                
        except Exception as e:
            self.logger.error(f"❌ Error updating trade P&L in database: {e}")
            if db_session:
                db_session.rollback()
        finally:
            if db_session:
                db_session.close()
    
    async def sync_actual_sharekhan_trades(self):
        """CRITICAL: Fetch ACTUAL executed trades from ShareKhan API"""
        try:
            if not self.sharekhan_client:
                self.logger.warning("⚠️ No ShareKhan client for trade sync")
                return
            
            self.logger.info("🔄 Syncing actual executed trades from ShareKhan...")
            
            # Get actual orders from ShareKhan API
            sharekhan_orders = await self.sharekhan_client.get_orders()
            
            if not sharekhan_orders:
                self.logger.warning("⚠️ No orders returned from ShareKhan API")
                return
            
            executed_trades = []
            for order in sharekhan_orders:
                if order.get('status') == 'COMPLETE':
                    # This is an ACTUAL executed trade
                    executed_trade = {
                        'trade_id': order.get('order_id'),
                        'symbol': order.get('tradingsymbol'),
                        'side': order.get('transaction_type'),
                        'quantity': order.get('filled_quantity', order.get('quantity')),
                        'price': order.get('average_price', order.get('price')),
                        'status': 'EXECUTED',
                        'executed_at': order.get('order_timestamp'),
                        'exchange_time': order.get('exchange_timestamp'),
                        'actual_execution': True  # Mark as real execution
                    }
                    executed_trades.append(executed_trade)
            
            self.logger.info(f"✅ Found {len(executed_trades)} actual executed trades from ShareKhan")
            
            # Update our records with ACTUAL execution data
            for trade in executed_trades:
                await self._update_with_actual_execution_data(trade)
            
            return executed_trades
            
        except Exception as e:
            self.logger.error(f"❌ Error syncing actual ShareKhan trades: {e}")
            return []
    
    async def _update_with_actual_execution_data(self, actual_trade: Dict):
        """Update internal trade records with ACTUAL execution data from ShareKhan"""
        try:
            trade_id = actual_trade['trade_id']
            
            # Update database with ACTUAL execution data
            from src.config.database import get_db
            db_session = next(get_db())
            
            if db_session:
                from sqlalchemy import text
                
                # Check if trade exists in our database
                check_query = text("SELECT order_id FROM trades WHERE order_id = :trade_id")
                existing = db_session.execute(check_query, {'trade_id': trade_id}).fetchone()
                
                if existing:
                    # Update with actual execution data
                    update_query = text("""
                        UPDATE trades 
                        SET quantity = :quantity,
                            price = :price,
                            executed_at = :executed_at,
                            actual_execution = true,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE order_id = :trade_id
                    """)
                    
                    db_session.execute(update_query, {
                        'quantity': actual_trade['quantity'],
                        'price': actual_trade['price'],
                        'executed_at': actual_trade['executed_at'],
                        'trade_id': trade_id
                    })
                else:
                    # Insert new ACTUAL trade that we didn't track before
                    insert_query = text("""
                        INSERT INTO trades (
                            order_id, symbol, trade_type, quantity, price,
                            status, executed_at, actual_execution, user_id
                        ) VALUES (
                            :trade_id, :symbol, :side, :quantity, :price,
                            :status, :executed_at, true, :user_id
                        )
                    """)
                    
                    db_session.execute(insert_query, {
                        'trade_id': trade_id,
                        'symbol': actual_trade['symbol'],
                        'side': actual_trade['side'],
                        'quantity': actual_trade['quantity'],
                        'price': actual_trade['price'],
                        'status': actual_trade['status'],
                        'executed_at': actual_trade['executed_at'],
                        'user_id': 'SHAREKHAN_SYNC'
                    })
                
                db_session.commit()
                self.logger.info(f"✅ Updated trade {trade_id} with ACTUAL execution data")
                
        except Exception as e:
            self.logger.error(f"❌ Error updating with actual execution data: {e}")
            if db_session:
                db_session.rollback()
        finally:
            if db_session:
                db_session.close()
    
    async def sync_actual_sharekhan_positions(self):
        """CRITICAL: Fetch ACTUAL positions from ShareKhan API for square-off"""
        try:
            if not self.sharekhan_client:
                self.logger.warning("⚠️ No ShareKhan client for position sync")
                return {}
            
            self.logger.info("🔄 Syncing actual positions from ShareKhan for square-off...")
            
            # Get ACTUAL positions from ShareKhan API
            positions_data = await self.sharekhan_client.get_positions()
            
            if not positions_data:
                self.logger.warning("⚠️ No positions returned from ShareKhan API")
                return {}
            
            # Extract net positions (for square-off)
            net_positions = positions_data.get('net', [])
            day_positions = positions_data.get('day', [])
            
            active_positions = {}
            
            # Process net positions (overnight positions)
            for pos in net_positions:
                if pos.get('quantity', 0) != 0:  # Only positions with quantity
                    symbol = pos.get('tradingsymbol')
                    active_positions[symbol] = {
                        'symbol': symbol,
                        'quantity': pos.get('quantity'),
                        'average_price': pos.get('average_price', 0),
                        'ltp': pos.get('last_price', 0),
                        'pnl': pos.get('pnl', 0),
                        'unrealized_pnl': pos.get('unrealized_pnl', 0),
                        'position_type': 'net',
                        'product': pos.get('product'),
                        'exchange': pos.get('exchange')
                    }
            
            # Process day positions (intraday)
            for pos in day_positions:
                if pos.get('quantity', 0) != 0:
                    symbol = pos.get('tradingsymbol')
                    active_positions[symbol] = {
                        'symbol': symbol,
                        'quantity': pos.get('quantity'),
                        'average_price': pos.get('average_price', 0),
                        'ltp': pos.get('last_price', 0),
                        'pnl': pos.get('pnl', 0),
                        'unrealized_pnl': pos.get('unrealized_pnl', 0),
                        'position_type': 'day',
                        'product': pos.get('product'),
                        'exchange': pos.get('exchange')
                    }
            
            self.logger.info(f"✅ Found {len(active_positions)} ACTUAL positions from ShareKhan")
            
            # Update position tracker with ACTUAL positions
            if self.position_tracker:
                await self._update_position_tracker_with_actual_data(active_positions)
            
            return active_positions
            
        except Exception as e:
            self.logger.error(f"❌ Error syncing actual ShareKhan positions: {e}")
            return {}
    
    async def _update_position_tracker_with_actual_data(self, actual_positions: Dict):
        """Update position tracker with ACTUAL ShareKhan position data"""
        try:
            for symbol, pos_data in actual_positions.items():
                await self.position_tracker.update_position(
                    symbol=symbol,
                    quantity=pos_data['quantity'],
                    price=pos_data['average_price'],
                    side='long' if pos_data['quantity'] > 0 else 'short'
                )
                
                # Update with real-time LTP for P&L calculation
                if pos_data['ltp'] > 0:
                    market_data = {symbol: pos_data['ltp']}
                    await self.position_tracker.update_market_prices(market_data)
            
            self.logger.info(f"✅ Updated position tracker with {len(actual_positions)} ACTUAL positions")
            
        except Exception as e:
            self.logger.error(f"❌ Error updating position tracker with actual data: {e}")
    
    async def start_real_time_sync(self):
        """Start background tasks for real-time ShareKhan data synchronization"""
        self.logger.info("🚀 Starting real-time ShareKhan data synchronization...")
        
        # Start trade sync (every 2 minutes)
        asyncio.create_task(self._periodic_trade_sync())
        
        # Start position sync (every 1 minute)  
        asyncio.create_task(self._periodic_position_sync())
        
        self.logger.info("✅ Real-time sync tasks started")
    
    async def _periodic_trade_sync(self):
        """Periodic task to sync actual trades from ShareKhan"""
        while True:
            try:
                await self.sync_actual_sharekhan_trades()
                await asyncio.sleep(120)  # Every 2 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ Error in periodic trade sync: {e}")
                await asyncio.sleep(120)
    
    async def _periodic_position_sync(self):
        """Periodic task to sync actual positions from ShareKhan"""
        while True:
            try:
                await self.sync_actual_sharekhan_positions()
                await asyncio.sleep(60)  # Every 1 minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ Error in periodic position sync: {e}")
                await asyncio.sleep(60)
    
    async def _get_current_market_price(self, symbol: str) -> Optional[float]:
        """Get current market price from ShareKhan cache"""
        try:
            # Try to get from ShareKhan cache
            from data.sharekhan_client import live_market_data
            if symbol in live_market_data:
                market_data = live_market_data[symbol]
                # Use LTP (Last Traded Price) or Close price
                return float(market_data.get('ltp', market_data.get('close', 0)))
            
            # Try Redis cache if available
            # Note: redis_client not available in this context
            # if hasattr(self, 'redis_client') and self.redis_client:
            #     cached_price = await self.redis_client.get(f"price:{symbol}")
            #     if cached_price:
            #         return float(cached_price)
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error getting market price for {symbol}: {e}")
            return None

    async def _store_trade_to_database(self, trade_record: Dict):
        """Store trade to database with P&L data"""
        try:
            from src.config.database import get_db
            db_session = next(get_db())
            
            if db_session:
                from sqlalchemy import text
                insert_query = text("""
                    INSERT INTO trades (
                        order_id, user_id, symbol, trade_type, quantity, price,
                        strategy, pnl, pnl_percent, status, executed_at
                    ) VALUES (
                        :order_id, :user_id, :symbol, :trade_type, :quantity, :price,
                        :strategy, :pnl, :pnl_percent, :status, :executed_at
                    )
                """)
                
                # Get user_id (ensure it exists)
                user_query = text("SELECT id FROM users WHERE username = 'PAPER_TRADER_001' LIMIT 1")
                user_result = db_session.execute(user_query)
                user_row = user_result.fetchone()
                user_id = user_row.id if user_row else 1
                
                db_session.execute(insert_query, {
                    'order_id': trade_record['trade_id'],  # Store the order reference in order_id field
                    'user_id': user_id,
                    'symbol': trade_record['symbol'],
                    'trade_type': trade_record['side'].lower(),
                    'quantity': trade_record['quantity'],
                    'price': trade_record['price'],
                    'strategy': trade_record['strategy'],
                    'pnl': trade_record.get('pnl', 0),
                    'pnl_percent': trade_record.get('pnl_percent', 0),
                    'status': trade_record['status'],
                    'executed_at': trade_record['executed_at']
                })
                
                db_session.commit()
                self.logger.info(f"✅ Trade stored to database with order_id: {trade_record['trade_id']}")
                
        except Exception as e:
            self.logger.error(f"❌ Error storing trade to database: {e}")
    
    async def _process_live_signal(self, signal: Dict):
        """Process signal in live trading mode"""
        try:
            # Check rate limiting
            current_time = time.time()
            if current_time - self.last_signal_time < (1.0 / self.signal_rate_limit):
                wait_time = (1.0 / self.signal_rate_limit) - (current_time - self.last_signal_time)
                self.logger.info(f"⏱️ Rate limiting: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
            
            # Process through order manager if available
            if self.order_manager:
                return await self._process_signal_through_order_manager(signal)
            elif self.sharekhan_client:
                return await self._process_signal_through_sharekhan(signal)
            else:
                self.logger.warning("❌ No order execution method available")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error processing live signal: {e}")
            return None
    
    async def _process_signal_through_order_manager(self, signal: Dict):
        """Process signal through order manager"""
        try:
            # Create order from signal
            order = self._create_order_from_signal(signal)
            
            # Submit order
            order_id = await self.order_manager.place_order(order)
            
            # Log order placement
            self.logger.info(f"📋 Order placed: {order_id} for user {signal.get('user_id', 'system')}")
            
            # Update rate limiting
            self.last_signal_time = time.time()
            
            return order_id
            
        except Exception as e:
            self.logger.error(f"❌ Error processing signal through order manager: {e}")
            return None
    
    async def _process_signal_through_sharekhan(self, signal: Dict):
        """Process signal through direct ShareKhan integration"""
        try:
            # CRITICAL FIX: Attempt to get ShareKhan client if not available
            if not self.sharekhan_client:
                self.logger.warning("⚠️ ShareKhan client not set, attempting to retrieve from orchestrator")
                await self._try_get_sharekhan_client_from_orchestrator()
            
            if not self.sharekhan_client:
                self.logger.warning("❌ No ShareKhan client available")
                return None
                
            # Create order
            order = self._create_order_from_signal(signal)
            
            # Place order through ShareKhan
            order_id = await self.sharekhan_client.place_order(order)
            
            if order_id:
                self.logger.info(f"📋 ShareKhan order placed: {order_id}")
                self.last_signal_time = time.time()
                return order_id
            else:
                self.logger.error("❌ ShareKhan order failed")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error processing signal through ShareKhan: {e}")
            return None
    
    def _create_order_from_signal(self, signal: Dict) -> Dict:
        """Create order parameters from signal"""
        # CRITICAL FIX: Properly map signal action to avoid direction reversal
        signal_action = signal.get('action', '').upper()
        if not signal_action:
            signal_action = signal.get('transaction_type', '').upper()
        if not signal_action:
            # Log warning if no action found - don't default to avoid wrong trades
            self.logger.warning(f"⚠️ No action found in signal for {signal.get('symbol', 'UNKNOWN')} - REJECTING")
            signal_action = 'INVALID'
        
        return {
            'symbol': signal.get('symbol'),
            'action': signal_action,  # ✅ FIXED: Primary action field
            'transaction_type': signal_action,  # ✅ FIXED: ShareKhan backup field
            'side': signal_action,  # ✅ FIXED: Generic backup field
            'quantity': signal.get('quantity', 0),
            'price': signal.get('entry_price'),
            'entry_price': signal.get('entry_price'),
            'order_type': signal.get('order_type', 'MARKET'),
            'product': self._get_product_type_for_symbol(signal.get('symbol', '')),  # FIXED: Dynamic product type
            'validity': signal.get('validity', 'DAY'),
            'tag': 'ALGO_TRADE',
            'user_id': signal.get('user_id', 'system')
        }
    
    def _get_product_type_for_symbol(self, symbol: str) -> str:
        """Get appropriate product type for symbol - FIXED for NFO options"""
        # 🔧 CRITICAL FIX: NFO options require NRML, not CNC
        if 'CE' in symbol or 'PE' in symbol:
            return 'NRML'  # Options must use NRML
        else:
            return 'CNC'   # Equity can use CNC

    def get_paper_orders(self) -> Dict:
        """Get all paper trading orders"""
        return self.paper_orders
    
    def get_paper_order_status(self, order_id: str) -> Optional[Dict]:
        """Get paper order status"""
        return self.paper_orders.get(order_id)
    
    async def cancel_paper_order(self, order_id: str) -> bool:
        """Cancel paper order"""
        if order_id in self.paper_orders:
            self.paper_orders[order_id]['status'] = 'CANCELLED'
            self.logger.info(f"📋 Paper order cancelled: {order_id}")
            return True
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get trade engine statistics"""
        try:
            executed_count = len([order for order in self.paper_orders.values() if order.get('status') == 'EXECUTED'])
            pending_count = len([order for order in self.paper_orders.values() if order.get('status') == 'PENDING'])
            cancelled_count = len([order for order in self.paper_orders.values() if order.get('status') == 'CANCELLED'])
            
            return {
                'total_orders': len(self.paper_orders),
                'executed_trades': executed_count,
                'pending_orders': pending_count,
                'cancelled_orders': cancelled_count,
                'paper_trading_enabled': self.paper_trading_enabled,
                'signals_processed': len(self.pending_signals),
                'rate_limit_per_second': self.signal_rate_limit,
                'last_signal_time': self.last_signal_time,
                'engine_status': 'active' if hasattr(self, 'is_running') and getattr(self, 'is_running', False) else 'inactive'
            }
        except Exception as e:
            self.logger.error(f"Error getting trade engine statistics: {e}")
            return {
                'total_orders': 0,
                'executed_trades': 0,
                'pending_orders': 0,
                'cancelled_orders': 0,
                'paper_trading_enabled': self.paper_trading_enabled,
                'signals_processed': 0,
                'rate_limit_per_second': self.signal_rate_limit,
                'last_signal_time': self.last_signal_time,
                'engine_status': 'error'
            }
    
    async def get_status(self) -> Dict[str, Any]:
        """Get trade engine status (async version)"""
        stats = self.get_statistics()
        stats.update({
            'initialized': hasattr(self, 'is_initialized') and getattr(self, 'is_initialized', False),
            'running': hasattr(self, 'is_running') and getattr(self, 'is_running', False),
            'order_manager_available': self.order_manager is not None,
            'sharekhan_client_available': self.sharekhan_client is not None,
            'risk_manager_available': self.risk_manager is not None,
            'timestamp': datetime.now().isoformat()
        })
        return stats
    
    async def save_paper_trade(self, trade_data: dict) -> bool:
        """Save paper trade to database with precise schema handling"""
        try:
            # Get paper trading user
            user = self.paper_user_manager.get_or_create_paper_user()
            if not user:
                self.logger.error("Failed to get paper trading user")
                return False
                
            # Create paper trade record with precise schema
            paper_trade = {
                'user_id': user['id'],  # Use the precise id field
                'symbol': trade_data.get('symbol'),
                'action': trade_data.get('action'),
                'quantity': trade_data.get('quantity'),
                'price': trade_data.get('price'),
                'timestamp': trade_data.get('timestamp', datetime.now()),
                'status': trade_data.get('status', 'executed'),
                'order_id': trade_data.get('order_id'),
                'pnl': trade_data.get('pnl', 0.0),
                'strategy': trade_data.get('strategy'),
                'created_at': datetime.now()
            }
            
            # Save to database
            async with self.db_config.get_session() as session:
                # Use text query for precise control
                insert_query = text("""
                    INSERT INTO paper_trades (
                        user_id, symbol, action, quantity, price, timestamp,
                        status, order_id, pnl, strategy, created_at
                    ) VALUES (
                        :user_id, :symbol, :action, :quantity, :price, :timestamp,
                        :status, :order_id, :pnl, :strategy, :created_at
                    )
                """)
                
                await session.execute(insert_query, paper_trade)
                await session.commit()
                
                self.logger.info(f"Paper trade saved: {trade_data['symbol']} {trade_data['action']} {trade_data['quantity']}@{trade_data['price']}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error saving paper trade: {e}")
            # Try to rollback if possible
            try:
                await session.rollback()
            except:
                pass
            return False 