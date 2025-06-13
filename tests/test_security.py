"""
Security Module Test Script
Tests encryption, JWT tokens, and webhook verification
"""

import asyncio
import time
import json
import logging
from pathlib import Path
import yaml
import redis.asyncio as redis
from typing import Dict, Optional

from security.auth_manager import SecurityManager
from security.secure_config import SecureConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_CONFIG = {
    'security': {
        'jwt_secret': 'test_jwt_secret',
        'webhook_secret': 'test_webhook_secret',
        'encryption_key': None,  # Will be generated
        'allowed_ips': ['127.0.0.1']
    },
    'redis': {
        'url': 'redis://localhost:6379'
    }
}

async def setup_test_environment() -> tuple[Dict, redis.Redis]:
    """Set up test environment with config and Redis"""
    try:
        # Initialize Redis
        redis_client = redis.from_url(TEST_CONFIG['redis']['url'], decode_responses=True)
        await redis_client.ping()
        logger.info("✓ Redis connection successful")
        
        return TEST_CONFIG, redis_client
    except Exception as e:
        logger.error(f"Failed to set up test environment: {e}")
        raise

async def test_encryption(config_manager: SecureConfigManager):
    """Test encryption functionality"""
    try:
        # Test data
        test_data = {
            "api_key": "test123",
            "secret": "mysecret",
            "public_data": "not_encrypted"
        }
        
        # Encrypt credentials
        encrypted = config_manager.encrypt_credentials(test_data)
        
        # Verify encryption
        assert encrypted['api_key'] != test_data['api_key'], "API key should be encrypted"
        assert encrypted['secret'] != test_data['secret'], "Secret should be encrypted"
        assert encrypted['public_data'] == test_data['public_data'], "Public data should not be encrypted"
        
        # Test decryption
        decrypted = config_manager.decrypt_sensitive_data(encrypted)
        assert decrypted['api_key'] == test_data['api_key'], "Decryption failed for API key"
        assert decrypted['secret'] == test_data['secret'], "Decryption failed for secret"
        
        logger.info("✓ Encryption/decryption tests passed")
        return True
    except Exception as e:
        logger.error(f"Encryption test failed: {e}")
        return False

async def test_jwt_tokens(security_manager: SecurityManager):
    """Test JWT token functionality"""
    try:
        # Generate tokens
        tokens = await security_manager.generate_tokens("test_user")
        
        # Verify token structure
        assert 'access_token' in tokens, "Access token missing"
        assert 'refresh_token' in tokens, "Refresh token missing"
        
        # Verify access token
        decoded = await security_manager.verify_token(tokens['access_token'])
        assert decoded['sub'] == "test_user", "Token subject mismatch"
        
        # Test token refresh
        new_tokens = await security_manager.refresh_access_token(tokens['refresh_token'])
        assert new_tokens['access_token'] != tokens['access_token'], "New access token should be different"
        
        logger.info("✓ JWT token tests passed")
        return True
    except Exception as e:
        logger.error(f"JWT token test failed: {e}")
        return False

async def test_webhook_verification(security_manager: SecurityManager):
    """Test webhook signature verification"""
    try:
        # Test data
        body = b'{"test": "data"}'
        timestamp = str(int(time.time()))
        
        # Generate signature
        signature = await security_manager._generate_webhook_signature(body, timestamp)
        
        # Verify signature
        result = await security_manager.verify_webhook_signature(body, signature, timestamp)
        assert result, "Valid signature should be verified"
        
        # Test invalid signature
        invalid_result = await security_manager.verify_webhook_signature(body, "invalid", timestamp)
        assert not invalid_result, "Invalid signature should be rejected"
        
        # Test expired timestamp
        old_timestamp = str(int(time.time()) - 3600)  # 1 hour ago
        expired_result = await security_manager.verify_webhook_signature(body, signature, old_timestamp)
        assert not expired_result, "Expired timestamp should be rejected"
        
        logger.info("✓ Webhook verification tests passed")
        return True
    except Exception as e:
        logger.error(f"Webhook verification test failed: {e}")
        return False

async def test_ip_whitelist(security_manager: SecurityManager):
    """Test IP whitelist functionality"""
    try:
        # Test allowed IP
        allowed = await security_manager.validate_ip_whitelist("127.0.0.1")
        assert allowed, "Localhost IP should be allowed"
        
        # Test disallowed IP
        disallowed = await security_manager.validate_ip_whitelist("192.168.1.1")
        assert not disallowed, "Non-whitelisted IP should be rejected"
        
        logger.info("✓ IP whitelist tests passed")
        return True
    except Exception as e:
        logger.error(f"IP whitelist test failed: {e}")
        return False

async def test_rate_limiting(security_manager: SecurityManager):
    """Test rate limiting functionality"""
    try:
        # Test rate limit
        for _ in range(5):  # Assuming limit is 5 requests per minute
            result = await security_manager.check_rate_limit("test_client")
            assert result, "Rate limit should not be exceeded"
        
        # Test exceeding rate limit
        exceeded = await security_manager.check_rate_limit("test_client")
        assert not exceeded, "Rate limit should be exceeded"
        
        logger.info("✓ Rate limiting tests passed")
        return True
    except Exception as e:
        logger.error(f"Rate limiting test failed: {e}")
        return False

async def run_tests():
    """Run all security tests"""
    try:
        # Set up test environment
        config, redis_client = await setup_test_environment()
        
        # Initialize managers
        config_manager = SecureConfigManager()
        security_manager = SecurityManager(config, redis_client)
        await security_manager.start()
        
        # Run tests
        tests = [
            ("Encryption", test_encryption(config_manager)),
            ("JWT Tokens", test_jwt_tokens(security_manager)),
            ("Webhook Verification", test_webhook_verification(security_manager)),
            ("IP Whitelist", test_ip_whitelist(security_manager)),
            ("Rate Limiting", test_rate_limiting(security_manager))
        ]
        
        # Print results
        print("\nTest Results:")
        print("=" * 50)
        all_passed = True
        for name, result in tests:
            status = "✓ PASSED" if await result else "✗ FAILED"
            print(f"{name}: {status}")
            if not await result:
                all_passed = False
        
        print("=" * 50)
        print(f"Overall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
        
        # Cleanup
        await security_manager.stop()
        await redis_client.close()
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(run_tests())
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        exit(1) 