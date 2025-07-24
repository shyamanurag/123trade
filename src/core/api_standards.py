"""
API Standardization System
Provides consistent response formats, versioning, and error handling across all endpoints
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Type
from enum import Enum
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field, validator
from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
import traceback
import uuid

logger = logging.getLogger(__name__)

# API Version Management
class APIVersion(str, Enum):
    """Supported API versions"""
    V1 = "v1"
    V2 = "v2"
    LATEST = "v2"

class ResponseStatus(str, Enum):
    """Standard response status values"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PARTIAL = "partial"

class ErrorCode(str, Enum):
    """Standard error codes"""
    # Client errors (4xx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    
    # Server errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"

@dataclass
class ResponseMeta:
    """Metadata for API responses"""
    request_id: str
    timestamp: str
    api_version: str
    processing_time_ms: Optional[float] = None
    server_id: Optional[str] = None
    rate_limit_remaining: Optional[int] = None
    cache_status: Optional[str] = None

class StandardAPIResponse(BaseModel):
    """
    Standardized API Response Format
    All endpoints should use this format for consistency
    """
    status: ResponseStatus = Field(..., description="Response status indicator")
    message: str = Field(..., description="Human-readable message")
    data: Optional[Union[Dict[str, Any], List[Any], Any]] = Field(None, description="Response payload")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="Error details if any")
    meta: ResponseMeta = Field(..., description="Response metadata")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class StandardErrorResponse(BaseModel):
    """Standardized error response format"""
    status: ResponseStatus = ResponseStatus.ERROR
    message: str = Field(..., description="Error message")
    error_code: ErrorCode = Field(..., description="Standardized error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    suggestions: Optional[List[str]] = Field(None, description="Suggested actions")
    meta: ResponseMeta = Field(..., description="Response metadata")
    
    class Config:
        use_enum_values = True

class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=1000, description="Items per page")
    total_items: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")

class PaginatedResponse(StandardAPIResponse):
    """Standardized paginated response"""
    pagination: PaginationMeta = Field(..., description="Pagination information")

class APIResponseBuilder:
    """Builder for creating standardized API responses"""
    
    def __init__(self, request: Optional[Request] = None, version: APIVersion = APIVersion.LATEST):
        self.request = request
        self.version = version
        self.request_id = str(uuid.uuid4())
        self.start_time = datetime.now()
        
    def _create_meta(self, **kwargs) -> ResponseMeta:
        """Create response metadata"""
        processing_time = (datetime.now() - self.start_time).total_seconds() * 1000
        
        return ResponseMeta(
            request_id=self.request_id,
            timestamp=datetime.now().isoformat(),
            api_version=self.version.value,
            processing_time_ms=round(processing_time, 2),
            **kwargs
        )
    
    def success(
        self,
        message: str,
        data: Optional[Any] = None,
        **meta_kwargs
    ) -> StandardAPIResponse:
        """Create success response"""
        return StandardAPIResponse(
            status=ResponseStatus.SUCCESS,
            message=message,
            data=data,
            meta=self._create_meta(**meta_kwargs)
        )
    
    def error(
        self,
        message: str,
        error_code: ErrorCode,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
        **meta_kwargs
    ) -> StandardErrorResponse:
        """Create error response"""
        return StandardErrorResponse(
            status=ResponseStatus.ERROR,
            message=message,
            error_code=error_code,
            details=details,
            suggestions=suggestions,
            meta=self._create_meta(**meta_kwargs)
        )
    
    def paginated(
        self,
        message: str,
        data: List[Any],
        page: int,
        page_size: int,
        total_items: int,
        **meta_kwargs
    ) -> PaginatedResponse:
        """Create paginated response"""
        total_pages = (total_items + page_size - 1) // page_size
        
        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )
        
        return PaginatedResponse(
            status=ResponseStatus.SUCCESS,
            message=message,
            data=data,
            pagination=pagination,
            meta=self._create_meta(**meta_kwargs)
        )
    
    def partial(
        self,
        message: str,
        data: Any,
        errors: List[Dict[str, Any]],
        **meta_kwargs
    ) -> StandardAPIResponse:
        """Create partial success response (some operations failed)"""
        return StandardAPIResponse(
            status=ResponseStatus.PARTIAL,
            message=message,
            data=data,
            errors=errors,
            meta=self._create_meta(**meta_kwargs)
        )

