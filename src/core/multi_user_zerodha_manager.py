"""
Multi-User ShareKhan Manager
Manages multiple ShareKhan user configurations and trading sessions
Integrates with dynamic user management system
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import os
import redis.asyncio as redis
from dataclasses import dataclass
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from brokers.sharekhan import ShareKhanIntegration
from brokers.resilient_sharekhan import ResilientShareKhanConnection

logger = logging.getLogger(__name__)

@dataclass
class UserTradingSession:
    """Trading session for a specific user"""
    user_id: int
    username: str
    sharekhan_client: Optional[ShareKhanIntegration]
    resilient_client: Optional[ResilientShareKhanConnection]
    is_connected: bool = False
    last_activity: Optional[datetime] = None
    api_key: Optional[str] = None
    client_id: Optional[str] = None
    access_token: Optional[str] = None
    session_config: Dict = None

class MultiUserShareKhanManager:
    """Manages multiple ShareKhan user sessions"""
    
    def __init__(self):
        self.user_sessions: Dict[int, UserTradingSession] = {}
        self.redis_client = None
        self.is_initialized = False
        self.session_cleanup_task = None
        
    async def initialize(self):
        """Initialize the multi-user manager"""
        try:
            # Initialize Redis connection
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = await redis.from_url(redis_url)
            
            # Load existing user sessions
            await self._load_user_sessions()
            
            # Start session cleanup task
            self.session_cleanup_task = asyncio.create_task(self._session_cleanup_loop())
            
            self.is_initialized = True
            logger.info("✅ MultiUserShareKhanManager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ MultiUserShareKhanManager initialization failed: {e}")
            return False
    
    async def add_user_session(
        self,
        user_id: int,
        username: str,
        api_key: str,
        api_secret: str,
        client_id: str,
        access_token: Optional[str] = None
    ) -> bool:
        """Add a new user trading session"""
        try:
            # Create ShareKhan configuration
            sharekhan_config = {
                'api_key': api_key,
                'api_secret': api_secret,
                'user_id': client_id,
                'access_token': access_token,
                'mock_mode': not access_token,  # Use mock mode if no access token
                'sandbox_mode': os.getenv('SHAREKHAN_SANDBOX_MODE', 'true').lower() == 'true'
            }
            
            # Create ShareKhan client
            sharekhan_client = ShareKhanIntegration(sharekhan_config)
            
            # Create resilient connection
            resilient_config = {
                'max_retries': 3,
                'retry_delay': 5,
                'health_check_interval': 30,
                'order_rate_limit': 1.0,
                'ws_reconnect_delay': 5,
                'ws_max_reconnect_attempts': 10
            }
            
            resilient_client = ResilientShareKhanConnection(sharekhan_client, resilient_config)
            
            # Create session
            session = UserTradingSession(
                user_id=user_id,
                username=username,
                sharekhan_client=sharekhan_client,
                resilient_client=resilient_client,
                api_key=api_key,
                client_id=client_id,
                access_token=access_token,
                session_config=sharekhan_config
            )
            
            # Store session
            self.user_sessions[user_id] = session
            
            # Store credentials in Redis
            await self._store_user_credentials(user_id, api_key, api_secret, client_id, access_token)
            
            logger.info(f"✅ User session added: {username} (ID: {user_id})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add user session for {username}: {e}")
            return False
    
    async def connect_user_session(self, user_id: int) -> bool:
        """Connect a specific user's trading session"""
        try:
            if user_id not in self.user_sessions:
                logger.error(f"❌ User session not found: {user_id}")
                return False
            
            session = self.user_sessions[user_id]
            
            # Initialize and connect resilient client
            if session.resilient_client:
                await session.resilient_client.initialize()
                session.is_connected = session.resilient_client.is_connected
                session.last_activity = datetime.utcnow()
                
                if session.is_connected:
                    logger.info(f"✅ User session connected: {session.username} (ID: {user_id})")
                    return True
                else:
                    logger.error(f"❌ Failed to connect user session: {session.username}")
                    return False
            else:
                logger.error(f"❌ No resilient client for user: {session.username}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error connecting user session {user_id}: {e}")
            return False
    
    async def disconnect_user_session(self, user_id: int) -> bool:
        """Disconnect a specific user's trading session"""
        try:
            if user_id not in self.user_sessions:
                return True  # Already disconnected
            
            session = self.user_sessions[user_id]
            
            if session.resilient_client:
                await session.resilient_client.disconnect()
            
            session.is_connected = False
            session.last_activity = datetime.utcnow()
            
            logger.info(f"✅ User session disconnected: {session.username} (ID: {user_id})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error disconnecting user session {user_id}: {e}")
            return False
    
    async def remove_user_session(self, user_id: int) -> bool:
        """Remove a user's trading session"""
        try:
            if user_id in self.user_sessions:
                # Disconnect first
                await self.disconnect_user_session(user_id)
                
                # Remove from memory
                del self.user_sessions[user_id]
                
                # Clean up Redis data
                await self._cleanup_user_credentials(user_id)
                
                logger.info(f"✅ User session removed: {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error removing user session {user_id}: {e}")
            return False
    
    async def place_user_order(self, user_id: int, order_params: Dict) -> Optional[str]:
        """Place order for a specific user"""
        try:
            if user_id not in self.user_sessions:
                logger.error(f"❌ User session not found for order: {user_id}")
                return None
            
            session = self.user_sessions[user_id]
            
            if not session.is_connected:
                logger.error(f"❌ User session not connected: {session.username}")
                return None
            
            # Update last activity
            session.last_activity = datetime.utcnow()
            
            # Place order through resilient client
            order_id = await session.resilient_client.place_order(order_params)
            
            if order_id:
                logger.info(f"✅ Order placed for user {session.username}: {order_id}")
                
                # Log order activity
                await self._log_user_activity(user_id, 'order_placed', {
                    'order_id': order_id,
                    'symbol': order_params.get('symbol'),
                    'action': order_params.get('action'),
                    'quantity': order_params.get('quantity')
                })
            
            return order_id
            
        except Exception as e:
            logger.error(f"❌ Error placing order for user {user_id}: {e}")
            return None
    
    async def get_user_holdings(self, user_id: int) -> Dict:
        """Get holdings for a specific user"""
        try:
            if user_id not in self.user_sessions:
                return {}
            
            session = self.user_sessions[user_id]
            
            if not session.is_connected:
                return {}
            
            # Update last activity
            session.last_activity = datetime.utcnow()
            
            # Get holdings through resilient client
            holdings = await session.resilient_client.get_holdings()
            
            return holdings
            
        except Exception as e:
            logger.error(f"❌ Error getting holdings for user {user_id}: {e}")
            return {}
    
    async def get_user_positions(self, user_id: int) -> Dict:
        """Get positions for a specific user"""
        try:
            if user_id not in self.user_sessions:
                return {}
            
            session = self.user_sessions[user_id]
            
            if not session.is_connected:
                return {}
            
            # Update last activity
            session.last_activity = datetime.utcnow()
            
            # Get positions through resilient client
            positions = await session.resilient_client.get_positions()
            
            return positions
            
        except Exception as e:
            logger.error(f"❌ Error getting positions for user {user_id}: {e}")
            return {}
    
    def get_user_session_status(self, user_id: int) -> Dict:
        """Get status of a user's trading session"""
        if user_id not in self.user_sessions:
            return {
                'user_id': user_id,
                'exists': False,
                'is_connected': False,
                'last_activity': None
            }
        
        session = self.user_sessions[user_id]
        status = {
            'user_id': user_id,
            'username': session.username,
            'exists': True,
            'is_connected': session.is_connected,
            'last_activity': session.last_activity.isoformat() if session.last_activity else None,
            'has_access_token': bool(session.access_token),
            'client_id': session.client_id
        }
        
        # Get connection details from resilient client
        if session.resilient_client:
            connection_status = session.resilient_client.connection_status
            status.update({
                'connection_state': connection_status.get('state'),
                'last_connected': connection_status.get('last_connected'),
                'reconnect_attempts': connection_status.get('reconnect_attempts', 0),
                'latency_ms': connection_status.get('latency_ms')
            })
        
        return status
    
    def get_all_sessions_status(self) -> List[Dict]:
        """Get status of all user sessions"""
        return [self.get_user_session_status(user_id) for user_id in self.user_sessions.keys()]
    
    async def update_user_access_token(self, user_id: int, access_token: str) -> bool:
        """Update access token for a user"""
        try:
            if user_id not in self.user_sessions:
                logger.error(f"❌ User session not found: {user_id}")
                return False
            
            session = self.user_sessions[user_id]
            
            # Update session
            session.access_token = access_token
            session.session_config['access_token'] = access_token
            session.session_config['mock_mode'] = False  # Enable real trading
            
            # Update ShareKhan client
            if session.sharekhan_client:
                session.sharekhan_client.access_token = access_token
                session.sharekhan_client.mock_mode = False
                
                # Set access token in ShareKhanConnect if available
                if hasattr(session.sharekhan_client, 'kite') and session.sharekhan_client.kite:
                    session.sharekhan_client.kite.set_access_token(access_token)
            
            # Store updated credentials
            await self._store_user_credentials(
                user_id,
                session.api_key,
                None,  # Don't store secret again
                session.client_id,
                access_token
            )
            
            logger.info(f"✅ Access token updated for user {session.username}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating access token for user {user_id}: {e}")
            return False
    
    async def _load_user_sessions(self):
        """Load existing user sessions from Redis"""
        try:
            if not self.redis_client:
                return
            
            # Get all user credential keys
            keys = await self.redis_client.keys("sharekhan:credentials:*")
            
            for key in keys:
                try:
                    user_id = int(key.decode().split(':')[-1])
                    credentials = await self.redis_client.hgetall(key)
                    
                    if credentials:
                        api_key = credentials.get(b'api_key', b'').decode()
                        client_id = credentials.get(b'client_id', b'').decode()
                        access_token = credentials.get(b'access_token', b'').decode()
                        
                        if api_key and client_id:
                            # Get username from database or use user_id
                            username = f"user_{user_id}"  # Fallback
                            
                            await self.add_user_session(
                                user_id=user_id,
                                username=username,
                                api_key=api_key,
                                api_secret="",  # Don't store/load secret
                                client_id=client_id,
                                access_token=access_token if access_token else None
                            )
                            
                except Exception as e:
                    logger.error(f"❌ Error loading session from key {key}: {e}")
                    continue
            
            logger.info(f"✅ Loaded {len(self.user_sessions)} user sessions")
            
        except Exception as e:
            logger.error(f"❌ Error loading user sessions: {e}")
    
    async def _store_user_credentials(
        self,
        user_id: int,
        api_key: str,
        api_secret: Optional[str],
        client_id: str,
        access_token: Optional[str]
    ):
        """Store user credentials in Redis"""
        try:
            if not self.redis_client:
                return
            
            credentials = {
                'api_key': api_key,
                'client_id': client_id,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Only store access token, not secret for security
            if access_token:
                credentials['access_token'] = access_token
            
            await self.redis_client.hset(
                f"sharekhan:credentials:{user_id}",
                mapping=credentials
            )
            
            # Set expiry for security
            await self.redis_client.expire(f"sharekhan:credentials:{user_id}", 86400 * 30)  # 30 days
            
        except Exception as e:
            logger.error(f"❌ Error storing credentials for user {user_id}: {e}")
    
    async def _cleanup_user_credentials(self, user_id: int):
        """Clean up user credentials from Redis"""
        try:
            if not self.redis_client:
                return
            
            keys_to_delete = [
                f"sharekhan:credentials:{user_id}",
                f"sharekhan:activity:{user_id}",
                f"sharekhan:session:{user_id}"
            ]
            
            for key in keys_to_delete:
                await self.redis_client.delete(key)
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up credentials for user {user_id}: {e}")
    
    async def _log_user_activity(self, user_id: int, activity_type: str, details: Dict):
        """Log user activity for monitoring"""
        try:
            if not self.redis_client:
                return
            
            activity = {
                'type': activity_type,
                'timestamp': datetime.utcnow().isoformat(),
                'details': json.dumps(details)
            }
            
            # Store in Redis list (keep last 100 activities)
            await self.redis_client.lpush(f"sharekhan:activity:{user_id}", json.dumps(activity))
            await self.redis_client.ltrim(f"sharekhan:activity:{user_id}", 0, 99)
            
        except Exception as e:
            logger.error(f"❌ Error logging activity for user {user_id}: {e}")
    
    async def _session_cleanup_loop(self):
        """Periodic cleanup of inactive sessions"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                current_time = datetime.utcnow()
                inactive_threshold = current_time - timedelta(hours=2)  # 2 hours of inactivity
                
                inactive_users = []
                for user_id, session in self.user_sessions.items():
                    if (session.last_activity and 
                        session.last_activity < inactive_threshold and 
                        session.is_connected):
                        inactive_users.append(user_id)
                
                # Disconnect inactive sessions
                for user_id in inactive_users:
                    logger.info(f"🔄 Disconnecting inactive session: {user_id}")
                    await self.disconnect_user_session(user_id)
                
                if inactive_users:
                    logger.info(f"✅ Cleaned up {len(inactive_users)} inactive sessions")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in session cleanup loop: {e}")
    
    async def cleanup(self):
        """Cleanup all resources"""
        try:
            # Cancel cleanup task
            if self.session_cleanup_task:
                self.session_cleanup_task.cancel()
                try:
                    await self.session_cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Disconnect all sessions
            for user_id in list(self.user_sessions.keys()):
                await self.disconnect_user_session(user_id)
            
            # Close Redis connection
            if self.redis_client:
                await self.redis_client.close()
            
            logger.info("✅ MultiUserShareKhanManager cleaned up successfully")
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")

# Global instance
multi_user_sharekhan_manager = MultiUserShareKhanManager() 