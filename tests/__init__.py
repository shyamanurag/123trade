"""
Test suite for Crypto Trading System
Comprehensive testing framework for APIs, services, and integrations
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Test configuration
TEST_CONFIG = {
    "timeout": 30,
    "retry_count": 3,
    "test_environment": "testing",
    "database_url": "sqlite:///test.db",
    "redis_url": "redis://localhost:6379/15",
}

__version__ = "1.0.0"