"""
Enhanced Trading Orchestrator
Integrates Set 1's sophisticated strategies with Set 2's production architecture
"""

import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Set, Any
from collections import defaultdict
import pandas as pd
import redis.asyncio as redis
from concurrent.futures import ThreadPoolExecutor
import json
from dataclasses import dataclass, asdict
import signal

from asyncio import PriorityQueue, Semaphore

# Enhanced strategy imports with Set 1 sophistication
from ..strategies.momentum_surfer import EnhancedMomentumSurfer
from ..strategies.volatility_explosion import EnhancedVolatilityExplosion
from ..strategies.volume_profile_scalper import EnhancedVolumeProfileScalper
from ..strategies.news_impact_scalper import EnhancedNewsImpactScalper

# Set 2 production infrastructure
from ..strategies.regime_adaptive_controller import RegimeAdaptiveController
from ..strategies.confluence_amplifier import ConfluenceAmplifier
from ..brokers.zerodha import ZerodhaIntegration
from ..data.truedata_provider import TrueDataProvider
from ..monitoring.event_monitor import EventMonitor
from .position_tracker import PositionTracker
from .order_manager import OrderManager
from .risk_manager import RiskManager
from ..risk.compliance_manager import ComplianceManager
from ..utils.notifications import NotificationService
from ..utils.constants import TradingHours, SystemLimits
from .events import EventBus, EventType, TradingEvent

# New imports for enhanced security and resilience
from ..security.auth_manager import SecurityManager
from ..core.connection_manager import ResilientConnection
from ..brokers.resilient_zerodha import ResilientZerodhaConnection
from ..data.resilient_truedata import ResilientTrueDataConnection
from ..monitoring.data_quality_monitor import DataQualityMonitor
from ..compliance.enhanced_compliance_manager import (
    PostTradeSurveillance, 
    DataRetentionManager
)

logger = logging.getLogger(__name__)

