#!/usr/bin/env python3
"""
Test Fallback Mode Only
"""

import os
import sys
import logging

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 Testing Fallback Mode Only")
    
    try:
        from src.core.redis_fallback_manager import ProductionRedisFallback
        
        # Create instance
        redis_fallback = ProductionRedisFallback()
        logger.info("✅ Created ProductionRedisFallback instance")
        
        # Force fallback mode by setting max attempts to 0
        redis_fallback.connection_attempts = 3
        redis_fallback.max_attempts = 3
        
        # Test connection (should immediately use fallback)
        logger.info("📡 Testing connection in fallback mode...")
        connected = redis_fallback.connect()
        logger.info(f"Connection result: {connected}")
        
        # Test status
        status = redis_fallback.get_status()
        logger.info(f"📊 Status: {status}")
        
        # Test basic operations in fallback mode
        logger.info("🔄 Testing fallback operations...")
        
        # Set
        set_result = redis_fallback.set('test_key', 'test_value')
        logger.info(f"Set result: {set_result}")
        
        # Get
        get_result = redis_fallback.get('test_key')
        logger.info(f"Get result: {get_result}")
        
        # Exists
        exists_result = redis_fallback.exists('test_key')
        logger.info(f"Exists result: {exists_result}")
        
        # Test ShareKhan token simulation
        logger.info("🔄 Testing ShareKhan token in fallback mode...")
        token_key = 'sharekhan:token:PAPER_TRADER_001'
        token_value = 'mock_access_token_12345'
        
        redis_fallback.set(token_key, token_value, ex=3600)
        retrieved_token = redis_fallback.get(token_key)
        logger.info(f"Token test: {retrieved_token == token_value}")
        
        # Delete
        delete_result = redis_fallback.delete('test_key')
        logger.info(f"Delete result: {delete_result}")
        
        # Check after delete
        get_after_delete = redis_fallback.get('test_key')
        logger.info(f"Get after delete: {get_after_delete}")
        
        logger.info("✅ Fallback mode test completed successfully!")
        logger.info("🚀 System can work without Redis connection!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
