"""
Error recovery system for the trading system
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, Optional, Type
from dataclasses import dataclass
from enum import Enum
import random

logger = logging.getLogger(__name__)

class RetryStrategy(Enum):
    """Retry strategy types"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"

@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    
    def __post_init__(self):
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.initial_delay < 0:
            raise ValueError("initial_delay must be non-negative")
        if self.max_delay < self.initial_delay:
            raise ValueError("max_delay must be >= initial_delay")
        if self.exponential_base <= 1:
            raise ValueError("exponential_base must be > 1")

class RecoveryManager:
    """Manages error recovery strategies"""
    
    def __init__(self):
        self._recovery_strategies: Dict[Type[Exception], Callable] = {}
        
    def register_recovery_strategy(
        self,
        exception_type: Type[Exception],
        strategy: Callable
    ) -> None:
        """Register a recovery strategy for an exception type"""
        self._recovery_strategies[exception_type] = strategy
        
    async def execute_with_recovery(
        self,
        func: Callable,
        *args: Any,
        retry_config: Optional[RetryConfig] = None,
        **kwargs: Any
    ) -> Any:
        """Execute function with recovery - NO FALLBACKS"""
        if retry_config is None:
            retry_config = RetryConfig()
            
        last_exception = None
        
        for attempt in range(retry_config.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
                    
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Attempt {attempt + 1}/{retry_config.max_retries + 1} failed: {str(e)}",
                    exc_info=True
                )
                
                # If this was the last attempt, don't sleep
                if attempt == retry_config.max_retries:
                    break
                    
                # Try recovery strategy
                recovery_attempted = False
                for exc_type, strategy in self._recovery_strategies.items():
                    if isinstance(e, exc_type):
                        try:
                            if asyncio.iscoroutinefunction(strategy):
                                await strategy(e, attempt)
                            else:
                                strategy(e, attempt)
                            recovery_attempted = True
                            break
                        except Exception as recovery_error:
                            logger.error(
                                f"Recovery strategy failed: {str(recovery_error)}",
                                exc_info=True
                            )
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(retry_config, attempt)
                
                logger.info(
                    f"Retrying in {delay:.2f} seconds... "
                    f"(attempt {attempt + 1}/{retry_config.max_retries + 1})"
                )
                
                await asyncio.sleep(delay)
        
        # All retries exhausted - raise the last exception
        if last_exception:
            logger.error(f"All retries exhausted. Final error: {str(last_exception)}")
            raise last_exception
        else:
            raise RuntimeError("Unknown error during execution with recovery")
    
    def _calculate_delay(self, config: RetryConfig, attempt: int) -> float:
        """Calculate delay for next retry attempt"""
        if config.initial_delay == 0:
            return 0
            
        # Calculate base delay using exponential backoff
        delay = config.initial_delay * (config.exponential_base ** attempt)
        delay = min(delay, config.max_delay)
        
        # Add jitter if enabled
        if config.jitter:
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
            
        return max(0, delay)

def retry_on_exception(
    exceptions: tuple = (Exception,),
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
):
    """Decorator for retrying functions on specific exceptions"""
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            retry_config = RetryConfig(
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter
            )
            
            recovery_manager = RecoveryManager()
            return await recovery_manager.execute_with_recovery(
                func, *args, retry_config=retry_config, **kwargs
            )
            
        def sync_wrapper(*args, **kwargs):
            # For sync functions, use asyncio.run
            retry_config = RetryConfig(
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter
            )
            
            recovery_manager = RecoveryManager()
            return asyncio.run(recovery_manager.execute_with_recovery(
                func, *args, retry_config=retry_config, **kwargs
            ))
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator

# Global recovery manager instance
recovery_manager = RecoveryManager() 