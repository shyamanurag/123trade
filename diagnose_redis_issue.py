#!/usr/bin/env python3
"""
Redis Connection Diagnostic Script
Diagnoses Redis connection issues in production environment
"""

import os
import sys
import logging
import asyncio
from typing import Optional

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_environment_variables():
    """Check Redis-related environment variables"""
    logger.info("🔍 Checking Redis Environment Variables:")
    
    redis_vars = [
        'REDIS_URL', 'REDIS_HOST', 'REDIS_PORT', 'REDIS_PASSWORD', 
        'REDIS_DB', 'REDIS_SSL', 'REDIS_USERNAME'
    ]
    
    for var in redis_vars:
        value = os.getenv(var)
        if value:
            # Mask password for security
            if 'PASSWORD' in var:
                masked_value = '*' * len(value) if len(value) > 0 else 'None'
                logger.info(f"  ✅ {var}: {masked_value}")
            else:
                logger.info(f"  ✅ {var}: {value}")
        else:
            logger.info(f"  ❌ {var}: Not set")

def test_basic_redis_connection():
    """Test basic Redis connection using redis-py"""
    logger.info("\n🔍 Testing Basic Redis Connection:")
    
    try:
        import redis
        
        # Try different connection methods
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_password = os.getenv('REDIS_PASSWORD')
        redis_ssl = os.getenv('REDIS_SSL', 'false').lower() == 'true'
        
        logger.info(f"  📡 Attempting connection to: {redis_url}")
        
        # Method 1: Using URL
        try:
            client = redis.Redis.from_url(
                redis_url,
                password=redis_password,
                ssl=redis_ssl,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            # Test connection
            result = client.ping()
            logger.info(f"  ✅ URL Connection successful: {result}")
            
            # Test basic operations
            client.set('test_key', 'test_value', ex=60)
            value = client.get('test_key')
            logger.info(f"  ✅ Set/Get test successful: {value}")
            
            client.delete('test_key')
            return True
            
        except Exception as e:
            logger.error(f"  ❌ URL Connection failed: {e}")
        
        # Method 2: Using host/port
        try:
            client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                ssl=redis_ssl,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            result = client.ping()
            logger.info(f"  ✅ Host/Port Connection successful: {result}")
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Host/Port Connection failed: {e}")
            
    except ImportError:
        logger.error("  ❌ Redis library not installed")
    
    return False

async def test_async_redis_connection():
    """Test async Redis connection"""
    logger.info("\n🔍 Testing Async Redis Connection:")
    
    try:
        import redis.asyncio as redis
        
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        redis_password = os.getenv('REDIS_PASSWORD')
        redis_ssl = os.getenv('REDIS_SSL', 'false').lower() == 'true'
        
        client = redis.Redis.from_url(
            redis_url,
            password=redis_password,
            ssl=redis_ssl,
            decode_responses=True
        )
        
        result = await client.ping()
        logger.info(f"  ✅ Async Connection successful: {result}")
        
        await client.close()
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Async Connection failed: {e}")
        return False

def test_production_redis_manager():
    """Test the production Redis manager"""
    logger.info("\n🔍 Testing Production Redis Manager:")
    
    try:
        from src.core.redis_connection_manager import redis_manager
        
        # Test connection
        if redis_manager.connect():
            logger.info("  ✅ Production Redis Manager connected")
            
            # Test operations
            if redis_manager.set('test_key', 'test_value', ex=60):
                logger.info("  ✅ Set operation successful")
            
            value = redis_manager.get('test_key')
            if value:
                logger.info(f"  ✅ Get operation successful: {value}")
            
            redis_manager.delete('test_key')
            return True
        else:
            logger.error("  ❌ Production Redis Manager connection failed")
            
    except Exception as e:
        logger.error(f"  ❌ Production Redis Manager error: {e}")
    
    return False

def test_sharekhan_token_retrieval():
    """Test ShareKhan token retrieval from Redis"""
    logger.info("\n🔍 Testing ShareKhan Token Retrieval:")
    
    try:
        from src.core.redis_connection_manager import redis_manager
        
        if not redis_manager.connect():
            logger.error("  ❌ Cannot connect to Redis for token test")
            return False
        
        # Test token retrieval for different user IDs
        user_ids = ['PAPER_TRADER_001', 'MASTER_USER_001', 'USER_001']
        
        for user_id in user_ids:
            token_key = f'sharekhan:token:{user_id}'
            token = redis_manager.get(token_key)
            
            if token:
                logger.info(f"  ✅ Token found for {user_id}: {token[:10]}...")
            else:
                logger.info(f"  ❌ No token found for {user_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Token retrieval test failed: {e}")
        return False

def main():
    """Main diagnostic function"""
    logger.info("🚀 Starting Redis Connection Diagnostics")
    logger.info("=" * 60)
    
    # Check environment
    check_environment_variables()
    
    # Test basic connection
    basic_success = test_basic_redis_connection()
    
    # Test async connection
    async_success = asyncio.run(test_async_redis_connection())
    
    # Test production manager
    manager_success = test_production_redis_manager()
    
    # Test token retrieval
    token_success = test_sharekhan_token_retrieval()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 DIAGNOSTIC SUMMARY:")
    logger.info(f"  Basic Redis Connection: {'✅ PASS' if basic_success else '❌ FAIL'}")
    logger.info(f"  Async Redis Connection: {'✅ PASS' if async_success else '❌ FAIL'}")
    logger.info(f"  Production Manager: {'✅ PASS' if manager_success else '❌ FAIL'}")
    logger.info(f"  Token Retrieval: {'✅ PASS' if token_success else '❌ FAIL'}")
    
    if not any([basic_success, async_success, manager_success]):
        logger.error("\n❌ CRITICAL: No Redis connections working!")
        logger.error("Possible causes:")
        logger.error("  1. Redis service not running")
        logger.error("  2. Incorrect connection credentials")
        logger.error("  3. Network connectivity issues")
        logger.error("  4. SSL/TLS configuration problems")
        logger.error("  5. Missing environment variables")
    else:
        logger.info("\n✅ At least one Redis connection method is working")

if __name__ == "__main__":
    main()
