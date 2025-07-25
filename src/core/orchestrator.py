"""
Production-Level Trading Orchestrator
====================================
Coordinates all trading system components with shared TrueData connection.
Implements proper initialization, error handling, and component management.
"""

import asyncio
import logging
import time as time_module
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple, AsyncGenerator
import sys
import os
import pytz
from urllib.parse import urlparse
import redis
import json
import re
import traceback

# Add project root to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ROBUST IMPORT HANDLING - prevent 500 errors from missing dependencies
try:
    from src.config.database import get_redis
except ImportError:
    # Fallback if Redis config is not available
    async def get_redis():
        return None

try:
    from src.events import EventBus
except ImportError:
    # Fallback EventBus if not available
    class EventBus:
        def __init__(self):
            pass
        async def initialize(self):
            pass
        async def subscribe(self, event_type, handler):
            pass

try:
    from src.core.position_tracker import ProductionPositionTracker
except ImportError:
    # Fallback PositionTracker if not available
    class ProductionPositionTracker:
        def __init__(self):
            pass
        async def initialize(self):
            pass
        async def get_status(self):
            return {"status": "fallback_position_tracker"}

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the correct TradeEngine
try:
    from src.core.trade_engine import TradeEngine
except ImportError:
    logger.warning("Could not import TradeEngine from trade_engine.py")
    TradeEngine = None

# Use unified ZerodhaIntegration directly (no wrapper needed)
from brokers.zerodha import ZerodhaIntegration

# CRITICAL FIX: Import redis_manager with production fallback support
try:
    from src.core.redis_fallback_manager import redis_fallback_manager as redis_manager
except ImportError:
    try:
        from src.core.redis_manager import redis_manager
    except ImportError:
        # Final fallback - dummy Redis manager
        logger.warning("No Redis manager available, using dummy implementation")
        class DummyRedisManager:
            def connect(self): return False
            def get(self, key): return None
            def set(self, key, value, ex=None): return False
            def delete(self, key): return False
            def get_status(self): return {'connected': False, 'fallback_mode': True}
        redis_manager = DummyRedisManager()

# Import signal deduplicator for quality filtering
try:
    from src.core.signal_deduplicator import signal_deduplicator
except ImportError:
    # Fallback if signal deduplicator is not available
    class DummySignalDeduplicator:
        def process_signals(self, signals):
            return signals
    signal_deduplicator = DummySignalDeduplicator()

