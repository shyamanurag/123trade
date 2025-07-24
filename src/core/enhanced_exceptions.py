"""
Enhanced Exception System
Comprehensive exception hierarchy with error codes, retry mechanisms, and recovery strategies
"""

import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Type, Union
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps
import traceback
import json

logger = logging.getLogger(__name__)

# Error severity levels
class ErrorSeverity(str, Enum):
    """Error severity levels for classification and handling"""
    CRITICAL = "critical"      # System-breaking, requires immediate attention
    HIGH = "high"              # Major functionality broken, affects operations
    MEDIUM = "medium"          # Feature degradation, workarounds available
    LOW = "low"                # Minor issues, doesn't affect core functionality
    INFO = "info"              # Informational, no action required

# Error categories for better organization
class ErrorCategory(str, Enum):
    """Error categories for classification"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    NETWORK = "network"
    CONFIGURATION = "configuration"
    SYSTEM = "system"
    TRADING = "trading"
    RISK_MANAGEMENT = "risk_management"
    DATA_PROCESSING = "data_processing"

# Recovery strategies
class RecoveryStrategy(str, Enum):
    """Available recovery strategies for exceptions"""
    NONE = "none"                    # No recovery possible
    RETRY = "retry"                  # Retry the operation
    FALLBACK = "fallback"            # Use fallback mechanism
    CIRCUIT_BREAKER = "circuit_breaker"  # Implement circuit breaker
    # Removed graceful degradation - system should fail fast
    MANUAL_INTERVENTION = "manual_intervention"  # Requires manual action

@dataclass
class ErrorDetails:
    """Detailed error information for comprehensive tracking"""
    error_id: str
    timestamp: datetime
    error_code: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    recovery_strategy: RecoveryStrategy
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    user_message: Optional[str] = None
    suggested_actions: List[str] = field(default_factory=list)
    related_errors: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3

class TradingSystemException(Exception):
    """Enhanced base exception for the trading system"""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        recovery_strategy: RecoveryStrategy = RecoveryStrategy.NONE,
        context: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        suggested_actions: Optional[List[str]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        
        self.error_details = ErrorDetails(
            error_id=f"{error_code}_{int(time.time())}",
            timestamp=datetime.now(),
            error_code=error_code,
            message=message,
            category=category,
            severity=severity,
            recovery_strategy=recovery_strategy,
            context=context or {},
            user_message=user_message,
            suggested_actions=suggested_actions or [],
            stack_trace=traceback.format_exc() if cause else None
        )
        
        # Store the original cause
        self.__cause__ = cause
        
        # Log the exception based on severity
        self._log_exception()
    
    def _log_exception(self):
        """Log the exception based on its severity"""
        log_data = {
            "error_id": self.error_details.error_id,
            "error_code": self.error_details.error_code,
            "category": self.error_details.category.value,
            "severity": self.error_details.severity.value,
            "context": self.error_details.context
        }
        
        if self.error_details.severity == ErrorSeverity.CRITICAL:
            logger.critical(self.error_details.message, extra=log_data)
        elif self.error_details.severity == ErrorSeverity.HIGH:
            logger.error(self.error_details.message, extra=log_data)
        elif self.error_details.severity == ErrorSeverity.MEDIUM:
            logger.warning(self.error_details.message, extra=log_data)
        else:
            logger.info(self.error_details.message, extra=log_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            "error_id": self.error_details.error_id,
            "error_code": self.error_details.error_code,
            "message": self.error_details.message,
            "user_message": self.error_details.user_message,
            "category": self.error_details.category.value,
            "severity": self.error_details.severity.value,
            "timestamp": self.error_details.timestamp.isoformat(),
            "suggested_actions": self.error_details.suggested_actions,
            "retry_count": self.error_details.retry_count,
            "context": self.error_details.context
        }
    
    def can_retry(self) -> bool:
        """Check if the exception supports retry"""
        return (
            self.error_details.recovery_strategy in [RecoveryStrategy.RETRY, RecoveryStrategy.CIRCUIT_BREAKER] and
            self.error_details.retry_count < self.error_details.max_retries
        )
    
    def increment_retry(self):
        """Increment retry count"""
        self.error_details.retry_count += 1

# Authentication & Authorization Exceptions
class AuthenticationError(TradingSystemException):
    """Authentication-related errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="AUTH_001",
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            user_message="Authentication failed. Please check your credentials.",
            suggested_actions=["Verify username and password", "Check if account is locked"],
            **kwargs
        )

