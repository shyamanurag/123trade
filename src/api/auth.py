"""
Secure Authentication API endpoints
Production-ready authentication with no default credentials
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import logging
import sys
import os
import jwt
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from security.secure_auth_manager import (
        SecureAuthManager,
        create_secure_auth_manager,
        LoginRequest,
        LoginResponse,
        UserCreate,
        User,
        UserRole
    )
    import redis.asyncio as redis
    SECURE_AUTH_AVAILABLE = True
except ImportError as e:
    SECURE_AUTH_AVAILABLE = False
    logging.warning(f"Secure auth manager not available: {e}")

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()
logger = logging.getLogger(__name__)

# Global auth manager instance
auth_manager: Optional[SecureAuthManager] = None

async def get_auth_manager() -> SecureAuthManager:
    """Get or create auth manager instance"""
    global auth_manager
    
    if not auth_manager and SECURE_AUTH_AVAILABLE:
        try:
            # Connect to Redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            redis_client = redis.from_url(redis_url, decode_responses=True)
            
            # Create auth manager
            auth_manager = create_secure_auth_manager(redis_client)
            
            # Initialize system (only creates admin if password provided)
            initial_admin_password = os.getenv("INITIAL_ADMIN_PASSWORD")
            await auth_manager.initialize_system(initial_admin_password)
            
            logger.info("✅ Secure authentication manager initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize auth manager: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication system unavailable"
            )
    
    if not auth_manager:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication system not available"
        )
    
    return auth_manager

class SystemInitRequest(BaseModel):
    """System initialization request"""
    admin_username: str
    admin_email: str
    admin_password: str
    admin_full_name: str

@router.post("/system/init", response_model=Dict[str, str])
async def initialize_system(
    init_data: SystemInitRequest,
    auth_mgr: SecureAuthManager = Depends(get_auth_manager)
):
    """
    Initialize the system with the first admin user
    This endpoint is only available when no users exist
    """
    try:
        # Check if any users already exist
        redis_client = auth_mgr.redis_client
        pattern = "user:*"
        existing_users = []
        async for key in redis_client.scan_iter(match=pattern):
            existing_users.append(key)
        
        if existing_users:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="System already initialized. Users already exist."
            )
        
        # Create first admin user
        admin_user_data = UserCreate(
            username=init_data.admin_username,
            email=init_data.admin_email,
            password=init_data.admin_password,
            full_name=init_data.admin_full_name,
            role=UserRole.ADMIN
        )
        
        user = await auth_mgr.create_user(admin_user_data, "system_initialization")
        
        logger.info(f"✅ System initialized with admin user: {user.username}")
        
        return {
            "message": "System initialized successfully",
            "admin_user": user.username,
            "next_step": "Login with your admin credentials"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"System initialization error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System initialization failed"
        )

@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    auth_mgr: SecureAuthManager = Depends(get_auth_manager)
):
    """
    Authenticate user and return JWT token
    PRODUCTION ONLY - No mock tokens allowed
    """
    try:
        # Authenticate user with real credentials only
        user = await auth_mgr.authenticate_user(
            credentials.username,
            credentials.password
        )
        
        if not user:
            logger.warning(f"Failed login attempt for user: {credentials.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Generate real JWT token
        access_token = await auth_mgr.create_access_token(user.user_id)
        
        logger.info(f"✅ User authenticated successfully: {user.username}")
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.user_id,
            username=user.username,
            role=user.role.value,
            message="Authentication successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )

async def get_current_user(auth_mgr: SecureAuthManager = Depends(get_auth_manager)) -> User:
    """Dependency to get current user"""
    return await auth_mgr.get_current_user()

@router.post("/users", response_model=Dict[str, Any])
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    auth_mgr: SecureAuthManager = Depends(get_auth_manager)
):
    """
    Create a new user (admin only)
    """
    # Check if current user is admin
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create users"
        )
    
    try:
        user = await auth_mgr.create_user(user_data, current_user.username)
        return {
            "message": "User created successfully",
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "created_at": user.created_at.isoformat()
            }
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"User creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User creation failed"
        )

@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "permissions": current_user.permissions,
        "is_active": current_user.is_active,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        "created_at": current_user.created_at.isoformat()
    }

@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_token(
    refresh_token: str,
    auth_mgr: SecureAuthManager = Depends(get_auth_manager)
):
    """Refresh access token using refresh token"""
    try:
        # Verify refresh token
        payload = jwt.decode(
            refresh_token,
            auth_mgr.config.jwt_secret,
            algorithms=[auth_mgr.config.jwt_algorithm]
        )
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Get user
        user = await auth_mgr.get_user_by_username(payload["username"])
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new access token
        new_access_token = auth_mgr.create_access_token(user)
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": auth_mgr.config.access_token_expire_minutes * 60
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """Logout user (token invalidation would be handled by client)"""
    logger.info(f"User logged out: {current_user.username}")
    return {"message": "Logged out successfully"}

@router.get("/system/status")
async def auth_system_status():
    """Get authentication system status"""
    try:
        auth_mgr = await get_auth_manager()
        
        # Check Redis connection
        redis_connected = True
        try:
            await auth_mgr.redis_client.ping()
        except:
            redis_connected = False
        
        # Count users (basic check)
        user_count = 0
        try:
            async for key in auth_mgr.redis_client.scan_iter(match="user:*"):
                user_count += 1
        except:
            pass
        
        return {
            "status": "healthy" if redis_connected else "degraded",
            "redis_connected": redis_connected,
            "secure_auth_available": SECURE_AUTH_AVAILABLE,
            "user_count": user_count,
            "requires_initialization": user_count == 0,
            "security_features": [
                "Strong password requirements",
                "Account lockout protection",
                "JWT token authentication",
                "Role-based access control",
                "No default credentials"
            ]
        }
    except Exception as e:
        logger.error(f"Auth status check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "secure_auth_available": SECURE_AUTH_AVAILABLE
        } 