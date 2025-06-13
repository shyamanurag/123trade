"""
TrueData provider for market data and WebSocket integration with Trial106 credentials
"""
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
import asyncio
from src.core.websocket_manager import WebSocketManager

# CRITICAL: Correct import path
from truedata_ws.websocket.TD import TD

class TrueDataProvider:
    def __init__(self, config: Dict):
        self.config = config
        self.is_sandbox = config.get('is_sandbox', False)  # Trial106 is not sandbox
        
        # Initialize TD with Trial106 configuration
        self.td = TD(
            config['username'],  # Trial106
            config['password'],  # shyam106
            live_port=config.get('live_port', 8086),  # Port 8086
            url=config.get('url', 'push.truedata.in'),  # Production URL
            log_level=config.get('log_level', logging.INFO),
            log_format="%(asctime)s - %(levelname)s - %(message)s"
        )
        
        # Initialize WebSocket manager
        ws_config = {
            'websocket_url': f"wss://{config.get('url', 'push.truedata.in')}:{config.get('live_port', 8086)}",
            'log_level': config.get('log_level', logging.INFO),
            'max_reconnect_attempts': config.get('max_reconnect_attempts', 3),
            'reconnect_delay': config.get('reconnect_delay', 5),
            'heartbeat_interval': config.get('heartbeat_interval', 30),
            'connection_timeout': config.get('connection_timeout', 60)
        }
        self.ws_manager = WebSocketManager(ws_config)
        
        self.subscribed_symbols = set()
        self.option_chains = {}
        self.data_queue = asyncio.Queue()  # Using asyncio.Queue instead of queue.Queue
        self.callbacks = {}
        self.connection_attempts = 0
        self.max_connection_attempts = config.get('max_connection_attempts', 3)
        self._connection_lock = asyncio.Lock()
        self.connected = False
        
        # Setup real-time data callback
        self._setup_callbacks()

    async def connect(self):
        """Connect to TrueData and WebSocket"""
        async with self._connection_lock:
            try:
                logging.info(f"Connecting to TrueData with username: {self.config['username']}")
                
                # Connect to TrueData using synchronous method
                try:
                    self.td.connect()
                    self.connected = True
                    logging.info("Successfully connected to TrueData")
                except Exception as td_error:
                    logging.error(f"TrueData connection failed: {td_error}")
                    self.connection_attempts += 1
                    
                    if self.connection_attempts < self.max_connection_attempts:
                        logging.warning(f"Connection attempt {self.connection_attempts} failed, retrying...")
                        await asyncio.sleep(5)  # Wait before retry
                        return await self.connect()
                    else:
                        raise ConnectionError(f"Max connection attempts ({self.max_connection_attempts}) reached")
                
                # Reset connection attempts on success
                self.connection_attempts = 0
                
                # Connect to WebSocket (optional, for additional features)
                try:
                    await self.ws_manager.connect(None, self.ws_manager.config['websocket_url'])
                    logging.info("WebSocket connection established")
                except Exception as ws_error:
                    logging.warning(f"WebSocket connection failed: {ws_error} (continuing without WebSocket)")
                
                return True
                
            except Exception as e:
                logging.error(f"Connection error: {e}")
                self.connected = False
                return False

    def _validate_trial_limits(self, symbols: List[str]) -> bool:
        """Validate against Trial106 account limits (50 symbols max)"""
        max_symbols = self.config.get('max_symbols', 50)
        
        if len(symbols) > max_symbols:
            logging.warning(f"Trial106 account limited to {max_symbols} symbols. Requested: {len(symbols)}")
            return False
            
        # Check total subscribed symbols including new ones
        total_symbols = len(self.subscribed_symbols) + len([s for s in symbols if s not in self.subscribed_symbols])
        if total_symbols > max_symbols:
            logging.warning(f"Total subscribed symbols would exceed limit: {total_symbols} > {max_symbols}")
            return False
            
        # Check for allowed symbols in trial account
        allowed_symbols = self.config.get('allowed_symbols', [])
        if allowed_symbols:
            invalid_symbols = [s for s in symbols if s not in allowed_symbols]
            if invalid_symbols:
                logging.warning(f"Symbols not in allowed list: {invalid_symbols}")
                return False
            
        return True

    def _validate_sandbox_limits(self, symbols: List[str]) -> bool:
        """Validate against sandbox environment limits"""
        if not self.is_sandbox:
            return True
            
        # Sandbox typically has limits on number of symbols
        max_symbols = self.config.get('sandbox_max_symbols', 5)
        if len(symbols) > max_symbols:
            logging.warning(f"Sandbox environment limited to {max_symbols} symbols")
            return False
            
        # Check for allowed symbols in sandbox
        allowed_symbols = self.config.get('sandbox_allowed_symbols', [
            'NIFTY-I', 'BANKNIFTY-I', 'RELIANCE', 'TCS', 'INFY'
        ])
        
        invalid_symbols = [s for s in symbols if s not in allowed_symbols]
        if invalid_symbols:
            logging.warning(f"Symbols not allowed in sandbox: {invalid_symbols}")
            return False
            
        return True

    def _setup_callbacks(self):
        """Setup callback handlers for real-time data"""
        @self.td.trade_callback
        def handle_trade(tick_data):
            try:
                # Process tick data
                processed_data = {
                    'symbol': tick_data.symbol,
                    'ltp': tick_data.ltp,
                    'volume': tick_data.v,
                    'timestamp': tick_data.timestamp,
                    'bid': getattr(tick_data, 'bid', None),
                    'ask': getattr(tick_data, 'ask', None)
                }
                
                # Create task for async processing
                asyncio.create_task(self._process_tick_data(processed_data))
                
                # Call user callbacks if registered
                if tick_data.symbol in self.callbacks:
                    self.callbacks[tick_data.symbol](processed_data)
                    
            except Exception as e:
                logging.error(f"Error in trade callback: {e}")

    async def _process_tick_data(self, data: Dict):
        """Process tick data asynchronously"""
        try:
            await self.data_queue.put(data)
        except Exception as e:
            logging.error(f"Error processing tick data: {e}")

    async def subscribe_symbols(self, symbols: List[str], callback: Optional[Callable] = None):
        """Subscribe to symbols for live data with Trial106 limits"""
        try:
            # Validate trial account limits (50 symbols max)
            if not self._validate_trial_limits(symbols):
                raise ValueError("Symbol subscription exceeds Trial106 account limits")
                
            # Register callbacks for symbols
            if callback:
                for symbol in symbols:
                    self.callbacks[symbol] = callback
            
            # Subscribe to new symbols only
            new_symbols = [s for s in symbols if s not in self.subscribed_symbols]
            
            if new_symbols:
                # Subscribe to TrueData
                try:
                    req_ids = self.td.start_live_data(new_symbols)
                    logging.info(f"Started live data for symbols: {new_symbols}")
                except Exception as td_error:
                    logging.error(f"TrueData subscription failed: {td_error}")
                    req_ids = []
                
                # Subscribe to WebSocket (if available)
                try:
                    await self.ws_manager.subscribe_symbols(new_symbols)
                    logging.info(f"WebSocket subscription successful for: {new_symbols}")
                except Exception as ws_error:
                    logging.warning(f"WebSocket subscription failed: {ws_error} (continuing with TrueData only)")
                
                # Update subscribed symbols
                self.subscribed_symbols.update(new_symbols)
                
                logging.info(f"Successfully subscribed to symbols: {new_symbols}")
                return req_ids if req_ids else True
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to subscribe symbols: {e}")
            return False

    async def _handle_ws_message(self, data: Dict):
        """Handle WebSocket messages"""
        try:
            if data['type'] == 'trade':
                symbol = data['symbol']
                if symbol in self.callbacks:
                    self.callbacks[symbol](data)
                    
            # Put in queue for async processing
            await self.data_queue.put(data)
            
        except Exception as e:
            logging.error(f"Error handling WebSocket message: {e}")

    async def get_option_chain(self, underlying: str, expiry: str) -> pd.DataFrame:
        """Get option chain for underlying"""
        try:
            # Convert expiry string to datetime
            expiry_date = datetime.strptime(expiry, '%Y-%m-%d')
            
            # Start option chain subscription
            chain = self.td.start_option_chain(
                underlying,
                expiry_date,
                chain_length=20,  # Get 20 strikes above and below ATM
                bid_ask=True,     # Include bid/ask data
                greek=True        # Include Greeks calculation
            )
            
            # Store chain object for later use
            self.option_chains[underlying] = chain
            
            # Get the option chain data
            option_df = chain.get_option_chain()
            
            if option_df.empty:
                logging.warning(f"No option chain data available for {underlying}")
                return pd.DataFrame()
                
            return option_df
            
        except Exception as e:
            logging.error(f"Error getting option chain: {e}")
            return pd.DataFrame()

    async def get_market_data(self, symbol: str, timeframe: str = '5min') -> Dict:
        """Get market data for symbol"""
        try:
            # Validate sandbox limits
            if not self._validate_sandbox_limits([symbol]):
                raise ValueError(f"Symbol {symbol} not allowed in sandbox")
                
            # Map timeframe to TrueData bar_size format
            bar_size_map = {
                '1min': '1 min',
                '5min': '5 min',
                '15min': '15 min',
                '30min': '30 min',
                '1hour': '60 min',
                '1day': '1 day'
            }
            
            bar_size = bar_size_map.get(timeframe, '5 min')
            
            # Determine duration based on timeframe
            duration_map = {
                '1 min': '1 D',
                '5 min': '5 D',
                '15 min': '10 D',
                '30 min': '15 D',
                '60 min': '30 D',
                '1 day': '1 Y'
            }
            
            duration = duration_map.get(bar_size, '5 D')
            
            # In sandbox, limit historical data duration
            if self.is_sandbox:
                duration = '1 D'  # Limit to 1 day in sandbox
                logging.info("Sandbox mode: Limited historical data to 1 day")
            
            # CORRECT: Use get_historical_data (not get_historic_data)
            hist_data = self.td.get_historical_data(
                symbol=symbol,
                bar_size=bar_size,
                duration=duration,
                end_time=datetime.now()
            )
            
            # Check if data is available
            if hist_data.empty:
                logging.warning(f"No historical data available for {symbol}")
                return {}
            
            # Calculate technical indicators
            atr = self._calculate_atr(hist_data)
            adx = self._calculate_adx(hist_data)
            
            # Get current VIX if available
            vix = await self._get_vix()
            
            # Get latest tick data
            latest_candle = hist_data.iloc[-1]
            
            return {
                'symbol': symbol,
                'spot': float(latest_candle['close']),
                'open': float(latest_candle['open']),
                'high': float(latest_candle['high']),
                'low': float(latest_candle['low']),
                'volume': float(latest_candle['volume']),
                'candles': hist_data.tail(100).to_dict('records'),  # Last 100 candles
                'atr': atr,
                'adx': adx,
                'vix': vix,
                'avg_volume': float(hist_data['volume'].mean()),
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logging.error(f"Failed to fetch market data for {symbol}: {e}")
            if self.is_sandbox:
                logging.warning("Running in sandbox mode - data may be limited")
            return {}

    async def get_spot_price(self, symbol: str) -> Optional[float]:
        """Get current spot price for symbol"""
        try:
            # Get 1-minute data for latest price
            data = self.td.get_historical_data(
                symbol=symbol,
                bar_size='1 min',
                duration='1 D',
                end_time=datetime.now()
            )
            
            if not data.empty:
                return float(data.iloc[-1]['close'])
            return None
            
        except Exception as e:
            logging.error(f"Failed to get spot price: {e}")
            return None

    async def _get_vix(self) -> Optional[float]:
        """Get current VIX value"""
        try:
            # India VIX symbol
            vix_data = self.td.get_historical_data(
                symbol='INDIAVIX-I',  # Continuous contract for India VIX
                bar_size='1 day',
                duration='1 D',
                end_time=datetime.now()
            )
            
            if not vix_data.empty:
                return float(vix_data.iloc[-1]['close'])
            return None
            
        except Exception as e:
            logging.error(f"Failed to get VIX: {e}")
            return None

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        try:
            high = df['high']
            low = df['low']
            close = df['close']
            
            # Calculate True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # Calculate ATR
            atr = tr.rolling(window=period).mean().iloc[-1]
            
            return float(atr) if not pd.isna(atr) else 0.0
            
        except Exception as e:
            logging.error(f"Error calculating ATR: {e}")
            return 0.0

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average Directional Index"""
        try:
            high = df['high']
            low = df['low']
            close = df['close']
            
            # Calculate +DM and -DM
            plus_dm = high.diff()
            minus_dm = -low.diff()
            
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm < 0] = 0
            
            # Calculate True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # Calculate +DI and -DI
            atr = tr.rolling(window=period).mean()
            plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
            minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
            
            # Calculate DX and ADX
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(window=period).mean().iloc[-1]
            
            return float(adx) if not pd.isna(adx) else 0.0
            
        except Exception as e:
            logging.error(f"Error calculating ADX: {e}")
            return 0.0

    def _calculate_greeks(self, option_df: pd.DataFrame, underlying: str) -> pd.DataFrame:
        """Calculate Greeks if not provided by API"""
        # This is a placeholder - implement Black-Scholes Greeks calculation if needed
        # TrueData usually provides Greeks when greek=True is set
        return option_df

    def _get_strike_interval(self, symbol: str) -> int:
        """Get strike interval for the symbol"""
        # Common strike intervals for Indian markets
        strike_intervals = {
            'NIFTY': 50,
            'BANKNIFTY': 100,
            'FINNIFTY': 50,
            'MIDCPNIFTY': 25
        }
        
        # Extract base symbol
        base_symbol = symbol.split('-')[0].upper()
        return strike_intervals.get(base_symbol, 50)

    async def unsubscribe_symbols(self, symbols: List[str]):
        """Unsubscribe from symbols"""
        try:
            # Remove from TrueData
            self.td.stop_live_data(symbols)
            
            # Remove from WebSocket
            await self.ws_manager.unsubscribe_symbols(None, symbols)
            
            # Update subscribed symbols
            self.subscribed_symbols.difference_update(symbols)
            
            # Remove callbacks
            for symbol in symbols:
                self.callbacks.pop(symbol, None)
                
            logging.info(f"Unsubscribed from symbols: {symbols}")
            
        except Exception as e:
            logging.error(f"Error unsubscribing from symbols: {e}")

    async def disconnect(self):
        """Disconnect from TrueData and WebSocket"""
        try:
            # Disconnect from TrueData
            self.td.stop_live_data(list(self.subscribed_symbols))
            
            # Disconnect from WebSocket
            await self.ws_manager.disconnect(None, None)
            
            # Clear all subscriptions
            self.subscribed_symbols.clear()
            self.callbacks.clear()
            self.option_chains.clear()
            
            logging.info("Disconnected from TrueData and WebSocket")
            
        except Exception as e:
            logging.error(f"Error disconnecting: {e}")

    def get_subscribed_symbols(self) -> List[str]:
        """Get list of currently subscribed symbols"""
        return list(self.subscribed_symbols)

# Example usage
if __name__ == "__main__":
    config = {
        'username': 'Trial106',
        'password': 'shyam106',
        'live_port': 8086,  # Updated port
        'log_level': logging.INFO,
        'url': 'push.truedata.in',  # Production URL
        'data_timeout': 60,  # 60 seconds timeout for data freshness
        'retry_attempts': 3,  # Number of retry attempts for failed operations
        'retry_delay': 5,    # Delay between retries in seconds
    }
    
    async def main():
        provider = TrueDataProvider(config)
        
        # Connect
        await provider.connect()
        
        # Subscribe to symbols
        symbols = ['NIFTY-I', 'BANKNIFTY-I', 'RELIANCE']
        await provider.subscribe_symbols(symbols)
        
        # Get market data
        data = await provider.get_market_data('NIFTY-I', '5min')
        print(f"Market data: {data}")
        
        # Get option chain
        chain = await provider.get_option_chain('NIFTY', '2025-06-26')
        print(f"Option chain shape: {chain.shape}")
    
    asyncio.run(main()) 