class APIVersionManager:
    """Manages API versioning and compatibility"""
    
    @staticmethod
    def get_version_from_request(request: Request) -> APIVersion:
        """Extract API version from request"""
        # Check header first
        version_header = request.headers.get("API-Version")
        if version_header:
            try:
                return APIVersion(version_header.lower())
            except ValueError:
                pass
        
        # Check path prefix
        path = request.url.path
        if path.startswith("/api/v1/"):
            return APIVersion.V1
        elif path.startswith("/api/v2/"):
            return APIVersion.V2
        
        # Default to latest
        return APIVersion.LATEST
    
    @staticmethod
    def transform_response_for_version(response: StandardAPIResponse, version: APIVersion) -> Dict[str, Any]:
        """Transform response based on API version"""
        if version == APIVersion.V1:
            # V1 format for backward compatibility
            return {
                "success": response.status == ResponseStatus.SUCCESS,
                "message": response.message,
                "data": response.data,
                "timestamp": response.meta.timestamp,
                "errors": response.errors
            }
        else:
            # V2+ uses full standardized format
            return response.dict()

class APIExceptionHandler:
    """Centralized exception handling for APIs"""
    
    @staticmethod
    def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle FastAPI HTTP exceptions"""
        builder = APIResponseBuilder(request)
        
        # Map HTTP status codes to error codes
        error_code_map = {
            400: ErrorCode.VALIDATION_ERROR,
            401: ErrorCode.AUTHENTICATION_ERROR,
            403: ErrorCode.AUTHORIZATION_ERROR,
            404: ErrorCode.NOT_FOUND,
            409: ErrorCode.CONFLICT,
            429: ErrorCode.RATE_LIMITED,
            500: ErrorCode.INTERNAL_ERROR,
            503: ErrorCode.SERVICE_UNAVAILABLE
        }
        
        error_code = error_code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
        
        error_response = builder.error(
            message=exc.detail,
            error_code=error_code,
            details={"status_code": exc.status_code}
        )
        
        # Transform for API version
        version = APIVersionManager.get_version_from_request(request)
        response_data = APIVersionManager.transform_response_for_version(error_response, version)
        
        return JSONResponse(
            status_code=exc.status_code,
            content=response_data
        )
    
    @staticmethod
    def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
        """Handle validation errors"""
        builder = APIResponseBuilder(request)
        
        # Extract validation details
        details = {}
        if hasattr(exc, 'errors'):
            details["validation_errors"] = exc.errors()
        
        error_response = builder.error(
            message="Request validation failed",
            error_code=ErrorCode.VALIDATION_ERROR,
            details=details,
            suggestions=[
                "Check the request format and required fields",
                "Verify data types match the API specification"
            ]
        )
        
        version = APIVersionManager.get_version_from_request(request)
        response_data = APIVersionManager.transform_response_for_version(error_response, version)
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=response_data
        )
    
    @staticmethod
    def handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions"""
        builder = APIResponseBuilder(request)
        
        # Log the full error for debugging
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        
        # Don't expose internal details in production
        details = {}
        if builder.version == APIVersion.V1:  # More permissive for development
            details = {
                "exception_type": type(exc).__name__,
                "exception_message": str(exc)
            }
        
        error_response = builder.error(
            message="An unexpected error occurred",
            error_code=ErrorCode.INTERNAL_ERROR,
            details=details,
            suggestions=[
                "Try the request again",
                "Contact support if the issue persists"
            ]
        )
        
        version = APIVersionManager.get_version_from_request(request)
        response_data = APIVersionManager.transform_response_for_version(error_response, version)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response_data
        )

