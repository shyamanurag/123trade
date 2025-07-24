# data/binance_client.py
"""
Comprehensive Binance Client for Quantum Crypto Trading
Handles all Binance API interactions with advanced features
"""

import logging
import asyncio
import time
import hmac
import hashlib
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import aiohttp
import pandas as pd

logger = logging.getLogger(__name__)

class BinanceClient:
    """
    Advanced Binance client with all necessary features for quantum trading
    """
    
    def __init__(self, config: Dict):
        self.api_key = config.get('api_key')
        self.api_secret = config.get('api_secret')
        self.testnet = config.get('testnet', True)
        
        # API endpoints
        if self.testnet:
            self.base_url = "https://testnet.binance.vision"
            self.ws_url = "wss://testnet.binance.vision/ws/"
        else:
            self.base_url = "https://api.binance.com"
            self.ws_url = "wss://stream.binance.com:9443/ws/"
        
        # Rate limiting
        self.last_request_time = 0
        self.request_count = 0
        self.rate_limit_per_minute = 1200
        
        # Session for connection pooling
        self.session = None
        
        logger.info(f"Binance client initialized ({'testnet' if self.testnet else 'mainnet'})")

    async def start(self):
        """Start the Binance client"""
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=100),
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        # Test connection
        server_time = await self.get_server_time()
        if server_time:
            logger.info("✅ Binance connection established")
        else:
            logger.error("❌ Failed to connect to Binance")

    async def stop(self):
        """Stop the Binance client"""
        if self.session:
            await self.session.close()

    def _generate_signature(self, params: Dict) -> str:
        """Generate API signature"""
        query_string = '&'.join([f"{key}={value}" for key, value in params.items()])
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    async def _make_request(self, method: str, endpoint: str, params: Dict = None, signed: bool = False) -> Optional[Dict]:
        """Make authenticated API request"""
        if not self.session:
            await self.start()
        
        # Rate limiting
        await self._rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        headers = {}
        
        if params is None:
            params = {}
        
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)
            headers['X-MBX-APIKEY'] = self.api_key
        
        try:
            if method == 'GET':
                async with self.session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Binance API error: {response.status} - {await response.text()}")
                        return None
            elif method == 'POST':
                async with self.session.post(url, data=params, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Binance API error: {response.status} - {await response.text()}")
                        return None
        except Exception as e:
            logger.error(f"Binance request error: {e}")
            return None

    async def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        
        # Reset counter every minute
        if current_time - self.last_request_time > 60:
            self.request_count = 0
            self.last_request_time = current_time
        
        # Check if we need to wait
        if self.request_count >= self.rate_limit_per_minute:
            wait_time = 60 - (current_time - self.last_request_time)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                self.request_count = 0
                self.last_request_time = time.time()
        
        self.request_count += 1

    # =============================================================================
    # MARKET DATA ENDPOINTS
    # =============================================================================

    async def get_server_time(self) -> Optional[int]:
        """Get server time"""
        result = await self._make_request('GET', '/api/v3/time')
        return result.get('serverTime') if result else None

    async def get_klines(self, symbol: str, interval: str, limit: int = 500, 
                        start_time: Optional[int] = None, end_time: Optional[int] = None) -> Optional[List]:
        """Get kline/candlestick data"""
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        return await self._make_request('GET', '/api/v3/klines', params)

    async def get_ticker_24hr(self, symbol: str = None) -> Optional[Dict]:
        """Get 24hr ticker price change statistics"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        return await self._make_request('GET', '/api/v3/ticker/24hr', params)

    async def get_symbol_price_ticker(self, symbol: str = None) -> Optional[Dict]:
        """Get latest price for symbol(s)"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        return await self._make_request('GET', '/api/v3/ticker/price', params)

    async def get_orderbook_ticker(self, symbol: str = None) -> Optional[Dict]:
        """Get best price/qty on the order book"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        return await self._make_request('GET', '/api/v3/ticker/bookTicker', params)

    async def get_order_book(self, symbol: str, limit: int = 100) -> Optional[Dict]:
        """Get order book depth"""
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        return await self._make_request('GET', '/api/v3/depth', params)

    async def get_recent_trades(self, symbol: str, limit: int = 500) -> Optional[List]:
        """Get recent trades"""
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        return await self._make_request('GET', '/api/v3/trades', params)

    async def get_historical_trades(self, symbol: str, limit: int = 500, from_id: int = None) -> Optional[List]:
        """Get historical trades"""
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        if from_id:
            params['fromId'] = from_id
        
        return await self._make_request('GET', '/api/v3/historicalTrades', params)

    async def get_agg_trades(self, symbol: str, limit: int = 500, 
                           start_time: Optional[int] = None, end_time: Optional[int] = None) -> Optional[List]:
        """Get compressed/aggregate trades"""
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        return await self._make_request('GET', '/api/v3/aggTrades', params)

    # =============================================================================
    # TRADING ENDPOINTS
    # =============================================================================

    async def place_order(self, symbol: str, side: str, order_type: str, 
                         quantity: float, price: float = None, time_in_force: str = 'GTC',
                         stop_price: float = None) -> Optional[Dict]:
        """Place a new order"""
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': str(quantity)
        }
        
        if order_type in ['LIMIT', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT']:
            params['timeInForce'] = time_in_force
            if price:
                params['price'] = str(price)
        
        if order_type in ['STOP_LOSS', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT', 'TAKE_PROFIT_LIMIT']:
            if stop_price:
                params['stopPrice'] = str(stop_price)
        
        return await self._make_request('POST', '/api/v3/order', params, signed=True)

    async def place_market_order(self, symbol: str, side: str, quantity: float) -> Optional[Dict]:
        """Place market order"""
        return await self.place_order(symbol, side, 'MARKET', quantity)

    async def place_limit_order(self, symbol: str, side: str, quantity: float, price: float) -> Optional[Dict]:
        """Place limit order"""
        return await self.place_order(symbol, side, 'LIMIT', quantity, price)

    async def cancel_order(self, symbol: str, order_id: int = None, orig_client_order_id: str = None) -> Optional[Dict]:
        """Cancel an active order"""
        params = {'symbol': symbol}
        
        if order_id:
            params['orderId'] = order_id
        elif orig_client_order_id:
            params['origClientOrderId'] = orig_client_order_id
        
        return await self._make_request('DELETE', '/api/v3/order', params, signed=True)

    async def cancel_all_orders(self, symbol: str) -> Optional[List]:
        """Cancel all active orders on a symbol"""
        params = {'symbol': symbol}
        return await self._make_request('DELETE', '/api/v3/openOrders', params, signed=True)

    async def get_order(self, symbol: str, order_id: int = None, orig_client_order_id: str = None) -> Optional[Dict]:
        """Check an order's status"""
        params = {'symbol': symbol}
        
        if order_id:
            params['orderId'] = order_id
        elif orig_client_order_id:
            params['origClientOrderId'] = orig_client_order_id
        
        return await self._make_request('GET', '/api/v3/order', params, signed=True)

    async def get_open_orders(self, symbol: str = None) -> Optional[List]:
        """Get all open orders"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        return await self._make_request('GET', '/api/v3/openOrders', params, signed=True)

    async def get_all_orders(self, symbol: str, order_id: int = None, 
                            start_time: int = None, end_time: int = None, limit: int = 500) -> Optional[List]:
        """Get all account orders"""
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        if order_id:
            params['orderId'] = order_id
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        return await self._make_request('GET', '/api/v3/allOrders', params, signed=True)

    # =============================================================================
    # ACCOUNT ENDPOINTS
    # =============================================================================

    async def get_account_info(self) -> Optional[Dict]:
        """Get current account information"""
        return await self._make_request('GET', '/api/v3/account', signed=True)

    async def get_account_trades(self, symbol: str, start_time: int = None, 
                               end_time: int = None, from_id: int = None, limit: int = 500) -> Optional[List]:
        """Get trades for a specific account and symbol"""
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        if from_id:
            params['fromId'] = from_id
        
        return await self._make_request('GET', '/api/v3/myTrades', params, signed=True)

    # =============================================================================
    # MARGIN TRADING ENDPOINTS
    # =============================================================================

    async def get_margin_account(self) -> Optional[Dict]:
        """Query cross-margin account details"""
        return await self._make_request('GET', '/sapi/v1/margin/account', signed=True)

    async def get_max_borrowable(self, asset: str, isolated_symbol: str = None) -> Optional[Dict]:
        """Query max borrow amount"""
        params = {'asset': asset}
        if isolated_symbol:
            params['isolatedSymbol'] = isolated_symbol
        
        return await self._make_request('GET', '/sapi/v1/margin/maxBorrowable', params, signed=True)

    # =============================================================================
    # FUTURES ENDPOINTS
    # =============================================================================

    async def get_futures_account_balance(self) -> Optional[List]:
        """Get futures account balance"""
        return await self._make_request('GET', '/fapi/v2/balance', signed=True)

    async def get_futures_position_info(self, symbol: str = None) -> Optional[List]:
        """Get current position information"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        return await self._make_request('GET', '/fapi/v2/positionRisk', params, signed=True)

    # =============================================================================
    # WEBSOCKET METHODS
    # =============================================================================

    async def get_listen_key(self) -> Optional[str]:
        """Start a new user data stream"""
        result = await self._make_request('POST', '/api/v3/userDataStream', signed=True)
        return result.get('listenKey') if result else None

    async def ping_listen_key(self, listen_key: str) -> bool:
        """Ping/Keep-alive a user data stream"""
        params = {'listenKey': listen_key}
        result = await self._make_request('PUT', '/api/v3/userDataStream', params, signed=True)
        return result is not None

    async def close_listen_key(self, listen_key: str) -> bool:
        """Close a user data stream"""
        params = {'listenKey': listen_key}
        result = await self._make_request('DELETE', '/api/v3/userDataStream', params, signed=True)
        return result is not None

    # =============================================================================
    # HELPER METHODS
    # =============================================================================

    async def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get trading rules and symbol information"""
        exchange_info = await self._make_request('GET', '/api/v3/exchangeInfo')
        if exchange_info and 'symbols' in exchange_info:
            for symbol_info in exchange_info['symbols']:
                if symbol_info['symbol'] == symbol:
                    return symbol_info
        return None

    async def get_trading_fees(self) -> Optional[List]:
        """Get trading fees"""
        return await self._make_request('GET', '/sapi/v1/asset/tradeFee', signed=True)

    def format_quantity(self, quantity: float, precision: int) -> str:
        """Format quantity according to symbol precision"""
        format_str = f"{{:.{precision}f}}"
        return format_str.format(quantity)

    def format_price(self, price: float, precision: int) -> str:
        """Format price according to symbol precision"""
        format_str = f"{{:.{precision}f}}"
        return format_str.format(price)

    # =============================================================================
    # ADVANCED ANALYTICS METHODS
    # =============================================================================

    async def get_market_data_enhanced(self, symbol: str) -> Dict:
        """Get comprehensive market data for analysis"""
        try:
            # Get multiple data points in parallel
            results = await asyncio.gather(
                self.get_ticker_24hr(symbol),
                self.get_klines(symbol, '1m', 100),
                self.get_order_book(symbol, 100),
                self.get_agg_trades(symbol, 100),
                return_exceptions=True
            )
            
            ticker_24hr, klines, order_book, agg_trades = results
            
            # Calculate additional metrics
            market_data = {
                'symbol': symbol,
                'timestamp': int(time.time() * 1000),
                'ticker_24hr': ticker_24hr if not isinstance(ticker_24hr, Exception) else None,
                'klines': klines if not isinstance(klines, Exception) else None,
                'order_book': order_book if not isinstance(order_book, Exception) else None,
                'agg_trades': agg_trades if not isinstance(agg_trades, Exception) else None
            }
            
            # Calculate enhanced metrics
            if klines and len(klines) > 0:
                df = pd.DataFrame(klines, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_asset_volume', 'number_of_trades',
                    'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
                ])
                
                df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
                
                # Calculate technical indicators
                market_data['volatility'] = df['close'].pct_change().std() * 100
                market_data['volume_avg'] = df['volume'].mean()
                market_data['price_change_1h'] = (df['close'].iloc[-1] - df['close'].iloc[-60]) / df['close'].iloc[-60] if len(df) >= 60 else 0
                
            return market_data
            
        except Exception as e:
            logger.error(f"Error getting enhanced market data for {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}

    async def get_volume_profile(self, symbol: str, interval: str = '1m', limit: int = 1000) -> Dict:
        """Get volume profile analysis"""
        try:
            klines = await self.get_klines(symbol, interval, limit)
            if not klines:
                return {}
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
            
            # Calculate VWAP
            df['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
            
            # Calculate volume profile
            volume_profile = {
                'symbol': symbol,
                'total_volume': df['volume'].sum(),
                'vwap': df['vwap'].iloc[-1],
                'volume_weighted_price': (df['volume'] * df['close']).sum() / df['volume'].sum(),
                'high_volume_nodes': [],
                'value_area_high': 0,
                'value_area_low': 0
            }
            
            return volume_profile
            
        except Exception as e:
            logger.error(f"Error calculating volume profile for {symbol}: {e}")
            return {'error': str(e)} 