"""
Advanced Security Middleware
Production-ready security features with comprehensive protection
"""

import asyncio
import logging
import time
import hashlib
import hmac
import jwt
import redis.asyncio as redis
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field
from fastapi import Request, Response, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import ipaddress
import re
from prometheus_client import Counter, Histogram, Gauge
import bcrypt

logger = logging.getLogger(__name__)

# Prometheus metrics
SECURITY_EVENTS = Counter(
    'security_events_total',
    'Total security events',
    ['event_type', 'severity', 'source']
)

RATE_LIMIT_HITS = Counter(
    'rate_limit_hits_total',
    'Rate limit violations',
    ['endpoint', 'client_type']
)

AUTH_ATTEMPTS = Counter(
    'auth_attempts_total',
    'Authentication attempts',
    ['status', 'method']
)

REQUEST_DURATION = Histogram(
    'security_middleware_duration_seconds',
    'Security middleware processing time',
    ['middleware_type']
)

ACTIVE_SESSIONS = Gauge(
    'active_sessions_total',
    'Number of active user sessions'
)

@dataclass
class SecurityConfig:
    """Security configuration parameters"""
    # Rate limiting
    global_rate_limit: int = 1000  # requests per minute
    user_rate_limit: int = 100     # requests per minute per user
    endpoint_rate_limits: Dict[str, int] = field(default_factory=dict)
    burst_multiplier: float = 1.5
    
    # Authentication
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire: int = 30  # minutes
    refresh_token_expire: int = 7  # days
    
    # Session management
    max_sessions_per_user: int = 5
    session_timeout: int = 3600    # seconds
    
    # Security policies
    password_min_length: int = 12
    password_require_special: bool = True
    password_require_numbers: bool = True
    password_require_uppercase: bool = True
    
    # Input validation
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    max_json_depth: int = 10
    allowed_content_types: Set[str] = field(default_factory=lambda: {
        'application/json', 'application/x-www-form-urlencoded', 'multipart/form-data'
    })
    
    # IP filtering
    blocked_ips: Set[str] = field(default_factory=set)
    allowed_ips: Set[str] = field(default_factory=set)
    geo_blocking_enabled: bool = False
    
    # Security headers
    enable_csrf_protection: bool = True
    enable_cors_protection: bool = True
    cors_allowed_origins: List[str] = field(default_factory=list)

@dataclass
class RateLimitRule:
    """Rate limiting rule configuration"""
    endpoint: str
    limit: int
    window: int  # seconds
    burst_limit: Optional[int] = None
    scope: str = "global"  # global, user, ip

