#!/usr/bin/env python3
"""
Fix Redis Configuration for Production Deployment
Creates proper Redis configuration for Digital Ocean environment
"""

import os
import sys
import logging

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_redis_fallback_manager():
    """Create a Redis fallback manager for production"""
    
    redis_fallback_content = '''"""
Production Redis Manager with Fallback Support
Handles Redis connection failures gracefully in production
"""

import os
import logging
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)

class ProductionRedisFallback:
    """Redis manager with in-memory fallback for production resilience"""
    
    def __init__(self):
        self.redis_client = None
        self.is_connected = False
        self.fallback_cache = {}  # In-memory fallback
        self.connection_attempts = 0
        self.max_attempts = 3
        
    def connect(self) -> bool:
        """Attempt to connect to Redis with fallback to in-memory cache"""
        if self.connection_attempts >= self.max_attempts:
            logger.warning("🔄 Max Redis connection attempts reached, using fallback mode")
            return True  # Use fallback mode
        
        try:
            import redis
            
            # Try to get Redis configuration from environment
            redis_url = os.getenv('REDIS_URL')
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_password = os.getenv('REDIS_PASSWORD')
            
            if redis_url:
                # Use URL-based connection
                self.redis_client = redis.Redis.from_url(
                    redis_url,
                    password=redis_password,
                    decode_responses=True,
                    socket_timeout=2,
                    socket_connect_timeout=2
                )
            else:
                # Use host/port connection
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    password=redis_password,
                    decode_responses=True,
                    socket_timeout=2,
                    socket_connect_timeout=2
                )
            
            # Test connection
            self.redis_client.ping()
            self.is_connected = True
            logger.info("✅ Redis connection established")
            return True
            
        except Exception as e:
            self.connection_attempts += 1
            logger.warning(f"⚠️ Redis connection failed (attempt {self.connection_attempts}): {e}")
            logger.info("🔄 Falling back to in-memory cache")
            self.redis_client = None
            self.is_connected = False
            return True  # Still return True to use fallback
    
    def get(self, key: str) -> Optional[str]:
        """Get value from Redis or fallback cache"""
        try:
            if self.redis_client and self.is_connected:
                return self.redis_client.get(key)
            else:
                # Use fallback cache
                return self.fallback_cache.get(key)
        except Exception as e:
            logger.warning(f"⚠️ Redis get failed for key {key}: {e}")
            return self.fallback_cache.get(key)
    
    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value in Redis or fallback cache"""
        try:
            if self.redis_client and self.is_connected:
                result = self.redis_client.set(key, value, ex=ex)
                # Also store in fallback cache
                self.fallback_cache[key] = value
                return result
            else:
                # Use fallback cache
                self.fallback_cache[key] = value
                return True
        except Exception as e:
            logger.warning(f"⚠️ Redis set failed for key {key}: {e}")
            self.fallback_cache[key] = value
            return True
    
    def delete(self, key: str) -> bool:
        """Delete key from Redis or fallback cache"""
        try:
            if self.redis_client and self.is_connected:
                result = self.redis_client.delete(key)
                # Also remove from fallback cache
                self.fallback_cache.pop(key, None)
                return bool(result)
            else:
                # Use fallback cache
                self.fallback_cache.pop(key, None)
                return True
        except Exception as e:
            logger.warning(f"⚠️ Redis delete failed for key {key}: {e}")
            self.fallback_cache.pop(key, None)
            return True
    
    def exists(self, key: str) -> bool:
        """Check if key exists in Redis or fallback cache"""
        try:
            if self.redis_client and self.is_connected:
                return bool(self.redis_client.exists(key))
            else:
                return key in self.fallback_cache
        except Exception as e:
            logger.warning(f"⚠️ Redis exists failed for key {key}: {e}")
            return key in self.fallback_cache
    
    def get_status(self) -> Dict[str, Any]:
        """Get Redis connection status"""
        return {
            'connected': self.is_connected,
            'fallback_mode': not self.is_connected,
            'fallback_cache_size': len(self.fallback_cache),
            'connection_attempts': self.connection_attempts
        }

# Global instance
redis_fallback_manager = ProductionRedisFallback()

# Convenience functions
def get_redis_client():
    """Get Redis client with fallback support"""
    if not redis_fallback_manager.is_connected:
        redis_fallback_manager.connect()
    return redis_fallback_manager

def get_redis_fallback():
    """Get Redis fallback manager"""
    return redis_fallback_manager
'''
    
    # Write the fallback manager
    with open('src/core/redis_fallback_manager.py', 'w') as f:
        f.write(redis_fallback_content)
    
    logger.info("✅ Created Redis fallback manager")

