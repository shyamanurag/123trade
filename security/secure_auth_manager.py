"""
Secure Authentication Manager
Production-ready authentication system with no default credentials
"""

import os
import jwt
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict, validator
import redis.asyncio as redis
import hashlib
import json
from dataclasses import dataclass
import asyncio
from enum import Enum

logger = logging.getLogger(__name__)

# Strong password context with bcrypt
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Strong hashing rounds
)

# Security Configuration
@dataclass
class SecurityConfig:
    """Security configuration"""
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30
    password_min_length: int = 12
    require_special_chars: bool = True
    require_numbers: bool = True
    require_uppercase: bool = True
    require_lowercase: bool = True

class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"

class User(BaseModel):
    """User model with strong validation"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    user_id: str
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    permissions: List[str] = []

class UserCreate(BaseModel):
    """User creation model with password validation"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    username: str
    email: str
    password: str
    full_name: str
    role: UserRole = UserRole.TRADER

    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v.lower()

    @validator('password')
    def validate_password(cls, v):
        """Strong password validation"""
        if len(v) < 12:
            raise ValueError('Password must be at least 12 characters')
        
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)
        
        if not has_upper:
            raise ValueError('Password must contain uppercase letters')
        if not has_lower:
            raise ValueError('Password must contain lowercase letters')
        if not has_digit:
            raise ValueError('Password must contain numbers')
        if not has_special:
            raise ValueError('Password must contain special characters')
            
        return v

class TokenData(BaseModel):
    """Token data model"""
    user_id: str
    username: str
    email: str
    role: str
    permissions: List[str]
    exp: datetime

class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str

class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]