class AdvancedRateLimiter:
    """Advanced rate limiting with multiple strategies"""
    
    def __init__(self, redis_client: redis.Redis, config: SecurityConfig):
        self.redis = redis_client
        self.config = config
        self.rules = self._load_rate_limit_rules()
        
    def _load_rate_limit_rules(self) -> List[RateLimitRule]:
        """Load rate limiting rules from configuration"""
        rules = [
            # Global limits
            RateLimitRule("/api/v1/auth/login", 5, 300, scope="ip"),
            RateLimitRule("/api/v1/auth/register", 3, 3600, scope="ip"),
            RateLimitRule("/api/v1/auth/reset-password", 3, 3600, scope="ip"),
            
            # Trading endpoints
            RateLimitRule("/api/v1/orders", 100, 60, scope="user"),
            RateLimitRule("/api/v1/orders/cancel", 50, 60, scope="user"),
            RateLimitRule("/api/v1/positions", 200, 60, scope="user"),
            
            # Market data
            RateLimitRule("/api/v1/market-data", 1000, 60, scope="user"),
            RateLimitRule("/api/v1/quotes", 500, 60, scope="user"),
            
            # Admin endpoints
            RateLimitRule("/api/v1/admin", 20, 60, scope="user"),
            
            # WebSocket connections
            RateLimitRule("/ws", 10, 300, scope="ip"),
        ]
        
        # Add custom rules from config
        for endpoint, limit in self.config.endpoint_rate_limits.items():
            rules.append(RateLimitRule(endpoint, limit, 60))
            
        return rules
    
    async def check_rate_limit(self, request: Request, user_id: Optional[str] = None) -> tuple[bool, Optional[int]]:
        """Check if request passes rate limiting"""
        client_ip = self._get_client_ip(request)
        endpoint = request.url.path
        
        # Find applicable rules
        applicable_rules = [rule for rule in self.rules if endpoint.startswith(rule.endpoint)]
        
        if not applicable_rules:
            # Apply global rate limit
            applicable_rules = [RateLimitRule("global", self.config.global_rate_limit, 60)]
        
        for rule in applicable_rules:
            allowed, retry_after = await self._check_rule(rule, client_ip, user_id, endpoint)
            if not allowed:
                RATE_LIMIT_HITS.labels(endpoint=endpoint, client_type=rule.scope).inc()
                return False, retry_after
                
        return True, None
    
    async def _check_rule(self, rule: RateLimitRule, client_ip: str, user_id: Optional[str], endpoint: str) -> tuple[bool, Optional[int]]:
        """Check individual rate limit rule"""
        # Determine key based on scope
        if rule.scope == "ip":
            key = f"rate_limit:ip:{client_ip}:{rule.endpoint}"
        elif rule.scope == "user" and user_id:
            key = f"rate_limit:user:{user_id}:{rule.endpoint}"
        else:
            key = f"rate_limit:global:{rule.endpoint}"
        
        # Sliding window rate limiting
        now = time.time()
        window_start = now - rule.window
        
        # Remove old entries
        await self.redis.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        current_count = await self.redis.zcard(key)
        
        # Check burst limit
        burst_limit = rule.burst_limit or int(rule.limit * self.config.burst_multiplier)
        
        if current_count >= burst_limit:
            # Calculate retry after
            oldest_request = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest_request:
                retry_after = int(oldest_request[0][1] + rule.window - now)
                return False, max(1, retry_after)
            return False, rule.window
        
        # Add current request
        await self.redis.zadd(key, {str(now): now})
        await self.redis.expire(key, rule.window)
        
        return True, None
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP with proxy support"""
        # Check X-Forwarded-For header (proxy support)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to client host
        return request.client.host if request.client else "unknown"

class InputValidator:
    """Comprehensive input validation and sanitization"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.dangerous_patterns = [
            r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',  # Script tags
            r'javascript:',  # JavaScript protocol
            r'on\w+\s*=',    # Event handlers
            r'expression\s*\(',  # CSS expressions
            r'@import',      # CSS imports
            r'eval\s*\(',    # eval() calls
            r'\b(union|select|insert|update|delete|drop|create|alter)\b',  # SQL keywords
        ]
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.dangerous_patterns]
    
    async def validate_request(self, request: Request) -> bool:
        """Validate incoming request"""
        # Check content type
        content_type = request.headers.get("content-type", "").split(";")[0]
        if content_type and content_type not in self.config.allowed_content_types:
            raise HTTPException(status_code=415, detail="Unsupported content type")
        
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.config.max_request_size:
            raise HTTPException(status_code=413, detail="Request too large")
        
        # Validate headers
        await self._validate_headers(request)
        
        # Validate query parameters
        await self._validate_query_params(request)
        
        return True
    
    async def validate_json_payload(self, payload: Any, max_depth: Optional[int] = None) -> bool:
        """Validate JSON payload"""
        if max_depth is None:
            max_depth = self.config.max_json_depth
        
        def check_depth(obj, current_depth=0):
            if current_depth > max_depth:
                raise HTTPException(status_code=400, detail="JSON depth exceeded")
            
            if isinstance(obj, dict):
                for value in obj.values():
                    check_depth(value, current_depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    check_depth(item, current_depth + 1)
        
        check_depth(payload)
        return True
    
    async def sanitize_input(self, text: str) -> str:
        """Sanitize text input"""
        if not isinstance(text, str):
            return text
        
        # Remove dangerous patterns
        sanitized = text
        for pattern in self.compiled_patterns:
            sanitized = pattern.sub('', sanitized)
        
        # HTML encode special characters
        sanitized = (sanitized
                    .replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;')
                    .replace("'", '&#x27;'))
        
        return sanitized
    
    async def _validate_headers(self, request: Request):
        """Validate request headers"""
        # Check for suspicious headers
        suspicious_headers = ['x-forwarded-host', 'x-originating-ip']
        for header in suspicious_headers:
            if header in request.headers:
                logger.warning(f"Suspicious header detected: {header}")
        
        # Validate User-Agent
        user_agent = request.headers.get("user-agent", "")
        if not user_agent or len(user_agent) > 500:
            logger.warning(f"Suspicious User-Agent: {user_agent[:100]}...")
    
    async def _validate_query_params(self, request: Request):
        """Validate query parameters"""
        for key, value in request.query_params.items():
            # Check for dangerous patterns
            for pattern in self.compiled_patterns:
                if pattern.search(value):
                    raise HTTPException(status_code=400, detail=f"Invalid parameter: {key}")

class JWTManager:
    """Advanced JWT token management with refresh and blacklisting"""
    
    def __init__(self, redis_client: redis.Redis, config: SecurityConfig):
        self.redis = redis_client
        self.config = config
        self.security = HTTPBearer()
    
    async def create_tokens(self, user_id: str, permissions: List[str]) -> Dict[str, str]:
        """Create access and refresh tokens"""
        now = datetime.utcnow()
        
        # Access token payload
        access_payload = {
            'user_id': user_id,
            'permissions': permissions,
            'type': 'access',
            'iat': now,
            'exp': now + timedelta(minutes=self.config.access_token_expire),
            'jti': self._generate_jti()
        }
        
        # Refresh token payload
        refresh_payload = {
            'user_id': user_id,
            'type': 'refresh',
            'iat': now,
            'exp': now + timedelta(days=self.config.refresh_token_expire),
            'jti': self._generate_jti()
        }
        
        # Generate tokens
        access_token = jwt.encode(access_payload, self.config.jwt_secret, algorithm=self.config.jwt_algorithm)
        refresh_token = jwt.encode(refresh_payload, self.config.jwt_secret, algorithm=self.config.jwt_algorithm)
        
        # Store refresh token
        await self._store_refresh_token(user_id, refresh_token, refresh_payload['jti'])
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': self.config.access_token_expire * 60
        }
    
    async def verify_token(self, token: str, token_type: str = 'access') -> Optional[Dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.config.jwt_secret, algorithms=[self.config.jwt_algorithm])
            
            # Check token type
            if payload.get('type') != token_type:
                return None
            
            # Check if token is blacklisted
            jti = payload.get('jti')
            if jti and await self._is_token_blacklisted(jti):
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """Create new access token from refresh token"""
        payload = await self.verify_token(refresh_token, 'refresh')
        if not payload:
            return None
        
        user_id = payload['user_id']
        
        # Get user permissions (implement based on your user system)
        permissions = await self._get_user_permissions(user_id)
        
        # Create new access token
        now = datetime.utcnow()
        access_payload = {
            'user_id': user_id,
            'permissions': permissions,
            'type': 'access',
            'iat': now,
            'exp': now + timedelta(minutes=self.config.access_token_expire),
            'jti': self._generate_jti()
        }
        
        access_token = jwt.encode(access_payload, self.config.jwt_secret, algorithm=self.config.jwt_algorithm)
        
        return {
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': self.config.access_token_expire * 60
        }
    
    async def blacklist_token(self, token: str):
        """Add token to blacklist"""
        try:
            payload = jwt.decode(token, self.config.jwt_secret, algorithms=[self.config.jwt_algorithm], options={"verify_exp": False})
            jti = payload.get('jti')
            exp = payload.get('exp')
            
            if jti and exp:
                # Store blacklisted token until expiration
                expiry_time = exp - int(datetime.utcnow().timestamp())
                if expiry_time > 0:
                    await self.redis.setex(f"blacklisted_token:{jti}", expiry_time, "1")
                    
        except jwt.InvalidTokenError:
            pass  # Token already invalid
    
    async def _store_refresh_token(self, user_id: str, token: str, jti: str):
        """Store refresh token for user"""
        key = f"refresh_tokens:{user_id}"
        await self.redis.hset(key, jti, token)
        await self.redis.expire(key, self.config.refresh_token_expire * 24 * 3600)
    
    async def _is_token_blacklisted(self, jti: str) -> bool:
        """Check if token is blacklisted"""
        return await self.redis.exists(f"blacklisted_token:{jti}")
    
    async def _get_user_permissions(self, user_id: str) -> List[str]:
        """Get user permissions (implement based on your user system)"""
        # This should be implemented based on your user/role system
        return ['read', 'trade']  # Default permissions
    
    def _generate_jti(self) -> str:
        """Generate unique token ID"""
        import uuid
        return str(uuid.uuid4())

