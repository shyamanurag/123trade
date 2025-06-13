"""
Centralized Error Handling System
Provides global exception handling, error tracking, and structured error responses
"""

import logging
import traceback
import sys
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Type
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import asyncio
from dataclasses import dataclass, asdict
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

logger = logging.getLogger(__name__)

@dataclass
class ErrorContext:
    """Context information for error tracking"""
    request_id: str
    user_id: Optional[str]
    endpoint: str
    method: str
    timestamp: datetime
    environment: str
    
@dataclass
class ErrorResponse:
    """Standardized error response structure"""
    error: str
    message: str
    code: str
    timestamp: str
    request_id: str
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response"""
        result = asdict(self)
        # Remove None values
        return {k: v for k, v in result.items() if v is not None}

class ErrorTracker:
    """Tracks and aggregates errors for monitoring"""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.error_history: list = []
        self.max_history = 1000
        
    async def track_error(self, error: Exception, context: ErrorContext):
        """Track an error occurrence"""
        error_type = type(error).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Add to history
        error_record = {
            "timestamp": context.timestamp.isoformat(),
            "error_type": error_type,
            "message": str(error),
            "endpoint": context.endpoint,
            "user_id": context.user_id,
            "request_id": context.request_id
        }
        
        self.error_history.append(error_record)
        
        # Maintain history size
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
            
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            "error_counts": self.error_counts,
            "total_errors": sum(self.error_counts.values()),
            "recent_errors": self.error_history[-10:],
            "error_types": list(self.error_counts.keys())
        }

class GlobalErrorHandler:
    """Global error handler for the application"""
    
    def __init__(self, app_name: str = "trading-system", environment: str = "production"):
        self.app_name = app_name
        self.environment = environment
        self.error_tracker = ErrorTracker()
        self.custom_handlers: Dict[Type[Exception], Callable] = {}
        
    def register_handler(self, exception_type: Type[Exception], handler: Callable):
        """Register a custom handler for specific exception type"""
        self.custom_handlers[exception_type] = handler
        
    async def handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """Main exception handler"""
        # Extract context
        context = ErrorContext(
            request_id=request.headers.get("X-Request-ID", str(datetime.now().timestamp())),
            user_id=getattr(request.state, "user_id", None),
            endpoint=request.url.path,
            method=request.method,
            timestamp=datetime.now(),
            environment=self.environment
        )
        
        # Track error
        await self.error_tracker.track_error(exc, context)
        
        # Check for custom handler
        for exc_type, handler in self.custom_handlers.items():
            if isinstance(exc, exc_type):
                return await handler(request, exc, context)
        
        # Handle specific exception types
        if isinstance(exc, HTTPException):
            return await self._handle_http_exception(request, exc, context)
        elif isinstance(exc, RequestValidationError):
            return await self._handle_validation_error(request, exc, context)
        elif isinstance(exc, asyncio.TimeoutError):
            return await self._handle_timeout_error(request, exc, context)
        else:
            return await self._handle_generic_exception(request, exc, context)
    
    async def _handle_http_exception(self, request: Request, exc: HTTPException, context: ErrorContext) -> JSONResponse:
        """Handle HTTP exceptions"""
        error_response = ErrorResponse(
            error=exc.__class__.__name__,
            message=exc.detail,
            code=f"HTTP_{exc.status_code}",
            timestamp=context.timestamp.isoformat(),
            request_id=context.request_id,
            details={"status_code": exc.status_code}
        )
        
        # Log based on status code
        if exc.status_code >= 500:
            logger.error(f"HTTP {exc.status_code} error: {exc.detail}", extra={"context": asdict(context)})
        else:
            logger.warning(f"HTTP {exc.status_code} error: {exc.detail}", extra={"context": asdict(context)})
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.to_dict()
        )
    
    async def _handle_validation_error(self, request: Request, exc: RequestValidationError, context: ErrorContext) -> JSONResponse:
        """Handle request validation errors"""
        # Extract validation errors
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
        
        error_response = ErrorResponse(
            error="ValidationError",
            message="Request validation failed",
            code="VALIDATION_ERROR",
            timestamp=context.timestamp.isoformat(),
            request_id=context.request_id,
            details={"validation_errors": errors}
        )
        
        logger.warning(f"Validation error on {context.endpoint}", extra={"errors": errors})
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response.to_dict()
        )
    
    async def _handle_timeout_error(self, request: Request, exc: asyncio.TimeoutError, context: ErrorContext) -> JSONResponse:
        """Handle timeout errors"""
        error_response = ErrorResponse(
            error="TimeoutError",
            message="Request timed out",
            code="TIMEOUT_ERROR",
            timestamp=context.timestamp.isoformat(),
            request_id=context.request_id
        )
        
        logger.error(f"Timeout error on {context.endpoint}", extra={"context": asdict(context)})
        
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content=error_response.to_dict()
        )
    
    async def _handle_generic_exception(self, request: Request, exc: Exception, context: ErrorContext) -> JSONResponse:
        """Handle generic exceptions"""
        # Log full traceback
        logger.error(
            f"Unhandled exception on {context.endpoint}",
            exc_info=True,
            extra={"context": asdict(context)}
        )
        
        # Prepare error response
        error_response = ErrorResponse(
            error=exc.__class__.__name__,
            message="An internal error occurred",
            code="INTERNAL_ERROR",
            timestamp=context.timestamp.isoformat(),
            request_id=context.request_id
        )
        
        # In development, include more details
        if self.environment == "development":
            error_response.details = {
                "exception": str(exc),
                "traceback": traceback.format_exc()
            }
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.to_dict()
        )
    
    def setup_exception_handlers(self, app):
        """Setup exception handlers for FastAPI app"""
        # Generic exception handler
        @app.exception_handler(Exception)
        async def generic_exception_handler(request: Request, exc: Exception):
            return await self.handle_exception(request, exc)
        
        # HTTP exception handler
        @app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            return await self.handle_exception(request, exc)
        
        # Starlette HTTP exception handler
        @app.exception_handler(StarletteHTTPException)
        async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
            return await self.handle_exception(request, exc)
        
        # Validation error handler
        @app.exception_handler(RequestValidationError)
        async def validation_exception_handler(request: Request, exc: RequestValidationError):
            return await self.handle_exception(request, exc)
        
        logger.info("Global exception handlers configured")

# Custom exception handlers for specific business logic errors
async def handle_trading_error(request: Request, exc: Exception, context: ErrorContext) -> JSONResponse:
    """Handle trading-specific errors"""
    try:
        from core.exceptions import TradingSystemError
    except ImportError:
        # If custom exceptions not available, handle as generic
        return await error_handler._handle_generic_exception(request, exc, context)
    
    if isinstance(exc, TradingSystemError):
        error_response = ErrorResponse(
            error=exc.__class__.__name__,
            message=getattr(exc, 'message', str(exc)),
            code=getattr(exc, 'error_code', 'TRADING_ERROR'),
            timestamp=context.timestamp.isoformat(),
            request_id=context.request_id,
            details={"error_code": getattr(exc, 'error_code', None)}
        )
        
        logger.error(f"Trading error: {getattr(exc, 'message', str(exc))}", extra={"context": asdict(context)})
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response.to_dict()
        )
    
    # Return generic handler for non-trading errors
    return await error_handler._handle_generic_exception(request, exc, context)

async def handle_broker_error(request: Request, exc: Exception, context: ErrorContext) -> JSONResponse:
    """Handle broker-specific errors"""
    error_response = ErrorResponse(
        error="BrokerError",
        message="Broker operation failed",
        code="BROKER_ERROR",
        timestamp=context.timestamp.isoformat(),
        request_id=context.request_id,
        details={"broker": getattr(exc, "broker", "unknown")}
    )
    
    logger.error(f"Broker error: {str(exc)}", extra={"context": asdict(context)})
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error_response.to_dict()
    )

# Error recovery middleware
class ErrorRecoveryMiddleware(BaseHTTPMiddleware):
    """Middleware for error recovery and circuit breaking"""
    
    def __init__(self, app, error_threshold: int = 10, recovery_time: int = 60):
        super().__init__(app)
        self.error_threshold = error_threshold
        self.recovery_time = recovery_time
        self.error_counts: Dict[str, int] = {}
        self.circuit_open: Dict[str, datetime] = {}
        
    async def dispatch(self, request: StarletteRequest, call_next):
        endpoint = request.url.path
        
        # Check if circuit is open
        if endpoint in self.circuit_open:
            if (datetime.now() - self.circuit_open[endpoint]).seconds < self.recovery_time:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "error": "CircuitBreakerOpen",
                        "message": "Service temporarily unavailable",
                        "retry_after": self.recovery_time
                    }
                )
            else:
                # Reset circuit
                del self.circuit_open[endpoint]
                self.error_counts[endpoint] = 0
        
        try:
            response = await call_next(request)
            
            # Reset error count on success
            if response.status_code < 500:
                self.error_counts[endpoint] = 0
                
            return response
            
        except Exception as e:
            # Increment error count
            self.error_counts[endpoint] = self.error_counts.get(endpoint, 0) + 1
            
            # Open circuit if threshold reached
            if self.error_counts[endpoint] >= self.error_threshold:
                self.circuit_open[endpoint] = datetime.now()
                logger.warning(f"Circuit breaker opened for {endpoint}")
            
            raise

# Create global error handler instance
error_handler = GlobalErrorHandler()

# Register custom handlers
try:
    from core.exceptions import TradingSystemError
    error_handler.register_handler(TradingSystemError, handle_trading_error)
except ImportError:
    logger.warning("TradingSystemError not available, using generic error handling") 