class AuthorizationError(TradingSystemException):
    """Authorization-related errors"""
    def __init__(self, message: str, required_permission: str = None, **kwargs):
        context = kwargs.get('context', {})
        if required_permission:
            context['required_permission'] = required_permission
        
        super().__init__(
            message=message,
            error_code="AUTHZ_001",
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.HIGH,
            user_message="You don't have permission to perform this action.",
            suggested_actions=["Contact administrator for access", "Check your role permissions"],
            context=context,
            **kwargs
        )

class TokenExpiredError(AuthenticationError):
    """Token expiration error"""
    def __init__(self, **kwargs):
        super().__init__(
            message="Authentication token has expired",
            error_code="AUTH_002",
            user_message="Your session has expired. Please log in again.",
            suggested_actions=["Log in again", "Use refresh token if available"],
            **kwargs
        )

# Validation Exceptions
class ValidationError(TradingSystemException):
    """Data validation errors"""
    def __init__(self, message: str, field: str = None, value: Any = None, **kwargs):
        context = kwargs.get('context', {})
        if field:
            context['field'] = field
        if value is not None:
            context['invalid_value'] = str(value)
        
        super().__init__(
            message=message,
            error_code="VAL_001",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            user_message="Invalid input provided. Please check your data.",
            suggested_actions=["Verify input format", "Check required fields"],
            context=context,
            **kwargs
        )

class BusinessRuleViolationError(TradingSystemException):
    """Business logic rule violations"""
    def __init__(self, message: str, rule: str = None, **kwargs):
        context = kwargs.get('context', {})
        if rule:
            context['violated_rule'] = rule
        
        super().__init__(
            message=message,
            error_code="BIZ_001",
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            user_message="Operation violates business rules.",
            suggested_actions=["Review business rules", "Contact support if needed"],
            context=context,
            **kwargs
        )

# Trading Exceptions
class TradingError(TradingSystemException):
    """Base trading system error"""
    def __init__(self, message: str, error_code: str = "TRD_001", **kwargs):
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.TRADING,
            severity=ErrorSeverity.HIGH,
            recovery_strategy=RecoveryStrategy.RETRY,
            **kwargs
        )

class OrderExecutionError(TradingError):
    """Order execution failures"""
    def __init__(self, message: str, order_id: str = None, symbol: str = None, **kwargs):
        context = kwargs.get('context', {})
        if order_id:
            context['order_id'] = order_id
        if symbol:
            context['symbol'] = symbol
        
        super().__init__(
            message=message,
            error_code="TRD_002",
            user_message="Order execution failed. Please try again.",
            suggested_actions=["Check market status", "Verify order parameters", "Retry order"],
            context=context,
            **kwargs
        )

class InsufficientFundsError(TradingError):
    """Insufficient funds for trading"""
    def __init__(self, required_amount: float = None, available_amount: float = None, **kwargs):
        context = kwargs.get('context', {})
        if required_amount:
            context['required_amount'] = required_amount
        if available_amount:
            context['available_amount'] = available_amount
        
        super().__init__(
            message="Insufficient funds for the requested operation",
            error_code="TRD_003",
            severity=ErrorSeverity.HIGH,
            user_message="Insufficient funds to complete this order.",
            suggested_actions=["Add funds to account", "Reduce order size", "Check available balance"],
            context=context,
            **kwargs
        )