class SecurityMiddleware(BaseHTTPMiddleware):
    """Main security middleware orchestrating all security features"""
    
    def __init__(self, app, redis_client: redis.Redis, config: SecurityConfig):
        super().__init__(app)
        self.redis = redis_client
        self.config = config
        self.rate_limiter = AdvancedRateLimiter(redis_client, config)
        self.input_validator = InputValidator(config)
        self.jwt_manager = JWTManager(redis_client, config)
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Main middleware dispatch method"""
        start_time = time.time()
        
        try:
            # IP filtering
            if not await self._check_ip_access(request):
                return JSONResponse(
                    status_code=403,
                    content={"error": "Access denied from this IP"}
                )
            
            # Input validation
            await self.input_validator.validate_request(request)
            
            # Rate limiting
            user_id = await self._extract_user_id(request)
            allowed, retry_after = await self.rate_limiter.check_rate_limit(request, user_id)
            
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"error": "Rate limit exceeded", "retry_after": retry_after},
                    headers={"Retry-After": str(retry_after)} if retry_after else {}
                )
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            self._add_security_headers(response)
            
            # Record metrics
            REQUEST_DURATION.labels(middleware_type='security').observe(time.time() - start_time)
            
            return response
            
        except HTTPException as e:
            SECURITY_EVENTS.labels(
                event_type='http_exception',
                severity='warning',
                source=self._get_client_ip(request)
            ).inc()
            return JSONResponse(
                status_code=e.status_code,
                content={"error": e.detail}
            )
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            SECURITY_EVENTS.labels(
                event_type='middleware_error',
                severity='critical',
                source=self._get_client_ip(request)
            ).inc()
            return JSONResponse(
                status_code=500,
                content={"error": "Internal security error"}
            )
    
    async def _check_ip_access(self, request: Request) -> bool:
        """Check if IP is allowed access"""
        client_ip = self._get_client_ip(request)
        
        # Check blocked IPs
        if client_ip in self.config.blocked_ips:
            logger.warning(f"Blocked IP attempted access: {client_ip}")
            return False
        
        # Check allowed IPs (if whitelist is configured)
        if self.config.allowed_ips and client_ip not in self.config.allowed_ips:
            logger.warning(f"Non-whitelisted IP attempted access: {client_ip}")
            return False
        
        return True
    
    async def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request for rate limiting"""
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        payload = await self.jwt_manager.verify_token(token)
        return payload.get('user_id') if payload else None
    
    def _add_security_headers(self, response: Response):
        """Add security headers to response"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        # Remove server identification
        response.headers.pop("server", None)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP with proxy support"""
        return self.rate_limiter._get_client_ip(request)

