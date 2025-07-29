"""
Authentication API for React Frontend
Provides login, logout, and token management
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import jwt
import logging

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = "your-super-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

# Pydantic Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    email: str
    role: str
    name: str

class UserInfo(BaseModel):
    user_id: str
    email: str
    name: str
    role: str

# Mock user database
MOCK_USERS = {
    "demo@trade123.com": {
        "user_id": "user_001",
        "email": "demo@trade123.com",
        "password": "demo123",  # In production, use hashed passwords
        "name": "Demo User",
        "role": "trader"
    },
    "admin@trade123.com": {
        "user_id": "admin_001",
        "email": "admin@trade123.com", 
        "password": "admin123",
        "name": "Admin User",
        "role": "admin"
    },
    "trader@trade123.com": {
        "user_id": "trader_001",
        "email": "trader@trade123.com",
        "password": "trader123", 
        "name": "Pro Trader",
        "role": "trader"
    }
}

def create_access_token(data: Dict[str, Any]) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Verify JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

async def get_current_user(token_data: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
    """Get current authenticated user"""
    user_id = token_data.get("sub")
    email = token_data.get("email")
    
    # Find user in mock database
    user = None
    for user_email, user_data in MOCK_USERS.items():
        if user_data["email"] == email:
            user = user_data
            break
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user

@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """Authenticate user and return access token"""
    try:
        # Find user by email
        user = MOCK_USERS.get(login_data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password (in production, use proper password hashing)
        if user["password"] != login_data.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Create access token
        access_token = create_access_token({
            "sub": user["user_id"],
            "email": user["email"],
            "role": user["role"],
            "name": user["name"]
        })
        
        logger.info(f"User {login_data.email} logged in successfully")
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user["user_id"],
            email=user["email"],
            role=user["role"],
            name=user["name"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/logout")
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Logout current user"""
    try:
        logger.info(f"User {current_user['email']} logged out")
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.post("/validate")
async def validate_token(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Validate current token"""
    return {
        "valid": True,
        "user": current_user,
        "message": "Token is valid"
    }

@router.post("/refresh")
async def refresh_token(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Refresh access token"""
    try:
        # Create new access token
        new_token = create_access_token({
            "sub": current_user["user_id"],
            "email": current_user["email"],
            "role": current_user["role"],
            "name": current_user["name"]
        })
        
        return {
            "access_token": new_token,
            "token_type": "bearer",
            "message": "Token refreshed successfully"
        }
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.get("/me")
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)) -> UserInfo:
    """Get current user information"""
    return UserInfo(
        user_id=current_user["user_id"],
        email=current_user["email"],
        name=current_user["name"],
        role=current_user["role"]
    ) 