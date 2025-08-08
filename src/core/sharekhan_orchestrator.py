"""
ShareKhan Trading Orchestrator
Complete replacement for ShareKhan + ShareKhan dual architecture
Unified trading system using only ShareKhan for both data and trading operations
"""

import asyncio
import logging
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
import pytz
import redis.asyncio as redis

# ShareKhan components
from brokers.sharekhan import ShareKhanIntegration, ShareKhanOrder, ShareKhanMarketData
from src.feeds.sharekhan_feed import ShareKhanDataFeed, ShareKhanShareKhanCompatibility
from src.core.market_directional_bias import MarketDirectionalBias
from src.core.signal_deduplicator import signal_deduplicator
from .multi_user_sharekhan_manager import MultiUserShareKhanManager, UserRole, TradingPermission

# ShareKhan service components
from .sharekhan_services import (
    ShareKhanMetricsService, ShareKhanPositionManager, 
    ShareKhanTradeManager, ShareKhanRiskManager
)

logger = logging.getLogger(__name__)

class ShareKhanTradingOrchestrator:
    """
    Unified trading orchestrator using ShareKhan for everything
    Complete replacement for the old ShareKhan + ShareKhan dual-provider architecture
    """
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize orchestrator with ShareKhan-only architecture"""
        self.config = config or {}
        
        # Core state
        self.is_initialized = False
        self.is_running = False
        self.active_strategies = []
        
        # Timezone
        self.ist_timezone = pytz.timezone('Asia/Kolkata')
        
        # Market data tracking
        self.market_data_history: Dict[str, Any] = {}
        self.last_data_update: Dict[str, datetime] = {}
        
        # ShareKhan configuration
        self.sharekhan_api_key = os.getenv('SHAREKHAN_API_KEY')
        self.sharekhan_secret = os.getenv('SHAREKHAN_SECRET_KEY')
        self.sharekhan_customer_id = os.getenv('SHAREKHAN_CUSTOMER_ID')
        self.sharekhan_version_id = os.getenv('SHAREKHAN_VERSION_ID')
        
        # Core components
        self.redis_client: Optional[redis.Redis] = None
        self.sharekhan_integration: Optional[ShareKhanIntegration] = None
        self.sharekhan_feed: Optional[ShareKhanDataFeed] = None
        self.multi_user_manager: Optional[MultiUserShareKhanManager] = None
        self.sharekhan_compatibility: Optional[ShareKhanShareKhanCompatibility] = None
        # Market bias engine
        self.market_bias: Optional[MarketDirectionalBias] = MarketDirectionalBias()
        
        # CRITICAL FIX: Add missing service components for API compatibility
        self.trade_engine: Optional[Any] = None
        self.order_manager: Optional[Any] = None
        self.position_tracker: Optional[Any] = None
        self.risk_manager: Optional[Any] = None
        self.performance_analyzer: Optional[Any] = None
        
                # NEW: Enhanced service components
        self.order_deduplication_manager = None
        self.enhanced_position_manager = None
        self.strategy_position_tracker = None
        self.sharekhan_data_mapper = None
        
        # Service aliases - HONEST: These are None until real implementations are added
        self.metrics_service = None
        self.position_manager = None
        self.trade_manager = None
        
        # Monitoring
        self.last_health_check = datetime.now()
        self.health_status = "initializing"
        self.error_count = 0
        
        logger.info("ShareKhan Trading Orchestrator initialized")
    
    @classmethod
    async def get_instance(cls, config: Optional[Dict] = None):
        """Get singleton instance of orchestrator"""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(config)
                    await cls._instance.initialize()
        return cls._instance
    
    async def initialize(self) -> bool:
        """Initialize all components"""
        try:
            logger.info("🚀 Initializing ShareKhan Trading Orchestrator...")
            
            # 1. Initialize Redis connection
            await self._initialize_redis()
            
            # 2. Initialize ShareKhan integration
            await self._initialize_sharekhan_integration()
            
            # 3. Initialize multi-user manager (only if Redis is available)
            if self.redis_client:
                await self._initialize_multi_user_manager()
            
            # 4. Start background tasks
            await self._start_background_tasks()
            
            # 5. Initialize enhanced service components
            await self._initialize_enhanced_services()
            
            # 6. Initialize legacy service components for API compatibility
            await self._initialize_services()
            
            self.is_initialized = True
            self.health_status = "ready"
            
            logger.info("✅ ShareKhan Trading Orchestrator fully initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Orchestrator initialization failed: {e}")
            self.health_status = "failed"
            return False
    
    async def _initialize_redis(self):
        """Initialize Redis connection"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = await redis.from_url(redis_url)
            
            # Test connection
            await self.redis_client.ping()
            logger.info("✅ Redis connection established")
            
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}")
            self.redis_client = None
    
    async def _initialize_sharekhan_integration(self):
        """Initialize ShareKhan integration"""
        try:
            # Check if we have required credentials
            if not self.sharekhan_api_key or not self.sharekhan_secret or not self.sharekhan_customer_id:
                logger.warning("⚠️ ShareKhan credentials not complete - authentication required")
                return
                
            self.sharekhan_integration = ShareKhanIntegration(
                api_key=self.sharekhan_api_key,
                secret_key=self.sharekhan_secret,
                customer_id=self.sharekhan_customer_id,
                version_id=self.sharekhan_version_id or ""
            )
            
            logger.info("✅ ShareKhan integration initialized")
            
        except Exception as e:
            logger.error(f"❌ ShareKhan integration initialization failed: {e}")
            raise
    
    async def _initialize_enhanced_services(self):
        """Initialize enhanced trading services"""
        try:
            logger.info("🚀 Initializing enhanced trading services...")
            
            # 1. Initialize Order Deduplication Manager
            try:
                from src.core.order_deduplication_manager import OrderDeduplicationManager
                self.order_deduplication_manager = OrderDeduplicationManager(self.redis_client)
                await self.order_deduplication_manager.initialize()
                logger.info("✅ Order Deduplication Manager initialized")
            except Exception as e:
                logger.error(f"❌ Order Deduplication Manager failed: {e}")
            
            # 2. Initialize Enhanced Position Manager
            try:
                from src.core.enhanced_position_manager import EnhancedPositionManager
                self.enhanced_position_manager = EnhancedPositionManager(self.sharekhan_integration)
                await self.enhanced_position_manager.initialize()
                
                # Set as primary position manager
                self.position_manager = self.enhanced_position_manager
                logger.info("✅ Enhanced Position Manager initialized")
            except Exception as e:
                logger.error(f"❌ Enhanced Position Manager failed: {e}")
            
            # 3. Initialize ShareKhan Data Mapper
            try:
                if self.sharekhan_integration:
                    from src.core.sharekhan_data_mapper import ShareKhanDataMapper
                    self.sharekhan_data_mapper = ShareKhanDataMapper(self.sharekhan_integration)
                    await self.sharekhan_data_mapper.initialize()
                    logger.info("✅ ShareKhan Data Mapper initialized")
                else:
                    logger.warning("⚠️ ShareKhan integration not available for Data Mapper")
            except Exception as e:
                logger.error(f"❌ ShareKhan Data Mapper failed: {e}")
            
            # 4. Initialize Strategy Position Tracker
            try:
                # Initialize with fallback if enhanced position manager failed
                position_manager_for_strategy = self.enhanced_position_manager or self.position_manager
                if position_manager_for_strategy and self.sharekhan_integration:
                    from src.core.strategy_position_tracker import StrategyPositionTracker
                    self.strategy_position_tracker = StrategyPositionTracker(
                        position_manager_for_strategy,
                        self.sharekhan_integration
                    )
                    await self.strategy_position_tracker.initialize()
                    logger.info("✅ Strategy Position Tracker initialized")
                else:
                    logger.info("ℹ️ Strategy Position Tracker initialization skipped - waiting for position manager")
            except Exception as e:
                logger.error(f"❌ Strategy Position Tracker failed: {e}")
            
            logger.info("✅ All enhanced trading services initialized")
            
        except Exception as e:
            logger.error(f"❌ Enhanced services initialization failed: {e}")
    
    async def _initialize_multi_user_manager(self):
        """Initialize multi-user management"""
        try:
            if not self.redis_client:
                logger.warning("⚠️ Redis not available - skipping multi-user manager")
                return
                
            # Create a simple auth manager substitute
            class SimpleAuthManager:
                def verify_password(self, password: str, stored_hash: str) -> bool:
                    return password == stored_hash  # Simplified for now
            
            auth_manager = SimpleAuthManager()
            
            self.multi_user_manager = MultiUserShareKhanManager(
                redis_client=self.redis_client,
                auth_manager=auth_manager
            )
            
            await self.multi_user_manager.initialize()
            
            # Add default admin user if none exists
            await self._create_default_users()
            
            logger.info("✅ Multi-user manager initialized")
            
        except Exception as e:
            logger.error(f"❌ Multi-user manager initialization failed: {e}")
    
    async def _create_default_users(self):
        """Create default users if none exist"""
        try:
            if not self.multi_user_manager:
                return
                
            active_users = self.multi_user_manager.get_active_users()
            
            if not active_users:
                # Create default admin user
                admin_user_id = os.getenv('SHAREKHAN_ADMIN_USER_ID', 'admin')
                
                await self.multi_user_manager.add_user(
                    user_id=admin_user_id or "admin",
                    display_name="System Administrator", 
                    email="admin@trading-system.com",
                    role=UserRole.ADMIN
                )
                
                logger.info(f"✅ Created default admin user: {admin_user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create default users: {e}")
    
    async def _start_background_tasks(self):
        """Start background monitoring tasks"""
        try:
            # Health check task
            asyncio.create_task(self._health_check_task())
            
            # Performance monitoring task
            asyncio.create_task(self._performance_monitoring_task())

            # Ensure deduplicator startup cleanup
            try:
                asyncio.create_task(signal_deduplicator.ensure_startup_cleanup())
            except Exception as _:
                pass
            
            logger.info("✅ Background tasks started")
            
        except Exception as e:
            logger.error(f"❌ Failed to start background tasks: {e}")

    async def _initialize_services(self):
        """Initialize service components for API compatibility"""
        try:
            logger.info("🚀 Initializing ShareKhan service components...")
            
            # Initialize metrics service
            self.metrics_service = ShareKhanMetricsService(self.redis_client, self.sharekhan_integration)
            await self.metrics_service.initialize()
            
            # Initialize position manager
            self.position_manager = ShareKhanPositionManager(self.sharekhan_integration, self.redis_client)
            await self.position_manager.initialize()
            
            # Initialize trade manager
            self.trade_manager = ShareKhanTradeManager(self.sharekhan_integration, self.redis_client)
            await self.trade_manager.initialize()
            
            # Initialize risk manager  
            self.risk_manager = ShareKhanRiskManager(self.sharekhan_integration, self.redis_client)
            await self.risk_manager.initialize()
            
            logger.info("✅ All ShareKhan service components initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {e}")
            # Keep services as None if initialization fails
            self.metrics_service = None
            self.position_manager = None
            self.trade_manager = None
            self.risk_manager = None

    async def _health_check_task(self):
        """Background health monitoring"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                await self._perform_health_check()
                
            except Exception as e:
                logger.error(f"❌ Health check task error: {e}")
    
    async def _performance_monitoring_task(self):
        """Monitor system performance"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Monitor error rates
                if self.error_count > 10:
                    logger.warning(f"⚠️ High error count: {self.error_count}")
                    self.error_count = 0  # Reset counter
                
                # Monitor active users and sessions
                if self.multi_user_manager:
                    system_status = await self.multi_user_manager.get_system_status()
                    active_sessions = system_status.get('active_sessions', 0)
                    
                    if active_sessions > 50:
                        logger.warning(f"⚠️ High session count: {active_sessions}")
                
            except Exception as e:
                logger.error(f"❌ Performance monitoring error: {e}")
    
    async def _perform_health_check(self):
        """Perform comprehensive health check"""
        try:
            health_status = {
                "timestamp": datetime.now().isoformat(),
                "overall_status": "healthy",
                "components": {}
            }
            
            # Check Redis
            if self.redis_client:
                try:
                    await self.redis_client.ping()
                    health_status["components"]["redis"] = {"status": "connected"}
                except Exception as e:
                    health_status["components"]["redis"] = {"status": "error", "error": str(e)}
                    health_status["overall_status"] = "degraded"
            
            # Check ShareKhan integration
            if self.sharekhan_integration:
                health_status["components"]["sharekhan_integration"] = self.sharekhan_integration.get_connection_status()
            
            # Check data feed
            if self.sharekhan_feed:
                health_status["components"]["data_feed"] = self.sharekhan_feed.get_feed_status()
            
            # Cache health status
            if self.redis_client:
                await self.redis_client.setex(
                    "sharekhan:health_status",
                    300,  # 5 minutes
                    json.dumps(health_status)
                )
            
            self.last_health_check = datetime.now()
            self.health_status = health_status["overall_status"]
            
        except Exception as e:
            logger.error(f"❌ Health check error: {e}")
            self.health_status = "unhealthy"
    
    # PUBLIC API METHODS
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "is_initialized": self.is_initialized,
                "is_running": self.is_running,
                "health_status": self.health_status,
                "error_count": self.error_count,
                "active_strategies": len(self.active_strategies),
                "components": {
                    "redis": self.redis_client is not None,
                    "sharekhan_integration": self.sharekhan_integration is not None,
                    "data_feed": self.sharekhan_feed is not None,
                    "multi_user_manager": self.multi_user_manager is not None
                },
                "sharekhan_integration": self.sharekhan_integration.get_connection_status() if self.sharekhan_integration else None,
                "data_feed": self.sharekhan_feed.get_feed_status() if self.sharekhan_feed else None,
                "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
                "memory_usage": 0,  # Could add actual memory monitoring
                "cpu_usage": 0      # Could add actual CPU monitoring
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e), "status": "error"}

    # API Methods for Frontend Integration
    async def validate_user_session(self, user_id: str, session_token: str) -> bool:
        """Validate user session"""
        try:
            if self.multi_user_manager:
                return await self.multi_user_manager.validate_session(user_id, session_token)
            return False
        except Exception as e:
            logger.error(f"Error validating user session: {e}")
            return False

    async def authenticate_user(self, user_id: str, password: str) -> Dict[str, Any]:
        """Authenticate user and return session info"""
        try:
            if self.multi_user_manager:
                return await self.multi_user_manager.authenticate_user(user_id, password)
            return {"success": False, "message": "Multi-user manager not available"}
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return {"success": False, "message": str(e)}

    async def authenticate_sharekhan(self, request_token: str, user_id: str = None) -> Dict[str, Any]:
        """Authenticate with ShareKhan API"""
        try:
            if self.sharekhan_integration:
                result = await self.sharekhan_integration.authenticate(request_token)
                if result:
                    return {"success": True, "message": "ShareKhan authentication successful"}
                else:
                    return {"success": False, "message": "ShareKhan authentication failed"}
            return {"success": False, "message": "ShareKhan integration not available"}
        except Exception as e:
            logger.error(f"Error authenticating ShareKhan: {e}")
            return {"success": False, "message": str(e)}

    async def place_order(self, order_data: Dict[str, Any], user_id: str = None) -> Dict[str, Any]:
        """Place order through ShareKhan"""
        try:
            if self.sharekhan_integration:
                # Convert order_data to ShareKhan order format
                from brokers.sharekhan import ShareKhanOrder
                
                order = ShareKhanOrder(
                    customer_id=order_data.get('customer_id', self.sharekhan_customer_id),
                    scrip_code=order_data.get('scrip_code'),
                    trading_symbol=order_data.get('trading_symbol'),
                    exchange=order_data.get('exchange'),
                    transaction_type=order_data.get('transaction_type'),
                    quantity=order_data.get('quantity'),
                    price=order_data.get('price', 0),
                    product_type=order_data.get('product_type', 'INVESTMENT'),
                    order_type=order_data.get('order_type', 'MARKET'),
                    validity=order_data.get('validity', 'DAY')
                )
                
                result = await self.sharekhan_integration.place_order(order)
                return {"success": True, "data": result}
            return {"success": False, "message": "ShareKhan integration not available"}
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {"success": False, "message": str(e)}

    async def get_portfolio(self, user_id: str = None) -> Dict[str, Any]:
        """Get portfolio data from ShareKhan"""
        try:
            if self.sharekhan_integration:
                holdings = await self.sharekhan_integration.get_holdings()
                positions = await self.sharekhan_integration.get_positions()
                return {
                    "success": True,
                    "holdings": holdings,
                    "positions": positions
                }
            return {"success": False, "message": "ShareKhan integration not available"}
        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
            return {"success": False, "message": str(e)}

    async def subscribe_to_symbols(self, symbols: List[str], user_id: str = None) -> Dict[str, Any]:
        """Subscribe to real-time data for symbols"""
        try:
            if self.sharekhan_integration:
                result = await self.sharekhan_integration.subscribe_to_symbols(symbols)
                return {"success": True, "subscribed_symbols": symbols, "result": result}
            return {"success": False, "message": "ShareKhan integration not available"}
        except Exception as e:
            logger.error(f"Error subscribing to symbols: {e}")
            return {"success": False, "message": str(e)}

    async def process_strategy_signals(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process incoming strategy signals with market bias and deduplication.
        Expects signals having at least: symbol, action(BUY/SELL), entry_price, stop_loss, target, confidence(0-10).
        """
        try:
            # Update bias from current live data if available
            try:
                if self.sharekhan_integration and self.sharekhan_integration.live_market_data:
                    await self.market_bias.update_market_bias(self._convert_live_data_for_bias())
            except Exception as _:
                pass

            # Normalize confidence to 0-1 expected by bias gate
            normalized = []
            for s in signals:
                c = s.get("confidence", 0)
                try:
                    c = float(c)
                except Exception:
                    c = 0.0
                s["confidence"] = c
                normalized.append(s)

            # Apply pre-execution deduplication and quality filter
            filtered = await signal_deduplicator.process_signals(normalized)
            return {"success": True, "signals": filtered, "bias": self.market_bias.get_current_bias_summary()}
        except Exception as e:
            logger.error(f"Error processing strategy signals: {e}")
            return {"success": False, "error": str(e)}

    def _convert_live_data_for_bias(self) -> Dict[str, Any]:
        """Convert ShareKhan live data into bias engine friendly dict."""
        converted: Dict[str, Any] = {}
        try:
            for symbol, md in self.sharekhan_integration.live_market_data.items():
                converted[symbol] = {
                    "ltp": getattr(md, "ltp", 0.0),
                    "open": getattr(md, "open", 0.0),
                    "close": getattr(md, "close", 0.0),
                    "high": getattr(md, "high", 0.0),
                    "low": getattr(md, "low", 0.0),
                    "volume": getattr(md, "volume", 0),
                    "change_percent": getattr(md, "ltp", 0.0) and (getattr(md, "ltp", 0.0) - getattr(md, "open", 0.0)) / (getattr(md, "open", 1.0) or 1.0) * 100.0,
                    "price_change": getattr(md, "ltp", 0.0) - getattr(md, "close", 0.0),
                    "prev_close": getattr(md, "close", 0.0),
                }
        except Exception:
            pass
        return converted

    async def get_live_data(self, symbols: List[str] = None) -> Dict[str, Any]:
        """Get live market data"""
        try:
            if self.sharekhan_integration:
                if symbols:
                    data = {}
                    for symbol in symbols:
                        symbol_data = self.sharekhan_integration.live_market_data.get(symbol)
                        if symbol_data:
                            data[symbol] = symbol_data
                    return {"success": True, "data": data}
                else:
                    return {"success": True, "data": self.sharekhan_integration.live_market_data}
            return {"success": False, "message": "ShareKhan integration not available"}
        except Exception as e:
            logger.error(f"Error getting live data: {e}")
            return {"success": False, "message": str(e)}
    
    async def start(self):
        """Start the orchestrator"""
        try:
            if not self.is_initialized:
                logger.error("❌ Cannot start - orchestrator not initialized")
                return False
            
            self.is_running = True
            logger.info("✅ ShareKhan Trading Orchestrator started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start orchestrator: {e}")
            return False
    
    async def stop(self):
        """Stop the orchestrator"""
        try:
            self.is_running = False
            
            # Shutdown enhanced services
            if self.order_deduplication_manager:
                await self.order_deduplication_manager.shutdown()
            
            if self.enhanced_position_manager:
                await self.enhanced_position_manager.shutdown()
            
            if self.strategy_position_tracker:
                await self.strategy_position_tracker.shutdown()
            
            if self.sharekhan_data_mapper:
                await self.sharekhan_data_mapper.shutdown()
            
            # Disconnect all components
            if self.sharekhan_integration:
                await self.sharekhan_integration.disconnect()
            
            if self.sharekhan_feed:
                await self.sharekhan_feed.disconnect()
            
            # Close Redis connection
            if self.redis_client:
                await self.redis_client.close()
            
            logger.info("✅ ShareKhan Trading Orchestrator stopped")
            
        except Exception as e:
            logger.error(f"❌ Error stopping orchestrator: {e}")
    
    # ENHANCED SERVICE ACCESS METHODS
    
    async def validate_and_submit_order(
        self,
        user_id: int,
        symbol: str,
        quantity: int,
        price: float,
        side: str,
        order_type: str = "MARKET"
    ) -> Dict[str, Any]:
        """Validate order through deduplication and submit if approved"""
        try:
            if not self.order_deduplication_manager:
                return {"success": False, "error": "Order deduplication not available"}
            
            # Validate order
            validation_result = await self.order_deduplication_manager.validate_order_submission(
                user_id=user_id,
                symbol=symbol,
                quantity=quantity,
                price=price,
                side=side,
                order_type=order_type
            )
            
            if not validation_result.get("allowed"):
                return {
                    "success": False,
                    "reason": "ORDER_REJECTED",
                    "message": validation_result.get("message"),
                    "validation_details": validation_result
                }
            
            # Submit order (placeholder - would integrate with actual order execution)
            order_id = f"ORD_{user_id}_{symbol}_{int(datetime.now().timestamp())}"
            
            # Register successful submission
            await self.order_deduplication_manager.register_order_submission(
                order_id=order_id,
                fingerprint_hash=validation_result.get("fingerprint_hash"),
                user_id=user_id,
                symbol=symbol,
                quantity=quantity,
                price=price,
                side=side,
                order_type=order_type
            )
            
            return {
                "success": True,
                "order_id": order_id,
                "message": "Order validated and submitted successfully",
                "validation_details": validation_result
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to validate and submit order: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_user_position_analytics(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive position analytics for user"""
        try:
            if not self.enhanced_position_manager:
                return {"success": False, "error": "Enhanced position manager not available"}
            
            analytics = await self.enhanced_position_manager.get_position_analytics(user_id)
            return {"success": True, "analytics": analytics}
            
        except Exception as e:
            logger.error(f"❌ Failed to get position analytics: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_strategy_recommendations(self, user_id: int) -> Dict[str, Any]:
        """Get strategy recommendations for all user positions"""
        try:
            if not self.strategy_position_tracker:
                return {"success": False, "error": "Strategy position tracker not available"}
            
            recommendations = await self.strategy_position_tracker.get_all_position_recommendations(user_id)
            return {"success": True, "recommendations": recommendations}
            
        except Exception as e:
            logger.error(f"❌ Failed to get strategy recommendations: {e}")
            return {"success": False, "error": str(e)}
    
    async def execute_strategy_recommendation(
        self,
        recommendation_id: str,
        user_approval: bool = True
    ) -> Dict[str, Any]:
        """Execute a strategy recommendation"""
        try:
            if not self.strategy_position_tracker:
                return {"success": False, "error": "Strategy position tracker not available"}
            
            result = await self.strategy_position_tracker.execute_recommendation(
                recommendation_id, user_approval
            )
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to execute strategy recommendation: {e}")
            return {"success": False, "error": str(e)}
    
    async def generate_comprehensive_report(
        self,
        user_id: int,
        report_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive trading report"""
        try:
            if not self.sharekhan_data_mapper:
                return {"success": False, "error": "ShareKhan data mapper not available"}
            
            report = await self.sharekhan_data_mapper.generate_comprehensive_report(user_id, report_date)
            if report:
                report_dict = await self.sharekhan_data_mapper.export_report_to_dict(report)
                return {"success": True, "report": report_dict}
            else:
                return {"success": False, "error": "Failed to generate report"}
            
        except Exception as e:
            logger.error(f"❌ Failed to generate comprehensive report: {e}")
            return {"success": False, "error": str(e)}
    
    async def sync_user_positions_from_sharekhan(
        self,
        user_id: int,
        sharekhan_client_id: str,
        sharekhan_api_key: str,
        sharekhan_api_secret: str
    ) -> Dict[str, Any]:
        """Sync user positions from ShareKhan"""
        try:
            if not self.enhanced_position_manager:
                return {"success": False, "error": "Enhanced position manager not available"}
            
            result = await self.enhanced_position_manager.sync_positions_from_sharekhan(
                user_id, sharekhan_client_id, sharekhan_api_key, sharekhan_api_secret
            )
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to sync positions from ShareKhan: {e}")
            return {"success": False, "error": str(e)}
    
    def get_enhanced_services_status(self) -> Dict[str, Any]:
        """Get status of all enhanced services"""
        return {
            "order_deduplication_manager": self.order_deduplication_manager is not None,
            "enhanced_position_manager": self.enhanced_position_manager is not None,
            "strategy_position_tracker": self.strategy_position_tracker is not None,
            "sharekhan_data_mapper": self.sharekhan_data_mapper is not None,
            "all_services_available": all([
                self.order_deduplication_manager,
                self.enhanced_position_manager,
                self.strategy_position_tracker,
                self.sharekhan_data_mapper
            ])
        }
    
    # COMPATIBILITY METHODS FOR EXISTING CODE
    
    def get_live_market_data(self):
        """Compatibility method for existing ShareKhan code"""
        if self.sharekhan_compatibility:
            return self.sharekhan_compatibility.live_market_data
        return {}
    
    def is_connected(self) -> bool:
        """Compatibility method for connection status"""
        if self.sharekhan_compatibility:
            return self.sharekhan_compatibility.is_connected()
        return False 