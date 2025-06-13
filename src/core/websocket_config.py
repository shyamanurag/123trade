"""
WebSocket configuration settings
"""
from typing import Dict, Any, Optional
import os
import ssl
import logging

logger = logging.getLogger(__name__)

# Security Settings
MAX_CONNECTIONS_PER_USER = int(os.getenv('WS_MAX_CONNECTIONS_PER_USER', '3'))
MAX_MESSAGE_SIZE = int(os.getenv('WS_MAX_MESSAGE_SIZE', str(1024 * 1024)))  # 1MB
RATE_LIMIT_WINDOW = int(os.getenv('WS_RATE_LIMIT_WINDOW', '60'))  # seconds
RATE_LIMIT_MAX = int(os.getenv('WS_RATE_LIMIT_MAX', '100'))  # messages per window

# SSL/TLS Settings
USE_SSL = os.getenv('WS_USE_SSL', 'true').lower() == 'true'
SSL_CERT_PATH = os.getenv('WS_SSL_CERT_PATH', '')
SSL_KEY_PATH = os.getenv('WS_SSL_KEY_PATH', '')
SSL_VERIFY = os.getenv('WS_SSL_VERIFY', 'true').lower() == 'true'

def get_ssl_context() -> Optional[ssl.SSLContext]:
    """Get SSL context based on configuration"""
    if not USE_SSL:
        return None
        
    if not SSL_CERT_PATH or not SSL_KEY_PATH:
        logger.warning("SSL enabled but certificate paths not provided")
        return None
        
    try:
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(SSL_CERT_PATH, SSL_KEY_PATH)
        ssl_context.verify_mode = ssl.CERT_REQUIRED if SSL_VERIFY else ssl.CERT_NONE
        return ssl_context
    except Exception as e:
        logger.error(f"Error creating SSL context: {e}")
        return None

# Performance Settings
BATCH_INTERVAL = int(os.getenv('WS_BATCH_INTERVAL', '100'))  # ms
MAX_BATCH_SIZE = int(os.getenv('WS_MAX_BATCH_SIZE', '50'))  # messages

# Circuit Breaker Settings
CIRCUIT_BREAKER_THRESHOLD = int(os.getenv('WS_CIRCUIT_BREAKER_THRESHOLD', '5'))
CIRCUIT_BREAKER_TIMEOUT = int(os.getenv('WS_CIRCUIT_BREAKER_TIMEOUT', '30'))  # seconds

# Connection Settings
HEARTBEAT_INTERVAL = int(os.getenv('WS_HEARTBEAT_INTERVAL', '30'))  # seconds
CONNECTION_TIMEOUT = int(os.getenv('WS_CONNECTION_TIMEOUT', '60'))  # seconds

# Monitoring Settings
ENABLE_METRICS = os.getenv('WS_ENABLE_METRICS', 'true').lower() == 'true'
METRICS_INTERVAL = int(os.getenv('WS_METRICS_INTERVAL', '60'))  # seconds

# Default configuration
DEFAULT_CONFIG: Dict[str, Any] = {
    'security': {
        'max_connections_per_user': MAX_CONNECTIONS_PER_USER,
        'max_message_size': MAX_MESSAGE_SIZE,
        'rate_limit_window': RATE_LIMIT_WINDOW,
        'rate_limit_max': RATE_LIMIT_MAX,
        'use_ssl': USE_SSL,
        'ssl_verify': SSL_VERIFY
    },
    'performance': {
        'batch_interval': BATCH_INTERVAL,
        'max_batch_size': MAX_BATCH_SIZE,
    },
    'circuit_breaker': {
        'threshold': CIRCUIT_BREAKER_THRESHOLD,
        'timeout': CIRCUIT_BREAKER_TIMEOUT,
    },
    'connection': {
        'heartbeat_interval': HEARTBEAT_INTERVAL,
        'connection_timeout': CONNECTION_TIMEOUT,
    },
    'monitoring': {
        'enable_metrics': ENABLE_METRICS,
        'metrics_interval': METRICS_INTERVAL,
    }
} 