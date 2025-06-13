"""
Webhook Test Script
Tests webhook functionality for trading signals
"""

import asyncio
import logging
from datetime import datetime
import json
import requests
from typing import Dict, Optional
import pytest
from unittest.mock import patch, MagicMock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_CONFIG = {
    'webhooks': {
        'n8n': {
            'url': 'https://shyamanurag.app.n8n.cloud/webhook-test/5977c6a6-1610-48a5-a11d-374379dae499',
            'timeout': 10,
            'retry_attempts': 3,
            'retry_delay': 1
        }
    }
}

class WebhookTester:
    def __init__(self, config: Dict):
        self.config = config
        self.webhook_url = config['webhooks']['n8n']['url']
        self.timeout = config['webhooks']['n8n']['timeout']
        self.retry_attempts = config['webhooks']['n8n']['retry_attempts']
        self.retry_delay = config['webhooks']['n8n']['retry_delay']
        
    def generate_signal(self, action: str, symbol: str, quantity: int, price: float, strategy: str) -> Dict:
        """Generate a test signal with current timestamp"""
        return {
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": price,
            "strategy": strategy,
            "signal_id": f"TEST_{action}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
    
    def send_signal(self, signal: Dict) -> tuple[bool, str]:
        """Send a signal to the webhook with retry logic"""
        for attempt in range(self.retry_attempts):
            try:
                response = requests.post(
                    self.webhook_url,
                    json=signal,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    return True, response.text
                else:
                    error_msg = f"Status {response.status_code}: {response.text}"
                    if attempt < self.retry_attempts - 1:
                        logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")
                        asyncio.sleep(self.retry_delay)
                    else:
                        return False, error_msg
                        
            except requests.exceptions.Timeout:
                error_msg = "Request timed out"
                if attempt < self.retry_attempts - 1:
                    logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")
                    asyncio.sleep(self.retry_delay)
                else:
                    return False, error_msg
                    
            except requests.exceptions.ConnectionError as e:
                error_msg = f"Connection error: {str(e)}"
                if attempt < self.retry_attempts - 1:
                    logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")
                    asyncio.sleep(self.retry_delay)
                else:
                    return False, error_msg
                    
            except Exception as e:
                return False, f"Unexpected error: {str(e)}"
        
        return False, "All retry attempts failed"

async def test_buy_signal(webhook_tester: WebhookTester):
    """Test sending a BUY signal"""
    try:
        # Generate BUY signal
        buy_signal = webhook_tester.generate_signal(
            action="BUY",
            symbol="NIFTY24500CE",
            quantity=100,
            price=250.50,
            strategy="momentum"
        )
        
        print("\nTesting BUY signal:")
        print(json.dumps(buy_signal, indent=2))
        
        # Send signal
        success, response = webhook_tester.send_signal(buy_signal)
        
        if success:
            print("✅ BUY signal test passed")
            print(f"Response: {response[:200]}...")  # First 200 chars
            return True
        else:
            print(f"❌ BUY signal test failed: {response}")
            return False
            
    except Exception as e:
        print(f"❌ BUY signal test failed with error: {e}")
        return False

async def test_sell_signal(webhook_tester: WebhookTester):
    """Test sending a SELL signal"""
    try:
        # Generate SELL signal
        sell_signal = webhook_tester.generate_signal(
            action="SELL",
            symbol="BANKNIFTY24500PE",
            quantity=50,
            price=180.75,
            strategy="scalping"
        )
        
        print("\nTesting SELL signal:")
        print(json.dumps(sell_signal, indent=2))
        
        # Send signal
        success, response = webhook_tester.send_signal(sell_signal)
        
        if success:
            print("✅ SELL signal test passed")
            print(f"Response: {response[:200]}...")  # First 200 chars
            return True
        else:
            print(f"❌ SELL signal test failed: {response}")
            return False
            
    except Exception as e:
        print(f"❌ SELL signal test failed with error: {e}")
        return False

async def test_invalid_signal(webhook_tester: WebhookTester):
    """Test sending an invalid signal"""
    try:
        # Generate invalid signal (missing required fields)
        invalid_signal = {
            "symbol": "NIFTY24500CE",
            "action": "BUY",
            # Missing quantity and price
            "strategy": "momentum",
            "signal_id": f"TEST_INVALID_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        print("\nTesting invalid signal:")
        print(json.dumps(invalid_signal, indent=2))
        
        # Send signal
        success, response = webhook_tester.send_signal(invalid_signal)
        
        # We expect this to fail
        if not success:
            print("✅ Invalid signal test passed (expected failure)")
            return True
        else:
            print("❌ Invalid signal test failed (unexpected success)")
            return False
            
    except Exception as e:
        print(f"❌ Invalid signal test failed with error: {e}")
        return False

async def test_webhook_timeout(webhook_tester: WebhookTester):
    """Test webhook timeout handling"""
    try:
        # Generate test signal
        signal = webhook_tester.generate_signal(
            action="BUY",
            symbol="NIFTY24500CE",
            quantity=100,
            price=250.50,
            strategy="timeout_test"
        )
        
        print("\nTesting webhook timeout:")
        print(json.dumps(signal, indent=2))
        
        # Mock requests.post to simulate timeout
        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout()
            
            # Send signal
            success, response = webhook_tester.send_signal(signal)
            
            if not success and "timed out" in response.lower():
                print("✅ Timeout test passed")
                return True
            else:
                print("❌ Timeout test failed")
                return False
                
    except Exception as e:
        print(f"❌ Timeout test failed with error: {e}")
        return False

async def run_tests():
    """Run all webhook tests"""
    try:
        # Initialize webhook tester
        webhook_tester = WebhookTester(TEST_CONFIG)
        
        print("\nWebhook Test Results:")
        print("=" * 50)
        print(f"URL: {webhook_tester.webhook_url}")
        print("=" * 50)
        
        # Run tests
        tests = [
            ("BUY Signal", test_buy_signal(webhook_tester)),
            ("SELL Signal", test_sell_signal(webhook_tester)),
            ("Invalid Signal", test_invalid_signal(webhook_tester)),
            ("Timeout Handling", test_webhook_timeout(webhook_tester))
        ]
        
        # Print results
        all_passed = True
        for name, result in tests:
            status = "✓ PASSED" if await result else "✗ FAILED"
            print(f"{name}: {status}")
            if not await result:
                all_passed = False
        
        print("=" * 50)
        print(f"Overall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
        
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