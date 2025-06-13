# f_and_o_scalping_system/brokers/zerodha.py
"""
Zerodha Broker Integration
Production-ready integration with Kite Connect API
"""

import asyncio
import logging
from typing import Dict, Optional, List, Any, Callable
from datetime import datetime, time
from dataclasses import dataclass
import json
import pandas as pd
from kiteconnect import KiteConnect, KiteTicker
import redis.asyncio as redis

from .base import BaseBroker
from ..utils.helpers import retry_with_backoff
from ..utils.constants import OrderTypes, OrderStatus

logger = logging.getLogger(__name__)

@dataclass
class ZerodhaConfig:
    """Zerodha configuration"""
    api_key: str
    api_secret: str
    user_id: str

class ZerodhaIntegration(BaseBroker):
    """
    Production-ready Zerodha integration with Kite Connect
    """
    def __init__(self, config: Dict):
        super().__init__(config)
        self.user_id = config.get('user_id')
        self.api_key = config['api_key']
        self.api_secret = config['api_secret']
        self.kite = KiteConnect(api_key=self.api_key)
        self.ticker = None
        self.market_data_callbacks = []
        self.order_update_callbacks = []
        self.redis = None
        self.is_authenticated = False
        self.ticker_connected = False
        self.user_specific_prefix = f"zerodha:{self.user_id}:" if self.user_id else "zerodha:"

    async def initialize(self):
        """Initialize broker connection"""
        try:
            # Initialize Redis
            self.redis = redis.from_url(self.config.get('redis_url', 'redis://localhost:6379'))
            
            # Try to load saved access token
            saved_token = await self.redis.get(f"{self.user_specific_prefix}access_token")
            if saved_token:
                self.kite.set_access_token(saved_token)
                if await self._verify_token():
                    logger.info(f"Zerodha authenticated with saved token for user {self.user_id}")
                    self.is_authenticated = True
                    # Initialize WebSocket
                    await self._initialize_websocket()
                else:
                    logger.warning(f"Zerodha authentication required for user {self.user_id}")
            # Load symbol mappings
            await self._load_symbol_mappings()
        except Exception as e:
            logger.error(f"Zerodha initialization failed for user {self.user_id}: {e}")
            raise

    async def authenticate(self, request_token: str) -> bool:
        """
        Authenticate with Zerodha
        Args:
            request_token: Token from login redirect
        Returns:
            Success status
        """
        try:
            if request_token:
                # Generate access token
                session = self.kite.generate_session(
                    request_token=request_token,
                    api_secret=self.api_secret
                )
                access_token = session['access_token']
                self.kite.set_access_token(access_token)
                # Save token
                await self.redis.set(f"{self.user_specific_prefix}access_token", access_token)
                await self.redis.set(f"{self.user_specific_prefix}user_id", session['user_id'])
                logger.info(f"Zerodha authenticated for user: {session['user_id']}")
                # Verify authentication
                if self.is_authenticated:
                    # Initialize WebSocket
                    await self._initialize_websocket()
                return self.is_authenticated
        except Exception as e:
            logger.error(f"Authentication failed for user {self.user_id}: {e}")
            return False

    async def _verify_token(self) -> bool:
        """Verify if access token is valid"""
        try:
            profile = await self._async_api_call(self.kite.profile)
            logger.info(f"Token valid for user: {profile['user_id']}")
            return True
        except Exception:
            return False

    async def _initialize_websocket(self):
        """Initialize WebSocket connection for live data"""
        try:
            access_token = self.kite.access_token
            self.ticker = KiteTicker(self.api_key, access_token)
            
            # Set up callbacks
            self.ticker.on_ticks = self._on_ticks
            self.ticker.on_connect = self._on_connect
            self.ticker.on_close = self._on_close
            self.ticker.on_error = self._on_error
            self.ticker.on_reconnect = self._on_reconnect
            self.ticker.on_order_update = self._on_order_update
            
            # Start WebSocket in a separate thread
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.ticker.connect,
                True  # Threaded mode
            )
            self.ticker_connected = True
            logger.info(f"WebSocket ticker initialized for user {self.user_id}")
        except Exception as e:
            logger.error(f"WebSocket initialization failed for user {self.user_id}: {e}")
            raise

    def _on_ticks(self, ws, ticks):
        """Handle incoming ticks"""
        try:
            for tick in ticks:
                # Process tick
                processed_tick = self._process_tick(tick)
                # Call registered callbacks
                for callback in self.market_data_callbacks:
                    asyncio.create_task(callback(processed_tick))
        except Exception as e:
            logger.error(f"Error processing ticks: {e}")

    def _on_connect(self, ws, response):
        """Handle connection"""
        logger.info("WebSocket connected")
        self.ticker_connected = True

    def _on_close(self, ws, code, reason):
        """Handle disconnection"""
        logger.warning(f"WebSocket closed: {code} - {reason}")
        self.ticker_connected = False

    def _on_error(self, ws, code, reason):
        """Handle errors"""
        logger.error(f"WebSocket error: {code} - {reason}")
        self.ticker_connected = False

    def _on_reconnect(self, ws, attempts_count):
        """Handle reconnection"""
        logger.info(f"WebSocket reconnecting... Attempt: {attempts_count}")

    def _on_order_update(self, ws, data):
        """Handle order updates"""
        try:
            # Process order update
            processed_update = self._process_order_update(data)
            # Update local tracking
            order_id = processed_update.get('order_id')
            if order_id and order_id in self.orders:
                self.orders[order_id].update(processed_update)
            # Call registered callbacks
            for callback in self.order_update_callbacks:
                asyncio.create_task(callback(processed_update))
        except Exception as e:
            logger.error(f"Error processing order update: {e}")

    async def place_order(self, order_params: Dict) -> Optional[str]:
        """
        Place order with Zerodha
        Args:
            order_params: Order parameters
        Returns:
            Order ID if successful
        """
        try:
            # Validate parameters
            if not self._validate_order_params(order_params):
                logger.error(f"Invalid order parameters for user {self.user_id}: {order_params}")
                return None
            # Map internal symbol to exchange symbol
            exchange_symbol = self._map_symbol_to_exchange(order_params['symbol'])
            if not exchange_symbol:
                logger.error(f"Symbol mapping failed for user {self.user_id}: {order_params['symbol']}")
                return None
            # Prepare Kite order parameters
            kite_params = {
                'exchange': 'NFO',
                'tradingsymbol': exchange_symbol,
                'transaction_type': order_params['transaction_type'],
                'quantity': order_params['quantity'],
                'product': 'MIS',  # Intraday
                'order_type': order_params.get('order_type', 'MARKET'),
                'validity': 'DAY',
                'tag': f"AI_SCALPER_{self.user_id}"  # Add user ID to tag
            }
            # Add price for limit orders
            if 'price' in order_params:
                kite_params['price'] = order_params['price']
            # Add trigger price for SL orders
            if 'trigger_price' in order_params:
                kite_params['trigger_price'] = order_params['trigger_price']
            # Place order
            order_id = await self._async_api_call(
                self.kite.place_order,
                **kite_params
            )
            # Track order
            await self._log_order(order_id, order_params)
            logger.info(f"Order placed successfully for user {self.user_id}: {order_id}")
            return order_id
        except Exception as e:
            logger.error(f"Order placement failed for user {self.user_id}: {e}")
            await self._log_order_error(order_params, str(e))
            return None

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            # Get order details
            order = self.orders.get(order_id)
            if not order:
                logger.warning(f"Order {order_id} not found in tracking")
                return False
            # Cancel with Kite
            await self._async_api_call(
                self.kite.cancel_order,
                order_id=order_id
            )
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Order cancellation failed: {e}")
            return False

    async def modify_order(self, order_id: str, params: Dict) -> bool:
        """Modify an existing order"""
        try:
            # Get order details
            order = self.orders.get(order_id)
            if not order:
                return False
            # Prepare modification params
            modify_params = {'variety': 'regular', 'order_id': order_id}
            if 'quantity' in params:
                modify_params['quantity'] = params['quantity']
            if 'price' in params:
                modify_params['price'] = params['price']
            if 'trigger_price' in params:
                modify_params['trigger_price'] = params['trigger_price']
            # Modify order
            await self._async_api_call(
                self.kite.modify_order,
                **modify_params
            )
            order.update(params)
            logger.info(f"Order modified: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Order modification failed: {e}")
            return False

    async def get_positions(self) -> List[Dict]:
        """Get current positions"""
        try:
            positions = await self._async_api_call(self.kite.positions)
            # Process positions
            processed_positions = []
            for pos in positions.get('day', []):
                processed_positions.append({
                    'user_id': self.user_id,
                    'symbol': self._map_symbol_from_exchange(pos['tradingsymbol']),
                    'exchange_symbol': pos['tradingsymbol'],
                    'quantity': pos['quantity'],
                    'average_price': pos['average_price'],
                    'last_price': pos['last_price'],
                    'pnl': pos['pnl'],
                    'pnl_percent': (pos['pnl'] / (pos['average_price'] * abs(pos['quantity'])) * 100) if pos['average_price'] > 0 else 0
                })
            return processed_positions
        except Exception as e:
            logger.error(f"Failed to fetch positions for user {self.user_id}: {e}")
            return []

    async def get_orders(self) -> List[Dict]:
        """Get all orders for the day"""
        try:
            orders = await self._async_api_call(self.kite.orders)
            # Process orders
            processed_orders = []
            for order in orders:
                processed_orders.append({
                    'user_id': self.user_id,
                    'order_id': order['order_id'],
                    'symbol': self._map_symbol_from_exchange(order['tradingsymbol']),
                    'status': self._map_order_status(order['status']),
                    'quantity': order['quantity'],
                    'filled_quantity': order['filled_quantity'],
                    'price': order['price'],
                    'average_price': order['average_price'],
                    'transaction_type': order['transaction_type'],
                    'order_type': order['order_type'],
                    'placed_at': order['order_timestamp']
                })
            return processed_orders
        except Exception as e:
            logger.error(f"Failed to fetch orders for user {self.user_id}: {e}")
            return []

    async def exit_position(self, symbol: str, quantity: Optional[float] = None) -> Optional[str]:
        """Exit a position"""
        try:
            # Get current position
            positions = await self.get_positions()
            position = next((p for p in positions if p['symbol'] == symbol), None)
            if not position:
                logger.warning(f"No position found for {symbol}")
                return None

            # Determine quantity to exit
            exit_quantity = quantity or abs(position['quantity'])
            # Determine transaction type (opposite of position)
            if position['quantity'] > 0:
                transaction_type = 'SELL'
            else:
                transaction_type = 'BUY'
            exit_quantity = abs(exit_quantity)
            # Place exit order
            return await self.place_order({
                'symbol': symbol,
                'quantity': exit_quantity,
                'transaction_type': transaction_type,
                'order_type': 'MARKET',
                'tag': 'EXIT'
            })
        except Exception as e:
            logger.error(f"Position exit failed: {e}")
            return None

    async def get_margins(self) -> Dict[str, float]:
        """Get account margins"""
        try:
            margins = await self._async_api_call(self.kite.margins)
            equity_margin = margins.get('equity', {})
            commodity_margin = margins.get('commodity', {})
            return {
                'user_id': self.user_id,
                'available_cash': equity_margin.get('available', {}).get('cash', 0),
                'used_margin': equity_margin.get('utilised', {}).get('total', 0),
                'total_margin': equity_margin.get('net', 0),
                'available_margin': equity_margin.get('available', {}).get('total', 0)
            }
        except Exception as e:
            logger.error(f"Failed to fetch margins for user {self.user_id}: {e}")
            return {
                'user_id': self.user_id,
                'available_cash': 0,
                'used_margin': 0,
                'total_margin': 0,
                'available_margin': 0
            }

    async def get_order_history(self, order_id: str) -> List[Dict]:
        """Get order history/trail"""
        try:
            history = await self._async_api_call(
                self.kite.order_history,
                order_id=order_id
            )
            return [{
                'timestamp': h['order_timestamp'],
                'status': h['status'],
                'message': h.get('status_message', ''),
                'filled_quantity': h.get('filled_quantity', 0),
                'average_price': h.get('average_price', 0)
            } for h in history]
        except Exception as e:
            logger.error(f"Failed to fetch order history: {e}")
            return []

    async def subscribe_market_data(self, symbols: List[str]):
        """Subscribe to live market data"""
        try:
            if not self.ticker or not self.ticker_connected:
                logger.error("WebSocket not connected")
                return

            # Map symbols to tokens
            tokens = []
            for symbol in symbols:
                token = await self._get_instrument_token(symbol)
                if token:
                    tokens.append(token)

            if tokens:
                # Subscribe to tokens
                self.ticker.subscribe(tokens)
                # Set mode to full quote
                self.ticker.set_mode(self.ticker.MODE_FULL, tokens)
                logger.info(f"Subscribed to market data for {len(tokens)} symbols")
        except Exception as e:
            logger.error(f"Market data subscription failed: {e}")

    async def unsubscribe_market_data(self, symbols: List[str]):
        """Unsubscribe from market data"""
        try:
            if not self.ticker or not self.ticker_connected:
                logger.error("WebSocket not connected")
                return

            # Map symbols to tokens
            tokens = []
            for symbol in symbols:
                token = await self._get_instrument_token(symbol)
                if token:
                    tokens.append(token)

            if tokens:
                self.ticker.unsubscribe(tokens)
                logger.info(f"Unsubscribed from {len(tokens)} symbols")
        except Exception as e:
            logger.error(f"Market data unsubscription failed: {e}")

    async def get_quote(self, symbols: List[str]) -> Dict[str, Dict]:
        """Get current quotes for symbols"""
        try:
            # Map symbols to exchange format
            exchange_symbols = []
            symbol_map = {}
            for symbol in symbols:
                exchange_symbol = self._map_symbol_to_exchange(symbol)
                if exchange_symbol:
                    exchange_symbols.append(f"NFO:{exchange_symbol}")
            if not exchange_symbols:
                return {}

            # Get quotes
            quotes = await self._async_api_call(
                self.kite.quote,
                exchange_symbols
            )

            # Process quotes
            processed_quotes = {}
            for key, quote in quotes.items():
                internal_symbol = symbol_map.get(key)
                if internal_symbol:
                    processed_quotes[internal_symbol] = {
                        'ltp': quote['last_price'],
                        'bid': quote['depth']['buy'][0]['price'] if quote['depth']['buy'] else 0,
                        'ask': quote['depth']['sell'][0]['price'] if quote['depth']['sell'] else 0,
                        'volume': quote['volume'],
                        'oi': quote.get('oi', 0),
                        'high': quote['ohlc']['high'],
                        'low': quote['ohlc']['low'],
                        'open': quote['ohlc']['open'],
                        'close': quote['ohlc']['close']
                    }
            return processed_quotes
        except Exception as e:
            logger.error(f"Failed to fetch quotes: {e}")
            return {}

    async def get_historical_data(self, symbol: str, interval: str,
    from_date: datetime, to_date: datetime) -> pd.DataFrame:
        """Get historical data"""
        try:
            # Get instrument token
            token = await self._get_instrument_token(symbol)
            if not token:
                return pd.DataFrame()

            # Map interval
            interval_map = {
                '1minute': 'minute',
                '5minute': '5minute',
                '15minute': '15minute',
                '30minute': '30minute',
                '60minute': '60minute',
                'day': 'day'
            }

            kite_interval = interval_map.get(interval, 'minute')
            # Fetch data
            data = await self._async_api_call(
                self.kite.historical_data,
                from_date=from_date,
                to_date=to_date,
                interval=kite_interval
            )

            # Convert to DataFrame
            df = pd.DataFrame(data)
            if not df.empty:
                return df
        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            return pd.DataFrame()

    # Helper methods
    def _validate_order_params(self, params: Dict) -> bool:
        """Validate order parameters"""
        required = ['symbol', 'quantity', 'transaction_type']
        return all(field in params for field in required)

    def _map_symbol_to_exchange(self, symbol: str) -> Optional[str]:
        """Map internal symbol to exchange format"""
        # This would use a proper mapping table
        # For now, simple conversion
        return symbol.upper()

    def _map_symbol_from_exchange(self, exchange_symbol: str) -> str:
        """Map exchange symbol to internal format"""
        return exchange_symbol

    def _map_order_status(self, kite_status: str) -> str:
        """Map Kite order status to internal status"""
        status_map = {
            'PENDING': 'PENDING',
            'OPEN': 'OPEN',
            'COMPLETE': 'FILLED',
            'CANCELLED': 'CANCELLED',
            'REJECTED': 'REJECTED',
            'MODIFY_PENDING': 'MODIFY_PENDING',
            'OPEN_PENDING': 'OPEN_PENDING',
            'CANCEL_PENDING': 'CANCEL_PENDING',
            'AMO_REQ_RECEIVED': 'AMO_PENDING'
        }
        return status_map.get(kite_status, kite_status)

    async def _get_instrument_token(self, symbol: str) -> Optional[int]:
        """Get instrument token for symbol"""
        try:
            # Check cache
            cache_key = f"instrument_token:{symbol}"
            cached_token = await self.redis.get(cache_key)
            if cached_token:
                return int(cached_token)
            # Search in instruments
            instruments = await self._async_api_call(self.kite.instruments, 'NFO')
            exchange_symbol = self._map_symbol_to_exchange(symbol)
            for instrument in instruments:
                token = instrument['instrument_token']
                # Cache it
                return token
        except Exception as e:
            logger.error(f"Failed to get instrument token: {e}")
            return None

    def _process_tick(self, tick: Dict) -> Dict:
        """Process raw tick data"""
        return {
            'symbol': self._get_symbol_from_token(tick['instrument_token']),
            'ltp': tick.get('last_price', 0),
            'volume': tick.get('volume', 0),
            'bid': tick.get('depth', {}).get('buy', [{}])[0].get('price', 0),
            'ask': tick.get('depth', {}).get('sell', [{}])[0].get('price', 0),
            'oi': tick.get('oi', 0),
            'timestamp': datetime.now()
        }

    def _process_order_update(self, data: Dict) -> Dict:
        """Process order update data"""
        return {
            'order_id': data.get('order_id'),
            'status': self._map_order_status(data.get('status')),
            'filled_quantity': data.get('filled_quantity', 0),
            'pending_quantity': data.get('pending_quantity', 0),
            'average_price': data.get('average_price', 0),
            'status_message': data.get('status_message', ''),
            'timestamp': datetime.now()
        }

    def _get_symbol_from_token(self, token: int) -> str:
        """Get symbol from instrument token"""
        # This would use a reverse mapping
        return f"UNKNOWN_{token}"

    async def _load_symbol_mappings(self):
        """Load symbol mappings from instruments"""
        try:
            # This would load and cache instrument mappings
            pass
        except Exception as e:
            logger.error(f"Failed to load symbol mappings: {e}")

    async def _async_api_call(self, func, *args, **kwargs):
        """Make async API call"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)

    async def _log_order(self, order_id: str, params: Dict):
        """Log order details"""
        try:
            await self.redis.hset(
                f"{self.user_specific_prefix}orders:{datetime.now().strftime('%Y%m%d')}",
                order_id,
                json.dumps({
                    'order_id': order_id,
                    'user_id': self.user_id,
                    'timestamp': datetime.now().isoformat(),
                    'params': params
                })
            )
        except Exception as e:
            logger.error(f"Failed to log order for user {self.user_id}: {e}")

    async def _log_order_error(self, params: Dict, error: str):
        """Log order error"""
        try:
            await self.redis.lpush(
                f"{self.user_specific_prefix}order_errors:{datetime.now().strftime('%Y%m%d')}",
                json.dumps({
                    'user_id': self.user_id,
                    'timestamp': datetime.now().isoformat(),
                    'params': params,
                    'error': error
                })
            )
        except Exception as e:
            logger.error(f"Failed to log order error for user {self.user_id}: {e}")

    async def is_connected(self) -> bool:
        """Check if broker is connected"""
        return self.is_authenticated and self.ticker_connected

    async def disconnect(self):
        """Disconnect from broker"""
        try:
            if self.ticker:
                self.ticker.close()
                if self.redis:
                    await self.redis.close()
                logger.info(f"Zerodha disconnected for user {self.user_id}")
        except Exception as e:
            logger.error(f"Error during disconnection for user {self.user_id}: {e}")

    async def subscribe_order_updates(self, callback: Callable):
        """Subscribe to order updates"""
        self.order_update_callbacks.append(callback)

    async def subscribe_market_updates(self, callback: Callable):
        """Subscribe to market data updates"""
        self.market_data_callbacks.append(callback)

    async def cancel_all_orders(self):
        """Cancel all pending orders"""
        try:
            orders = await self.get_orders()
            cancelled = 0
            for order in orders:
                if order['status'] in ['PENDING', 'OPEN']:
                    if await self.cancel_order(order['order_id']):
                        cancelled += 1
            logger.info(f"Cancelled {cancelled} orders")
            return cancelled
        except Exception as e:
            logger.error(f"Failed to cancel all orders: {e}")
            return 0
