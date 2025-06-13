"""
Consolidated Authentication Manager
Handles authentication, authorization, and security for all services
"""

import logging
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, Security
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import redis.asyncio as redis
from functools import wraps

logger = logging.getLogger(__name__)

class AuthConfig:
    """Authentication configuration"""
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    TOKEN_TYPE: str = "Bearer"
    
class Token(BaseModel):
    """Token model"""
    access_token: str
    refresh_token: str
    token_type: str
    
class TokenData(BaseModel):
    """Token data model"""
    username: str
    roles: List[str]
    permissions: List[str]
    
class User(BaseModel):
    """User model"""
    username: str
    email: str
    full_name: str
    disabled: bool = False
    roles: List[str] = []
    permissions: List[str] = []
    
class AuthManager:
    """Consolidated authentication manager"""
    
    def __init__(self, config: AuthConfig, redis_client: redis.Redis):
        self.config = config
        self.redis_client = redis_client
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
        
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password"""
        try:
            # Get user from Redis
            user_data = await self.redis_client.hgetall(f"user:{username}")
            if not user_data:
                return None
                
            # Verify password
            if not bcrypt.checkpw(
                password.encode(),
                user_data["password_hash"].encode()
            ):
                return None
                
            return User(**user_data)
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
            
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(
            minutes=self.config.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        to_encode.update({"exp": expire})
        return jwt.encode(
            to_encode,
            self.config.SECRET_KEY,
            algorithm=self.config.ALGORITHM
        )
        
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(
            days=self.config.REFRESH_TOKEN_EXPIRE_DAYS
        )
        to_encode.update({"exp": expire})
        return jwt.encode(
            to_encode,
            self.config.SECRET_KEY,
            algorithm=self.config.ALGORITHM
        )
        
    async def verify_token(self, token: str) -> TokenData:
        """Verify token and return token data"""
        try:
            payload = jwt.decode(
                token,
                self.config.SECRET_KEY,
                algorithms=[self.config.ALGORITHM]
            )
            return TokenData(**payload)
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
            
    async def get_current_user(
        self,
        token: str = Security(OAuth2PasswordBearer(tokenUrl="token"))
    ) -> User:
        """Get current user from token"""
        token_data = await self.verify_token(token)
        user_data = await self.redis_client.hgetall(f"user:{token_data.username}")
        if not user_data:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )
        return User(**user_data)
        
    def require_permission(self, permission: str):
        """Decorator to require specific permission"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                user = await self.get_current_user(kwargs.get("token"))
                if permission not in user.permissions:
                    raise HTTPException(
                        status_code=403,
                        detail="Permission denied"
                    )
                return await func(*args, **kwargs)
            return wrapper
        return decorator
        
    def require_role(self, role: str):
        """Decorator to require specific role"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                user = await self.get_current_user(kwargs.get("token"))
                if role not in user.roles:
                    raise HTTPException(
                        status_code=403,
                        detail="Role required"
                    )
                return await func(*args, **kwargs)
            return wrapper
        return decorator
        
    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: str,
        roles: List[str] = [],
        permissions: List[str] = []
    ) -> User:
        """Create new user"""
        try:
            # Hash password
            password_hash = bcrypt.hashpw(
                password.encode(),
                bcrypt.gensalt()
            ).decode()
            
            # Create user
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                roles=roles,
                permissions=permissions
            )
            
            # Store in Redis
            await self.redis_client.hset(
                f"user:{username}",
                mapping={
                    **user.dict(),
                    "password_hash": password_hash
                }
            )
            
            return user
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise HTTPException(
                status_code=500,
                detail="Error creating user"
            )
            
    async def update_user(
        self,
        username: str,
        **kwargs
    ) -> User:
        """Update user"""
        try:
            # Get existing user
            user_data = await self.redis_client.hgetall(f"user:{username}")
            if not user_data:
                raise HTTPException(
                    status_code=404,
                    detail="User not found"
                )
                
            # Update user data
            user = User(**user_data)
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
                    
            # Store updated user
            await self.redis_client.hset(
                f"user:{username}",
                mapping=user.dict()
            )
            
            return user
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            raise HTTPException(
                status_code=500,
                detail="Error updating user"
            )
            
    async def delete_user(self, username: str) -> None:
        """Delete user"""
        try:
            # Check if user exists
            if not await self.redis_client.exists(f"user:{username}"):
                raise HTTPException(
                    status_code=404,
                    detail="User not found"
                )
                
            # Delete user
            await self.redis_client.delete(f"user:{username}")
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            raise HTTPException(
                status_code=500,
                detail="Error deleting user"
            )
            
    async def verify_webhook_signature(
        self,
        data: Dict[str, Any],
        signature: str
    ) -> bool:
        """Verify webhook signature"""
        try:
            # Get webhook secret
            webhook_secret = await self.redis_client.get("webhook:secret")
            if not webhook_secret:
                return False
                
            # Verify signature
            expected = jwt.encode(
                data,
                webhook_secret,
                algorithm=self.config.ALGORITHM
            )
            return signature == expected
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False 