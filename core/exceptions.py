"""
Custom exceptions for the trading system
"""

class TradingSystemError(Exception):
    """Base exception for all trading system errors"""
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class ConnectionError(TradingSystemError):
    """Raised when there are connection issues with brokers or data providers"""
    def __init__(self, message: str, provider: str, error_code: str = "CONN_001"):
        self.provider = provider
        super().__init__(message, error_code)

class AuthenticationError(TradingSystemError):
    """Raised when there are authentication issues"""
    def __init__(self, message: str, service: str, error_code: str = "AUTH_001"):
        self.service = service
        super().__init__(message, error_code)

class ValidationError(TradingSystemError):
    """Raised when input validation fails"""
    def __init__(self, message: str, field: str, error_code: str = "VAL_001"):
        self.field = field
        super().__init__(message, error_code)

class StrategyError(TradingSystemError):
    """Raised when there are issues with strategy execution"""
    def __init__(self, message: str, strategy: str, error_code: str = "STRAT_001"):
        self.strategy = strategy
        super().__init__(message, error_code)

class RiskManagementError(TradingSystemError):
    """Raised when risk management rules are violated"""
    def __init__(self, message: str, rule: str, error_code: str = "RISK_001"):
        self.rule = rule
        super().__init__(message, error_code)

class OrderError(TradingSystemError):
    """Raised when there are issues with order execution"""
    def __init__(self, message: str, order_id: str, error_code: str = "ORD_001"):
        self.order_id = order_id
        super().__init__(message, error_code)

class DataError(TradingSystemError):
    """Raised when there are issues with market data"""
    def __init__(self, message: str, data_type: str, error_code: str = "DATA_001"):
        self.data_type = data_type
        super().__init__(message, error_code)

class ConfigurationError(TradingSystemError):
    """Raised when there are issues with system configuration"""
    def __init__(self, message: str, config_key: str, error_code: str = "CONFIG_001"):
        self.config_key = config_key
        super().__init__(message, error_code)

class WebhookError(TradingSystemError):
    """Raised when there are issues with webhook notifications"""
    def __init__(self, message: str, webhook_url: str, error_code: str = "WEB_001"):
        self.webhook_url = webhook_url
        super().__init__(message, error_code)

class RecoveryError(TradingSystemError):
    """Raised when error recovery fails"""
    def __init__(self, message: str, original_error: Exception, error_code: str = "REC_001"):
        self.original_error = original_error
        super().__init__(message, error_code) 