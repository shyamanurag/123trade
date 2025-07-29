"""
ShareKhan Token Manager
Handles token storage, retrieval, and validation with proper Redis connection handling
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class ShareKhanTokenManager:
    """Manages ShareKhan token storage and retrieval with enhanced reliability"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.user_id = os.getenv('SHAREKHAN_USER_ID', 'QSW899')
        
        # Check if SSL is required (DigitalOcean managed Redis)
        self.ssl_required = (
            'ondigitalocean.com' in self.redis_url or 
            self.redis_url.startswith('rediss://')
        )
        
        logger.info(f"Token Manager initialized for user: {self.user_id}")
    
    async def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client with proper SSL configuration"""
        try:
            if self.redis_client is None:
                # Parse Redis URL for connection details
                from urllib.parse import urlparse
                parsed = urlparse(self.redis_url)
                
                config = {
                    'host': parsed.hostname or 'localhost',
                    'port': parsed.port or 6379,
                    'password': parsed.password,
                    'db': int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0,
                    'decode_responses': True,
                    'socket_timeout': 10,
                    'socket_connect_timeout': 10,
                    'retry_on_timeout': True,
                    'health_check_interval': 30
                }
                
                # CRITICAL FIX: DigitalOcean Redis requires SSL even with redis:// URLs
                if self.ssl_required or 'ondigitalocean.com' in self.redis_url:
                    config.update({
                        'ssl': True,
                        'ssl_cert_reqs': None,
                        'ssl_check_hostname': False,
                        'retry_on_timeout': True
                    })
                
                self.redis_client = redis.Redis(**config)
                
                # Test connection
                await self.redis_client.ping()
                logger.info("✅ Redis connection established for token manager")
            
            return self.redis_client
            
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self.redis_client = None
            return None
    
    async def get_token(self, user_id: Optional[str] = None) -> Optional[str]:
        """Get ShareKhan token with comprehensive key search"""
        target_user_id = user_id or self.user_id
        
        try:
            client = await self._get_redis_client()
            if not client:
                logger.warning("⚠️ Redis not available, cannot retrieve token")
                return None
            
            # Define all possible token key patterns
            token_keys_to_check = [
                f"sharekhan:token:{target_user_id}",
                f"sharekhan:token:{os.getenv('SHAREKHAN_USER_ID', 'QSW899')}",
                f"sharekhan:token:PAPER_TRADER_MAIN", 
                f"sharekhan:token:QSW899",
                f"sharekhan:{target_user_id}:access_token",
                f"sharekhan:access_token",
                f"sharekhan_token_{target_user_id}",
                f"sharekhan:token:SHAREKHAN_DEFAULT"
            ]
            
            # Check each key pattern
            for key in token_keys_to_check:
                try:
                    stored_token = await client.get(key)
                    if stored_token:
                        logger.info(f"✅ Found token with key: {key}")
                        return stored_token
                except Exception as e:
                    logger.warning(f"⚠️ Failed to check key {key}: {e}")
                    continue
            
            # If no token found in specific keys, search all sharekhan:token:* keys
            logger.info("🔍 Searching all sharekhan:token:* keys...")
            try:
                all_keys = await client.keys("sharekhan:token:*")
                logger.info(f"🔍 Found {len(all_keys)} sharekhan:token:* keys")
                
                for key in all_keys:
                    try:
                        key_str = key.decode() if isinstance(key, bytes) else key
                        stored_token = await client.get(key)
                        if stored_token:
                            logger.info(f"✅ Found token with wildcard key: {key_str}")
                            return stored_token
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to check wildcard key {key}: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"❌ Failed to search wildcard keys: {e}")
            
            logger.warning(f"❌ No token found for user {target_user_id}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Token retrieval failed: {e}")
            return None
    
    async def store_token(self, token: str, user_id: Optional[str] = None, expiry_hours: int = 18) -> bool:
        """Store ShareKhan token with proper expiry"""
        target_user_id = user_id or self.user_id
        
        try:
            client = await self._get_redis_client()
            if not client:
                logger.warning("⚠️ Redis not available, cannot store token")
                return False
            
            # Store token with expiry
            key = f"sharekhan:token:{target_user_id}"
            expiry_seconds = expiry_hours * 3600
            
            await client.set(key, token, ex=expiry_seconds)
            
            # Also store expiry time for reference
            expiry_time = datetime.now() + timedelta(hours=expiry_hours)
            await client.set(f"sharekhan:token_expiry:{target_user_id}", expiry_time.isoformat())
            
            logger.info(f"✅ Token stored for user {target_user_id} with {expiry_hours}h expiry")
            return True
            
        except Exception as e:
            logger.error(f"❌ Token storage failed: {e}")
            return False
    
    async def validate_token(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Validate token and return status"""
        target_user_id = user_id or self.user_id
        
        try:
            token = await self.get_token(target_user_id)
            
            if not token:
                return {
                    'valid': False,
                    'message': 'No token found',
                    'user_id': target_user_id
                }
            
            # Check expiry if available
            client = await self._get_redis_client()
            if client:
                expiry_key = f"sharekhan:token_expiry:{target_user_id}"
                expiry_time = await client.get(expiry_key)
                
                if expiry_time:
                    try:
                        expiry_dt = datetime.fromisoformat(expiry_time)
                        if expiry_dt <= datetime.now():
                            return {
                                'valid': False,
                                'message': 'Token expired',
                                'user_id': target_user_id,
                                'expired_at': expiry_time
                            }
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to parse expiry time: {e}")
            
            return {
                'valid': True,
                'message': 'Token is valid',
                'user_id': target_user_id,
                'token_preview': token[:10] + '...' if len(token) > 10 else token
            }
            
        except Exception as e:
            logger.error(f"❌ Token validation failed: {e}")
            return {
                'valid': False,
                'message': f'Validation error: {str(e)}',
                'user_id': target_user_id
            }
    
    async def get_all_tokens(self) -> Dict[str, Any]:
        """Get all stored tokens for debugging"""
        try:
            client = await self._get_redis_client()
            if not client:
                return {'error': 'Redis not available'}
            
            all_keys = await client.keys("sharekhan:token:*")
            tokens = {}
            
            for key in all_keys:
                try:
                    key_str = key.decode() if isinstance(key, bytes) else key
                    token = await client.get(key)
                    if token:
                        tokens[key_str] = {
                            'token_preview': token[:10] + '...' if len(token) > 10 else token,
                            'length': len(token)
                        }
                except Exception as e:
                    tokens[key_str] = {'error': str(e)}
            
            return {
                'total_keys': len(all_keys),
                'tokens': tokens
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get all tokens: {e}")
            return {'error': str(e)}
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

# Global instance
token_manager = ShareKhanTokenManager()

async def get_token_manager() -> ShareKhanTokenManager:
    """Get the global token manager instance"""
    return token_manager 