class RiskLimitExceededError(TradingError):
    """Risk management limit exceeded"""
    def __init__(self, limit_type: str, current_value: float = None, limit_value: float = None, **kwargs):
        context = kwargs.get('context', {})
        context.update({
            'limit_type': limit_type,
            'current_value': current_value,
            'limit_value': limit_value
        })
        
        super().__init__(
            message=f"Risk limit exceeded: {limit_type}",
            error_code="RISK_001",
            category=ErrorCategory.RISK_MANAGEMENT,
            severity=ErrorSeverity.HIGH,
            user_message=f"Operation blocked due to {limit_type} risk limit.",
            suggested_actions=["Review risk settings", "Wait for limits to reset", "Contact risk management"],
            context=context,
            **kwargs
        )

# External Service Exceptions
class ExternalServiceError(TradingSystemException):
    """External service failures"""
    def __init__(self, service_name: str, message: str = None, **kwargs):
        super().__init__(
            message=message or f"External service '{service_name}' is unavailable",
            error_code="EXT_001",
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.HIGH,
            recovery_strategy=RecoveryStrategy.RETRY,
            user_message="External service is temporarily unavailable.",
            suggested_actions=["Try again later", "Check service status"],
            context={"service_name": service_name},
            **kwargs
        )

class MarketDataError(ExternalServiceError):
    """Market data service errors"""
    def __init__(self, symbol: str = None, **kwargs):
        context = kwargs.get('context', {})
        if symbol:
            context['symbol'] = symbol
        
        super().__init__(
            service_name="market_data",
            message="Market data service error",
            error_code="MKT_001",
            recovery_strategy=RecoveryStrategy.FALLBACK,
            suggested_actions=["Use cached data if available", "Try alternative data source"],
            context=context,
            **kwargs
        )

class BrokerConnectionError(ExternalServiceError):
    """Broker connection errors"""
    def __init__(self, broker_name: str, **kwargs):
        super().__init__(
            service_name=broker_name,
            message=f"Failed to connect to broker: {broker_name}",
            error_code="BRK_001",
            severity=ErrorSeverity.CRITICAL,
            recovery_strategy=RecoveryStrategy.CIRCUIT_BREAKER,
            suggested_actions=["Check broker status", "Verify credentials", "Check network connection"],
            **kwargs
        )

# Database Exceptions
class DatabaseError(TradingSystemException):
    """Database operation errors"""
    def __init__(self, message: str, operation: str = None, **kwargs):
        context = kwargs.get('context', {})
        if operation:
            context['database_operation'] = operation
        
        super().__init__(
            message=message,
            error_code="DB_001",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            recovery_strategy=RecoveryStrategy.RETRY,
            user_message="Database operation failed. Please try again.",
            suggested_actions=["Retry operation", "Check database status"],
            context=context,
            **kwargs
        )

class DatabaseConnectionError(DatabaseError):
    """Database connection failures"""
    def __init__(self, **kwargs):
        super().__init__(
            message="Database connection failed",
            error_code="DB_002",
            severity=ErrorSeverity.CRITICAL,
            recovery_strategy=RecoveryStrategy.CIRCUIT_BREAKER,
            user_message="Database is temporarily unavailable.",
            suggested_actions=["Check database status", "Contact system administrator"],
            **kwargs
        )

# Configuration Exceptions
class ConfigurationError(TradingSystemException):
    """Configuration-related errors"""
    def __init__(self, message: str, config_key: str = None, **kwargs):
        context = kwargs.get('context', {})
        if config_key:
            context['config_key'] = config_key
        
        super().__init__(
            message=message,
            error_code="CFG_001",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            recovery_strategy=RecoveryStrategy.MANUAL_INTERVENTION,
            user_message="System configuration error detected.",
            suggested_actions=["Check configuration file", "Contact system administrator"],
            context=context,
            **kwargs
        )

# System Exceptions
class SystemError(TradingSystemException):
    """System-level errors"""
    def __init__(self, message: str, component: str = None, **kwargs):
        context = kwargs.get('context', {})
        if component:
            context['component'] = component
        
        super().__init__(
            message=message,
            error_code="SYS_001",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            recovery_strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
            user_message="System error occurred. Functionality may be limited.",
            suggested_actions=["Contact system administrator", "Check system status"],
            context=context,
            **kwargs
        )

