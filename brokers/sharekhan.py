"""
ShareKhan Broker Integration
Complete replacement for Zerodha with unified trading and market data
"""

import asyncio
import logging
import websocket
import json
import threading
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import requests
from dataclasses import dataclass, asdict
import hmac
import hashlib
import uuid

logger = logging.getLogger(__name__)

class ShareKhanOrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"

class ShareKhanProductType(Enum):
    INVESTMENT = "INVESTMENT"
    TRADING = "TRADING"
    MTF = "MTF"

class ShareKhanTransactionType(Enum):
    BUY = "B"
    SELL = "S"

class ShareKhanExchange(Enum):
    NSE = "NC"
    BSE = "BC"
    MCX = "MX"
    NCDEX = "NX"

@dataclass
class ShareKhanOrder:
    """ShareKhan order structure"""
    customer_id: str
    scrip_code: int
    trading_symbol: str
    exchange: str
    transaction_type: str
    quantity: int
    price: float
    product_type: str
    order_type: str = "NORMAL"
    validity: str = "GFD"
    disclosed_qty: int = 0
    trigger_price: float = 0
    after_hour: str = "N"
    channel_user: str = ""
    rms_code: str = ""
    request_type: str = "NEW"

@dataclass
class ShareKhanMarketData:
    """ShareKhan market data structure"""
    symbol: str
    exchange: str
    ltp: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: datetime
    bid_price: float = 0
    ask_price: float = 0
    bid_qty: int = 0
    ask_qty: int = 0

