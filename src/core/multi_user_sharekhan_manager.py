"""
Multi-User ShareKhan Manager
Comprehensive user management system for ShareKhan integration
Complete replacement for Zerodha multi-user system
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert
import uuid
import hashlib
import hmac
from dataclasses import dataclass, asdict
from enum import Enum

from brokers.sharekhan import ShareKhanIntegration, ShareKhanOrder, ShareKhanMarketData
from src.config.database import get_async_session
from src.models.trading_models import User, Order, TradingTrade
from security.auth_manager import AuthManager

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """User roles with different permissions"""
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"
    LIMITED_TRADER = "limited_trader"

class TradingPermission(Enum):
    """Trading permissions for role-based access"""
    PLACE_ORDER = "place_order"
    MODIFY_ORDER = "modify_order"
    CANCEL_ORDER = "cancel_order"
    VIEW_PORTFOLIO = "view_portfolio"
    VIEW_TRADES = "view_trades"
    VIEW_MARKET_DATA = "view_market_data"
    MANAGE_USERS = "manage_users"
    SYSTEM_CONFIG = "system_config"
    RISK_OVERRIDE = "risk_override"

@dataclass
class UserConfig:
    """User configuration and settings"""
    user_id: str
    display_name: str
    email: str
    role: UserRole
    permissions: List[TradingPermission]
    risk_limits: Dict[str, float]
    active: bool = True
    created_at: datetime = None
    last_login: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class UserSession:
    """Active user session"""
    user_id: str
    session_id: str
    access_token: str
    expires_at: datetime
    permissions: List[TradingPermission]
    last_activity: datetime
    ip_address: str = None
    
@dataclass
class UserTradingStats:
    """User trading statistics"""
    user_id: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    daily_pnl: float = 0.0
    max_drawdown: float = 0.0
    daily_trade_count: int = 0
    risk_violations: int = 0
    last_trade_time: datetime = None

class MultiUserShareKhanManager:
    """
    Comprehensive multi-user management for ShareKhan trading system
    Complete replacement for Zerodha multi-user architecture
    """
    
    def __init__(self, redis_client: redis.Redis, auth_manager: AuthManager):
        self.redis_client = redis_client
        self.auth_manager = auth_manager
        
        # ShareKhan configurations per user
        self.user_integrations: Dict[str, ShareKhanIntegration] = {}
        self.user_configs: Dict[str, UserConfig] = {}
        self.active_sessions: Dict[str, UserSession] = {}
        
        # Master ShareKhan integration for system operations
        self.master_integration: Optional[ShareKhanIntegration] = None
        self.master_api_key = os.getenv('SHAREKHAN_API_KEY')
        self.master_secret = os.getenv('SHAREKHAN_SECRET_KEY')
        self.master_customer_id = os.getenv('SHAREKHAN_MASTER_CUSTOMER_ID')
        
        # Role-based permissions
        self.role_permissions = {
            UserRole.ADMIN: [perm for perm in TradingPermission],
            UserRole.TRADER: [
                TradingPermission.PLACE_ORDER,
                TradingPermission.MODIFY_ORDER,
                TradingPermission.CANCEL_ORDER,
                TradingPermission.VIEW_PORTFOLIO,
                TradingPermission.VIEW_TRADES,
                TradingPermission.VIEW_MARKET_DATA
            ],
            UserRole.LIMITED_TRADER: [
                TradingPermission.PLACE_ORDER,
                TradingPermission.VIEW_PORTFOLIO,
                TradingPermission.VIEW_TRADES,
                TradingPermission.VIEW_MARKET_DATA
            ],
            UserRole.VIEWER: [
                TradingPermission.VIEW_PORTFOLIO,
                TradingPermission.VIEW_TRADES,
                TradingPermission.VIEW_MARKET_DATA
            ]
        }
        
        # Default risk limits per role
        self.default_risk_limits = {
            UserRole.ADMIN: {
                "max_position_size": 1000000,  # 10 Lakh
                "max_daily_loss": 50000,       # 50k
                "max_order_value": 100000,     # 1 Lakh
                "max_orders_per_minute": 20
            },
            UserRole.TRADER: {
                "max_position_size": 500000,   # 5 Lakh
                "max_daily_loss": 25000,       # 25k
                "max_order_value": 50000,      # 50k
                "max_orders_per_minute": 10
            },
            UserRole.LIMITED_TRADER: {
                "max_position_size": 100000,   # 1 Lakh
                "max_daily_loss": 10000,       # 10k
                "max_order_value": 25000,      # 25k
                "max_orders_per_minute": 5
            },
            UserRole.VIEWER: {
                "max_position_size": 0,
                "max_daily_loss": 0,
                "max_order_value": 0,
                "max_orders_per_minute": 0
            }
        }
        
        # Monitoring
        self.user_activity = {}
        self.user_stats: Dict[str, UserTradingStats] = {}
        self.risk_violations = {}
        
        logger.info("Multi-user ShareKhan manager initialized")
    
    async def initialize(self) -> bool:
        """Initialize the multi-user manager"""
        try:
            # Initialize master ShareKhan integration
            if self.master_api_key and self.master_secret and self.master_customer_id:
                self.master_integration = ShareKhanIntegration(
                    api_key=self.master_api_key,
                    secret_key=self.master_secret,
                    customer_id=self.master_customer_id
                )
                logger.info("✅ Master ShareKhan integration initialized")
            
            # Load existing user configs from Redis
            await self._load_user_configs()
            
            # Load user stats
            await self._load_user_stats()
            
            # Start background tasks
            asyncio.create_task(self._session_cleanup_task())
            asyncio.create_task(self._user_monitoring_task())
            asyncio.create_task(self._daily_reset_task())
            
            logger.info("✅ Multi-user ShareKhan manager fully initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Multi-user manager initialization failed: {e}")
            return False
    
    async def _load_user_configs(self):
        """Load user configurations from Redis"""
        try:
            user_configs_data = await self.redis_client.hgetall("sharekhan:users")
            
            for user_id, config_json in user_configs_data.items():
                try:
                    config_data = json.loads(config_json)
                    user_config = UserConfig(**config_data)
                    self.user_configs[user_id] = user_config
                    
                    # Initialize user stats if not exists
                    if user_id not in self.user_stats:
                        self.user_stats[user_id] = UserTradingStats(user_id=user_id)
                        
                except Exception as e:
                    logger.error(f"Failed to load config for user {user_id}: {e}")
            
            logger.info(f"✅ Loaded {len(self.user_configs)} user configurations")
            
        except Exception as e:
            logger.error(f"❌ Failed to load user configs: {e}")
    
    async def _load_user_stats(self):
        """Load user trading statistics from Redis"""
        try:
            stats_data = await self.redis_client.hgetall("sharekhan:user_stats")
            
            for user_id, stats_json in stats_data.items():
                try:
                    stats_data = json.loads(stats_json)
                    user_stats = UserTradingStats(**stats_data)
                    self.user_stats[user_id] = user_stats
                except Exception as e:
                    logger.error(f"Failed to load stats for user {user_id}: {e}")
            
            logger.info(f"✅ Loaded statistics for {len(self.user_stats)} users")
            
        except Exception as e:
            logger.error(f"❌ Failed to load user stats: {e}")
    
    # USER MANAGEMENT
    
    async def add_user(self, user_id: str, display_name: str, email: str, 
                      role: UserRole, custom_limits: Dict[str, float] = None) -> bool:
        """Add new user to the system"""
        try:
            if user_id in self.user_configs:
                logger.warning(f"User {user_id} already exists")
                return False
            
            # Get permissions for role
            permissions = self.role_permissions.get(role, [])
            
            # Set risk limits
            risk_limits = self.default_risk_limits.get(role, {})
            if custom_limits:
                risk_limits.update(custom_limits)
            
            # Create user config
            user_config = UserConfig(
                user_id=user_id,
                display_name=display_name,
                email=email,
                role=role,
                permissions=permissions,
                risk_limits=risk_limits,
                active=True,
                created_at=datetime.now()
            )
            
            # Store in memory and Redis
            self.user_configs[user_id] = user_config
            await self._cache_user_config(user_config)
            
            # Initialize user stats
            self.user_stats[user_id] = UserTradingStats(user_id=user_id)
            await self._cache_user_stats(self.user_stats[user_id])
            
            logger.info(f"✅ Added user: {user_id} ({display_name}) with role {role.value}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add user {user_id}: {e}")
            return False
    
    async def remove_user(self, user_id: str) -> bool:
        """Remove user from the system"""
        try:
            if user_id not in self.user_configs:
                logger.warning(f"User {user_id} not found")
                return False
            
            # Deactivate user instead of deleting
            self.user_configs[user_id].active = False
            await self._cache_user_config(self.user_configs[user_id])
            
            # Remove active sessions
            sessions_to_remove = [
                session_id for session_id, session in self.active_sessions.items()
                if session.user_id == user_id
            ]
            
            for session_id in sessions_to_remove:
                await self.terminate_session(session_id)
            
            # Remove user integration
            if user_id in self.user_integrations:
                await self.user_integrations[user_id].disconnect()
                del self.user_integrations[user_id]
            
            logger.info(f"✅ Deactivated user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to remove user {user_id}: {e}")
            return False
    
    async def update_user_role(self, user_id: str, new_role: UserRole) -> bool:
        """Update user role and permissions"""
        try:
            if user_id not in self.user_configs:
                logger.error(f"User {user_id} not found")
                return False
            
            user_config = self.user_configs[user_id]
            old_role = user_config.role
            
            # Update role and permissions
            user_config.role = new_role
            user_config.permissions = self.role_permissions.get(new_role, [])
            
            # Update risk limits to defaults for new role
            user_config.risk_limits = self.default_risk_limits.get(new_role, {})
            
            # Save changes
            await self._cache_user_config(user_config)
            
            # Update active sessions
            for session in self.active_sessions.values():
                if session.user_id == user_id:
                    session.permissions = user_config.permissions
            
            logger.info(f"✅ Updated user {user_id} role: {old_role.value} → {new_role.value}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update user role for {user_id}: {e}")
            return False
    
    async def update_user_limits(self, user_id: str, new_limits: Dict[str, float]) -> bool:
        """Update user risk limits"""
        try:
            if user_id not in self.user_configs:
                logger.error(f"User {user_id} not found")
                return False
            
            user_config = self.user_configs[user_id]
            user_config.risk_limits.update(new_limits)
            
            await self._cache_user_config(user_config)
            
            logger.info(f"✅ Updated limits for user {user_id}: {new_limits}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update limits for {user_id}: {e}")
            return False
    
    # AUTHENTICATION AND SESSIONS
    
    async def authenticate_user(self, user_id: str, password: str, ip_address: str = None) -> Optional[UserSession]:
        """Authenticate user and create session"""
        try:
            # Check if user exists and is active
            if user_id not in self.user_configs:
                logger.warning(f"Authentication failed: User {user_id} not found")
                return None
            
            user_config = self.user_configs[user_id]
            
            if not user_config.active:
                logger.warning(f"Authentication failed: User {user_id} is deactivated")
                return None
            
            # Verify password (implement proper password hashing in production)
            if not self._verify_password(user_id, password):
                logger.warning(f"Authentication failed: Invalid password for {user_id}")
                return None
            
            # Create session
            session_id = str(uuid.uuid4())
            access_token = self._generate_access_token(user_id, session_id)
            expires_at = datetime.now() + timedelta(hours=24)
            
            session = UserSession(
                user_id=user_id,
                session_id=session_id,
                access_token=access_token,
                expires_at=expires_at,
                permissions=user_config.permissions,
                last_activity=datetime.now(),
                ip_address=ip_address
            )
            
            # Store session
            self.active_sessions[session_id] = session
            await self._cache_session(session)
            
            # Update user last login
            user_config.last_login = datetime.now()
            await self._cache_user_config(user_config)
            
            logger.info(f"✅ User authenticated: {user_id}")
            return session
            
        except Exception as e:
            logger.error(f"❌ Authentication failed for {user_id}: {e}")
            return None
    
    def _verify_password(self, user_id: str, password: str) -> bool:
        """Verify user password (simplified - implement proper hashing)"""
        # In production, implement proper password hashing and verification
        # For now, using environment variable or default
        expected_password = os.getenv(f'SHAREKHAN_USER_{user_id.upper()}_PASSWORD', 'default123')
        return password == expected_password
    
    def _generate_access_token(self, user_id: str, session_id: str) -> str:
        """Generate secure access token"""
        timestamp = str(int(datetime.now().timestamp()))
        data = f"{user_id}:{session_id}:{timestamp}"
        
        secret_key = os.getenv('SHAREKHAN_SECRET_KEY', 'default_secret')
        signature = hmac.new(
            secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"{data}:{signature}"
    
    async def validate_session(self, access_token: str) -> Optional[UserSession]:
        """Validate access token and return session"""
        try:
            # Find session by access token
            for session in self.active_sessions.values():
                if session.access_token == access_token:
                    # Check if session is expired
                    if datetime.now() > session.expires_at:
                        await self.terminate_session(session.session_id)
                        return None
                    
                    # Update last activity
                    session.last_activity = datetime.now()
                    await self._cache_session(session)
                    
                    return session
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Session validation error: {e}")
            return None
    
    async def terminate_session(self, session_id: str) -> bool:
        """Terminate user session"""
        try:
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                
                # Remove from active sessions
                del self.active_sessions[session_id]
                
                # Remove from Redis
                await self.redis_client.hdel("sharekhan:sessions", session_id)
                
                logger.info(f"✅ Terminated session for user: {session.user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Session termination error: {e}")
            return False
    
    # USER SHAREKHAN INTEGRATION
    
    async def get_user_integration(self, user_id: str) -> Optional[ShareKhanIntegration]:
        """Get or create ShareKhan integration for user"""
        try:
            if user_id not in self.user_configs:
                return None
            
            # For now, all users use the master integration
            # In production, users would have their own ShareKhan credentials
            if user_id not in self.user_integrations:
                if self.master_integration:
                    # Create a copy of master integration for user tracking
                    user_integration = ShareKhanIntegration(
                        api_key=self.master_api_key,
                        secret_key=self.master_secret,
                        customer_id=self.master_customer_id
                    )
                    
                    # Use master credentials but track separately for user
                    user_integration.access_token = self.master_integration.access_token
                    user_integration.is_authenticated = self.master_integration.is_authenticated
                    
                    self.user_integrations[user_id] = user_integration
                    
                    logger.info(f"✅ Created ShareKhan integration for user: {user_id}")
            
            return self.user_integrations.get(user_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to get integration for user {user_id}: {e}")
            return None
    
    # ORDER MANAGEMENT WITH USER TRACKING
    
    async def place_user_order(self, user_id: str, order: ShareKhanOrder) -> Dict:
        """Place order for specific user with risk validation"""
        try:
            # Validate user permissions
            if not await self._check_user_permission(user_id, TradingPermission.PLACE_ORDER):
                raise Exception(f"User {user_id} does not have order placement permission")
            
            # Validate risk limits
            if not await self._validate_order_risk(user_id, order):
                raise Exception(f"Order violates risk limits for user {user_id}")
            
            # Get user integration
            user_integration = await self.get_user_integration(user_id)
            if not user_integration:
                raise Exception(f"No ShareKhan integration available for user {user_id}")
            
            # Place order via ShareKhan
            result = await user_integration.place_order(order)
            
            if result.get('success'):
                # Update user stats
                await self._update_user_order_stats(user_id, order, result)
                
                # Log user activity
                await self._log_user_activity(user_id, "ORDER_PLACED", {
                    "order_id": result.get('order_id'),
                    "symbol": order.trading_symbol,
                    "quantity": order.quantity,
                    "price": order.price
                })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Order placement failed for user {user_id}: {e}")
            
            # Log risk violation if applicable
            await self._log_risk_violation(user_id, "ORDER_FAILED", str(e))
            
            raise
    
    async def _check_user_permission(self, user_id: str, permission: TradingPermission) -> bool:
        """Check if user has specific permission"""
        user_config = self.user_configs.get(user_id)
        if not user_config or not user_config.active:
            return False
        
        return permission in user_config.permissions
    
    async def _validate_order_risk(self, user_id: str, order: ShareKhanOrder) -> bool:
        """Validate order against user risk limits"""
        try:
            user_config = self.user_configs.get(user_id)
            if not user_config:
                return False
            
            risk_limits = user_config.risk_limits
            user_stats = self.user_stats.get(user_id, UserTradingStats(user_id=user_id))
            
            # Check order value limit
            order_value = order.quantity * order.price
            if order_value > risk_limits.get('max_order_value', 0):
                logger.warning(f"Order value {order_value} exceeds limit for user {user_id}")
                return False
            
            # Check daily loss limit
            if user_stats.daily_pnl < -risk_limits.get('max_daily_loss', 0):
                logger.warning(f"Daily loss limit exceeded for user {user_id}")
                return False
            
            # Check order rate limit
            now = datetime.now()
            recent_orders = await self._get_recent_order_count(user_id, timedelta(minutes=1))
            if recent_orders >= risk_limits.get('max_orders_per_minute', 0):
                logger.warning(f"Order rate limit exceeded for user {user_id}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Risk validation error for user {user_id}: {e}")
            return False
    
    async def _get_recent_order_count(self, user_id: str, time_window: timedelta) -> int:
        """Get count of recent orders for rate limiting"""
        try:
            # Implementation would query recent orders from database or cache
            # For now, return 0 (placeholder)
            return 0
        except Exception as e:
            logger.error(f"❌ Failed to get recent order count for {user_id}: {e}")
            return 0
    
    # USER STATISTICS AND MONITORING
    
    async def _update_user_order_stats(self, user_id: str, order: ShareKhanOrder, result: Dict):
        """Update user trading statistics"""
        try:
            user_stats = self.user_stats.get(user_id, UserTradingStats(user_id=user_id))
            
            # Update order count
            user_stats.daily_trade_count += 1
            user_stats.total_trades += 1
            user_stats.last_trade_time = datetime.now()
            
            # Store updated stats
            self.user_stats[user_id] = user_stats
            await self._cache_user_stats(user_stats)
            
        except Exception as e:
            logger.error(f"❌ Failed to update stats for user {user_id}: {e}")
    
    async def _log_user_activity(self, user_id: str, activity_type: str, details: Dict):
        """Log user activity for audit trail"""
        try:
            activity_log = {
                "user_id": user_id,
                "activity_type": activity_type,
                "details": details,
                "timestamp": datetime.now().isoformat(),
                "ip_address": None  # Get from session if available
            }
            
            # Store in Redis for audit trail
            log_key = f"sharekhan:activity:{user_id}:{datetime.now().strftime('%Y%m%d')}"
            await self.redis_client.lpush(log_key, json.dumps(activity_log))
            await self.redis_client.ltrim(log_key, 0, 999)  # Keep last 1000 entries
            await self.redis_client.expire(log_key, 86400 * 30)  # 30 days retention
            
        except Exception as e:
            logger.error(f"❌ Failed to log activity for user {user_id}: {e}")
    
    async def _log_risk_violation(self, user_id: str, violation_type: str, details: str):
        """Log risk violation for monitoring"""
        try:
            violation = {
                "user_id": user_id,
                "violation_type": violation_type,
                "details": details,
                "timestamp": datetime.now().isoformat()
            }
            
            # Store violation
            violation_key = f"sharekhan:violations:{user_id}"
            await self.redis_client.lpush(violation_key, json.dumps(violation))
            await self.redis_client.ltrim(violation_key, 0, 99)  # Keep last 100
            await self.redis_client.expire(violation_key, 86400 * 7)  # 7 days retention
            
            # Update user stats
            user_stats = self.user_stats.get(user_id, UserTradingStats(user_id=user_id))
            user_stats.risk_violations += 1
            await self._cache_user_stats(user_stats)
            
        except Exception as e:
            logger.error(f"❌ Failed to log violation for user {user_id}: {e}")
    
    # CACHE MANAGEMENT
    
    async def _cache_user_config(self, user_config: UserConfig):
        """Cache user configuration in Redis"""
        try:
            config_dict = asdict(user_config)
            # Convert datetime objects to ISO strings
            if config_dict['created_at']:
                config_dict['created_at'] = config_dict['created_at'].isoformat()
            if config_dict['last_login']:
                config_dict['last_login'] = config_dict['last_login'].isoformat()
            
            await self.redis_client.hset(
                "sharekhan:users",
                user_config.user_id,
                json.dumps(config_dict)
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to cache user config: {e}")
    
    async def _cache_user_stats(self, user_stats: UserTradingStats):
        """Cache user statistics in Redis"""
        try:
            stats_dict = asdict(user_stats)
            # Convert datetime to ISO string
            if stats_dict['last_trade_time']:
                stats_dict['last_trade_time'] = stats_dict['last_trade_time'].isoformat()
            
            await self.redis_client.hset(
                "sharekhan:user_stats",
                user_stats.user_id,
                json.dumps(stats_dict)
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to cache user stats: {e}")
    
    async def _cache_session(self, session: UserSession):
        """Cache user session in Redis"""
        try:
            session_dict = asdict(session)
            # Convert datetime objects to ISO strings
            session_dict['expires_at'] = session_dict['expires_at'].isoformat()
            session_dict['last_activity'] = session_dict['last_activity'].isoformat()
            
            await self.redis_client.hset(
                "sharekhan:sessions",
                session.session_id,
                json.dumps(session_dict)
            )
            await self.redis_client.expire("sharekhan:sessions", 86400)  # 24 hours
            
        except Exception as e:
            logger.error(f"❌ Failed to cache session: {e}")
    
    # BACKGROUND TASKS
    
    async def _session_cleanup_task(self):
        """Clean up expired sessions"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                expired_sessions = []
                now = datetime.now()
                
                for session_id, session in self.active_sessions.items():
                    if now > session.expires_at:
                        expired_sessions.append(session_id)
                
                for session_id in expired_sessions:
                    await self.terminate_session(session_id)
                
                if expired_sessions:
                    logger.info(f"✅ Cleaned up {len(expired_sessions)} expired sessions")
                
            except Exception as e:
                logger.error(f"❌ Session cleanup task error: {e}")
    
    async def _user_monitoring_task(self):
        """Monitor user activity and performance"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                for user_id, user_stats in self.user_stats.items():
                    # Check for unusual activity patterns
                    if user_stats.daily_trade_count > 100:
                        logger.warning(f"⚠️ High trading activity for user {user_id}: {user_stats.daily_trade_count} trades")
                    
                    if user_stats.daily_pnl < -10000:
                        logger.warning(f"⚠️ High daily loss for user {user_id}: {user_stats.daily_pnl}")
                
            except Exception as e:
                logger.error(f"❌ User monitoring task error: {e}")
    
    async def _daily_reset_task(self):
        """Reset daily statistics at market open"""
        while True:
            try:
                # Wait until next 9:00 AM
                now = datetime.now()
                next_reset = now.replace(hour=9, minute=0, second=0, microsecond=0)
                if now >= next_reset:
                    next_reset += timedelta(days=1)
                
                wait_seconds = (next_reset - now).total_seconds()
                await asyncio.sleep(wait_seconds)
                
                # Reset daily stats for all users
                for user_id, user_stats in self.user_stats.items():
                    user_stats.daily_pnl = 0.0
                    user_stats.daily_trade_count = 0
                    await self._cache_user_stats(user_stats)
                
                logger.info("✅ Daily user statistics reset completed")
                
            except Exception as e:
                logger.error(f"❌ Daily reset task error: {e}")
    
    # PUBLIC API METHODS
    
    def get_user_config(self, user_id: str) -> Optional[UserConfig]:
        """Get user configuration"""
        return self.user_configs.get(user_id)
    
    def get_user_stats(self, user_id: str) -> Optional[UserTradingStats]:
        """Get user trading statistics"""
        return self.user_stats.get(user_id)
    
    def get_active_users(self) -> List[str]:
        """Get list of active user IDs"""
        return [
            user_id for user_id, config in self.user_configs.items()
            if config.active
        ]
    
    def get_user_sessions(self, user_id: str) -> List[UserSession]:
        """Get active sessions for user"""
        return [
            session for session in self.active_sessions.values()
            if session.user_id == user_id
        ]
    
    async def get_system_status(self) -> Dict:
        """Get overall system status"""
        try:
            return {
                "total_users": len(self.user_configs),
                "active_users": len([c for c in self.user_configs.values() if c.active]),
                "active_sessions": len(self.active_sessions),
                "master_integration_status": self.master_integration.get_connection_status() if self.master_integration else None,
                "user_integrations": len(self.user_integrations),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Failed to get system status: {e}")
            return {"error": str(e)} 