class PasswordValidator:
    """Advanced password validation and strength checking"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
    
    def validate_password(self, password: str) -> tuple[bool, List[str]]:
        """Validate password strength"""
        errors = []
        
        # Length check
        if len(password) < self.config.password_min_length:
            errors.append(f"Password must be at least {self.config.password_min_length} characters long")
        
        # Uppercase check
        if self.config.password_require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        # Lowercase check
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        # Numbers check
        if self.config.password_require_numbers and not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        # Special characters check
        if self.config.password_require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        # Common password check
        if self._is_common_password(password):
            errors.append("Password is too common, please choose a more unique password")
        
        return len(errors) == 0, errors
    
    def _is_common_password(self, password: str) -> bool:
        """Check if password is in common passwords list"""
        common_passwords = {
            'password', '123456', '123456789', 'qwerty', 'abc123',
            'password123', 'admin', 'letmein', 'welcome', 'monkey'
        }
        return password.lower() in common_passwords
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# Factory functions for easy integration
async def create_security_middleware(app, redis_url: str, config: SecurityConfig = None) -> SecurityMiddleware:
    """Create and configure security middleware"""
    if config is None:
        config = SecurityConfig()
    
    # Initialize Redis client
    redis_client = redis.from_url(redis_url)
    
    return SecurityMiddleware(app, redis_client, config)

def get_security_config_from_env() -> SecurityConfig:
    """Load security configuration from environment variables"""
    import os
    
    return SecurityConfig(
        global_rate_limit=int(os.getenv('SECURITY_GLOBAL_RATE_LIMIT', '1000')),
        user_rate_limit=int(os.getenv('SECURITY_USER_RATE_LIMIT', '100')),
        jwt_secret=os.getenv('JWT_SECRET_KEY', 'change-me-in-production'),
        jwt_algorithm=os.getenv('JWT_ALGORITHM', 'HS256'),
        access_token_expire=int(os.getenv('ACCESS_TOKEN_EXPIRE', '30')),
        refresh_token_expire=int(os.getenv('REFRESH_TOKEN_EXPIRE', '7')),
        max_request_size=int(os.getenv('MAX_REQUEST_SIZE', str(10 * 1024 * 1024))),
        password_min_length=int(os.getenv('PASSWORD_MIN_LENGTH', '12')),
        cors_allowed_origins=os.getenv('CORS_ALLOWED_ORIGINS', '').split(',') if os.getenv('CORS_ALLOWED_ORIGINS') else []
    ) 