class ProductionRiskManager:
    """Production-level risk manager with proper error handling"""
    
    def __init__(self, event_bus=None, position_tracker=None, max_daily_loss=100000, max_position_size=1000000):
        self.event_bus = event_bus
        self.position_tracker = position_tracker
        self.max_daily_loss = max_daily_loss
        self.max_position_size = max_position_size
        self.daily_pnl = 0.0  # Initialize daily P&L tracking
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self) -> bool:
        """Initialize risk manager"""
        try:
            self.logger.info("Risk manager initialized")
            return True
        except Exception as e:
            self.logger.error(f"Risk manager initialization failed: {e}")
            return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Get risk manager status"""
        return {
            'status': 'production_risk_manager_active',
            'daily_pnl': self.daily_pnl,
            'max_daily_loss': self.max_daily_loss,
            'risk_limit_used': abs(self.daily_pnl) / self.max_daily_loss if self.max_daily_loss > 0 else 0.0
        }
    
    async def get_risk_metrics(self) -> Dict[str, Any]:
        """Get detailed risk metrics"""
        return {
            'success': True,
            'data': {
                'daily_pnl': self.daily_pnl,
                'max_daily_loss': self.max_daily_loss,
                'max_position_size': self.max_position_size,
                'risk_limit_used': abs(self.daily_pnl) / self.max_daily_loss if self.max_daily_loss > 0 else 0.0,
                'risk_status': 'active' if abs(self.daily_pnl) < self.max_daily_loss else 'limit_reached',
                'positions_at_risk': 'ERROR_REAL_CALCULATION_REQUIRED',
                'var_95': 'ERROR_REAL_CALCULATION_REQUIRED',
                'sharpe_ratio': 'ERROR_REAL_CALCULATION_REQUIRED',
                'WARNING': 'FAKE_RISK_METRICS_ELIMINATED_FOR_SAFETY',
                'timestamp': datetime.now().isoformat()
            }
        }

class TradingOrchestrator:
    """
    DEPRECATED: Legacy production-level trading orchestrator 
    ⚠️ WARNING: This is deprecated in favor of ShareKhanTradingOrchestrator
    """
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __init__(self, config: Optional[Dict] = None):
        """DEPRECATED: Initialize legacy orchestrator - DO NOT USE FOR NEW IMPLEMENTATIONS"""
        self.config = config or {}
        self.strategies: Dict[str, Any] = {}
        self.active_strategies = []
        self.running = False
        self.is_running = False
        self.is_initialized = False
        self.components = {}
        self.logger = logging.getLogger(__name__)
        
        # CRITICAL: Mark as deprecated
        self.logger.warning("🚨 DEPRECATED: TradingOrchestrator is deprecated. Use ShareKhanTradingOrchestrator instead.")
        
        # Set timezone
        self.ist_timezone = pytz.timezone('Asia/Kolkata')
        
        # HONEST: No fallback system - set components to None until properly initialized
        self.trade_engine = None
        self.market_data = None
        self.position_tracker = None
        self.risk_manager = None
        self.notification_manager = None
        
        # Market data tracking
        self.market_data_history = {}
        self.last_data_update = {}
        
        self.logger.warning("🚨 Legacy orchestrator initialized - migrate to ShareKhan system")
        
        # Initialize TrueData access
        self.logger.info("🚀 Initializing Trading Orchestrator with simple TrueData access...")
        
        # Test TrueData cache access
        self.logger.info("🔄 Testing access to existing TrueData cache...")
        
        try:
            from data.truedata_client import live_market_data
            if live_market_data:
                self.logger.info(f"✅ TrueData cache contains {len(live_market_data)} symbols")
                self.truedata_cache = live_market_data
            else:
                self.logger.info("⚠️ TrueData cache is empty - will use API fallback")
                self.truedata_cache = {}
        except ImportError:
            self.logger.error("❌ TrueData client not available")
            self.truedata_cache = {}
        
        # Initialize Redis connection with enhanced error handling using new manager
        self.logger.info("🔄 Initializing Redis connection with ProductionRedisManager...")
        self.redis_client = None
        self.redis_manager = redis_manager
        
        # Initialize database configuration
        from src.config.database import DatabaseConfig
        self.db_config = DatabaseConfig()
        self.logger.info("✅ Database configuration initialized")
        
        # Initialize position tracker
        from src.core.position_tracker import ProductionPositionTracker
        self.position_tracker = ProductionPositionTracker()
        
        # Initialize daily capital sync for dynamic capital management
        from src.core.daily_capital_sync import DailyCapitalSync
        self.capital_sync = DailyCapitalSync(self)
        
        # Initialize performance tracker
        self.performance_tracker = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'daily_pnl': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'win_rate': 0.0
        }
        
        # Initialize notification manager (simplified for now)
        self.notification_manager = None  # Will be initialized later if needed
        
        # Initialize risk manager
        from src.core.risk_manager import RiskManager
        from src.events import EventBus
        self.event_bus = EventBus()
        
        # CRITICAL FIX: Create proper config for RiskManager with Redis settings
        risk_manager_config = {
            'redis': {
                'host': os.environ.get('REDIS_HOST', 'localhost'),
                'port': int(os.environ.get('REDIS_PORT', 6379)),
                'db': int(os.environ.get('REDIS_DB', 0))
            } if self.redis_manager else None
        }
        self.risk_manager = RiskManager(risk_manager_config, self.position_tracker, self.event_bus)
        self.logger.info("Risk manager initialized")
        
        # Initialize Zerodha client with enhanced credential handling
        self.logger.info("🔄 Initializing Zerodha client...")
        self.zerodha_client = None  # Will be initialized async later
        
        # CRITICAL FIX: Enhanced OrderManager initialization with multiple fallback levels
        self.logger.info("🔄 Initializing OrderManager with enhanced fallback system...")
        self.order_manager = self._initialize_order_manager_with_fallback()
        
        # Initialize trade engine with proper configuration
        trade_engine_config = {
            'max_retries': 3,
            'retry_delay': 1,
            'paper_trading': self.config.get('paper_trading', True),
            'database': {
                'url': self.config.get('database_url', 'sqlite:///trading_system.db'),
                'timeout': 0.5
            }
        }
        
        # Initialize trade engine with all required components and configuration
        self.trade_engine = TradeEngine(
            self.db_config,
            self.order_manager,
            self.position_tracker,
            self.performance_tracker,
            self.notification_manager,
            trade_engine_config
        )
        
        # Set additional components after initialization
        self.trade_engine.zerodha_client = self.zerodha_client
        self.trade_engine.risk_manager = self.risk_manager
        
        # CRITICAL FIX: Initialize real-time P&L calculator
        self.pnl_calculator = None
        
        self.logger.info("✅ Trading Orchestrator initialized successfully")
        
        # Load strategies
        self.logger.info("Loading 5 trading strategies (news_impact_scalper removed for debugging)...")
        # Note: _load_strategies is async and will be called during initialize()
        
        # Initialize Position Monitor for continuous auto square-off
        self.position_monitor = None  # Will be initialized during async initialize()
        
        # System ready
        self.logger.info("✅ Trading orchestrator initialized successfully")
        
        # Schedule TrueData manual connection
        self._schedule_truedata_connection()
        
        # Log component status
        self._log_component_status()
        
    async def initialize(self) -> bool:
        """Initialize the orchestrator asynchronously"""
        try:
            self.logger.info("🚀 Initializing TradingOrchestrator async components...")
            
            # CRITICAL FIX: Test Redis connection with retry logic (moved from __init__)
            if self.redis_manager:
                try:
                    # Test connection with retry logic
                    for attempt in range(5):  # Increased retry attempts
                        try:
                            await self.redis_manager.ping()
                            self.logger.info(f"✅ Redis connected successfully (attempt {attempt + 1})")
                            break
                        except Exception as e:
                            if attempt == 4:  # Last attempt
                                self.logger.error(f"❌ Redis connection failed after {attempt + 1} attempts: {e}")
                                self.redis_client = None  # Disable Redis on failure
                                break
                            self.logger.warning(f"⚠️ Redis connection attempt {attempt + 1} failed: {e}, retrying...")
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                except Exception as e:
                    self.logger.error(f"❌ Redis connection test failed: {e}")
                    self.redis_client = None
            
            # Test Redis connection (enhanced with retry)
            if self.redis_manager:
                try:
                    await self.redis_manager.ping()
                    self.logger.info("✅ Redis connection verified and working")
                except Exception as e:
                    self.logger.error(f"❌ Redis connection test failed: {e}")
                    # CRITICAL: Don't continue without Redis in production
                    if os.getenv('ENVIRONMENT') == 'production':
                        self.logger.error("🚨 PRODUCTION ERROR: Redis connection required!")
                        # Try to reconnect with better settings
                        try:
                            # Parse the Redis URL provided by DigitalOcean
                            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
                            parsed = urlparse(redis_url)
                            
                            # Enhanced Redis config with better resilience
                            redis_config = {
                                'host': parsed.hostname,
                                'port': parsed.port or 25061,
                                'password': parsed.password,
                                'username': parsed.username or 'default',
                                'db': int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0,
                                'decode_responses': True,
                                'socket_timeout': 10,  # Reduced timeout
                                'socket_connect_timeout': 10,  # Reduced timeout
                                'retry_on_timeout': True,
                                'retry_on_error': [Exception],  # Retry on all errors
                                'ssl': True,
                                'ssl_check_hostname': False,
                                'ssl_cert_reqs': None,
                                'health_check_interval': 60,
                                'socket_keepalive': True,
                                'socket_keepalive_options': {},
                                'max_connections': 3  # Reduced connections
                            }
                            
                            # Create new Redis client with enhanced config
                            self.redis_client = redis.Redis(**redis_config)
                            await self.redis_client.ping()
                            self.logger.info("✅ Redis reconnected successfully with enhanced config")
                        except Exception as reconnect_error:
                            self.logger.warning(f"⚠️ Redis reconnection failed: {reconnect_error}")
                            self.redis_client = None
                    else:
                        self.logger.info("🔄 Development mode: System will continue in memory-only mode")
                        self.redis_client = None
            else:
                self.logger.info("ℹ️ Redis not configured - using memory-only mode")
            
            # Initialize event bus
            if hasattr(self, 'event_bus'):
                await self.event_bus.initialize()
                self.logger.info("✅ Event bus initialized")
            
            # Initialize position tracker
            if hasattr(self, 'position_tracker'):
                await self.position_tracker.initialize()
                self.logger.info("✅ Position tracker initialized")
            
            # Initialize trade engine
            if hasattr(self, 'trade_engine'):
                await self.trade_engine.initialize()
                self.logger.info("✅ Trade engine initialized")
            
            # Load strategies
            await self._load_strategies()
            self.logger.info("✅ Strategies loaded")
            
            # Initialize Zerodha client
            if not self.zerodha_client:
                try:
                    self.zerodha_client = await self._initialize_zerodha_client()
                    if self.zerodha_client:
                        self.logger.info("✅ Zerodha client initialized successfully")
                    else:
                        self.logger.error("❌ Zerodha client initialization returned None")
                except Exception as e:
                    self.logger.error(f"❌ Zerodha client initialization failed: {e}")
                    self.zerodha_client = None
            
            # Initialize Zerodha client
            if self.zerodha_client:
                try:
                    await self.zerodha_client.initialize()
                    self.logger.info("✅ Zerodha client initialized")
                except Exception as e:
                    self.logger.warning(f"⚠️ Zerodha client initialization failed: {e}")
            
            # CRITICAL FIX: Set Zerodha client in trade engine after initialization
            if hasattr(self, 'trade_engine') and self.trade_engine and self.zerodha_client:
                self.trade_engine.zerodha_client = self.zerodha_client
                self.logger.info("✅ Zerodha client assigned to trade engine")
            else:
                self.logger.error("❌ Failed to assign Zerodha client to trade engine")
                if not hasattr(self, 'trade_engine'):
                    self.logger.error("❌ Trade engine not found")
                if not self.trade_engine:
                    self.logger.error("❌ Trade engine is None")
                if not self.zerodha_client:
                    self.logger.error("❌ Zerodha client is None")
            
            # Initialize Position Monitor for continuous auto square-off
            try:
                from src.core.position_monitor import PositionMonitor
                self.position_monitor = PositionMonitor(
                    orchestrator=self,
                    position_tracker=self.position_tracker,
                    risk_manager=self.risk_manager,
                    order_manager=self.order_manager
                )
                self.logger.info("✅ Position Monitor initialized - continuous auto square-off ready")
            except Exception as e:
                self.logger.error(f"❌ Position Monitor initialization failed: {e}")
                self.logger.warning("⚠️ Auto square-off monitoring will not be available")
                self.position_monitor = None
            
            # CRITICAL FIX: Start market data to position tracker bridge
            await self._start_market_data_to_position_tracker_bridge()
            
            self.logger.info("🎉 TradingOrchestrator fully initialized and ready")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize TradingOrchestrator: {e}")
            return False
    
    def _initialize_order_manager_with_fallback(self):
        """Initialize Clean OrderManager - NO FALLBACKS"""
        try:
            from src.core.clean_order_manager import OrderManager
            
            # Clean config - no fake fallbacks
            config = {
                'zerodha_client': self.zerodha_client,
                'redis_client': self.redis_manager,
                'database_url': os.environ.get('DATABASE_URL')
            }
            
            self.logger.info("🔧 Initializing CLEAN OrderManager (no fallbacks)...")
            order_manager = OrderManager(config)
            self.logger.info("✅ Clean OrderManager initialized successfully")
            return order_manager
            
        except Exception as e:
            self.logger.error(f"❌ OrderManager initialization FAILED: {e}")
            self.logger.error("❌ NO FALLBACKS - System must be fixed properly")
            raise e
            
    def _initialize_simple_order_manager(self):
        """Initialize SimpleOrderManager as fallback"""
        try:
            from src.core.simple_order_manager import SimpleOrderManager
            
            # CRITICAL FIX: Add redis_url to config for consistency
            redis_url = os.environ.get('REDIS_URL')
            config = {
                'zerodha_client': self.zerodha_client,
                'redis_url': redis_url,  # Add redis_url for consistency
                'redis': self.redis_manager
            }
            
            self.logger.info("🔄 Attempting SimpleOrderManager initialization...")
            order_manager = SimpleOrderManager(config)
            self.logger.info("✅ SimpleOrderManager initialized successfully")
            return order_manager
            
        except Exception as e:
            self.logger.error(f"❌ SimpleOrderManager initialization failed: {e}")
            self.logger.error("🔄 Falling back to MinimalOrderManager...")
            return self._initialize_minimal_order_manager()
            
    def _initialize_minimal_order_manager(self):
        """Initialize MinimalOrderManager as last resort"""
        try:
            from src.core.minimal_order_manager import MinimalOrderManager
            
            # CRITICAL FIX: Add redis_url to config for consistency
            redis_url = os.environ.get('REDIS_URL')
            config = {
                'zerodha_client': self.zerodha_client,
                'redis_url': redis_url  # Add redis_url for consistency
            }
            
            self.logger.info("🔄 Attempting MinimalOrderManager initialization...")
            order_manager = MinimalOrderManager(config)
            self.logger.info("✅ MinimalOrderManager initialized successfully")
            return order_manager
            
        except Exception as e:
            self.logger.error(f"❌ MinimalOrderManager initialization failed: {e}")
            self.logger.error("❌ ALL OrderManager fallbacks failed - this is CRITICAL")
            self.logger.error("❌ System will NOT be able to execute trades")
            return None
            
    def _schedule_truedata_connection(self):
        """Schedule TrueData connection after deployment stabilizes"""
        import asyncio
        import threading
        
        def connect_truedata_delayed():
            """Connect TrueData after delay"""
            import time
            time.sleep(30)  # Wait 30 seconds for deployment to stabilize
            
            try:
                self.logger.info("🔄 Attempting delayed TrueData connection...")
                from data.truedata_client import truedata_client
                
                # Reset circuit breaker and connection attempts
                truedata_client._circuit_breaker_active = False
                truedata_client._connection_attempts = 0
                
                # Attempt connection
                if truedata_client.connect():
                    self.logger.info("✅ TrueData connected successfully after deployment")
                    # Update our cache reference
                    from data.truedata_client import live_market_data
                    self.truedata_cache = live_market_data
                else:
                    self.logger.warning("⚠️ TrueData connection failed - will retry later")
                    
            except Exception as e:
                self.logger.error(f"❌ Delayed TrueData connection failed: {e}")
        
        # Start delayed connection in background thread
        connection_thread = threading.Thread(target=connect_truedata_delayed, daemon=True)
        connection_thread.start()
        self.logger.info("🔄 TrueData connection scheduled for 30 seconds")
        
    def _log_component_status(self):
        """Log comprehensive component status"""
        self.logger.info("📊 Component Status:")
        self.logger.info(f"   {'✅' if self.truedata_cache else '❌'} truedata_cache: {bool(self.truedata_cache)}")
        self.logger.info(f"   {'✅' if self.event_bus else '❌'} event_bus: {bool(self.event_bus)}")
        self.logger.info(f"   {'✅' if self.position_tracker else '❌'} position_tracker: {bool(self.position_tracker)}")
        self.logger.info(f"   {'✅' if self.risk_manager else '❌'} risk_manager: {bool(self.risk_manager)}")
        self.logger.info(f"   {'✅' if self.zerodha_client else '❌'} zerodha: {bool(self.zerodha_client)}")
        self.logger.info(f"   {'✅' if self.order_manager else '❌'} order_manager: {bool(self.order_manager)}")
        self.logger.info(f"   {'✅' if self.trade_engine else '❌'} trade_engine: {bool(self.trade_engine)}")
        
        # Log critical warnings
        if not self.order_manager:
            self.logger.error("❌ OrderManager initialization failed - this is CRITICAL for real money trading")
            self.logger.error("❌ System will NOT use simplified components for real money")
            self.logger.warning("⚠️ Starting in degraded mode - manual OrderManager initialization required")
        else:
            self.logger.info("✅ OrderManager available - trade execution enabled")
            
    async def _initialize_zerodha_client(self):
        """Initialize Zerodha client with enhanced credential handling"""
        try:
            # CRITICAL FIX: Get credentials from trading_control first
            zerodha_credentials = await self._get_zerodha_credentials_from_trading_control()
            
            logger.info(f"🔍 DEBUG: Credentials from trading_control: {zerodha_credentials}")
            
            if zerodha_credentials:
                api_key = zerodha_credentials.get('api_key')
                user_id = zerodha_credentials.get('user_id')
                access_token = zerodha_credentials.get('access_token')
                
                logger.info(f"🔍 DEBUG: API Key: {api_key[:8] if api_key else None}")
                logger.info(f"🔍 DEBUG: User ID: {user_id if user_id else None}")
                logger.info(f"🔍 DEBUG: Access Token: {access_token[:10] if access_token else None}")
                
                if api_key and user_id:
                    self.logger.info(f"✅ Using Zerodha credentials from trading_control: API Key: {api_key[:8]}..., User ID: {user_id}")
                    
                    # Create Zerodha client
                    from brokers.zerodha import ZerodhaIntegration
                    
                    # Set environment variables for the client
                    os.environ['ZERODHA_API_KEY'] = api_key
                    os.environ['ZERODHA_USER_ID'] = user_id
                    
                    # Create broker instance with proper config dictionary
                    has_valid_credentials = all([api_key, user_id, access_token])
                    zerodha_config = {
                        'api_key': api_key,
                        'user_id': user_id,
                        'access_token': access_token,
                        'mock_mode': not has_valid_credentials,  # False when we have all credentials
                        'sandbox_mode': os.getenv('ZERODHA_SANDBOX_MODE', 'true').lower() == 'true'  # Default to sandbox for safety
                    }
                    
                    # Create config for resilient connection
                    resilient_config = {
                        'max_retries': 3,
                        'retry_delay': 5,
                        'health_check_interval': 30,
                        'order_rate_limit': 1.0,
                        'ws_reconnect_delay': 5,
                        'ws_max_reconnect_attempts': 10
                    }
                    
                    # Create unified broker instance with built-in resilience
                    unified_config = {**zerodha_config, **resilient_config}
                    zerodha_client = ZerodhaIntegration(unified_config)
                    logger.info(f"✅ Zerodha client initialized in {'REAL' if not zerodha_config['mock_mode'] else 'MOCK'} mode")
                    logger.info(f"   Sandbox: {'ON' if zerodha_config['sandbox_mode'] else 'OFF'}")
                    return zerodha_client
                else:
                    self.logger.error("❌ Incomplete Zerodha credentials from trading_control")
            else:
                self.logger.warning("⚠️ No Zerodha credentials found in trading_control")
                
            # Fallback to environment variables
            self.logger.info("🔄 Falling back to environment variables for Zerodha credentials")
            return await self._initialize_zerodha_from_env()
            
        except Exception as e:
            self.logger.error(f"❌ Zerodha client initialization error: {e}")
            return None
            
    async def _get_zerodha_credentials_from_trading_control(self):
        """Get Zerodha credentials from trading_control module with dynamic user support"""
        try:
            from src.api.trading_control import broker_users, get_master_user, get_user_by_zerodha_id
            
            # First try to get the master user (the one that can execute trades)
            try:
                master_user = get_master_user()
                if master_user:
                    zerodha_user_id = master_user['user_id']  # This is the real Zerodha user ID
                    credentials = {
                        'api_key': master_user.get('api_key'),
                        'api_secret': master_user.get('api_secret'), 
                        'user_id': zerodha_user_id  # Use real Zerodha user ID
                    }
                    
                    self.logger.info(f"✅ Found master Zerodha user credentials: {zerodha_user_id}")
                    
                    # Get access token from Redis using the REAL Zerodha user ID
                    access_token = await self._get_access_token_from_redis(zerodha_user_id)
                    if access_token:
                        credentials['access_token'] = access_token
                        self.logger.info(f"✅ Retrieved access token from Redis for Zerodha user: {zerodha_user_id}")
                        return credentials
                    else:
                        self.logger.warning(f"⚠️ No access token found in Redis for Zerodha user: {zerodha_user_id}")
                        # Try alternative patterns for backward compatibility
                        # DYNAMIC FALLBACK: Use environment-based alternatives
                        master_user_id = os.getenv('ZERODHA_USER_ID', 'QSW899')
                        for alt_user_id in [zerodha_user_id, master_user_id, 'QSW899', 'PAPER_TRADER_MAIN']:
                            access_token = await self._get_access_token_from_redis(alt_user_id)
                            if access_token:
                                credentials['access_token'] = access_token
                                self.logger.info(f"✅ Retrieved access token from Redis for alt user: {alt_user_id}")
                                return credentials
            except Exception as master_error:
                self.logger.warning(f"⚠️ Error getting master user: {master_error}")
            
            # Fallback: Look for any active Zerodha user
            for user_id, user_data in broker_users.items():
                if user_data.get('is_active') and user_data.get('broker') == 'zerodha':
                    zerodha_user_id = user_data.get('client_id', user_id)
                    credentials = {
                        'api_key': user_data.get('api_key'),
                        'user_id': zerodha_user_id,  # client_id is the Zerodha user_id
                        'api_secret': user_data.get('api_secret')
                    }
                    
                    if credentials.get('api_key') and credentials.get('user_id'):
                        self.logger.info(f"✅ Found fallback Zerodha credentials for user: {zerodha_user_id}")
                        
                        # Get access token from Redis
                        access_token = await self._get_access_token_from_redis(zerodha_user_id)
                        if access_token:
                            credentials['access_token'] = access_token
                            self.logger.info(f"✅ Retrieved access token from Redis for user: {zerodha_user_id}")
                            return credentials
                        
            self.logger.warning("⚠️ No active Zerodha users found in trading_control")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error getting Zerodha credentials from trading_control: {e}")
            return None
    
    async def _get_access_token_from_redis(self, user_id: str) -> Optional[str]:
        """Get access token from Redis where frontend stores it"""
        try:
            import redis.asyncio as redis
            import os
            
            # Initialize Redis client with proper SSL configuration
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                # CRITICAL FIX: Use proper SSL configuration for DigitalOcean Redis
                if 'ondigitalocean.com' in redis_url:
                    redis_client = redis.from_url(
                        redis_url, 
                        decode_responses=True,
                        ssl_cert_reqs=None,
                        ssl_check_hostname=False
                    )
                else:
                    redis_client = redis.from_url(redis_url, decode_responses=True)
            else:
                redis_client = redis.Redis(
                    host=os.getenv('REDIS_HOST', 'localhost'),
                    port=int(os.getenv('REDIS_PORT', 6379)),
                    password=os.getenv('REDIS_PASSWORD'),
                    decode_responses=True
                )
            
            # CRITICAL TOKEN SYNC FIX: Check ALL possible Redis keys exhaustively
            self.logger.info(f"🔍 EXHAUSTIVE token search for user: {user_id}")
            
            # PRIORITIZED TOKEN SEARCH: Check specific user ID first, then fallbacks
            master_user_id = os.getenv('ZERODHA_USER_ID', 'QSW899')
            token_keys_to_check = [
                f"zerodha:token:{user_id}",                    # 1. Exact user ID (highest priority)
                f"zerodha:token:{master_user_id}",             # 2. Master user ID  
                f"zerodha:token:QSW899",                       # 3. Specific known user
                f"zerodha:access_token",                       # 4. Simple pattern
                f"zerodha:{user_id}:access_token",             # 5. Alternative pattern
                f"zerodha_token_{user_id}",                    # 6. Alternative format
                f"zerodha:token:ZERODHA_DEFAULT"               # 7. Default pattern
            ]
            
            # First check priority keys for the specific user
            for key in token_keys_to_check:
                try:
                    access_token = await redis_client.get(key)
                    if access_token:
                        await redis_client.close()
                        self.logger.info(f"✅ Found prioritized token for user {user_id} with key: {key}")
                        return access_token
                except Exception as e:
                    self.logger.warning(f"⚠️ Error checking priority key {key}: {e}")
            
            # Only if no priority keys found, do wildcard search as fallback
            try:
                all_zerodha_keys = await redis_client.keys("zerodha:token:*")
                self.logger.info(f"🔍 No priority token found, checking {len(all_zerodha_keys)} wildcard keys")
                for key in all_zerodha_keys:
                    key_str = key.decode() if isinstance(key, bytes) else key
                    # Skip if we already checked this key in priority list
                    if key_str in token_keys_to_check:
                        continue
                    try:
                        token_value = await redis_client.get(key)
                        if token_value:
                            self.logger.info(f"🔍 Fallback key: {key_str} -> Token: {token_value[:10]}...")
                            await redis_client.close()
                            self.logger.warning(f"⚠️ Using fallback token from key: {key_str} (should check why priority keys missing)")
                            return token_value
                    except Exception as e:
                        self.logger.warning(f"⚠️ Error reading fallback key {key_str}: {e}")
            except Exception as e:
                self.logger.warning(f"⚠️ Error listing zerodha keys: {e}")
            
            self.logger.warning(f"⚠️ No access token found in Redis for user: {user_id} with any key pattern")
            await redis_client.close()
            
            # CRITICAL FIX: Check memory storage as fallback
            if hasattr(self, '_memory_token_store') and user_id in self._memory_token_store:
                memory_token = self._memory_token_store[user_id]
                self.logger.info(f"✅ Found access token in memory for user: {user_id}")
                return memory_token
            
            return None
                
        except Exception as e:
            self.logger.error(f"❌ Error retrieving access token from Redis: {e}")
            return None
    
    async def update_zerodha_token(self, user_id: str, access_token: str):
        """Update Zerodha access token dynamically without restart"""
        try:
            self.logger.info(f"✅ Updating Zerodha access token for user: {user_id}")
            
            # CRITICAL FIX: Store token in memory as fallback if Redis fails
            if not hasattr(self, '_memory_token_store'):
                self._memory_token_store = {}
            self._memory_token_store[user_id] = access_token
            self.logger.info(f"✅ Token stored in memory for user: {user_id}")
            
            # Try to store in Redis as well
            try:
                import redis.asyncio as redis
                import os
                
                redis_url = os.getenv('REDIS_URL')
                if redis_url:
                    redis_client = redis.from_url(
                        redis_url, 
                        decode_responses=True,
                        ssl_cert_reqs=None,
                        ssl_check_hostname=False
                    )
                    
                    # Store token with expiration (8 hours)
                    redis_key = f"zerodha:token:{user_id}"
                    await redis_client.set(redis_key, access_token, ex=28800)  # 8 hours
                    await redis_client.close()
                    self.logger.info(f"✅ Token stored in Redis at {redis_key}")
                else:
                    self.logger.warning("⚠️ REDIS_URL not available, using memory storage only")
            except Exception as redis_error:
                self.logger.warning(f"⚠️ Redis storage failed, using memory storage: {redis_error}")
            
            # Update the token in the existing Zerodha client if available
            if hasattr(self, 'zerodha_client') and self.zerodha_client:
                # CRITICAL FIX: ZerodhaIntegration IS the broker directly, no .broker attribute
                self.zerodha_client.access_token = access_token
                if hasattr(self.zerodha_client, 'kite') and self.zerodha_client.kite:
                    self.zerodha_client.kite.set_access_token(access_token)
                    self.logger.info(f"✅ Updated KiteConnect access token in Zerodha client")
                
                # Use the update_access_token method for proper token handling
                if hasattr(self.zerodha_client, 'update_access_token'):
                    await self.zerodha_client.update_access_token(access_token)
                    self.logger.info(f"✅ Updated access token using ZerodhaIntegration method")
                    
            # Update the token in trade engine if available
            if hasattr(self, 'trade_engine') and self.trade_engine:
                if hasattr(self.trade_engine, 'zerodha_client') and self.trade_engine.zerodha_client:
                    # CRITICAL FIX: ZerodhaIntegration IS the broker directly, no .broker attribute
                    self.trade_engine.zerodha_client.access_token = access_token
                    if hasattr(self.trade_engine.zerodha_client, 'kite') and self.trade_engine.zerodha_client.kite:
                        self.trade_engine.zerodha_client.kite.set_access_token(access_token)
                        self.logger.info(f"✅ Updated KiteConnect access token in trade engine Zerodha client")
                    
                    # Use the update_access_token method for proper token handling
                    if hasattr(self.trade_engine.zerodha_client, 'update_access_token'):
                        await self.trade_engine.zerodha_client.update_access_token(access_token)
                        self.logger.info(f"✅ Updated trade engine access token using ZerodhaIntegration method")
            
            # Re-initialize the Zerodha client with the new token
            await self._initialize_zerodha_client()
            
            self.logger.info(f"✅ Successfully updated Zerodha access token for user: {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error updating Zerodha access token: {e}")
            return False
            
    async def _initialize_zerodha_from_env(self):
        """Initialize Zerodha client from environment variables"""
        try:
            api_key = os.environ.get('ZERODHA_API_KEY')
            user_id = os.environ.get('ZERODHA_USER_ID')  # Note: corrected variable name
            
            if api_key and user_id:
                self.logger.info(f"✅ Using Zerodha credentials from environment: API Key: {api_key[:8]}..., User ID: {user_id}")
                
                # Get access token from environment or Redis
                access_token = os.getenv('ZERODHA_ACCESS_TOKEN')
                
                # If no access token in environment, check Redis with multiple key patterns using new manager
                if not access_token:
                    try:
                        # Use the new Redis manager for better connection handling
                        if self.redis_manager:
                            await self.redis_manager.initialize()
                            
                            # Check multiple Redis key patterns to find the token
                            # DYNAMIC TOKEN PATTERNS: Use environment-based user ID
                            master_user_id = os.getenv('ZERODHA_USER_ID', 'QSW899')
                            token_keys_to_check = [
                                f"zerodha:token:{user_id}",  # Standard pattern with env user_id
                                f"zerodha:token:{master_user_id}",  # Dynamic master user pattern
                                f"zerodha:token:PAPER_TRADER_MAIN",  # Alternative paper trader ID
                                f"zerodha:token:QSW899",  # Backup specific user ID
                                f"zerodha:{user_id}:access_token",  # Alternative pattern
                                f"zerodha:access_token",  # Simple pattern
                                f"zerodha_token_{user_id}",  # Alternative format
                            ]
                            
                            for key in token_keys_to_check:
                                stored_token = await self.redis_manager.safe_get(key)
                                if stored_token:
                                    access_token = stored_token
                                    self.logger.info(f"✅ Found Zerodha token in Redis with key: {key}")
                                    break
                            
                            # If still no token, check all zerodha:token:* keys
                            if not access_token:
                                self.logger.info("🔍 Searching all zerodha:token:* keys in Redis...")
                                all_keys = await self.redis_manager.safe_keys("zerodha:token:*")
                                for key in all_keys:
                                    stored_token = await self.redis_manager.safe_get(key)
                                    if stored_token:
                                        access_token = stored_token
                                        self.logger.info(f"✅ Found Zerodha token in Redis with key: {key}")
                                        break
                        else:
                            # Fallback to direct Redis connection with proper SSL configuration
                            import redis.asyncio as redis
                            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
                            
                            # CRITICAL FIX: Use proper SSL configuration for DigitalOcean Redis
                            if 'ondigitalocean.com' in redis_url:
                                redis_client = redis.from_url(
                                    redis_url, 
                                    decode_responses=True,
                                    ssl_cert_reqs=None,
                                    ssl_check_hostname=False
                                )
                            else:
                                redis_client = redis.from_url(redis_url, decode_responses=True)
                            
                            # Check multiple Redis key patterns to find the token
                            # DYNAMIC TOKEN PATTERNS: Use environment-based user ID
                            master_user_id = os.getenv('ZERODHA_USER_ID', 'QSW899')
                            token_keys_to_check = [
                                f"zerodha:token:{user_id}",  # Standard pattern with env user_id
                                f"zerodha:token:{master_user_id}",  # Dynamic master user pattern
                                f"zerodha:token:PAPER_TRADER_MAIN",  # Alternative paper trader ID
                                f"zerodha:token:QSW899",  # Backup specific user ID
                                f"zerodha:access_token",  # Simple pattern
                                f"zerodha:{user_id}:access_token",  # Alternative pattern
                                f"zerodha_token_{user_id}",  # Alternative format
                                f"zerodha:token:ZERODHA_DEFAULT"  # Default pattern
                            ]
                            
                            for key in token_keys_to_check:
                                try:
                                    stored_token = await redis_client.get(key)
                                    if stored_token:
                                        access_token = stored_token.decode() if isinstance(stored_token, bytes) else stored_token
                                        self.logger.info(f"✅ Found Zerodha token in Redis with key: {key}")
                                        break
                                except Exception as key_error:
                                    self.logger.warning(f"⚠️ Error checking Redis key {key}: {key_error}")
                                    continue
                            
                            await redis_client.close()
                        
                    except Exception as redis_error:
                        self.logger.warning(f"Could not check Redis for stored token: {redis_error}")
                
                # Create proper broker instance and config
                from brokers.zerodha import ZerodhaIntegration
                
                # Create unified config with built-in resilience features
                has_valid_credentials = all([api_key, user_id, access_token])
                has_api_credentials = all([api_key, user_id])
                
                unified_config = {
                    'api_key': api_key,
                    'user_id': user_id,
                    'access_token': access_token,  # Can be None initially
                    'mock_mode': not has_api_credentials,  # Only require API credentials, not token
                    'sandbox_mode': os.getenv('ZERODHA_SANDBOX_MODE', 'true').lower() == 'true',
                    'allow_token_update': True,  # Allow token to be set later
                    # Built-in resilience configuration
                    'max_retries': 3,
                    'retry_delay': 5,
                    'health_check_interval': 30,
                    'order_rate_limit': 1.0,
                    'ws_reconnect_delay': 5,
                    'ws_max_reconnect_attempts': 10
                }
                
                # Log initialization status
                if has_api_credentials:
                    if access_token:
                        self.logger.info(f"✅ Zerodha initializing with token for user {user_id}: {access_token[:10]}...")
                    else:
                        self.logger.info(f"🔧 Zerodha initializing WITHOUT token for user {user_id} - will accept token from frontend")
                    self.logger.info("🔄 Zerodha will use REAL API with built-in resilience")
                else:
                    self.logger.warning(f"❌ Missing Zerodha API credentials - running in mock mode")
                
                # Create unified broker instance with built-in resilience
                zerodha_client = ZerodhaIntegration(unified_config)
                self.logger.info("✅ Zerodha client initialized from environment with proper config")
                return zerodha_client
            else:
                self.logger.error("❌ Missing Zerodha credentials in environment variables")
                self.logger.error("❌ Required: ZERODHA_API_KEY and ZERODHA_USER_ID")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Zerodha client initialization error: {e}")
            return None
    
    async def _get_market_data_from_api(self) -> Dict[str, Any]:
        """Get market data from Redis cache - SOLVES PROCESS ISOLATION"""
        try:
            # CRITICAL FIX: Import json at function level to ensure it's always available
            import json
            
            # STRATEGY 1: Redis cache (PRIMARY - fixes process isolation)
            if not hasattr(self, 'redis_client') or not self.redis_client:
                try:
                    import redis
                except ImportError:
                    self.logger.warning("Redis package not available - using fallback")
                    redis = None
                
                if redis:
                    redis_host = os.environ.get('REDIS_HOST', 'localhost')
                    redis_port = int(os.environ.get('REDIS_PORT', 6379))
                    redis_password = os.environ.get('REDIS_PASSWORD')
                    
                    try:
                        # CRITICAL FIX: Proper DigitalOcean Redis connection
                        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
                        
                        # DigitalOcean managed Redis requires SSL even with redis:// URLs
                        if 'ondigitalocean.com' in redis_url:
                            # Use redis.from_url with SSL configuration for DigitalOcean
                            self.redis_client = redis.from_url(
                                redis_url,
                                decode_responses=True,
                                socket_timeout=10,
                                socket_connect_timeout=10,
                                retry_on_timeout=True,
                                ssl_cert_reqs=None,
                                ssl_check_hostname=False,
                                health_check_interval=30
                            )
                        else:
                            # Local Redis without SSL
                            connection_pool = redis.ConnectionPool(
                                host=redis_host,
                                port=redis_port,
                                password=redis_password,
                                decode_responses=True,
                                socket_connect_timeout=5,
                                socket_timeout=5,
                                socket_keepalive=True,
                                socket_keepalive_options={},
                                health_check_interval=60,
                                max_connections=2,
                                retry_on_timeout=True,
                                retry_on_error=[redis.exceptions.ConnectionError, redis.exceptions.TimeoutError]
                            )
                            self.redis_client = redis.Redis(connection_pool=connection_pool)
                        
                        # Test connection with retry logic
                        for attempt in range(3):
                            try:
                                self.redis_client.ping()
                                self.logger.info(f"✅ Orchestrator Redis connected (attempt {attempt + 1}): {redis_host}:{redis_port}")
                                break
                            except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
                                if attempt == 2:  # Last attempt
                                    raise e
                                await asyncio.sleep(1)  # Wait before retry
                        
                    except Exception as redis_error:
                        self.logger.warning(f"⚠️ Redis connection failed after retries: {redis_error}")
                        self.redis_client = None
                else:
                    self.redis_client = None
            
            # Try to get data from Redis first
            if self.redis_client:
                try:
                    cached_data = self.redis_client.hgetall("truedata:live_cache")
                    
                    if cached_data:
                        # Parse JSON data
                        parsed_data = {}
                        for symbol, json_data in cached_data.items():
                            try:
                                parsed_data[symbol] = json.loads(json_data)
                            except json.JSONDecodeError:
                                continue
                        
                        if parsed_data:
                            self.logger.info(f"📊 Using Redis cache: {len(parsed_data)} symbols")
                            # CRITICAL FIX: Update orchestrator's truedata_cache reference
                            self.truedata_cache = parsed_data
                            return parsed_data
                except Exception as redis_error:
                    self.logger.warning(f"⚠️ Redis cache read failed: {redis_error}")
            
            # STRATEGY 2: Direct TrueData cache access (FALLBACK)
            from data.truedata_client import live_market_data, get_all_live_data
            
            # Try direct access first (most reliable)
            if live_market_data:
                self.logger.info(f"📊 Using direct TrueData cache: {len(live_market_data)} symbols")
                # CRITICAL FIX: Update orchestrator's truedata_cache reference
                self.truedata_cache = live_market_data
                return live_market_data.copy()  # Return copy to avoid modification issues
            
            # Fallback to get_all_live_data() function
            all_data = get_all_live_data()
            if all_data:
                self.logger.info(f"📊 Using TrueData get_all_live_data(): {len(all_data)} symbols")
                return all_data
            
            # STRATEGY 3: API call to market data endpoint (FINAL FALLBACK)
            try:
                import aiohttp
            except ImportError:
                self.logger.warning("aiohttp package not available - skipping API fallback")
                aiohttp = None
            
            if aiohttp:
                try:
                    async with aiohttp.ClientSession() as session:
                        # Call the working market data API endpoint
                        api_url = "http://localhost:8000/api/v1/market-data"
                        async with session.get(api_url, timeout=5) as response:
                            if response.status == 200:
                                api_data = await response.json()
                                if api_data.get('success') and api_data.get('data'):
                                    market_data = api_data['data']
                                    self.logger.info(f"📊 Using market data API: {len(market_data)} symbols")
                                    return market_data
                except Exception as api_error:
                    self.logger.warning(f"API fallback failed: {api_error}")
            
            self.logger.warning("⚠️ All TrueData access methods failed")
            return {}
                
        except ImportError:
            self.logger.warning("⚠️ TrueData client not available")
            return {}
        except Exception as e:
            self.logger.error(f"❌ Error accessing TrueData cache: {e}")
            return {}
    
    async def _process_market_data(self):
        """Process market data from shared connection and run strategies"""
        try:
            # Get market data from shared connection instead of creating new TrueData connection
            market_data = await self._get_market_data_from_api()
            
            if not market_data:
                self.logger.warning("⚠️ No market data available for strategy processing")
                return
                
            # Transform market data for strategies
            transformed_data = self._transform_market_data_for_strategies(market_data)
            
            # Run strategies with market data
            await self._run_strategies(transformed_data)
            
        except Exception as e:
            self.logger.error(f"❌ Error processing market data: {e}")
    
    async def _run_strategies(self, market_data: Dict[str, Any]):
        """Run all active strategies with transformed data and collect signals"""
        try:
            all_signals = []
            # CRITICAL FIX: Use the already-transformed data passed in, don't re-transform
            # transformed_data = self._transform_market_data_for_strategies(market_data)  # ❌ REMOVED: Causes double processing
            transformed_data = market_data  # ✅ FIXED: Use pre-transformed data
            
            # DEBUG: Show strategy status before processing
            self.logger.info(f"🔍 DEBUG: Total strategies loaded: {len(self.strategies)}")
            for strategy_key, strategy_info in self.strategies.items():
                active = strategy_info.get('active', False)
                has_instance = 'instance' in strategy_info
                self.logger.info(f"   📋 {strategy_key}: active={active}, has_instance={has_instance}")
            
            for strategy_key, strategy_info in self.strategies.items():
                if strategy_info.get('active', False) and 'instance' in strategy_info:
                    try:
                        strategy_instance = strategy_info['instance']
                        self.logger.info(f"🔍 Processing strategy: {strategy_key}")
                        
                        # Call strategy's on_market_data method with TRANSFORMED data
                        await strategy_instance.on_market_data(transformed_data)
                        
                        # Collect signals and track generation count
                        signals_generated = 0
                        if hasattr(strategy_instance, 'current_positions'):
                            for symbol, signal in strategy_instance.current_positions.items():
                                if isinstance(signal, dict) and 'action' in signal and signal.get('action') != 'HOLD':
                                    # Add strategy info to signal
                                    signal['strategy'] = strategy_key
                                    signal['signal_id'] = f"{strategy_key}_{symbol}_{int(datetime.now().timestamp())}"
                                    signal['generated_at'] = datetime.now().isoformat()
                                    all_signals.append(signal.copy())  # Copy signal to avoid reference issues
                                    signals_generated += 1
                                    self.logger.info(f"🚨 SIGNAL COLLECTED: {strategy_key} -> {signal}")
                                    
                                    # TRACK: Increment signals generated count
                                    self._track_signal_generated(strategy_key, signal)
                        
                        if signals_generated == 0:
                            self.logger.info(f"📝 {strategy_key}: No signals generated (normal operation)")
                        else:
                            # Clear signals after collection (correct behavior)
                            # Signals should be void if execution fails
                            for symbol in list(strategy_instance.current_positions.keys()):
                                if (isinstance(strategy_instance.current_positions[symbol], dict) and 
                                    strategy_instance.current_positions[symbol].get('action') != 'HOLD'):
                                    strategy_instance.current_positions[symbol] = None
                        
                        # Update last signal time
                        strategy_info['last_signal'] = datetime.now().isoformat()
                        
                    except Exception as e:
                        self.logger.error(f"Error running strategy {strategy_key}: {e}")
            
            # Process all collected signals through deduplicator and trade engine
            if all_signals:
                # Apply signal deduplication and quality filtering
                self.logger.info(f"🔍 Deduplicating {len(all_signals)} raw signals")
                filtered_signals = signal_deduplicator.process_signals(all_signals)
                
                if filtered_signals:
                    if self.trade_engine:
                        self.logger.info(f"🚀 Processing {len(filtered_signals)} high-quality signals through trade engine")
                        await self.trade_engine.process_signals(filtered_signals)
                    else:
                        self.logger.error("❌ Trade engine not available - signals cannot be processed")
                        # TRACK: Mark all signals as failed due to no trade engine
                        for signal in filtered_signals:
                            self._track_signal_failed(signal, "No trade engine available")
                else:
                    self.logger.info("📭 No high-quality signals after deduplication")
                    # TRACK: Mark filtered signals as rejected
                    for signal in all_signals:
                        self._track_signal_failed(signal, "Filtered out by quality/deduplication")
            else:
                self.logger.debug("📭 No signals generated this cycle")
                    
        except Exception as e:
            self.logger.error(f"Error running strategies: {e}")
    
    def _track_signal_generated(self, strategy: str, signal: Dict):
        """Track signal generation for analytics"""
        try:
            if not hasattr(self, 'signal_stats'):
                self.signal_stats = {
                    'generated': 0,
                    'executed': 0,
                    'failed': 0,
                    'by_strategy': {},
                    'recent_signals': [],
                    'failed_signals': []
                }
            
            # Increment counters
            self.signal_stats['generated'] += 1
            
            if strategy not in self.signal_stats['by_strategy']:
                self.signal_stats['by_strategy'][strategy] = {
                    'generated': 0, 'executed': 0, 'failed': 0
                }
            self.signal_stats['by_strategy'][strategy]['generated'] += 1
            
            # Store recent signals (last 10)
            signal_record = {
                'signal_id': signal.get('signal_id'),
                'strategy': strategy,
                'symbol': signal.get('symbol'),
                'action': signal.get('action'),
                'confidence': signal.get('confidence'),
                'generated_at': signal.get('generated_at'),
                'status': 'GENERATED'
            }
            
            self.signal_stats['recent_signals'].append(signal_record)
            if len(self.signal_stats['recent_signals']) > 10:
                self.signal_stats['recent_signals'].pop(0)
                
            self.logger.info(f"📊 SIGNAL TRACKED: Total generated: {self.signal_stats['generated']}")
            
        except Exception as e:
            self.logger.error(f"Error tracking signal generation: {e}")
    
    def _track_signal_failed(self, signal: Dict, reason: str):
        """Track failed signal execution for debugging"""
        try:
            if not hasattr(self, 'signal_stats'):
                self.signal_stats = {
                    'generated': 0, 'executed': 0, 'failed': 0,
                    'by_strategy': {}, 'recent_signals': [], 'failed_signals': []
                }
            
            # Increment counters
            self.signal_stats['failed'] += 1
            
            strategy = signal.get('strategy', 'unknown')
            if strategy not in self.signal_stats['by_strategy']:
                self.signal_stats['by_strategy'][strategy] = {
                    'generated': 0, 'executed': 0, 'failed': 0
                }
            self.signal_stats['by_strategy'][strategy]['failed'] += 1
            
            # Store failed signals for debugging (last 10)
            failed_record = {
                'signal_id': signal.get('signal_id'),
                'strategy': strategy,
                'symbol': signal.get('symbol'),
                'action': signal.get('action'),
                'confidence': signal.get('confidence'),
                'generated_at': signal.get('generated_at'),
                'failed_at': datetime.now().isoformat(),
                'failure_reason': reason,
                'status': 'FAILED'
            }
            
            self.signal_stats['failed_signals'].append(failed_record)
            if len(self.signal_stats['failed_signals']) > 10:
                self.signal_stats['failed_signals'].pop(0)
                
            self.logger.error(f"📊 SIGNAL FAILED: {signal.get('symbol')} - {reason}")
            self.logger.info(f"📊 FAILURE STATS: Total failed: {self.signal_stats['failed']}")
            
        except Exception as e:
            self.logger.error(f"Error tracking signal failure: {e}")
    
    def get_signal_stats(self) -> Dict:
        """Get signal generation and execution statistics"""
        if not hasattr(self, 'signal_stats'):
            return {
                'generated': 0, 'executed': 0, 'failed': 0,
                'by_strategy': {}, 'recent_signals': [], 'failed_signals': []
            }
        return self.signal_stats.copy()
    
    async def _clear_successful_signals(self, signals: List[Dict], execution_results):
        """Clear signals from strategy instances only if execution was successful"""
        try:
            if not execution_results:
                self.logger.info("⚠️ No execution results - keeping all signals for retry")
                return
            
            # If execution_results is a list of results
            if isinstance(execution_results, list):
                for i, signal in enumerate(signals):
                    if i < len(execution_results) and execution_results[i]:
                        # Execution successful - clear signal from strategy
                        strategy_instance = signal.get('_strategy_instance')
                        symbol_key = signal.get('_symbol_key')
                        if strategy_instance and symbol_key:
                            strategy_instance.current_positions[symbol_key] = None
                            self.logger.info(f"✅ Cleared successful signal: {symbol_key}")
                    else:
                        # Execution failed - keep signal for next cycle
                        self.logger.info(f"⚠️ Keeping failed signal for retry: {signal.get('symbol')}")
            else:
                # Single result or boolean
                if execution_results:
                    # All signals executed successfully
                    for signal in signals:
                        strategy_instance = signal.get('_strategy_instance')
                        symbol_key = signal.get('_symbol_key')
                        if strategy_instance and symbol_key:
                            strategy_instance.current_positions[symbol_key] = None
                            self.logger.info(f"✅ Cleared successful signal: {symbol_key}")
                else:
                    self.logger.info("⚠️ Execution failed - keeping all signals for retry")
                    
        except Exception as e:
            self.logger.error(f"Error clearing signals: {e}")
            # On error, don't clear any signals to be safe

    def _transform_market_data_for_strategies(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform and FILTER market data - send only UNDERLYING symbols to strategies"""
        current_time = datetime.now(self.ist_timezone)
        transformed_data = {}
        
        try:
            # CRITICAL FIX: Use DYNAMIC underlying symbols from autonomous symbol manager
            underlying_symbols = self._get_dynamic_underlying_symbols_for_strategies()
            
            self.logger.info(f"🔍 Filtering {len(raw_data)} symbols → {len(underlying_symbols)} DYNAMIC underlying symbols for strategies")
            
            for symbol, data in raw_data.items():
                try:
                    # DYNAMIC FILTERING: Only process symbols that are in our autonomous underlying list
                    if symbol not in underlying_symbols:
                        continue  # Skip symbols not in our dynamic underlying list
                    
                    # Convert TrueData format to strategy format
                    if isinstance(data, dict):
                        # Extract price data with multiple fallbacks
                        ltp = data.get('ltp', data.get('price', data.get('last_price', 0)))
                        if not ltp or ltp <= 0:
                            continue
                        
                        # Extract volume with multiple fallbacks
                        volume = 0
                        volume_fields = ['volume', 'ttq', 'total_traded_quantity', 'vol', 'day_volume']
                        for field in volume_fields:
                            vol = data.get(field, 0)
                            if vol and vol > 0:
                                volume = int(vol)
                                break
                        
                        # Calculate volume change (required for strategies)
                        prev_volume = self.market_data_history.get(symbol, {}).get('volume', 0)
                        volume_change = volume - prev_volume if prev_volume > 0 else 0
                        volume_change_percent = (volume_change / prev_volume * 100) if prev_volume > 0 else 0
                        
                        # Store current data for next comparison
                        if symbol not in self.market_data_history:
                            self.market_data_history[symbol] = {}
                        self.market_data_history[symbol]['volume'] = volume
                        
                        # Extract OHLC data with fallbacks
                        ohlc = {
                            'open': data.get('open', ltp),
                            'high': data.get('high', ltp),
                            'low': data.get('low', ltp),
                            'close': ltp
                        }
                        
                        # Extract bid/ask with fallbacks
                        bid = data.get('bid', data.get('best_bid', ltp * 0.999))
                        ask = data.get('ask', data.get('best_ask', ltp * 1.001))
                        
                        # Calculate spread
                        spread = ask - bid if ask > bid else 0
                        spread_percent = (spread / ltp * 100) if ltp > 0 else 0
                        
                        # Create strategy-compatible data structure
                        strategy_data = {
                            'symbol': symbol,
                            'price': float(ltp),
                            'ltp': float(ltp),
                            'volume': volume,
                            'volume_change': volume_change,
                            'volume_change_percent': volume_change_percent,
                            'bid': float(bid),
                            'ask': float(ask),
                            'spread': spread,
                            'spread_percent': spread_percent,
                            'open': float(ohlc['open']),
                            'high': float(ohlc['high']),
                            'low': float(ohlc['low']),
                            'close': float(ohlc['close']),
                            'timestamp': current_time.isoformat(),
                            'data_source': 'truedata',
                            'market_depth': data.get('market_depth', {}),
                            'raw_data': data  # Include raw data for debugging
                        }
                        
                        # Add to transformed data
                        transformed_data[symbol] = strategy_data
                        
                        self.logger.debug(f"📊 Transformed {symbol}: ₹{ltp:,.2f} | Vol: {volume:,} (+{volume_change_percent:.1f}%)")
                        
                    else:
                        self.logger.warning(f"⚠️ Invalid data format for {symbol}: {type(data)}")
                        
                except Exception as e:
                    self.logger.error(f"❌ Error transforming data for {symbol}: {e}")
                    continue
            
            self.logger.info(f"📊 Strategy symbols: {list(transformed_data.keys())[:5]}...")
            self.logger.info(f"🎯 Options symbols remain available in TrueData cache for execution pricing")
            return transformed_data
            
        except Exception as e:
            self.logger.error(f"Critical error in data transformation: {e}")
            # CRITICAL FIX: Instead of returning raw_data, return empty dict to force retry
            return {}
    
    def _get_dynamic_underlying_symbols_for_strategies(self) -> set:
        """Get underlying symbols for strategies with ROBUST FALLBACKS"""
        underlying_symbols = set()
        
        try:
            # DYNAMIC APPROACH: Get current symbols from autonomous symbol manager
            from config.truedata_symbols import get_autonomous_symbol_status, get_complete_fo_symbols
            
            # Get current autonomous strategy and symbols with fallback handling
            try:
                status = get_autonomous_symbol_status()
                current_strategy = status.get("current_strategy", "MIXED")
                
                # Get all symbols from current autonomous selection (with fallbacks built-in)
                all_symbols = get_complete_fo_symbols()
                
                # CRITICAL FIX: Validate that we got a reasonable symbol list
                if not all_symbols or len(all_symbols) < 10:
                    self.logger.warning("❌ Dynamic symbol generation returned invalid list, using static fallback")
                    raise Exception("Invalid dynamic symbol list")
                    
            except Exception as dynamic_error:
                self.logger.warning(f"⚠️ Dynamic symbol selection failed: {dynamic_error}")
                self.logger.info("🔄 Using static fallback symbol list")
                
                # STATIC FALLBACK: Use known working symbol list
                all_symbols = [
                    # Core Indices
                    'NIFTY-I', 'BANKNIFTY-I', 'FINNIFTY-I', 'MIDCPNIFTY-I', 'SENSEX-I',
                    
                    # Top 45 F&O Stocks (Most liquid and reliable)
                    'RELIANCE', 'TCS', 'HDFC', 'INFY', 'ICICIBANK', 'HDFCBANK', 'ITC',
                    'BHARTIARTL', 'KOTAKBANK', 'LT', 'SBIN', 'WIPRO', 'AXISBANK',
                    'MARUTI', 'ASIANPAINT', 'HCLTECH', 'POWERGRID', 'NTPC', 'COALINDIA',
                    'TECHM', 'TATAMOTORS', 'ADANIPORTS', 'ULTRACEMCO', 'NESTLEIND',
                    'TITAN', 'BAJFINANCE', 'M&M', 'DRREDDY', 'SUNPHARMA', 'CIPLA',
                    'APOLLOHOSP', 'DIVISLAB', 'HINDUNILVR', 'BRITANNIA', 'DABUR',
                    'ADANIGREEN', 'ADANITRANS', 'ADANIPOWER', 'JSWSTEEL', 'TATASTEEL',
                    'HINDALCO', 'VEDL', 'GODREJCP', 'BAJAJFINSV', 'BAJAJ-AUTO',
                    'HEROMOTOCO', 'EICHERMOT', 'TVSMOTOR', 'INDIGO', 'SPICEJET'
                ]
                current_strategy = "STATIC_FALLBACK"
            
            # Filter to get only underlying symbols (not options contracts)
            for symbol in all_symbols:
                # Include if it's an underlying symbol (not an options contract)
                # FIXED: More robust options detection
                if not self._is_options_contract(symbol):
                    underlying_symbols.add(symbol)
            
            self.logger.info(f"🤖 UNDERLYING SYMBOLS: {len(underlying_symbols)} symbols from strategy: {current_strategy}")
            self.logger.debug(f"📋 Sample underlying symbols: {list(underlying_symbols)[:10]}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get dynamic underlying symbols: {e}")
            
            # FINAL FALLBACK: Minimal core symbols that should always work
            underlying_symbols = {
                'NIFTY-I', 'BANKNIFTY-I', 'FINNIFTY-I', 'MIDCPNIFTY-I', 'SENSEX-I',
                'RELIANCE', 'TCS', 'HDFC', 'INFY', 'ICICIBANK', 'HDFCBANK', 'ITC',
                'BHARTIARTL', 'KOTAKBANK', 'LT', 'SBIN', 'WIPRO', 'AXISBANK',
                'MARUTI', 'ASIANPAINT'
            }
            self.logger.warning(f"🔄 Using MINIMAL fallback underlying symbols: {len(underlying_symbols)} symbols")
        
        return underlying_symbols
    
    def _is_options_contract(self, symbol: str) -> bool:
        """Check if symbol is an options contract (more robust detection)"""
        if not symbol or not isinstance(symbol, str):
            return False
        
        # CRITICAL FIX: Only consider CE/PE at the END of symbol as options
        if symbol.endswith('CE') or symbol.endswith('PE'):
            # Additional check: Options contracts should have expiry patterns
            # Look for month abbreviations (JAN, FEB, etc.) in the symbol
            month_patterns = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 
                             'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
            
            has_month = any(month in symbol for month in month_patterns)
            
            # If it ends with CE/PE AND has a month pattern, it's likely an options contract
            if has_month:
                return True
            
            # Additional check: If it has numbers before CE/PE, it's likely strike price
            # Example: NIFTY25JUL24000CE - has numbers (24000) before CE
            import re
            has_strike = bool(re.search(r'\d+(?:CE|PE)$', symbol))
            if has_strike:
                return True
        
        # FIXED: Don't flag stocks that just contain month names (like RELIANCE) as options
        # Only flag if they actually end with CE/PE and have proper options structure
        return False

    async def _load_strategies(self):
        """Load and initialize trading strategies"""
        try:
            # Clear existing strategies to prevent duplicates
            self.strategies.clear()
            self.active_strategies.clear()
            
            # FIXED: Original strategies only - no emergency systems
            strategy_configs = {
                'momentum_surfer': {'name': 'EnhancedMomentumSurfer', 'config': {}},
                'volatility_explosion': {'name': 'EnhancedVolatilityExplosion', 'config': {}},
                'volume_profile_scalper': {'name': 'EnhancedVolumeProfileScalper', 'config': {}},
                'regime_adaptive_controller': {'name': 'RegimeAdaptiveController', 'config': {}},
                'confluence_amplifier': {'name': 'ConfluenceAmplifier', 'config': {}}
            }
            
            self.logger.info(f"Loading {len(strategy_configs)} trading strategies (news_impact_scalper removed for debugging)...")
            
            for strategy_key, strategy_info in strategy_configs.items():
                try:
                    # Import strategy class
                    if strategy_key == 'momentum_surfer':
                        from strategies.momentum_surfer import EnhancedMomentumSurfer
                        strategy_instance = EnhancedMomentumSurfer(strategy_info['config'])
                    elif strategy_key == 'volatility_explosion':
                        from strategies.volatility_explosion import EnhancedVolatilityExplosion
                        strategy_instance = EnhancedVolatilityExplosion(strategy_info['config'])
                    elif strategy_key == 'volume_profile_scalper':
                        from strategies.volume_profile_scalper import EnhancedVolumeProfileScalper
                        strategy_instance = EnhancedVolumeProfileScalper(strategy_info['config'])
                    elif strategy_key == 'regime_adaptive_controller':
                        from strategies.regime_adaptive_controller import RegimeAdaptiveController
                        strategy_instance = RegimeAdaptiveController(strategy_info['config'])
                    elif strategy_key == 'confluence_amplifier':
                        from strategies.confluence_amplifier import ConfluenceAmplifier
                        strategy_instance = ConfluenceAmplifier(strategy_info['config'])
                    else:
                        continue
                    
                    # Initialize strategy
                    await strategy_instance.initialize()
                    
                    # Store strategy instance
                    self.strategies[strategy_key] = {
                        'name': strategy_key,
                        'instance': strategy_instance,
                        'active': True,
                        'last_signal': None
                    }
                    self.active_strategies.append(strategy_key)
                    self.logger.info(f"✓ Loaded and initialized strategy: {strategy_key}")
                    
                except Exception as e:
                    self.logger.error(f"✗ Failed to load strategy {strategy_key}: {e}")
            
            self.logger.info(f"✓ Successfully loaded {len(self.strategies)}/{len(strategy_configs)} trading strategies")
            
        except Exception as e:
            self.logger.error(f"Error loading strategies: {e}")

    async def start_trading(self) -> bool:
        """Start autonomous trading system"""
        try:
            self.logger.info("🚀 Starting autonomous trading...")
            
            # Ensure system is initialized
            if not self.is_initialized:
                self.logger.info("🔄 Initializing system first...")
                init_success = await self.initialize()
                if not init_success:
                    self.logger.error("❌ Failed to initialize system")
                    return False
            
            # Start the trading loop
            self.is_running = True
            
            # CRITICAL FIX: Ensure active_strategies list is properly populated
            self.active_strategies.clear()
            
            # Activate all loaded strategies and add to active_strategies list
            for strategy_key, strategy_info in self.strategies.items():
                strategy_info['active'] = True
                self.active_strategies.append(strategy_key)
                self.logger.info(f"✅ Activated strategy: {strategy_key}")
            
            # CRITICAL FIX: Verify active_strategies is populated
            if not self.active_strategies:
                self.logger.error("❌ No strategies in active_strategies list - forcing reload")
                # Force reload strategies if active_strategies is empty
                await self._load_strategies()
                for strategy_key in self.strategies.keys():
                    if strategy_key not in self.active_strategies:
                        self.active_strategies.append(strategy_key)
            
            # CRITICAL FIX: Update components dictionary with active status
            self.components.update({
                'system_ready': True,
                'is_active': True,
                'session_id': f"session_{int(time_module.time())}",
                'start_time': datetime.now().isoformat(),
                'strategy_engine': len(self.strategies) > 0,
                'market_data': bool(self.truedata_cache)
            })
            
            self.logger.info(f"✅ Active strategies list: {self.active_strategies}")
            
            # Start market data processing
            if not hasattr(self, '_trading_task') or self._trading_task is None:
                self._trading_task = asyncio.create_task(self._trading_loop())
                self.logger.info("🔄 Started trading loop")
            
            # CRITICAL FIX: Sync capital before trading starts
            if self.capital_sync:
                try:
                    await self.capital_sync.sync_all_accounts()
                    self.logger.info("✅ Dynamic capital sync completed - using real broker funds")
                except Exception as e:
                    self.logger.warning(f"⚠️ Capital sync failed, using defaults: {e}")
            
            # Start Position Monitor for continuous auto square-off
            if self.position_monitor:
                try:
                    await self.position_monitor.start_monitoring()
                    self.logger.info("🔄 Position Monitor started - continuous auto square-off active")
                except Exception as e:
                    self.logger.error(f"❌ Failed to start Position Monitor: {e}")
            else:
                self.logger.warning("⚠️ Position Monitor not available - auto square-off monitoring disabled")
            
            # CRITICAL NEW: Start real-time Zerodha data synchronization
            if self.trade_engine and hasattr(self.trade_engine, 'start_real_time_sync'):
                try:
                    await self.trade_engine.start_real_time_sync()
                    self.logger.info("🔄 Real-time Zerodha sync started - actual trade/position data")
                except Exception as e:
                    self.logger.error(f"❌ Failed to start real-time sync: {e}")
            else:
                self.logger.warning("⚠️ Real-time sync not available - using local trade data only")
            
            self.logger.info(f"✅ Autonomous trading started with {len(self.active_strategies)} active strategies")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start trading: {e}")
            return False
    
    async def disable_trading(self) -> bool:
        """Stop autonomous trading system"""
        try:
            self.logger.info("🛑 Stopping autonomous trading...")
            
            # Stop the trading loop
            self.is_running = False
            
            # Deactivate all strategies
            for strategy_key, strategy_info in self.strategies.items():
                strategy_info['active'] = False
                self.logger.info(f"🔴 Deactivated strategy: {strategy_key}")
            
            # Cancel trading task if running
            if hasattr(self, '_trading_task') and self._trading_task is not None:
                self._trading_task.cancel()
                self._trading_task = None
                self.logger.info("🛑 Cancelled trading loop")
            
            # Stop Position Monitor
            if self.position_monitor:
                try:
                    await self.position_monitor.stop_monitoring()
                    self.logger.info("🛑 Position Monitor stopped")
                except Exception as e:
                    self.logger.error(f"❌ Error stopping Position Monitor: {e}")
            
            self.logger.info("✅ Autonomous trading stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to stop trading: {e}")
            return False
    
    async def get_trading_status(self) -> Dict[str, Any]:
        """Get comprehensive trading status"""
        try:
            # Ensure active_strategies is always a list
            if not isinstance(self.active_strategies, list):
                self.active_strategies = []
            
            # Check if system is properly initialized
            system_ready = (
                self.is_initialized and 
                self.is_running and 
                len(self.active_strategies) > 0 and
                bool(self.components.get('trade_engine'))  # Fix: Check if trade_engine exists (not False)
            )
            
            # Get strategy details
            strategy_details = []
            for strategy_key, strategy_info in self.strategies.items():
                strategy_details.append({
                    'name': strategy_key,
                    'active': strategy_info.get('active', False),
                    'status': 'running' if strategy_info.get('active', False) else 'inactive',
                    'initialized': 'instance' in strategy_info
                })
            
            # Get actual trading data from trade engine and position tracker
            total_trades = 0
            daily_pnl = 0.0
            active_positions = 0
            
            # Get trades from trade engine
            if self.trade_engine:
                try:
                    # CRITICAL FIX: Use get_statistics() instead of get_status() for full-featured TradeEngine
                    if hasattr(self.trade_engine, 'get_statistics'):
                        trade_engine_status = self.trade_engine.get_statistics()
                        total_trades = trade_engine_status.get('executed_trades', 0)
                    elif hasattr(self.trade_engine, 'get_status'):
                        trade_engine_status = await self.trade_engine.get_status()
                        total_trades = trade_engine_status.get('executed_trades', 0)
                    else:
                        self.logger.warning("Trade engine has no get_statistics or get_status method")
                        total_trades = 0
                except Exception as e:
                    self.logger.warning(f"Could not get trade engine status: {e}")
                    total_trades = 0
            
            # Get positions from position tracker
            if self.position_tracker:
                try:
                    positions = getattr(self.position_tracker, 'positions', {})
                    active_positions = len(positions)
                    
                    # Calculate daily P&L from positions
                    for position in positions.values():
                        if isinstance(position, dict):
                            daily_pnl += position.get('unrealized_pnl', 0.0)
                        else:
                            daily_pnl += getattr(position, 'unrealized_pnl', 0.0)
                except Exception as e:
                    self.logger.warning(f"Could not get position data: {e}")
            
            # Get market status
            market_open = self._is_market_open()
            
            # Get risk status - FIXED: Proper risk assessment
            risk_status = {
                'max_daily_loss': 100000,
                'max_position_size': 1000000,
                'current_positions': active_positions,
                'daily_pnl': daily_pnl,
                'status': self._get_risk_status(daily_pnl, active_positions, system_ready)
            }
            
            return {
                'is_running': self.is_running,
                'is_active': self.is_running,  # Frontend expects is_active
                'system_ready': system_ready,
                'active_strategies': self.active_strategies,  # Return list not count
                'active_strategies_count': len(self.active_strategies),  # Add count separately
                'strategy_details': strategy_details,
                'total_trades': total_trades,  # CRITICAL FIX: Add actual trade count
                'daily_pnl': daily_pnl,  # CRITICAL FIX: Add actual P&L
                'active_positions': active_positions,  # CRITICAL FIX: Add position count
                'market_status': 'OPEN' if market_open else 'CLOSED',  # CRITICAL FIX: Add market status
                'session_id': self.components.get('session_id', f"session_{int(time_module.time())}"),
                'start_time': self.components.get('start_time'),
                'last_heartbeat': datetime.now().isoformat(),
                'risk_status': risk_status,
                'components': self.components.copy(),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting trading status: {e}")
            return {
                'is_running': False,
                'is_active': False,
                'system_ready': False,
                'active_strategies': [],
                'active_strategies_count': 0,
                'total_trades': 0,
                'daily_pnl': 0.0,
                'active_positions': 0,
                'market_status': 'UNKNOWN',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive orchestrator status"""
        try:
            # Get trading status
            trading_status = await self.get_trading_status()
            
            # Get component status
            component_status = self.components.copy()
            
            # Get market data status
            market_data_status = {
                'connected': self.components.get('truedata_cache', False),
                'symbols_active': 0,
                'last_update': None
            }
            
            # Get strategy status
            strategy_status = {
                'total_strategies': len(self.strategies),
                'active_strategies': len(self.active_strategies),
                'strategy_list': list(self.strategies.keys())
            }
            
            return {
                'initialized': self.is_initialized,
                'trading_status': trading_status,
                'component_status': component_status,
                'market_data_status': market_data_status,
                'strategy_status': strategy_status,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting orchestrator status: {e}")
            return {
                'initialized': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def initialize_system(self) -> Dict[str, Any]:
        """Initialize the entire trading system"""
        try:
            self.logger.info("🚀 Initializing complete trading system...")
            
            # Initialize orchestrator
            success = await self.initialize()
            
            if success:
                return {
                    'success': True,
                    'message': 'Trading system initialized successfully',
                    'components': self.components.copy(),
                    'strategies': len(self.strategies),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'message': 'Trading system initialization failed',
                    'components': self.components.copy(),
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"System initialization failed: {e}")
            return {
                'success': False,
                'message': f'System initialization failed: {e}',
                'timestamp': datetime.now().isoformat()
            }

    async def _trading_loop(self):
        """Main trading loop - processes market data and generates signals"""
        self.logger.info("🔄 Starting trading loop...")
        
        while self.is_running:
            try:
                # Process market data
                await self._process_market_data()
                
                # Small delay to prevent overwhelming the system
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                self.logger.info("🛑 Trading loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
        
        self.logger.info("🛑 Trading loop stopped")

    def _is_market_open(self) -> bool:
        """Check if market is currently open (IST timezone)"""
        try:
            now = datetime.now(self.ist_timezone)
            current_time = now.time()
            
            # Market hours: 9:15 AM to 3:30 PM IST
            market_open = time(9, 15)
            market_close = time(15, 30)
            
            # Check if it's a weekday (Monday=0, Sunday=6)
            is_weekday = now.weekday() < 5
            
            # Check if current time is within market hours
            is_market_hours = market_open <= current_time <= market_close
            
            return is_weekday and is_market_hours
            
        except Exception as e:
            self.logger.error(f"Error checking market hours: {e}")
            return True  # Default to open to avoid blocking trading

    def _can_start_trading(self) -> bool:
        """
        Check if autonomous trading can start
        
        Returns:
            bool: True if trading can start, False otherwise
        """
        try:
            # CRITICAL FIX: Always allow trading start when markets are open
            import datetime
            now = datetime.datetime.now()
            
            # Check if we're in market hours (9:15 AM to 3:30 PM IST)
            market_start = now.replace(hour=9, minute=15, second=0, microsecond=0)
            market_end = now.replace(hour=15, minute=30, second=0, microsecond=0)
            
            # Check if paper trading is enabled - bypass all checks
            paper_trading_enabled = os.getenv('PAPER_TRADING', 'false').lower() == 'true'
            
            if paper_trading_enabled:
                logger.info("🎯 Paper trading mode enabled - bypassing all checks")
                return True
            
            # For live trading, check market hours
            if not (market_start <= now <= market_end):
                logger.info(f"❌ Market is closed - current time: {now.strftime('%H:%M:%S')}")
                return False
            
            # CRITICAL FIX: Allow trading even with degraded OrderManager
            if not self.trade_engine:
                logger.warning("❌ TradeEngine not initialized - cannot start trading")
                return False
            
            # CRITICAL FIX: Allow trading even without strategies initially
            if not self.strategies:
                logger.warning("⚠️ No strategies loaded yet - will load during startup")
                # Don't return False - allow startup to continue
            
            logger.info("✅ All conditions met for trading startup")
            return True
            
        except Exception as e:
            logger.error(f"Error checking trading conditions: {e}")
            return False

    @classmethod
    async def get_instance(cls):
        """Get singleton instance of TradingOrchestrator"""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance.initialize()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (for testing)"""
        cls._instance = None

    def __del__(self):
        """Cleanup when orchestrator is destroyed"""
        if hasattr(self, '_trading_task') and self._trading_task is not None:
            self._trading_task.cancel()



    async def _start_market_data_to_position_tracker_bridge(self):
        """Connect market data updates to position tracker for real-time P&L"""
        try:
            if not self.position_tracker:
                self.logger.warning("⚠️ Position tracker not available for market data bridge")
                return
                
            # Start background task to update positions with market prices
            asyncio.create_task(self._update_positions_with_market_data())
            self.logger.info("✅ Market data to position tracker bridge started")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start market data bridge: {e}")

    async def _update_positions_with_market_data(self):
        """Background task to update position tracker with real-time market prices"""
        while self.running and self.is_running:
            try:
                if not self.position_tracker:
                    await asyncio.sleep(10)
                    continue
                
                # Get market data from TrueData API
                market_prices = {}
                try:
                    # Use the same method as orchestrator uses for market data
                    market_data_response = await self._get_market_data_from_api()
                    if market_data_response and market_data_response.get('data'):
                        for symbol, data in market_data_response['data'].items():
                            if isinstance(data, dict) and 'ltp' in data:
                                ltp = data.get('ltp', 0)
                                if ltp and ltp > 0:
                                    market_prices[symbol] = float(ltp)
                    
                    self.logger.debug(f"📊 Retrieved {len(market_prices)} market prices for position updates")
                    
                except Exception as e:
                    self.logger.error(f"❌ Error getting market data for positions: {e}")
                    # Fallback: try direct TrueData import
                    try:
                        from data.truedata_client import live_market_data
                        for symbol, data in live_market_data.items():
                            ltp = data.get('ltp', 0)
                            if ltp and ltp > 0:
                                market_prices[symbol] = float(ltp)
                    except ImportError:
                        pass
                
                # Update position tracker with current prices
                if market_prices:
                    await self.position_tracker.update_market_prices(market_prices)
                    self.logger.debug(f"📊 Updated {len(market_prices)} market prices in position tracker")
                
                # Update every 30 seconds
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error(f"❌ Error updating positions with market data: {e}")
                await asyncio.sleep(5)

    def _get_risk_status(self, daily_pnl: float, active_positions: int, system_ready: bool) -> str:
        """Determine risk status based on current conditions"""
        try:
            # Check for critical risk conditions
            if abs(daily_pnl) > 50000:  # Major daily loss/gain
                return 'critical'
            
            if abs(daily_pnl) > 25000:  # Significant daily movement
                return 'warning'
            
            if active_positions > 10:  # Too many positions
                return 'warning'
            
            if not system_ready:  # System not fully ready
                return 'monitoring'
            
            # All good
            return 'healthy'
            
        except Exception as e:
            self.logger.error(f"Error determining risk status: {e}")
            return 'unknown'


# Global function to get orchestrator instance
async def get_orchestrator() -> TradingOrchestrator:
    """Get the singleton TradingOrchestrator instance"""
    return await TradingOrchestrator.get_instance()


# Global variable to store orchestrator instance
_orchestrator_instance = None


def set_orchestrator_instance(instance: Optional[TradingOrchestrator]):
    """Set the global orchestrator instance"""
    global _orchestrator_instance
    _orchestrator_instance = instance


def get_orchestrator_instance() -> Optional[TradingOrchestrator]:
    """Get the global orchestrator instance"""
    return _orchestrator_instance
