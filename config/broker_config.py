"""
Broker Configuration System
Allows easy switching between Zerodha (testing) and Sharekhan (production)
NO MOCK DATA - ALL DATA MUST BE REAL
"""

import os
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass

class BrokerType(Enum):
    """Supported broker types"""
    ZERODHA = "zerodha"
    SHAREKHAN = "sharekhan"

@dataclass
class BrokerConfig:
    """Broker configuration data - NO MOCK MODE"""
    name: str
    type: BrokerType
    paper_trading: bool
    # NO MOCK MODE - ALL DATA MUST BE REAL
    api_credentials: Dict[str, str]
    features: Dict[str, bool]
    description: str

class BrokerConfigManager:
    """Manages broker configurations and switching - NO MOCK DATA"""
    
    def __init__(self):
        self.configs = self._load_broker_configs()
        self.active_broker = self._get_active_broker()
    
    def _load_broker_configs(self) -> Dict[str, BrokerConfig]:
        """Load all broker configurations - NO MOCK CONFIGURATIONS"""
        return {
            'zerodha_testing': BrokerConfig(
                name="Zerodha Testing",
                type=BrokerType.ZERODHA,
                paper_trading=True,
                api_credentials={
                    'api_key': os.getenv('ZERODHA_API_KEY', ''),
                    'api_secret': os.getenv('ZERODHA_API_SECRET', ''),
                    'access_token': os.getenv('ZERODHA_ACCESS_TOKEN', ''),
                    'user_id': os.getenv('ZERODHA_USER_ID', ''),
                },
                features={
                    'real_time_data': True,
                    'paper_trading': True,
                    'websocket_support': True,
                    'historical_data': True,
                    'order_management': True,
                    'portfolio_tracking': True,
                },
                description="Zerodha with paper trading for safe testing - REAL API REQUIRED"
            ),
            
            'zerodha_live': BrokerConfig(
                name="Zerodha Live",
                type=BrokerType.ZERODHA,
                paper_trading=False,
                api_credentials={
                    'api_key': os.getenv('ZERODHA_API_KEY', ''),
                    'api_secret': os.getenv('ZERODHA_API_SECRET', ''),
                    'access_token': os.getenv('ZERODHA_ACCESS_TOKEN', ''),
                    'user_id': os.getenv('ZERODHA_USER_ID', ''),
                },
                features={
                    'real_time_data': True,
                    'paper_trading': False,
                    'websocket_support': True,
                    'historical_data': True,
                    'order_management': True,
                    'portfolio_tracking': True,
                },
                description="Zerodha with real live trading - REAL API REQUIRED"
            ),
            
            'sharekhan_production': BrokerConfig(
                name="Sharekhan Production",
                type=BrokerType.SHAREKHAN,
                paper_trading=False,
                api_credentials={
                    'api_key': os.getenv('SHAREKHAN_API_KEY', ''),
                    'secret_key': os.getenv('SHAREKHAN_SECRET_KEY', ''),
                    'customer_id': os.getenv('SHAREKHAN_CUSTOMER_ID', ''),
                    'access_token': os.getenv('SHAREKHAN_ACCESS_TOKEN', ''),
                },
                features={
                    'real_time_data': True,
                    'paper_trading': False,
                    'websocket_support': True,
                    'historical_data': True,
                    'order_management': True,
                    'portfolio_tracking': True,
                },
                description="Sharekhan for production trading - REAL API REQUIRED"
            ),
            
            # NO MOCK MODE - ALL TESTING MUST USE REAL APIs WITH PAPER TRADING
        }
    
    def _get_active_broker(self) -> str:
        """Get the currently active broker from environment"""
        return os.getenv('ACTIVE_BROKER', 'zerodha_testing')
    
    def get_active_config(self) -> BrokerConfig:
        """Get the active broker configuration"""
        return self.configs.get(self.active_broker, self.configs['zerodha_testing'])
    
    def get_config(self, broker_name: str) -> Optional[BrokerConfig]:
        """Get a specific broker configuration"""
        return self.configs.get(broker_name)
    
    def list_brokers(self) -> Dict[str, str]:
        """List all available brokers with descriptions"""
        return {name: config.description for name, config in self.configs.items()}
    
    def switch_broker(self, broker_name: str) -> bool:
        """Switch to a different broker"""
        if broker_name in self.configs:
            self.active_broker = broker_name
            # In a real implementation, you'd update environment variables
            # For now, we'll just update the instance
            return True
        return False
    
    def validate_broker_config(self, broker_name: str) -> Dict[str, Any]:
        """Validate a broker configuration - NO MOCK MODE"""
        if broker_name not in self.configs:
            return {
                'valid': False,
                'error': f'Unknown broker: {broker_name}',
                'missing_credentials': [],
                'available_features': {}
            }
        
        config = self.configs[broker_name]
        missing_credentials = []
        
        # Check required credentials - NO MOCK MODE BYPASS
        for key, value in config.api_credentials.items():
            if not value:
                missing_credentials.append(key)
        
        return {
            'valid': len(missing_credentials) == 0,
            'broker_name': config.name,
            'broker_type': config.type.value,
            'paper_trading': config.paper_trading,
            'missing_credentials': missing_credentials,
            'available_features': config.features,
            'description': config.description
        }
    
    def get_market_data_config(self) -> Dict[str, Any]:
        """Get market data configuration for the active broker"""
        config = self.get_active_config()
        
        return {
            'broker_type': config.type.value,
            'paper_trading': config.paper_trading,
            'credentials': config.api_credentials,
            'features': config.features
        }
    
    def get_trading_config(self) -> Dict[str, Any]:
        """Get trading configuration for the active broker"""
        config = self.get_active_config()
        
        return {
            'broker_type': config.type.value,
            'paper_trading': config.paper_trading,
            'credentials': config.api_credentials,
            'order_management': config.features.get('order_management', False),
            'portfolio_tracking': config.features.get('portfolio_tracking', False)
        }

# Global instance
_broker_config_manager = None

def get_broker_config_manager() -> BrokerConfigManager:
    """Get the global broker configuration manager"""
    global _broker_config_manager
    if _broker_config_manager is None:
        _broker_config_manager = BrokerConfigManager()
    return _broker_config_manager

def get_active_broker_config() -> Dict[str, Any]:
    """Get the active broker configuration"""
    manager = get_broker_config_manager()
    return manager.get_market_data_config()

# Convenience functions
def is_paper_trading() -> bool:
    """Check if paper trading is enabled"""
    config = get_active_broker_config()
    return config.get('paper_trading', True)

def get_broker_type() -> str:
    """Get the active broker type"""
    config = get_active_broker_config()
    return config.get('broker_type', 'zerodha')

def switch_to_zerodha_testing():
    """Switch to Zerodha testing mode"""
    manager = get_broker_config_manager()
    return manager.switch_broker('zerodha_testing')

def switch_to_sharekhan_production():
    """Switch to Sharekhan production mode"""
    manager = get_broker_config_manager()
    return manager.switch_broker('sharekhan_production')

# NO MOCK TESTING FUNCTION - ALL TESTING MUST USE REAL APIs 