# Utility functions for common response patterns
def success_response(
    request: Request,
    message: str,
    data: Optional[Any] = None,
    **kwargs
) -> JSONResponse:
    """Helper function to create standardized success response"""
    builder = APIResponseBuilder(request)
    response = builder.success(message, data, **kwargs)
    
    version = APIVersionManager.get_version_from_request(request)
    response_data = APIVersionManager.transform_response_for_version(response, version)
    
    return JSONResponse(content=response_data)

def error_response(
    request: Request,
    message: str,
    error_code: ErrorCode,
    status_code: int = 500,
    **kwargs
) -> JSONResponse:
    """Helper function to create standardized error response"""
    builder = APIResponseBuilder(request)
    response = builder.error(message, error_code, **kwargs)
    
    version = APIVersionManager.get_version_from_request(request)
    response_data = APIVersionManager.transform_response_for_version(response, version)
    
    return JSONResponse(status_code=status_code, content=response_data)

def paginated_response(
    request: Request,
    message: str,
    data: List[Any],
    page: int,
    page_size: int,
    total_items: int,
    **kwargs
) -> JSONResponse:
    """Helper function to create standardized paginated response"""
    builder = APIResponseBuilder(request)
    response = builder.paginated(message, data, page, page_size, total_items, **kwargs)
    
    version = APIVersionManager.get_version_from_request(request)
    response_data = APIVersionManager.transform_response_for_version(response, version)
    
    return JSONResponse(content=response_data)

# Middleware for API standardization
class APIStandardizationMiddleware:
    """Middleware to ensure all responses follow standards"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        """Process requests and standardize responses"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Add request ID to context
        request_id = str(uuid.uuid4())
        scope["request_id"] = request_id
        
        # Add API version to context
        api_version = APIVersionManager.get_version_from_request(request)
        scope["api_version"] = api_version
        
        await self.app(scope, receive, send)

# Decorator for automatic response standardization
def standardize_response(version: APIVersion = APIVersion.LATEST):
    """Decorator to automatically standardize endpoint responses"""
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            builder = APIResponseBuilder(request, version)
            
            try:
                # Execute the endpoint function
                result = await func(request, *args, **kwargs)
                
                # If result is already a JSONResponse, return as-is
                if isinstance(result, JSONResponse):
                    return result
                
                # If result is a dict with 'success' key, handle legacy format
                if isinstance(result, dict) and 'success' in result:
                    if result['success']:
                        response = builder.success(
                            message=result.get('message', 'Operation successful'),
                            data=result.get('data')
                        )
                    else:
                        response = builder.error(
                            message=result.get('message', 'Operation failed'),
                            error_code=ErrorCode.INTERNAL_ERROR
                        )
                else:
                    # Wrap raw response
                    response = builder.success(
                        message="Operation completed successfully",
                        data=result
                    )
                
                # Transform for API version
                response_data = APIVersionManager.transform_response_for_version(response, version)
                return JSONResponse(content=response_data)
                
            except HTTPException as e:
                return APIExceptionHandler.handle_http_exception(request, e)
            except Exception as e:
                return APIExceptionHandler.handle_generic_exception(request, e)
        
        return wrapper
    return decorator

# Configuration class for API standards
@dataclass
class APIConfig:
    """Configuration for API standardization"""
    default_version: APIVersion = APIVersion.LATEST
    enable_version_deprecation_warnings: bool = True
    max_page_size: int = 1000
    default_page_size: int = 20
    enable_request_logging: bool = True
    enable_response_compression: bool = True
    
def get_api_config() -> APIConfig:
    """Get API configuration"""
    return APIConfig()

# Export main components
__all__ = [
    "APIVersion",
    "ResponseStatus", 
    "ErrorCode",
    "StandardAPIResponse",
    "StandardErrorResponse",
    "PaginatedResponse",
    "APIResponseBuilder",
    "APIVersionManager",
    "APIExceptionHandler",
    "success_response",
    "error_response", 
    "paginated_response",
    "standardize_response",
    "APIStandardizationMiddleware",
    "APIConfig",
    "get_api_config"
] 