class SecureAuthManager:
    """Secure authentication manager with no default credentials"""
    
    def __init__(self, config: SecurityConfig, redis_client: redis.Redis):
        self.config = config
        self.redis_client = redis_client
        self.security_scheme = HTTPBearer()
        
        # Validate JWT secret strength
        if len(self.config.jwt_secret) < 32:
            raise ValueError("JWT secret must be at least 32 characters")
        
        logger.info("🔒 Secure Authentication Manager initialized")
    
    def _generate_secure_password_hash(self, password: str) -> str:
        """Generate secure password hash"""
        return pwd_context.hash(password)
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def _generate_user_id(self) -> str:
        """Generate unique user ID"""
        return f"user_{secrets.token_hex(16)}"
    
    async def create_user(self, user_data: UserCreate, created_by: str) -> User:
        """Create a new user with secure defaults"""
        # Check if username exists
        existing_user = await self.get_user_by_username(user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Check if email exists
        existing_email = await self.get_user_by_email(user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        
        # Create user
        user_id = self._generate_user_id()
        password_hash = self._generate_secure_password_hash(user_data.password)
        
        user = User(
            user_id=user_id,
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            role=user_data.role,
            created_at=datetime.utcnow(),
            permissions=self._get_role_permissions(user_data.role)
        )
        
        # Store user data
        await self.redis_client.hset(
            f"user:{user.username}",
            mapping={
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "password_hash": password_hash,
                "is_active": str(user.is_active),
                "created_at": user.created_at.isoformat(),
                "permissions": json.dumps(user.permissions),
                "failed_login_attempts": "0",
                "created_by": created_by
            }
        )
        
        # Store by email for lookup
        await self.redis_client.set(f"email:{user.email}", user.username)
        
        logger.info(f"✅ Created user: {user.username} with role: {user.role}")
        return user
    
    def _get_role_permissions(self, role: UserRole) -> List[str]:
        """Get permissions for a role"""
        role_permissions = {
            UserRole.ADMIN: [
                "users:read", "users:write", "users:delete",
                "trading:read", "trading:write", "trading:control",
                "system:read", "system:write", "system:admin",
                "monitoring:read", "monitoring:write"
            ],
            UserRole.TRADER: [
                "trading:read", "trading:write",
                "portfolio:read", "portfolio:write",
                "orders:read", "orders:write",
                "monitoring:read"
            ],
            UserRole.VIEWER: [
                "trading:read", "portfolio:read",
                "orders:read", "monitoring:read"
            ]
        }
        return role_permissions.get(role, [])
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        user_data = await self.redis_client.hgetall(f"user:{username}")
        if not user_data:
            return None
        
        return User(
            user_id=user_data["user_id"],
            username=user_data["username"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            role=user_data["role"],
            is_active=user_data["is_active"] == "true",
            created_at=datetime.fromisoformat(user_data["created_at"]),
            last_login=datetime.fromisoformat(user_data["last_login"]) if user_data.get("last_login") else None,
            failed_login_attempts=int(user_data.get("failed_login_attempts", 0)),
            locked_until=datetime.fromisoformat(user_data["locked_until"]) if user_data.get("locked_until") else None,
            permissions=json.loads(user_data.get("permissions", "[]"))
        )
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        username = await self.redis_client.get(f"email:{email}")
        if not username:
            return None
        return await self.get_user_by_username(username)
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with rate limiting and lockout"""
        user = await self.get_user_by_username(username)
        if not user:
            # Prevent username enumeration by adding delay
            await asyncio.sleep(0.5)
            return None
        
        # Check if user is locked
        if user.locked_until and datetime.utcnow() < user.locked_until:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account locked until {user.locked_until.isoformat()}"
            )
        
        # Check if account is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )
        
        # Get password hash
        user_data = await self.redis_client.hgetall(f"user:{username}")
        password_hash = user_data.get("password_hash")
        
        if not password_hash or not self._verify_password(password, password_hash):
            # Increment failed attempts
            await self._handle_failed_login(username)
            return None
        
        # Reset failed attempts on successful login
        await self._reset_failed_attempts(username)
        
        # Update last login
        await self.redis_client.hset(
            f"user:{username}",
            "last_login",
            datetime.utcnow().isoformat()
        )
        
        logger.info(f"✅ User authenticated: {username}")
        return user
    
    async def _handle_failed_login(self, username: str):
        """Handle failed login attempt"""
        # Increment failed attempts
        failed_attempts = await self.redis_client.hincrby(f"user:{username}", "failed_login_attempts", 1)
        
        # Lock account if too many failures
        if failed_attempts >= self.config.max_login_attempts:
            locked_until = datetime.utcnow() + timedelta(minutes=self.config.lockout_duration_minutes)
            await self.redis_client.hset(
                f"user:{username}",
                "locked_until",
                locked_until.isoformat()
            )
            logger.warning(f"🔒 Account locked due to failed attempts: {username}")
    
    async def _reset_failed_attempts(self, username: str):
        """Reset failed login attempts"""
        await self.redis_client.hset(f"user:{username}", "failed_login_attempts", "0")
        await self.redis_client.hdel(f"user:{username}", "locked_until")
    
    def create_access_token(self, user: User) -> str:
        """Create JWT access token"""
        payload = {
            "sub": user.user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "permissions": user.permissions,
            "exp": datetime.utcnow() + timedelta(minutes=self.config.access_token_expire_minutes),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        return jwt.encode(payload, self.config.jwt_secret, algorithm=self.config.jwt_algorithm)
    
    def create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token"""
        payload = {
            "sub": user.user_id,
            "username": user.username,
            "exp": datetime.utcnow() + timedelta(days=self.config.refresh_token_expire_days),
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        return jwt.encode(payload, self.config.jwt_secret, algorithm=self.config.jwt_algorithm)
    
    def verify_token(self, token: str) -> TokenData:
        """Verify JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret,
                algorithms=[self.config.jwt_algorithm]
            )
            
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            return TokenData(
                user_id=payload["sub"],
                username=payload["username"],
                email=payload["email"],
                role=payload["role"],
                permissions=payload["permissions"],
                exp=datetime.fromtimestamp(payload["exp"])
            )
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    async def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
    ) -> User:
        """Get current user from token"""
        token_data = self.verify_token(credentials.credentials)
        user = await self.get_user_by_username(token_data.username)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        
        return user
    
    def require_permission(self, permission: str):
        """Decorator to require specific permission"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Extract user from kwargs or args
                user = None
                for arg in args:
                    if isinstance(arg, User):
                        user = arg
                        break
                
                if not user:
                    for key, value in kwargs.items():
                        if isinstance(value, User):
                            user = value
                            break
                
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User authentication required"
                    )
                
                if permission not in user.permissions:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission denied: {permission}"
                    )
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    async def login(self, login_data: LoginRequest) -> LoginResponse:
        """Login user and return tokens"""
        user = await self.authenticate_user(login_data.username, login_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        access_token = self.create_access_token(user)
        refresh_token = self.create_refresh_token(user)
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.config.access_token_expire_minutes * 60,
            user={
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "permissions": user.permissions
            }
        )
    
    async def initialize_system(self, initial_admin_password: Optional[str] = None):
        """Initialize the system with proper security"""
        # Check if any users exist
        users_exist = await self.redis_client.exists("user:*")
        
        if not users_exist and initial_admin_password:
            # Only create initial admin if explicitly provided
            logger.info("🔧 Creating initial admin user...")
            
            admin_user_data = UserCreate(
                username="admin",
                email="admin@trading-system.local",
                password=initial_admin_password,
                full_name="System Administrator",
                role=UserRole.ADMIN
            )
            
            await self.create_user(admin_user_data, "system_initialization")
            logger.info("✅ Initial admin user created")
        else:
            logger.info("👥 Users already exist or no initial password provided")

def create_secure_auth_manager(redis_client: redis.Redis) -> SecureAuthManager:
    """Factory function to create secure auth manager"""
    
    # Get JWT secret from environment or generate one
    jwt_secret = os.getenv("JWT_SECRET")
    if not jwt_secret:
        logger.warning("⚠️ No JWT_SECRET found in environment. Generating random secret.")
        logger.warning("⚠️ This will invalidate all existing tokens on restart!")
        jwt_secret = secrets.token_urlsafe(64)
    
    config = SecurityConfig(
        jwt_secret=jwt_secret,
        access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
        refresh_token_expire_days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")),
        max_login_attempts=int(os.getenv("MAX_LOGIN_ATTEMPTS", "5")),
        lockout_duration_minutes=int(os.getenv("LOCKOUT_DURATION_MINUTES", "30"))
    )
    
    return SecureAuthManager(config, redis_client) 