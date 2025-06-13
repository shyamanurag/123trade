"""
Authentication API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
import hashlib
from typing import Optional
import os
import logging

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-here")  # Use env variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Default admin user (for initial setup)
DEFAULT_USERS = {
    "admin": {
        "username": "admin",
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "full_name": "Admin User",
        "email": "admin@algoauto.com",
        "is_active": True,
        "is_admin": True
    }
}

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_info: dict

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

@router.post("/login")
async def login(request: Request, login_data: LoginRequest):
    """Login endpoint"""
    logger.info(f"Login attempt for user: {login_data.username}")
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Request origin: {request.headers.get('origin', 'unknown')}")
    
    # Check if user exists
    user = DEFAULT_USERS.get(login_data.username)
    
    if not user:
        logger.warning(f"User not found: {login_data.username}")
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )
    
    # Verify password
    if not verify_password(login_data.password, user["password_hash"]):
        logger.warning(f"Invalid password for user: {login_data.username}")
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )
    
    # Check if user is active
    if not user.get("is_active", True):
        logger.warning(f"User is inactive: {login_data.username}")
        raise HTTPException(
            status_code=403,
            detail="User account is disabled"
        )
    
    logger.info(f"Login successful for user: {login_data.username}")
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "is_admin": user.get("is_admin", False)},
        expires_delta=access_token_expires
    )
    
    # Return token and user info
    response = {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "username": user["username"],
            "email": user["email"],
            "role": "admin" if user.get("is_admin", False) else "trader",
            "capital": 100000,  # Default capital
            "permissions": ["trade", "view_analytics"] if user.get("is_admin", False) else ["trade"]
        },
        "user_info": {
            "username": user["username"],
            "full_name": user["full_name"],
            "email": user["email"],
            "is_admin": user.get("is_admin", False)
        }
    }
    
    logger.info(f"Returning login response for user: {login_data.username}")
    return response

@router.get("/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user info"""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = DEFAULT_USERS.get(username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "username": user["username"],
            "full_name": user["full_name"],
            "email": user["email"],
            "is_admin": user.get("is_admin", False)
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/logout")
async def logout():
    """Logout endpoint (client should remove token)"""
    return {"message": "Logged out successfully"}

@router.get("/test")
async def test_auth():
    """Test endpoint to verify auth router is working"""
    return {
        "message": "Auth router is working!", 
        "endpoint": "/api/v1/auth/test",
        "default_users": list(DEFAULT_USERS.keys()),
        "admin_password_hint": "admin123"
    }

@router.get("/debug")
async def debug_auth():
    """Debug endpoint to check auth configuration"""
    admin_user = DEFAULT_USERS.get("admin", {})
    expected_hash = hashlib.sha256("admin123".encode()).hexdigest()
    
    return {
        "auth_configured": True,
        "admin_user_exists": "admin" in DEFAULT_USERS,
        "admin_password_hash_matches": admin_user.get("password_hash") == expected_hash,
        "expected_hash": expected_hash,
        "actual_hash": admin_user.get("password_hash", "NOT_SET"),
        "jwt_secret_configured": bool(SECRET_KEY),
        "cors_note": "Make sure CORS is properly configured in main.py"
    } 