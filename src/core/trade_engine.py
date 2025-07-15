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

class TradeEngine:
    """Enhanced trade engine with paper trading support"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.order_manager = None
        self.zerodha_client = None
        self.risk_manager = None
        self.logger = logging.getLogger(__name__)
        
        # Paper trading configuration
        self.paper_trading_enabled = os.getenv('PAPER_TRADING', 'false').lower() == 'true'
        self.paper_orders = {}  # Store simulated orders
        
        # Rate limiting
        self.rate_limit = config.get('rate_limit', {})
        self.last_signal_time = 0
        self.signal_count = 0
        self.signal_rate_limit = self.rate_limit.get('max_trades_per_second', 7)
        
        # Batch processing
        self.batch_config = config.get('batch_processing', {})
        self.pending_signals = []
        self.batch_size = self.batch_config.get('size', 5)
        self.batch_timeout = self.batch_config.get('timeout', 0.5)
        
        self.logger.info(f"Trade Engine initialized - Paper Trading: {self.paper_trading_enabled}")
    
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
        """Process multiple trading signals"""
        try:
            if not signals:
                return []
            
            self.logger.info(f"🚀 Processing {len(signals)} signals for execution")
            
            results = []
            for signal in signals:
                try:
                    # Process each signal
                    order_id = await self.process_signal(signal)
                    
                    result = {
                        'signal_id': signal.get('signal_id'),
                        'symbol': signal.get('symbol'),
                        'action': signal.get('action'),
                        'order_id': order_id,
                        'status': 'SUCCESS' if order_id else 'FAILED',
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    results.append(result)
                    
                    if order_id:
                        self.logger.info(f"✅ Signal processed successfully: {signal.get('symbol')} {signal.get('action')} - Order ID: {order_id}")
                    else:
                        self.logger.error(f"❌ Signal processing failed: {signal.get('symbol')} {signal.get('action')}")
                        
                except Exception as e:
                    self.logger.error(f"❌ Error processing signal {signal.get('signal_id', 'unknown')}: {e}")
                    
                    results.append({
                        'signal_id': signal.get('signal_id'),
                        'symbol': signal.get('symbol'),
                        'action': signal.get('action'),
                        'order_id': None,
                        'status': 'ERROR',
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Error processing signals batch: {e}")
            return []
    
    async def _process_paper_signal(self, signal: Dict):
        """Process signal in paper trading mode"""
        try:
            # Create simulated order
            order_id = f"PAPER_{int(time.time() * 1000)}"
            symbol = signal.get('symbol', 'UNKNOWN')
            action = signal.get('action', 'BUY')
            quantity = signal.get('quantity', 0)
            price = signal.get('entry_price', 0)
            
            # Store paper order
            self.paper_orders[order_id] = {
                'order_id': order_id,
                'symbol': symbol,
                'action': action,
                'quantity': quantity,
                'price': price,
                'status': 'EXECUTED',
                'timestamp': datetime.now().isoformat(),
                'signal': signal
            }
            
            self.logger.info(f"📋 PAPER TRADING: Signal processed - {order_id}")
            self.logger.info(f"   Symbol: {symbol}, Action: {action}, Qty: {quantity}, Price: ₹{price}")
            
            return order_id
            
        except Exception as e:
            self.logger.error(f"❌ Error processing paper signal: {e}")
            return None
    
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
            elif self.zerodha_client:
                return await self._process_signal_through_zerodha(signal)
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
    
    async def _process_signal_through_zerodha(self, signal: Dict):
        """Process signal through direct Zerodha integration"""
        try:
            if not self.zerodha_client:
                self.logger.warning("❌ No Zerodha client available")
                return None
                
            # Create order
            order = self._create_order_from_signal(signal)
            
            # Place order through Zerodha
            order_id = await self.zerodha_client.place_order(order)
            
            if order_id:
                self.logger.info(f"📋 Zerodha order placed: {order_id}")
                self.last_signal_time = time.time()
                return order_id
            else:
                self.logger.error("❌ Zerodha order failed")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error processing signal through Zerodha: {e}")
            return None
    
    def _create_order_from_signal(self, signal: Dict) -> Dict:
        """Create order parameters from signal"""
        return {
            'symbol': signal.get('symbol'),
            'action': signal.get('action', 'BUY'),
            'transaction_type': signal.get('action', 'BUY'),
            'quantity': signal.get('quantity', 0),
            'price': signal.get('entry_price'),
            'entry_price': signal.get('entry_price'),
            'order_type': signal.get('order_type', 'MARKET'),
            'product': signal.get('product', 'MIS'),
            'validity': signal.get('validity', 'DAY'),
            'tag': 'ALGO_TRADE',
            'user_id': signal.get('user_id', 'system')
        }
    
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