class ResourceExhaustionError(SystemError):
    """Resource exhaustion errors"""
    def __init__(self, resource_type: str, **kwargs):
        super().__init__(
            message=f"Resource exhausted: {resource_type}",
            error_code="SYS_002",
            user_message="System resources are currently exhausted.",
            suggested_actions=["Wait and try again", "Contact administrator"],
            context={"resource_type": resource_type},
            **kwargs
        )

# Retry mechanism decorator
def with_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Decorator to add retry logic to functions"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        wait_time = delay * (backoff ** attempt)
                        logger.warning(
                            f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}), "
                            f"retrying in {wait_time:.2f}s: {str(e)}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"Function {func.__name__} failed after {max_retries + 1} attempts")
            
            # If it's a TradingSystemException, increment retry count
            if isinstance(last_exception, TradingSystemException):
                last_exception.increment_retry()
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        wait_time = delay * (backoff ** attempt)
                        logger.warning(
                            f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}), "
                            f"retrying in {wait_time:.2f}s: {str(e)}"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Function {func.__name__} failed after {max_retries + 1} attempts")
            
            # If it's a TradingSystemException, increment retry count
            if isinstance(last_exception, TradingSystemException):
                last_exception.increment_retry()
            
            raise last_exception
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Circuit breaker implementation
class CircuitBreaker:
    """Circuit breaker for external service calls"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise ExternalServiceError(
                    service_name="circuit_breaker",
                    message="Circuit breaker is OPEN - service unavailable"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        return (
            self.last_failure_time and
            (datetime.now() - self.last_failure_time).seconds >= self.recovery_timeout
        )
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker opened due to {self.failure_count} failures")

# Error aggregation for multiple failures
class ErrorAggregator:
    """Aggregate multiple errors for batch operations"""
    
    def __init__(self):
        self.errors: List[TradingSystemException] = []
        self.successes: List[Any] = []
    
    def add_error(self, error: TradingSystemException):
        """Add an error to the aggregator"""
        self.errors.append(error)
    
    def add_success(self, result: Any):
        """Add a successful result"""
        self.successes.append(result)
    
    def has_errors(self) -> bool:
        """Check if there are any errors"""
        return len(self.errors) > 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all errors and successes"""
        error_summary = {}
        for error in self.errors:
            category = error.error_details.category.value
            if category not in error_summary:
                error_summary[category] = []
            error_summary[category].append(error.to_dict())
        
        return {
            "total_operations": len(self.errors) + len(self.successes),
            "successful_operations": len(self.successes),
            "failed_operations": len(self.errors),
            "success_rate": len(self.successes) / max(1, len(self.errors) + len(self.successes)),
            "errors_by_category": error_summary
        }
    
    def raise_if_critical(self):
        """Raise exception if any critical errors are present"""
        critical_errors = [
            error for error in self.errors 
            if error.error_details.severity == ErrorSeverity.CRITICAL
        ]
        
        if critical_errors:
            raise SystemError(
                message=f"{len(critical_errors)} critical errors occurred",
                context={"critical_errors": [e.to_dict() for e in critical_errors]}
            )

# Export all exception classes and utilities
__all__ = [
    # Enums
    "ErrorSeverity", "ErrorCategory", "RecoveryStrategy",
    
    # Base classes
    "TradingSystemException", "ErrorDetails",
    
    # Specific exceptions
    "AuthenticationError", "AuthorizationError", "TokenExpiredError",
    "ValidationError", "BusinessRuleViolationError",
    "TradingError", "OrderExecutionError", "InsufficientFundsError", "RiskLimitExceededError",
    "ExternalServiceError", "MarketDataError", "BrokerConnectionError",
    "DatabaseError", "DatabaseConnectionError",
    "ConfigurationError", "SystemError", "ResourceExhaustionError",
    
    # Utilities
    "with_retry", "CircuitBreaker", "ErrorAggregator"
] 