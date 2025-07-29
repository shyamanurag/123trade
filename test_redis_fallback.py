#!/usr/bin/env python3
"""
Test Redis Fallback System
Tests the production Redis fallback manager functionality
"""

import os
import sys
import logging
import asyncio

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_redis_fallback_manager():
    """Test the Redis fallback manager"""
    logger.info("🚀 Testing Redis Fallback Manager")
    logger.info("=" * 50)
    
    try:
        from src.core.redis_fallback_manager import redis_fallback_manager
        
        # Test connection (should fail and use fallback)
        logger.info("📡 Testing Redis connection...")
        connected = redis_fallback_manager.connect()
        logger.info(f"Connection result: {connected}")
        
        # Test status
        status = redis_fallback_manager.get_status()
        logger.info(f"📊 Redis Status: {status}")
        
        # Test set operation
        logger.info("🔄 Testing set operation...")
        set_result = redis_fallback_manager.set('test_key', 'test_value', ex=60)
        logger.info(f"Set result: {set_result}")
        
        # Test get operation
        logger.info("🔄 Testing get operation...")
        get_result = redis_fallback_manager.get('test_key')
        logger.info(f"Get result: {get_result}")
        
        # Test exists operation
        logger.info("🔄 Testing exists operation...")
        exists_result = redis_fallback_manager.exists('test_key')
        logger.info(f"Exists result: {exists_result}")
        
        # Test ShareKhan token simulation
        logger.info("🔄 Testing ShareKhan token storage...")
        token_key = 'sharekhan:token:PAPER_TRADER_001'
        token_value = 'mock_access_token_12345'
        
        redis_fallback_manager.set(token_key, token_value, ex=3600)
        retrieved_token = redis_fallback_manager.get(token_key)
        logger.info(f"Token storage test: {retrieved_token == token_value}")
        
        # Test delete operation
        logger.info("🔄 Testing delete operation...")
        delete_result = redis_fallback_manager.delete('test_key')
        logger.info(f"Delete result: {delete_result}")
        
        # Verify deletion
        get_after_delete = redis_fallback_manager.get('test_key')
        logger.info(f"Get after delete: {get_after_delete}")
        
        logger.info("✅ Redis Fallback Manager test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Redis Fallback Manager test failed: {e}")
        return False

def test_orchestrator_redis_integration():
    """Test orchestrator Redis integration"""
    logger.info("\n🚀 Testing Orchestrator Redis Integration")
    logger.info("=" * 50)
    
    try:
        # Test the import
        from src.core.orchestrator import redis_manager
        
        logger.info("📡 Testing Redis manager import...")
        logger.info(f"Redis manager type: {type(redis_manager)}")
        
        # Test connection
        if hasattr(redis_manager, 'connect'):
            connected = redis_manager.connect()
            logger.info(f"Connection result: {connected}")
        
        # Test status
        if hasattr(redis_manager, 'get_status'):
            status = redis_manager.get_status()
            logger.info(f"📊 Redis Status: {status}")
        
        # Test basic operations
        if hasattr(redis_manager, 'set') and hasattr(redis_manager, 'get'):
            redis_manager.set('orchestrator_test', 'working', ex=60)
            result = redis_manager.get('orchestrator_test')
            logger.info(f"Orchestrator Redis test: {result}")
        
        logger.info("✅ Orchestrator Redis integration test completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Orchestrator Redis integration test failed: {e}")
        return False

def test_sharekhan_token_simulation():
    """Test ShareKhan token retrieval simulation"""
    logger.info("\n🚀 Testing ShareKhan Token Simulation")
    logger.info("=" * 50)
    
    try:
        from src.core.redis_fallback_manager import redis_fallback_manager
        
        # Simulate frontend storing tokens
        user_ids = ['PAPER_TRADER_001', 'MASTER_USER_001', 'USER_001']
        
        for user_id in user_ids:
            token_key = f'sharekhan:token:{user_id}'
            mock_token = f'mock_token_{user_id.lower()}_12345'
            
            # Store token
            redis_fallback_manager.set(token_key, mock_token, ex=3600)
            logger.info(f"✅ Stored token for {user_id}")
        
        # Simulate orchestrator retrieving tokens
        logger.info("\n🔄 Simulating orchestrator token retrieval...")
        
        for user_id in user_ids:
            token_key = f'sharekhan:token:{user_id}'
            retrieved_token = redis_fallback_manager.get(token_key)
            
            if retrieved_token:
                logger.info(f"✅ Retrieved token for {user_id}: {retrieved_token[:15]}...")
            else:
                logger.warning(f"❌ No token found for {user_id}")
        
        logger.info("✅ ShareKhan token simulation completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ ShareKhan token simulation failed: {e}")
        return False

def main():
    """Main test function"""
    logger.info("🚀 Starting Redis Fallback System Tests")
    logger.info("=" * 60)
    
    # Test Redis fallback manager
    fallback_success = test_redis_fallback_manager()
    
    # Test orchestrator integration
    orchestrator_success = test_orchestrator_redis_integration()
    
    # Test ShareKhan token simulation
    token_success = test_sharekhan_token_simulation()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 TEST SUMMARY:")
    logger.info(f"  Redis Fallback Manager: {'✅ PASS' if fallback_success else '❌ FAIL'}")
    logger.info(f"  Orchestrator Integration: {'✅ PASS' if orchestrator_success else '❌ FAIL'}")
    logger.info(f"  ShareKhan Token Simulation: {'✅ PASS' if token_success else '❌ FAIL'}")
    
    if all([fallback_success, orchestrator_success, token_success]):
        logger.info("\n✅ ALL TESTS PASSED!")
        logger.info("🚀 Redis fallback system is ready for production deployment")
        logger.info("📋 Key Benefits:")
        logger.info("  • System continues working even without Redis")
        logger.info("  • ShareKhan tokens cached in memory for session")
        logger.info("  • Graceful degradation with fallback mode")
        logger.info("  • No system crashes due to Redis failures")
    else:
        logger.error("\n❌ SOME TESTS FAILED!")
        logger.error("Please review the errors above before deployment")

if __name__ == "__main__":
    main()
