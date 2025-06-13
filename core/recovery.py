"""
Error recovery system for the trading system
"""

import asyncio
import functools
import time
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union
from .exceptions import TradingSystemError, RecoveryError
from .logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

class RetryConfig:
    """Configuration for retry mechanism"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

class RecoveryManager:
    """Manages error recovery strategies"""
    
    def __init__(self):
        self._recovery_strategies: Dict[Type[Exception], Callable] = {}
        self._fallback_strategies: Dict[Type[Exception], Callable] = {}
        
    def register_recovery_strategy(
        self,
        exception_type: Type[Exception],
        strategy: Callable
    ) -> None:
        """Register a recovery strategy for an exception type"""
        self._recovery_strategies[exception_type] = strategy
        
    def register_fallback_strategy(
        self,
        exception_type: Type[Exception],
        strategy: Callable
    ) -> None:
        """Register a fallback strategy for an exception type"""
        self._fallback_strategies[exception_type] = strategy
        
    async def execute_with_recovery(
        self,
        func: Callable,
        *args: Any,
        retry_config: Optional[RetryConfig] = None,
        **kwargs: Any
    ) -> Any:
        """
        Execute a function with recovery mechanisms
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            retry_config: Configuration for retry mechanism
            **kwargs: Keyword arguments for the function
            
        Returns:
            Any: Result of the function execution
            
        Raises:
            RecoveryError: If all recovery attempts fail
        """
        retry_config = retry_config or RetryConfig()
        attempt = 0
        last_exception = None
        
        while attempt < retry_config.max_attempts:
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                attempt += 1
                
                if attempt == retry_config.max_attempts:
                    break
                    
                # Calculate delay with exponential backoff
                delay = min(
                    retry_config.initial_delay * (retry_config.exponential_base ** (attempt - 1)),
                    retry_config.max_delay
                )
                
                if retry_config.jitter:
                    delay *= (0.5 + 0.5 * time.random())
                    
                logger.warning(
                    f"Attempt {attempt} failed: {str(e)}. Retrying in {delay:.2f} seconds..."
                )
                
                await asyncio.sleep(delay)
                
                # Try recovery strategy if available
                for exc_type, strategy in self._recovery_strategies.items():
                    if isinstance(e, exc_type):
                        try:
                            if asyncio.iscoroutinefunction(strategy):
                                await strategy(e)
                            else:
                                strategy(e)
                            break
                        except Exception as recovery_error:
                            logger.error(
                                f"Recovery strategy failed: {str(recovery_error)}"
                            )
        
        # If all retries failed, try fallback strategy
        if last_exception:
            for exc_type, strategy in self._fallback_strategies.items():
                if isinstance(last_exception, exc_type):
                    try:
                        if asyncio.iscoroutinefunction(strategy):
                            return await strategy(last_exception)
                        return strategy(last_exception)
                    except Exception as fallback_error:
                        raise RecoveryError(
                            f"Fallback strategy failed: {str(fallback_error)}",
                            last_exception
                        )
        
        raise RecoveryError(
            f"All recovery attempts failed after {retry_config.max_attempts} tries",
            last_exception
        )

def with_recovery(
    retry_config: Optional[RetryConfig] = None,
    recovery_manager: Optional[RecoveryManager] = None
) -> Callable[[F], F]:
    """
    Decorator for adding recovery mechanisms to functions
    
    Args:
        retry_config: Configuration for retry mechanism
        recovery_manager: Recovery manager instance
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            manager = recovery_manager or RecoveryManager()
            return await manager.execute_with_recovery(
                func,
                *args,
                retry_config=retry_config,
                **kwargs
            )
            
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            manager = recovery_manager or RecoveryManager()
            return manager.execute_with_recovery(
                func,
                *args,
                retry_config=retry_config,
                **kwargs
            )
            
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
    return decorator

# Create global recovery manager instance
recovery_manager = RecoveryManager()

# Example recovery strategies
async def handle_connection_error(error: Exception) -> None:
    """Handle connection errors"""
    logger.info("Attempting to reconnect...")
    # Implement reconnection logic here

async def handle_authentication_error(error: Exception) -> None:
    """Handle authentication errors"""
    logger.info("Refreshing authentication token...")
    # Implement token refresh logic here

# Register recovery strategies
recovery_manager.register_recovery_strategy(
    ConnectionError,
    handle_connection_error
)
recovery_manager.register_recovery_strategy(
    AuthenticationError,
    handle_authentication_error
) 