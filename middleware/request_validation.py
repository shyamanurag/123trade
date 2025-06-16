"""
Request Validation Middleware
Provides comprehensive validation for incoming requests to prevent injection attacks
and ensure data consistency and integrity across the API.
"""

import json
import inspect
import logging
from typing import Any, Dict, List, Optional, Type, Union, Set, Callable
import re
from datetime import datetime

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError, create_model
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.logging_config import get_logger

logger = get_logger(__name__)

# Common regex patterns for validation
PATTERNS = {
    "email": re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
    "password": re.compile(r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$"),
    "username": re.compile(r"^[a-zA-Z0-9_-]{3,30}$"),
    "numeric": re.compile(r"^[0-9]+$"),
    "alphanumeric": re.compile(r"^[a-zA-Z0-9]+$"),
    "date": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "datetime": re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$"),
    "uuid": re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
    "phone": re.compile(r"^\+?[0-9]{10,15}$"),
    "ip": re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$"),
    "url": re.compile(r"^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$")
}

# Common suspicious patterns that might indicate injection attacks
SUSPICIOUS_PATTERNS = [
    re.compile(r"<script.*?>.*?</script>", re.IGNORECASE | re.DOTALL),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),  # onclick, onload, etc
    re.compile(r"((\%27)|('))((\%6F)|o|(\%4F))((\%72)|r|(\%52))", re.IGNORECASE),  # SQL Injection
    re.compile(r"union\s+select", re.IGNORECASE),
    re.compile(r"exec\s*\(", re.IGNORECASE),
    re.compile(r"eval\s*\(", re.IGNORECASE),
    re.compile(r"/\*.*?\*/", re.IGNORECASE | re.DOTALL),  # SQL comments
    re.compile(r"--.*?$", re.IGNORECASE | re.MULTILINE),  # SQL comments
    re.compile(r"document\.cookie", re.IGNORECASE),
    re.compile(r"document\.location", re.IGNORECASE),
    re.compile(r"\.\.\/", re.IGNORECASE),  # Directory traversal
    re.compile(r"\$\{.*?\}", re.IGNORECASE),  # Template injection
    re.compile(r"\{\{.*?\}\}", re.IGNORECASE)  # Template injection
]

# Max content-length that we'll allow (10MB)
MAX_CONTENT_LENGTH = 10 * 1024 * 1024

class ValidationConfig:
    """Configuration for request validation"""
    
    def __init__(self, 
                 max_content_length: int = MAX_CONTENT_LENGTH,
                 exempt_paths: Set[str] = None,
                 exempt_methods: Set[str] = None,
                 security_headers: Dict[str, str] = None,
                 additional_patterns: Dict[str, re.Pattern] = None,
                 strict_content_type: bool = True):
        """
        Initialize validation configuration.
        
        Args:
            max_content_length: Maximum allowed request body size in bytes
            exempt_paths: Set of URL paths to exempt from validation
            exempt_methods: Set of HTTP methods to exempt from validation
            security_headers: Dictionary of security headers to add to responses
            additional_patterns: Additional regex patterns for validation
            strict_content_type: Whether to enforce correct Content-Type header
        """
        self.max_content_length = max_content_length
        self.exempt_paths = exempt_paths or {"/health", "/health/liveness", "/health/readiness", "/metrics"}
        self.exempt_methods = exempt_methods or {"OPTIONS", "HEAD"}
        self.strict_content_type = strict_content_type
        
        # Default security headers
        self.security_headers = security_headers or {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'self'",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "Cache-Control": "no-store, must-revalidate"
        }
        
        # Add any additional patterns
        if additional_patterns:
            self.patterns = {**PATTERNS, **additional_patterns}
        else:
            self.patterns = PATTERNS
            
    def is_path_exempt(self, path: str) -> bool:
        """Check if a path is exempt from validation"""
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return True
        return False
        
    def is_method_exempt(self, method: str) -> bool:
        """Check if a method is exempt from validation"""
        return method in self.exempt_methods


class ValidationContext:
    """Context for request validation"""
    
    def __init__(self, request: Request, config: ValidationConfig):
        self.request = request
        self.config = config
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        
    def add_error(self, field: str, message: str, code: str = "invalid_field"):
        """Add a validation error"""
        self.errors.append({
            "field": field,
            "message": message,
            "code": code
        })
        
    def add_warning(self, field: str, message: str, code: str = "warning"):
        """Add a validation warning"""
        self.warnings.append({
            "field": field,
            "message": message,
            "code": code
        })
        
    def has_errors(self) -> bool:
        """Check if there are validation errors"""
        return len(self.errors) > 0