class TradingOrchestrator:
    """Enhanced trading orchestrator with sophisticated strategies"""

    def __init__(self, config: Dict):
        # Basic configuration
        self.config = config
        self.is_running = False
        self.is_trading_enabled = False
        self.is_market_open = False
        
        # Initialize Redis client
        self.redis_client = redis.Redis(
            host=config.get('redis', {}).get('host', 'localhost'),
            port=config.get('redis', {}).get('port', 6379),
            db=config.get('redis', {}).get('db', 0),
            decode_responses=True
        )
        
        # Initialize event bus
        self.event_bus = EventBus()
        
        # Initialize core components
        self.position_tracker = PositionTracker(self.event_bus, self.redis_client)
        self.order_manager = OrderManager(self.event_bus, self.redis_client)
        self.risk_manager = RiskManager(self.event_bus, self.redis_client)
        self.compliance_manager = ComplianceManager(self.event_bus, self.redis_client)
        self.notifier = NotificationService(config.get('notifications', {}))
        
        # Add security manager
        self.security_manager = SecurityManager(config['security'], self.redis_client)
        
        # Add data quality monitor
        self.data_quality_monitor = DataQualityMonitor(config)
        
        # Add compliance components
        self.post_trade_surveillance = PostTradeSurveillance(config)
        self.data_retention = DataRetentionManager(config, self.redis_client)
        
        # Initialize strategies
        self.strategies = {}
        self._initialize_strategies()
        
        # Initialize market data and broker connections
        self._initialize_connections(config)
        
        # Performance tracking
        self.metrics = defaultdict(float)
        self.last_update = datetime.now()
        
        # State management
        self._state_lock = asyncio.Lock()
        self._connection_lock = asyncio.Lock()
        
        # Task management
        self.tasks = set()
        self._task_semaphore = Semaphore(10)  # Limit concurrent tasks
        
        # Event monitoring
        self.event_monitor = EventMonitor(self.event_bus)
        
        # Setup event handlers
        self._setup_event_handlers()

    def _initialize_connections(self, config: Dict):
        """Initialize market data and broker connections with resilience"""
        # Initialize broker with resilient connection
        self.broker = ZerodhaIntegration(config['broker'])
        self.broker_connection = ResilientZerodhaConnection(self.broker, config['connection'])
        
        # Initialize data provider with resilient connection
        self.data_provider = TrueDataProvider(config['data_provider'])
        self.data_connection = ResilientTrueDataConnection(self.data_provider, config['connection'])

    def _initialize_strategies(self):
        """Initialize trading strategies"""
        strategy_configs = self.config.get('strategies', {})
        
        # Initialize regime controller first
        self.regime_controller = RegimeAdaptiveController(self.config)
        self.strategies['regime_controller'] = self.regime_controller
        
        # Initialize confluence amplifier
        self.confluence_amplifier = ConfluenceAmplifier(self.config)
        self.strategies['confluence_amplifier'] = self.confluence_amplifier
        
        # Initialize other strategies
        if strategy_configs.get('volatility_explosion', {}).get('enabled', True):
            self.strategies['volatility_explosion'] = EnhancedVolatilityExplosion(self.config)
        
        if strategy_configs.get('momentum_surfer', {}).get('enabled', True):
            self.strategies['momentum_surfer'] = EnhancedMomentumSurfer(self.config)
        
        if strategy_configs.get('volume_profile_scalper', {}).get('enabled', True):
            self.strategies['volume_profile_scalper'] = EnhancedVolumeProfileScalper(self.config)
        
        if strategy_configs.get('news_impact_scalper', {}).get('enabled', True):
            self.strategies['news_impact_scalper'] = EnhancedNewsImpactScalper(self.config)

    async def _run_strategy_wrapper(self, name: str, strategy):
        """Wrapper to run strategy coroutine and auto-restart on failure."""
        while self.is_trading_enabled:
            try:
                await strategy.run(self.event_bus)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Strategy {name} crashed: {exc}")
                await asyncio.sleep(5)  # back-off before restart

    async def enable_trading(self):
        if self.is_trading_enabled:
            return
        self.is_trading_enabled = True
        self.session_start = datetime.utcnow()

        # Spawn a task per strategy
        for name, strat in self.strategies.items():
            task = asyncio.create_task(self._run_strategy_wrapper(name, strat), name=f"strat-{name}")
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)

    async def disable_trading(self):
        if not self.is_trading_enabled:
            return
        self.is_trading_enabled = False
        # Cancel all strategy tasks gracefully
        for task in list(self.tasks):
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()

    async def get_trading_status(self) -> Dict[str, Any]:
        """Return a snapshot consumable by REST layer (non-blocking)."""
        return {
            "is_active": self.is_trading_enabled,
            "session_id": self.config.get("session_id", "unknown"),
            "start_time": getattr(self, "session_start", None),
            "last_heartbeat": datetime.utcnow().isoformat(),
            "active_strategies": list(self.strategies.keys()),
            "active_positions": await self.position_tracker_count_open(),
            "total_trades": self.metrics.get("total_trades", 0),
            "daily_pnl": self.metrics.get("daily_pnl", 0.0),
            "risk_status": await self.get_risk_metrics(),
            "market_status": "OPEN" if self.is_market_open else "CLOSED",
        }

    # Convenience wrappers used by routers ----------------------------------
    @property
    def position_manager(self):
        return self.position_tracker  # alias for router expectation

    async def get_all_positions(self):
        return await self.position_tracker.dump_open_positions()

    async def get_trading_metrics(self):
        return {
            "total_trades": self.metrics.get("total_trades", 0),
            "daily_pnl": self.metrics.get("daily_pnl", 0.0),
        }

    async def get_active_strategies(self):
        return list(self.strategies.keys())

    async def get_risk_metrics(self):
        if hasattr(self.risk_manager, "current_metrics"):
            return await self.risk_manager.current_metrics()
        return {}

    async def position_tracker_count_open(self):
        if hasattr(self.position_tracker, "count_open"):
            return await self.position_tracker.count_open()
        return 0

    # ... rest of the class implementation remains the same ... 