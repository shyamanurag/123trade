"""
Production-grade JWT authentication handler for the crypto trading system
"""

import os
import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-this-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

class TokenData(BaseModel):
    """Token data model"""
    user_id: str
    username: str
    email: Optional[str] = None
    role: str = "user"
    permissions: list = []

class JWTHandler:
    """JWT token handler with comprehensive security features"""
    
    def __init__(self):
        self.secret_key = JWT_SECRET
        self.algorithm = JWT_ALGORITHM
        self.expiration_hours = JWT_EXPIRATION_HOURS
        
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)
        
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
        
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=self.expiration_hours)
            
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            logger.info(f"Created access token for user: {data.get('username', 'unknown')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating access token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create access token"
            )
            
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create a JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=7)  # Refresh tokens last 7 days
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            logger.info(f"Created refresh token for user: {data.get('username', 'unknown')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating refresh token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create refresh token"
            )
            
    def verify_token(self, token: str) -> TokenData:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            token_type = payload.get("type")
            if token_type != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
                
            # Extract user data
            user_id = payload.get("user_id")
            username = payload.get("username")
            
            if not user_id or not username:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
                
            return TokenData(
                user_id=user_id,
                username=username,
                email=payload.get("email"),
                role=payload.get("role", "user"),
                permissions=payload.get("permissions", [])
            )
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError as e:
            logger.error(f"JWT validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        except Exception as e:
            logger.error(f"Unexpected error in token verification: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token verification failed"
            )
            
    def verify_refresh_token(self, token: str) -> TokenData:
        """Verify and decode a refresh token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            token_type = payload.get("type")
            if token_type != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
                
            # Extract user data
            user_id = payload.get("user_id")
            username = payload.get("username")
            
            if not user_id or not username:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token payload"
                )
                
            return TokenData(
                user_id=user_id,
                username=username,
                email=payload.get("email"),
                role=payload.get("role", "user"),
                permissions=payload.get("permissions", [])
            )
            
        except jwt.ExpiredSignatureError:
            logger.warning("Refresh token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )
        except jwt.JWTError as e:
            logger.error(f"Refresh token validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate refresh token"
            )
            
    def get_token_payload(self, token: str) -> Dict[str, Any]:
        """Get token payload without verification (for debugging)"""
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception as e:
            logger.error(f"Error decoding token payload: {e}")
            return {}

# Global JWT handler instance
jwt_handler = JWTHandler()

# Convenience functions
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create access token"""
    return jwt_handler.create_access_token(data, expires_delta)

def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create refresh token"""
    return jwt_handler.create_refresh_token(data)

def verify_token(token: str) -> TokenData:
    """Verify token"""
    return jwt_handler.verify_token(token)

def verify_refresh_token(token: str) -> TokenData:
    """Verify refresh token"""
    return jwt_handler.verify_refresh_token(token)

def hash_password(password: str) -> str:
    """Hash password"""
    return jwt_handler.hash_password(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    return jwt_handler.verify_password(plain_password, hashed_password)
