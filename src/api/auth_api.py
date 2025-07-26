"""
Authentication API Endpoints for React Frontend
Handles user login, logout, token validation and refresh
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
import bcrypt
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

security = HTTPBearer()

# Pydantic Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    user: Dict[str, Any]
    token: str
    expires_at: str

class TokenValidationRequest(BaseModel):
    token: str

class TokenRefreshRequest(BaseModel):
    token: str

# Mock user database (replace with real database in production)
MOCK_USERS = {
    "demo@trade123.com": {
        "id": "user_001",
        "name": "Demo User",
        "email": "demo@trade123.com",
        "password_hash": bcrypt.hashpw("demo123".encode('utf-8'), bcrypt.gensalt()),
        "role": "trader",
        "is_active": True,
        "created_at": "2025-01-01T00:00:00Z"
    },
    "admin@trade123.com": {
        "id": "admin_001", 
        "name": "Admin User",
        "email": "admin@trade123.com",
        "password_hash": bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()),
        "role": "admin",
        "is_active": True,
        "created_at": "2025-01-01T00:00:00Z"
    }
}

def create_jwt_token(user_data: Dict[str, Any]) -> tuple[str, str]:
    """Create JWT token with expiration"""
    expires_at = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "user_id": user_data["id"],
        "email": user_data["email"],
        "role": user_data["role"],
        "exp": expires_at,
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token, expires_at.isoformat()

def validate_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate JWT token and return user data"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    payload = validate_jwt_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return payload

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """User login endpoint"""
    try:
        # Find user
        user = MOCK_USERS.get(request.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not bcrypt.checkpw(request.password.encode('utf-8'), user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled"
            )
        
        # Create JWT token
        token, expires_at = create_jwt_token(user)
        
        # Return user data (without password hash)
        user_response = {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "is_active": user["is_active"],
            "created_at": user["created_at"]
        }
        
        logger.info(f"User {request.email} logged in successfully")
        
        return LoginResponse(
            user=user_response,
            token=token,
            expires_at=expires_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/logout")
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    """User logout endpoint"""
    try:
        logger.info(f"User {current_user['email']} logged out")
        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/validate")
async def validate_token(request: TokenValidationRequest):
    """Validate JWT token"""
    try:
        payload = validate_jwt_token(request.token)
        return {"valid": payload is not None}
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return {"valid": False}

@router.post("/refresh")
async def refresh_token(request: TokenRefreshRequest):
    """Refresh JWT token"""
    try:
        # Validate current token
        payload = validate_jwt_token(request.token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Find user
        user = MOCK_USERS.get(payload["email"])
        if not user or not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new token
        new_token, expires_at = create_jwt_token(user)
        
        return {
            "token": new_token,
            "expires_at": expires_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/me")
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user information"""
    try:
        # Find full user data
        user = MOCK_USERS.get(current_user["email"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "is_active": user["is_active"],
            "created_at": user["created_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user info error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) 