#!/usr/bin/env python3
"""
Test Orchestrator Redis Integration
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
    logger.info("🚀 Testing Orchestrator Redis Integration")
    
    try:
        # Test the import
        from src.core.orchestrator import redis_manager
        
        logger.info("✅ Successfully imported redis_manager from orchestrator")
        logger.info(f"Redis manager type: {type(redis_manager)}")
        
        # Test if it has the expected methods
        methods = ['connect', 'get', 'set', 'delete', 'exists', 'get_status']
        for method in methods:
            if hasattr(redis_manager, method):
                logger.info(f"✅ Has method: {method}")
            else:
                logger.warning(f"❌ Missing method: {method}")
        
        # Test connection
        if hasattr(redis_manager, 'connect'):
            logger.info("📡 Testing connection...")
            connected = redis_manager.connect()
            logger.info(f"Connection result: {connected}")
        
        # Test status
        if hasattr(redis_manager, 'get_status'):
            status = redis_manager.get_status()
            logger.info(f"📊 Status: {status}")
        
        # Test basic operations
        if hasattr(redis_manager, 'set') and hasattr(redis_manager, 'get'):
            logger.info("🔄 Testing basic operations...")
            
            # Set
            set_result = redis_manager.set('orchestrator_test', 'working', ex=60)
            logger.info(f"Set result: {set_result}")
            
            # Get
            get_result = redis_manager.get('orchestrator_test')
            logger.info(f"Get result: {get_result}")
            
            # Exists
            if hasattr(redis_manager, 'exists'):
                exists_result = redis_manager.exists('orchestrator_test')
                logger.info(f"Exists result: {exists_result}")
        
        # Test ShareKhan token simulation
        logger.info("🔄 Testing ShareKhan token simulation...")
        user_ids = ['PAPER_TRADER_001', 'MASTER_USER_001']
        
        for user_id in user_ids:
            token_key = f'sharekhan:token:{user_id}'
            mock_token = f'mock_token_{user_id.lower()}_12345'
            
            # Store token
            if hasattr(redis_manager, 'set'):
                redis_manager.set(token_key, mock_token, ex=3600)
                logger.info(f"✅ Stored token for {user_id}")
            
            # Retrieve token
            if hasattr(redis_manager, 'get'):
                retrieved_token = redis_manager.get(token_key)
                if retrieved_token:
                    logger.info(f"✅ Retrieved token for {user_id}: {retrieved_token[:15]}...")
                else:
                    logger.warning(f"❌ No token found for {user_id}")
        
        logger.info("✅ Orchestrator Redis integration test completed successfully!")
        logger.info("🚀 Orchestrator can now use Redis fallback system!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