class RequestValidator:
    """Validator for FastAPI requests"""
    
    def __init__(self, config: ValidationConfig = None):
        """
        Initialize the request validator.
        
        Args:
            config: Validation configuration
        """
        self.config = config or ValidationConfig()
        
    async def validate_request(self, request: Request) -> ValidationContext:
        """
        Validate an incoming request.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            ValidationContext: Context containing validation results
        """
        context = ValidationContext(request, self.config)
        
        # Skip validation for exempt paths or methods
        if (self.config.is_path_exempt(request.url.path) or
            self.config.is_method_exempt(request.method)):
            return context
        
        # Validate content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.config.max_content_length:
            context.add_error("content-length", 
                              f"Request body too large ({content_length} bytes)",
                              "request_too_large")
            return context
            
        # Validate content type for POST/PUT/PATCH requests
        if self.config.strict_content_type and request.method in {"POST", "PUT", "PATCH"}:
            content_type = request.headers.get("content-type", "")
            
            if not content_type:
                context.add_error("content-type", "Content-Type header is required", "missing_content_type")
            elif not any(ct in content_type.lower() for ct in ["application/json", "multipart/form-data", "application/x-www-form-urlencoded"]):
                context.add_error("content-type", f"Unsupported Content-Type: {content_type}", "invalid_content_type")
        
        # For requests with body, validate the content
        if request.method in {"POST", "PUT", "PATCH"}:
            await self._validate_request_body(context)
            
        # Validate query parameters
        await self._validate_query_params(context)
            
        return context
    
    async def _validate_request_body(self, context: ValidationContext):
        """Validate request body content"""
        request = context.request
        content_type = request.headers.get("content-type", "").lower()
        
        if "application/json" in content_type:
            try:
                # Try to parse body as JSON
                body = await request.json()
                
                # Check for suspicious patterns in JSON values
                self._scan_for_suspicious_patterns(body, context)
                    
            except json.JSONDecodeError:
                context.add_error("body", "Invalid JSON format", "invalid_json")
                
        elif any(ct in content_type for ct in ["multipart/form-data", "application/x-www-form-urlencoded"]):
            try:
                # For form data, check each field
                form = await request.form()
                for field_name, field_value in form.items():
                    # Text fields
                    if isinstance(field_value, str):
                        if self._contains_suspicious_pattern(field_value):
                            context.add_error(
                                field_name, 
                                "Field contains potentially unsafe content", 
                                "suspicious_content"
                            )
            except Exception as e:
                context.add_error("body", f"Error parsing form data: {str(e)}", "form_parse_error")
    
    async def _validate_query_params(self, context: ValidationContext):
        """Validate query parameters"""
        query_params = context.request.query_params
        
        for param_name, param_value in query_params.items():
            if self._contains_suspicious_pattern(param_value):
                context.add_error(
                    param_name, 
                    "Query parameter contains potentially unsafe content", 
                    "suspicious_content"
                )
                
            # Check specific parameter formats
            if param_name == "email" and not self.config.patterns["email"].match(param_value):
                context.add_error(param_name, "Invalid email format", "invalid_format")
                
            elif param_name == "date" and not self.config.patterns["date"].match(param_value):
                context.add_error(param_name, "Invalid date format (use YYYY-MM-DD)", "invalid_format")
                
            elif param_name == "phone" and not self.config.patterns["phone"].match(param_value):
                context.add_error(param_name, "Invalid phone number format", "invalid_format")
                
            elif param_name in ["limit", "offset", "page", "size"] and not self.config.patterns["numeric"].match(param_value):
                context.add_error(param_name, f"Invalid {param_name} value (must be numeric)", "invalid_format")
    
    def _scan_for_suspicious_patterns(self, data: Any, context: ValidationContext, path: str = ""):
        """Recursively scan for suspicious patterns in JSON data"""
        if isinstance(data, str):
            if self._contains_suspicious_pattern(data):
                field_path = path or "body"
                context.add_error(
                    field_path, 
                    "Field contains potentially unsafe content", 
                    "suspicious_content"
                )
        
        elif isinstance(data, dict):
            for key, value in data.items():
                # Check the key itself
                if self._contains_suspicious_pattern(key):
                    field_path = f"{path}.{key}" if path else key
                    context.add_error(
                        field_path, 
                        "Field name contains potentially unsafe content", 
                        "suspicious_content"
                    )
                
                # Check the value recursively
                new_path = f"{path}.{key}" if path else key
                self._scan_for_suspicious_patterns(value, context, new_path)
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                new_path = f"{path}[{i}]" if path else f"[{i}]"
                self._scan_for_suspicious_patterns(item, context, new_path)
    
    def _contains_suspicious_pattern(self, value: str) -> bool:
        """Check if a string contains any suspicious patterns"""
        if not isinstance(value, str):
            return False
            
        for pattern in SUSPICIOUS_PATTERNS:
            if pattern.search(value):
                return True
        return False


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for validating incoming HTTP requests"""
    
    def __init__(self, app: ASGIApp, config: ValidationConfig = None):
        """
        Initialize the request validation middleware.
        
        Args:
            app: ASGI application
            config: Validation configuration
        """
        super().__init__(app)
        self.validator = RequestValidator(config or ValidationConfig())
        self.config = self.validator.config
        
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process an incoming request.
        
        Args:
            request: FastAPI request
            call_next: Function to call the next middleware or route handler
        
        Returns:
            Response: HTTP response
        """
        # Skip validation for exempt paths
        if self.config.is_path_exempt(request.url.path):
            response = await call_next(request)
            self._add_security_headers(response)
            return response
        
        # Validate the request
        context = await self.validator.validate_request(request)
        
        # If there are validation errors, return a 400 response
        if context.has_errors():
            logger.warning(
                f"Request validation failed: {len(context.errors)} errors",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "client_host": request.client.host if request.client else "unknown",
                    "errors": context.errors
                }
            )
            
            response = JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "detail": "Request validation failed",
                    "errors": context.errors,
                    "timestamp": datetime.now().isoformat()
                }
            )
            self._add_security_headers(response)
            return response
            
        # If there are warnings, log them but continue processing
        if context.warnings:
            logger.info(
                f"Request validation warnings: {len(context.warnings)} warnings",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "warnings": context.warnings
                }
            )
            
        # Process the request normally
        try:
            response = await call_next(request)
            self._add_security_headers(response)
            return response
            
        except RequestValidationError as exc:
            # Handle FastAPI's built-in validation errors
            errors = self._format_validation_errors(exc.errors())
            
            logger.warning(
                f"Request schema validation failed",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "client_host": request.client.host if request.client else "unknown",
                    "errors": errors
                }
            )
            
            response = JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "detail": "Request validation failed",
                    "errors": errors,
                    "timestamp": datetime.now().isoformat()
                }
            )
            self._add_security_headers(response)
            return response
            
    def _add_security_headers(self, response: Response):
        """Add security headers to the response"""
        for name, value in self.config.security_headers.items():
            response.headers[name] = value
            
    def _format_validation_errors(self, errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format FastAPI validation errors to match our error format"""
        formatted_errors = []
        
        for error in errors:
            field = ".".join(str(loc) for loc in error.get("loc", []))
            formatted_errors.append({
                "field": field,
                "message": error.get("msg", "Validation error"),
                "code": error.get("type", "validation_error")
            })
            
        return formatted_errors


# Utility function for validating specific field formats
def validate_field_format(value: str, pattern_name: str) -> bool:
    """
    Validate that a field matches a specific format pattern.
    
    Args:
        value: Field value to validate
        pattern_name: Name of the pattern in PATTERNS dictionary
        
    Returns:
        bool: True if the value matches the pattern, False otherwise
    """
    if pattern_name not in PATTERNS:
        raise ValueError(f"Unknown pattern: {pattern_name}")
        
    return bool(PATTERNS[pattern_name].match(value))


# Function to create a middleware instance with default configuration
def get_validation_middleware(app: ASGIApp) -> RequestValidationMiddleware:
    """
    Create a request validation middleware with default configuration.
    
    Args:
        app: ASGI application
        
    Returns:
        RequestValidationMiddleware: Configured middleware instance
    """
    config = ValidationConfig(
        exempt_paths={
            "/health", 
            "/health/liveness", 
            "/health/readiness", 
            "/metrics",
            "/docs", 
            "/redoc", 
            "/openapi.json"
        }
    )
    return RequestValidationMiddleware(app, config)