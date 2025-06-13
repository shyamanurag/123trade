"""
Unit tests for webhook functionality
"""
import pytest
import json
from unittest.mock import Mock, patch
from src.api.webhook import WebhookHandler

@pytest.fixture
def webhook_handler():
    """Create a WebhookHandler instance for testing"""
    return WebhookHandler()

@pytest.fixture
def sample_webhook_data():
    """Sample webhook data for testing"""
    return {
        "type": "trade",
        "symbol": "NIFTY",
        "price": 19000.0,
        "quantity": 100,
        "timestamp": "2024-01-06T14:30:00Z"
    }

def test_webhook_validation(webhook_handler, sample_webhook_data):
    """Test webhook data validation"""
    # Test valid data
    assert webhook_handler.validate_webhook_data(sample_webhook_data) is True
    
    # Test invalid data
    invalid_data = sample_webhook_data.copy()
    del invalid_data["type"]
    assert webhook_handler.validate_webhook_data(invalid_data) is False

@patch('src.api.webhook.WebhookHandler.process_webhook')
def test_webhook_processing(mock_process, webhook_handler, sample_webhook_data):
    """Test webhook processing"""
    # Process webhook
    result = webhook_handler.handle_webhook(sample_webhook_data)
    
    # Verify processing was called
    mock_process.assert_called_once_with(sample_webhook_data)
    assert result["status"] == "success"

def test_webhook_error_handling(webhook_handler):
    """Test webhook error handling"""
    # Test with invalid data
    result = webhook_handler.handle_webhook({})
    assert result["status"] == "error"
    assert "error" in result

@patch('src.api.webhook.WebhookHandler.notify_subscribers')
def test_webhook_notification(mock_notify, webhook_handler, sample_webhook_data):
    """Test webhook notification to subscribers"""
    # Process webhook
    webhook_handler.handle_webhook(sample_webhook_data)
    
    # Verify notification was sent
    mock_notify.assert_called_once_with(sample_webhook_data)

def test_webhook_rate_limiting(webhook_handler, sample_webhook_data):
    """Test webhook rate limiting"""
    # Send multiple webhooks in quick succession
    for _ in range(10):
        result = webhook_handler.handle_webhook(sample_webhook_data)
        assert result["status"] == "success"
    
    # Verify rate limiting is enforced
    result = webhook_handler.handle_webhook(sample_webhook_data)
    assert result["status"] == "error"
    assert "rate limit" in result["error"].lower() 