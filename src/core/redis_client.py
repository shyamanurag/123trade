"""
Redis client singleton for the application
"""
import redis
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Singleton instance
_redis_client: Optional[redis.Redis] = None

def get_redis_client() -> redis.Redis:
    """Get the singleton Redis client instance"""
    global _redis_client
    if _redis_client is None:
        try:
            # Get Redis configuration from environment variables
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            redis_password = os.getenv('REDIS_PASSWORD')
            redis_ssl = os.getenv('REDIS_SSL', 'false').lower() == 'true'
            
            # Create Redis client
            _redis_client = redis.Redis.from_url(
                redis_url,
                password=redis_password,
                ssl=redis_ssl,
                decode_responses=True
            )
            
            # Test connection
            _redis_client.ping()
            logger.info("Redis client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            raise
            
    return _redis_client

def close_redis_client():
    """Close the Redis client connection"""
    global _redis_client
    if _redis_client is not None:
        try:
            _redis_client.close()
            _redis_client = None
            logger.info("Redis client closed")
        except Exception as e:
            logger.error(f"Error closing Redis client: {e}") 