def update_orchestrator_redis_handling():
    """Update orchestrator to use Redis fallback manager"""
    
    # Read current orchestrator
    with open('src/core/orchestrator.py', 'r') as f:
        content = f.read()
    
    # Add import for Redis fallback manager
    if 'redis_fallback_manager' not in content:
        # Find the redis_manager import and replace it
        import_section = '''try:
    from src.core.redis_manager import redis_manager
except ImportError:
    # Fallback Redis manager for production resilience
    try:
        from src.core.redis_fallback_manager import redis_fallback_manager as redis_manager
    except ImportError:
        logger.warning("⚠️ No Redis manager available, using dummy implementation")
        class DummyRedisManager:
            def connect(self): return False
            def get(self, key): return None
            def set(self, key, value, ex=None): return False
            def delete(self, key): return False
            def get_status(self): return {'connected': False, 'fallback_mode': True}
        redis_manager = DummyRedisManager()'''
        
        # Replace the existing redis_manager import
        old_import = '''try:
    from src.core.redis_manager import redis_manager
except ImportError:
    logger.warning("⚠️ Redis manager not available - using dummy implementation")
    class DummyRedisManager:
        def connect(self): return False
        def get(self, key): return None
        def set(self, key, value, ex=None): return False
        def delete(self, key): return False
    redis_manager = DummyRedisManager()'''
        
        if old_import in content:
            content = content.replace(old_import, import_section)
        else:
            # Add after the existing import section
            content = content.replace(
                '# CRITICAL FIX: Import redis_manager after it\'s defined',
                '# CRITICAL FIX: Import redis_manager after it\'s defined\n' + import_section
            )
    
    # Update the _get_access_token_from_redis method to handle connection failures
    redis_method_update = '''    async def _get_access_token_from_redis(self, user_id: str) -> Optional[str]:
        """Get access token from Redis where frontend stores it"""
        try:
            # Connect to Redis with fallback support
            if not self.redis_manager.connect():
                self.logger.warning(f"⚠️ Redis connection failed, cannot retrieve token for {user_id}")
                return None
            
            # Try to get token from Redis
            token_key = f'sharekhan:token:{user_id}'
            access_token = self.redis_manager.get(token_key)
            
            if access_token:
                self.logger.info(f"✅ Retrieved access token for {user_id} from Redis")
                return access_token
            else:
                self.logger.warning(f"⚠️ No access token found in Redis for {user_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error retrieving access token from Redis for {user_id}: {e}")
            return None'''
    
    # Replace the existing method if it exists
    if '_get_access_token_from_redis' in content:
        # Find and replace the method
        import re
        pattern = r'async def _get_access_token_from_redis\(self, user_id: str\) -> Optional\[str\]:.*?(?=\n    async def|\n    def|\nclass|\Z)'
        content = re.sub(pattern, redis_method_update.strip(), content, flags=re.DOTALL)
    
    # Write updated orchestrator
    with open('src/core/orchestrator.py', 'w') as f:
        f.write(content)
    
    logger.info("✅ Updated orchestrator Redis handling")

def create_environment_config():
    """Create environment configuration for production"""
    
    env_config = '''# Production Environment Configuration for Digital Ocean
# These should be set as environment variables in the deployment

# Redis Configuration (Digital Ocean Managed Redis or external Redis service)
REDIS_URL=redis://localhost:6379
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_SSL=false

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/trading_system
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=trading_system
DATABASE_USER=user
DATABASE_PASSWORD=password

# Trading Configuration
PAPER_TRADING=true
AUTONOMOUS_TRADING_ENABLED=true
SHAREKHAN_SANDBOX_MODE=true

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
ENABLE_CORS=true
CORS_ORIGINS=*

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Security
JWT_SECRET=your-production-jwt-secret-key
ENCRYPTION_KEY=your-32-byte-encryption-key-here
WEBHOOK_SECRET=your-webhook-secret

# ShareKhan Configuration
SHAREKHAN_USERNAME=your-sharekhan-username
SHAREKHAN_PASSWORD=your-sharekhan-password
SHAREKHAN_URL=https://api.sharekhan.in
SHAREKHAN_LIVE_PORT=8082

# ShareKhan Configuration
SHAREKHAN_API_KEY=your-sharekhan-api-key
SHAREKHAN_API_SECRET=your-sharekhan-api-secret
SHAREKHAN_USER_ID=your-sharekhan-user-id
'''
    
    with open('.env.production', 'w') as f:
        f.write(env_config)
    
    logger.info("✅ Created production environment configuration")

def main():
    """Main fix function"""
    logger.info("🚀 Fixing Redis Configuration for Production")
    logger.info("=" * 60)
    
    # Create Redis fallback manager
    create_redis_fallback_manager()
    
    # Update orchestrator
    update_orchestrator_redis_handling()
    
    # Create environment config
    create_environment_config()
    
    logger.info("\n✅ Redis Production Fix Complete!")
    logger.info("=" * 60)
    logger.info("📋 Next Steps:")
    logger.info("1. Deploy the updated code to Digital Ocean")
    logger.info("2. Configure Redis service in Digital Ocean (optional)")
    logger.info("3. Set environment variables in Digital Ocean App Platform")
    logger.info("4. System will use in-memory fallback if Redis is unavailable")
    logger.info("5. ShareKhan tokens will be cached in memory for the session")

if __name__ == "__main__":
    main()