class ShareKhanIntegration:
    """
    Unified ShareKhan integration for trading and market data
    Replaces both Zerodha trading and TrueData market data
    """
    
    def __init__(self, api_key: str, secret_key: str, customer_id: str, version_id: Optional[str] = None):
        self.api_key = api_key
        self.secret_key = secret_key
        self.customer_id = customer_id
        self.version_id = version_id
        
        # Connection state
        self.access_token = None
        self.session_token = None
        self.is_authenticated = False
        self.is_connected = False
        
        # API endpoints - VERIFIED FROM OFFICIAL SOURCES
        self.base_url = "https://api.sharekhan.com"
        self.ws_url = "wss://wspush.sharekhan.com"
        self.login_url = "https://newtrade.sharekhan.com"  # For authentication portal
        
        # Additional endpoints for different data types
        self.feed_url = "wss://wspush.sharekhan.com"  # Real-time data feed
        self.data_url = f"{self.base_url}/feed"  # Market data API
        
        # WebSocket for real-time data
        self.ws = None
        self.ws_thread = None
        self.is_ws_connected = False
        self.subscribed_symbols = set()
        
        # Market data callbacks
        self.market_data_callbacks: List[Callable] = []
        self.order_update_callbacks: List[Callable] = []
        
        # Rate limiting
        self.last_request_time = 0
        self.request_semaphore = asyncio.Semaphore(10)
        
        # Real-time data storage
        self.live_market_data: Dict[str, ShareKhanMarketData] = {}
        self.order_book: Dict[str, Dict] = {}
        self.positions: Dict[str, Dict] = {}
        
        logger.info(f"✅ ShareKhan integration initialized for customer: {customer_id}")
    
    async def authenticate(self, request_token: str = None) -> bool:
        """Authenticate with ShareKhan API"""
        try:
            if request_token:
                # Generate session with request token
                if self.version_id is not None:
                    session_data = await self._generate_session_with_version(request_token)
                else:
                    session_data = await self._generate_session_without_version(request_token)
                
                if session_data and session_data.get('success'):
                    self.access_token = session_data.get('access_token')
                    self.session_token = session_data.get('session_token')
                    self.is_authenticated = True
                    
                    # Initialize WebSocket connection
                    await self._initialize_websocket()
                    
                    logger.info("✅ ShareKhan authentication successful")
                    return True
            
            logger.error("❌ ShareKhan authentication failed - no request token provided")
            return False
            
        except Exception as e:
            logger.error(f"❌ ShareKhan authentication error: {e}")
            return False
    
    async def _generate_session_with_version(self, request_token: str) -> Dict:
        """Generate session with version ID"""
        url = f"{self.base_url}/session/withversion"
        
        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key
        }
        
        payload = {
            "request_token": request_token,
            "secret_key": self.secret_key,
            "version_id": self.version_id or ""
        }
        
        async with self.request_semaphore:
            response = requests.post(url, headers=headers, json=payload)
            return response.json() if response.status_code == 200 else {}
    
    async def _generate_session_without_version(self, request_token: str) -> Dict:
        """Generate session without version ID"""
        url = f"{self.base_url}/session/generate"
        
        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key
        }
        
        payload = {
            "request_token": request_token,
            "secret_key": self.secret_key
        }
        
        async with self.request_semaphore:
            response = requests.post(url, headers=headers, json=payload)
            return response.json() if response.status_code == 200 else {}
    
    async def place_order(self, order: ShareKhanOrder) -> Dict:
        """Place order via ShareKhan API"""
        try:
            if not self.is_authenticated:
                raise Exception("Not authenticated - call authenticate() first")
            
            url = f"{self.base_url}/orders/place"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}",
                "X-Session-Token": self.session_token
            }
            
            # Convert order to ShareKhan format
            payload = asdict(order)
            
            async with self.request_semaphore:
                response = requests.post(url, headers=headers, json=payload)
                result = response.json()
                
                if response.status_code == 200 and result.get('success'):
                    order_id = result.get('order_id')
                    logger.info(f"✅ Order placed successfully: {order_id}")
                    
                    # Update order book in memory
                    self.order_book[order_id] = {
                        **payload,
                        'order_id': order_id,
                        'status': 'PLACED',
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    return result
                else:
                    error_msg = result.get('error', 'Unknown error')
                    raise Exception(f"Order placement failed: {error_msg}")
                    
        except Exception as e:
            logger.error(f"❌ Order placement error: {e}")
            raise
    
    async def modify_order(self, order_id: str, modifications: Dict) -> Dict:
        """Modify existing order"""
        try:
            if not self.is_authenticated:
                raise Exception("Not authenticated")
            
            url = f"{self.base_url}/orders/modify"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}",
                "X-Session-Token": self.session_token
            }
            
            payload = {
                "order_id": order_id,
                **modifications
            }
            
            async with self.request_semaphore:
                response = requests.post(url, headers=headers, json=payload)
                result = response.json()
                
                if response.status_code == 200 and result.get('success'):
                    # Update order book in memory
                    if order_id in self.order_book:
                        self.order_book[order_id].update(modifications)
                        self.order_book[order_id]['status'] = 'MODIFIED'
                        self.order_book[order_id]['modified_at'] = datetime.now().isoformat()
                    
                    logger.info(f"✅ Order modified successfully: {order_id}")
                    return result
                else:
                    error_msg = result.get('error', 'Unknown error')
                    raise Exception(f"Order modification failed: {error_msg}")
                    
        except Exception as e:
            logger.error(f"❌ Order modification error: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> Dict:
        """Cancel existing order"""
        try:
            if not self.is_authenticated:
                raise Exception("Not authenticated")
            
            url = f"{self.base_url}/orders/cancel"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}",
                "X-Session-Token": self.session_token
            }
            
            payload = {"order_id": order_id}
            
            async with self.request_semaphore:
                response = requests.post(url, headers=headers, json=payload)
                result = response.json()
                
                if response.status_code == 200 and result.get('success'):
                    # Update order book in memory
                    if order_id in self.order_book:
                        self.order_book[order_id]['status'] = 'CANCELLED'
                        self.order_book[order_id]['cancelled_at'] = datetime.now().isoformat()
                    
                    logger.info(f"✅ Order cancelled successfully: {order_id}")
                    return result
                else:
                    error_msg = result.get('error', 'Unknown error')
                    raise Exception(f"Order cancellation failed: {error_msg}")
                    
        except Exception as e:
            logger.error(f"❌ Order cancellation error: {e}")
            raise
    
    async def get_orders(self) -> List[Dict]:
        """Get all orders for the day"""
        try:
            if not self.is_authenticated:
                raise Exception("Not authenticated")
            
            url = f"{self.base_url}/orders/day"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "X-Session-Token": self.session_token
            }
            
            async with self.request_semaphore:
                response = requests.get(url, headers=headers)
                result = response.json()
                
                if response.status_code == 200 and result.get('success'):
                    orders = result.get('orders', [])
                    
                    # Update in-memory order book
                    for order in orders:
                        order_id = order.get('order_id')
                        if order_id:
                            self.order_book[order_id] = order
                    
                    return orders
                else:
                    error_msg = result.get('error', 'Unknown error')
                    raise Exception(f"Failed to fetch orders: {error_msg}")
                    
        except Exception as e:
            logger.error(f"❌ Error fetching orders: {e}")
            raise
    
    async def get_positions(self) -> Dict:
        """Get current positions"""
        try:
            if not self.is_authenticated:
                raise Exception("Not authenticated")
            
            url = f"{self.base_url}/portfolio/positions"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "X-Session-Token": self.session_token
            }
            
            async with self.request_semaphore:
                response = requests.get(url, headers=headers)
                result = response.json()
                
                if response.status_code == 200 and result.get('success'):
                    positions = result.get('positions', {})
                    
                    # Update in-memory positions
                    self.positions.update(positions)
                    
                    return positions
                else:
                    error_msg = result.get('error', 'Unknown error')
                    raise Exception(f"Failed to fetch positions: {error_msg}")
                    
        except Exception as e:
            logger.error(f"❌ Error fetching positions: {e}")
            raise
    
    async def get_holdings(self) -> List[Dict]:
        """Get portfolio holdings"""
        try:
            if not self.is_authenticated:
                raise Exception("Not authenticated")
            
            url = f"{self.base_url}/portfolio/holdings"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "X-Session-Token": self.session_token
            }
            
            async with self.request_semaphore:
                response = requests.get(url, headers=headers)
                result = response.json()
                
                if response.status_code == 200 and result.get('success'):
                    return result.get('holdings', [])
                else:
                    error_msg = result.get('error', 'Unknown error')
                    raise Exception(f"Failed to fetch holdings: {error_msg}")
                    
        except Exception as e:
            logger.error(f"❌ Error fetching holdings: {e}")
            raise
    
    async def get_funds(self) -> Dict:
        """Get available funds"""
        try:
            if not self.is_authenticated:
                raise Exception("Not authenticated")
            
            url = f"{self.base_url}/portfolio/funds"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "X-Session-Token": self.session_token
            }
            
            async with self.request_semaphore:
                response = requests.get(url, headers=headers)
                result = response.json()
                
                if response.status_code == 200 and result.get('success'):
                    return result.get('funds', {})
                else:
                    error_msg = result.get('error', 'Unknown error')
                    raise Exception(f"Failed to fetch funds: {error_msg}")
                    
        except Exception as e:
            logger.error(f"❌ Error fetching funds: {e}")
            raise
    
    async def get_market_quote(self, symbols: List[str]) -> Dict[str, ShareKhanMarketData]:
        """Get market quotes for symbols"""
        try:
            if not self.is_authenticated:
                raise Exception("Not authenticated")
            
            url = f"{self.base_url}/market/quote"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}",
                "X-Session-Token": self.session_token
            }
            
            payload = {"symbols": symbols}
            
            async with self.request_semaphore:
                response = requests.post(url, headers=headers, json=payload)
                result = response.json()
                
                if response.status_code == 200 and result.get('success'):
                    quotes_data = result.get('quotes', {})
                    quotes = {}
                    
                    for symbol, data in quotes_data.items():
                        market_data = ShareKhanMarketData(
                            symbol=symbol,
                            exchange=data.get('exchange', ''),
                            ltp=float(data.get('ltp', 0)),
                            open=float(data.get('open', 0)),
                            high=float(data.get('high', 0)),
                            low=float(data.get('low', 0)),
                            close=float(data.get('close', 0)),
                            volume=int(data.get('volume', 0)),
                            timestamp=datetime.now(),
                            bid_price=float(data.get('bid_price', 0)),
                            ask_price=float(data.get('ask_price', 0)),
                            bid_qty=int(data.get('bid_qty', 0)),
                            ask_qty=int(data.get('ask_qty', 0))
                        )
                        quotes[symbol] = market_data
                        
                        # Update live data cache
                        self.live_market_data[symbol] = market_data
                    
                    return quotes
                else:
                    error_msg = result.get('error', 'Unknown error')
                    raise Exception(f"Failed to fetch market quotes: {error_msg}")
                    
        except Exception as e:
            logger.error(f"❌ Error fetching market quotes: {e}")
            raise
    
    async def _initialize_websocket(self):
        """Initialize WebSocket connection for real-time data"""
        try:
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    self._handle_websocket_message(data)
                except Exception as e:
                    logger.error(f"WebSocket message parsing error: {e}")
            
            def on_error(ws, error):
                logger.error(f"WebSocket error: {error}")
                self.is_ws_connected = False
            
            def on_close(ws, close_status_code, close_msg):
                logger.warning("WebSocket connection closed")
                self.is_ws_connected = False
                # Auto-reconnect
                time.sleep(5)
                self._reconnect_websocket()
            
            def on_open(ws):
                logger.info("✅ WebSocket connection established")
                self.is_ws_connected = True
                # Subscribe to order updates
                self._subscribe_to_order_updates()
            
            # Create WebSocket connection
            ws_url = f"{self.ws_url}?access_token={self.access_token}"
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            
            # Start WebSocket in separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            logger.info("🔌 WebSocket connection initialized")
            
        except Exception as e:
            logger.error(f"❌ WebSocket initialization error: {e}")
    
    def _handle_websocket_message(self, data: Dict):
        """Handle incoming WebSocket messages"""
        try:
            message_type = data.get('type')
            
            if message_type == 'market_data':
                # Handle market data updates
                symbol = data.get('symbol')
                if symbol:
                    market_data = ShareKhanMarketData(
                        symbol=symbol,
                        exchange=data.get('exchange', ''),
                        ltp=float(data.get('ltp', 0)),
                        open=float(data.get('open', 0)),
                        high=float(data.get('high', 0)),
                        low=float(data.get('low', 0)),
                        close=float(data.get('close', 0)),
                        volume=int(data.get('volume', 0)),
                        timestamp=datetime.now(),
                        bid_price=float(data.get('bid_price', 0)),
                        ask_price=float(data.get('ask_price', 0)),
                        bid_qty=int(data.get('bid_qty', 0)),
                        ask_qty=int(data.get('ask_qty', 0))
                    )
                    
                    # Update live data cache immediately
                    self.live_market_data[symbol] = market_data
                    
                    # Notify callbacks
                    for callback in self.market_data_callbacks:
                        try:
                            callback(market_data)
                        except Exception as e:
                            logger.error(f"Market data callback error: {e}")
            
            elif message_type == 'order_update':
                # Handle order updates
                order_id = data.get('order_id')
                if order_id:
                    # Update order book in memory
                    self.order_book[order_id] = data
                    
                    # Notify callbacks
                    for callback in self.order_update_callbacks:
                        try:
                            callback(data)
                        except Exception as e:
                            logger.error(f"Order update callback error: {e}")
                            
        except Exception as e:
            logger.error(f"❌ WebSocket message handling error: {e}")
    
    async def subscribe_to_symbols(self, symbols: List[str]):
        """Subscribe to real-time market data for symbols"""
        try:
            if not self.is_ws_connected or self.ws is None:
                logger.warning("WebSocket not connected - cannot subscribe to symbols")
                return False
            
            message = {
                "action": "subscribe",
                "symbols": symbols
            }
            
            self.ws.send(json.dumps(message))
            self.subscribed_symbols.update(symbols)
            
            logger.info(f"✅ Subscribed to symbols: {symbols}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Symbol subscription error: {e}")
            return False
    
    async def unsubscribe_from_symbols(self, symbols: List[str]):
        """Unsubscribe from real-time market data for symbols"""
        try:
            if not self.is_ws_connected or self.ws is None:
                return False
            
            message = {
                "action": "unsubscribe",
                "symbols": symbols
            }
            
            self.ws.send(json.dumps(message))
            self.subscribed_symbols.difference_update(symbols)
            
            logger.info(f"✅ Unsubscribed from symbols: {symbols}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Symbol unsubscription error: {e}")
            return False
    
    def _subscribe_to_order_updates(self):
        """Subscribe to order updates via WebSocket"""
        try:
            if self.ws is None:
                logger.error("WebSocket not available for order updates subscription")
                return
                
            message = {
                "action": "subscribe",
                "channel": "order_updates",
                "customer_id": self.customer_id
            }
            
            self.ws.send(json.dumps(message))
            logger.info("✅ Subscribed to order updates")
            
        except Exception as e:
            logger.error(f"❌ Order updates subscription error: {e}")
    
    def _reconnect_websocket(self):
        """Reconnect WebSocket if disconnected"""
        try:
            if not self.is_ws_connected and self.access_token:
                logger.info("🔄 Attempting WebSocket reconnection...")
                asyncio.create_task(self._initialize_websocket())
        except Exception as e:
            logger.error(f"❌ WebSocket reconnection error: {e}")
    
    def add_market_data_callback(self, callback: Callable):
        """Add callback for market data updates"""
        self.market_data_callbacks.append(callback)
    
    def add_order_update_callback(self, callback: Callable):
        """Add callback for order updates"""
        self.order_update_callbacks.append(callback)
    
    async def get_live_data(self, symbol: str) -> Optional[ShareKhanMarketData]:
        """Get live data for a symbol from memory cache"""
        return self.live_market_data.get(symbol)
    
    async def disconnect(self):
        """Disconnect from ShareKhan API and WebSocket"""
        try:
            self.is_authenticated = False
            self.is_connected = False
            
            if self.ws:
                self.ws.close()
                self.is_ws_connected = False
            
            if self.ws_thread and self.ws_thread.is_alive():
                self.ws_thread.join(timeout=5)
            
            logger.info("✅ ShareKhan integration disconnected")
            
        except Exception as e:
            logger.error(f"❌ Disconnection error: {e}")
    
    def get_connection_status(self) -> Dict:
        """Get current connection status"""
        return {
            "authenticated": self.is_authenticated,
            "websocket_connected": self.is_ws_connected,
            "subscribed_symbols": len(self.subscribed_symbols),
            "live_data_symbols": len(self.live_market_data),
            "orders_cached": len(self.order_book),
            "last_activity": datetime.now().isoformat()
        } 