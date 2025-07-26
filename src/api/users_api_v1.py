"""
Users API v1 Endpoints for React Frontend
Handles user management, creation, and directory operations
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, EmailStr
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from .auth_api import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/users", tags=["users-v1"])

# Pydantic Models
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    role: str = "trader"
    trading_limit: float = 50000.0
    is_active: bool = True

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    trading_limit: Optional[float] = None
    is_active: Optional[bool] = None

# Mock users database
MOCK_USERS_DB = {
    "user_001": {
        "id": "user_001",
        "name": "Demo User",
        "email": "demo@trade123.com",
        "role": "trader",
        "trading_limit": 100000.0,
        "is_active": True,
        "created_at": "2025-01-01T00:00:00Z",
        "last_login": datetime.now().isoformat(),
        "total_trades": 25,
        "total_pnl": 15000.0
    },
    "admin_001": {
        "id": "admin_001", 
        "name": "Admin User",
        "email": "admin@trade123.com",
        "role": "admin",
        "trading_limit": 500000.0,
        "is_active": True,
        "created_at": "2025-01-01T00:00:00Z",
        "last_login": (datetime.now() - timedelta(hours=2)).isoformat(),
        "total_trades": 50,
        "total_pnl": 35000.0
    },
    "user_002": {
        "id": "user_002",
        "name": "Jane Smith",
        "email": "jane@trade123.com", 
        "role": "trader",
        "trading_limit": 75000.0,
        "is_active": False,
        "created_at": "2025-01-15T10:30:00Z",
        "last_login": None,
        "total_trades": 0,
        "total_pnl": 0.0
    }
}

@router.get("/")
async def get_users(
    active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get list of users with filtering and pagination"""
    try:
        # Check permissions (admin or getting own data)
        if current_user.get("role") != "admin":
            # Non-admin users can only see themselves
            user_id = current_user["user_id"]
            if user_id in MOCK_USERS_DB:
                return {
                    "success": True,
                    "data": [MOCK_USERS_DB[user_id]],
                    "total": 1,
                    "limit": limit,
                    "offset": offset
                }
            else:
                return {
                    "success": True,
                    "data": [],
                    "total": 0,
                    "limit": limit,
                    "offset": offset
                }
        
        # Admin can see all users
        all_users = list(MOCK_USERS_DB.values())
        
        # Apply filters
        if active is not None:
            all_users = [user for user in all_users if user["is_active"] == active]
        
        # Apply pagination
        total = len(all_users)
        paginated_users = all_users[offset:offset + limit]
        
        logger.info(f"Users list requested by {current_user['email']}, returned {len(paginated_users)} users")
        
        return {
            "success": True,
            "data": paginated_users,
            "total": total,
            "limit": limit,
            "offset": offset,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get users error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch users"
        )

@router.post("/")
async def create_user(
    user_data: UserCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new user (admin only)"""
    try:
        # Check admin permissions
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=403,
                detail="Admin access required to create users"
            )
        
        # Check if email already exists
        for existing_user in MOCK_USERS_DB.values():
            if existing_user["email"] == user_data.email:
                raise HTTPException(
                    status_code=400,
                    detail="Email already exists"
                )
        
        # Generate new user ID
        import uuid
        user_id = f"user_{str(uuid.uuid4())[:8]}"
        
        # Create user record
        new_user = {
            "id": user_id,
            "name": user_data.name,
            "email": user_data.email,
            "role": user_data.role,
            "trading_limit": user_data.trading_limit,
            "is_active": user_data.is_active,
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "total_trades": 0,
            "total_pnl": 0.0
        }
        
        # Store user
        MOCK_USERS_DB[user_id] = new_user
        
        logger.info(f"New user created: {user_data.email} by {current_user['email']}")
        
        return {
            "success": True,
            "user": new_user,
            "message": "User created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create user error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create user"
        )

@router.get("/{user_id}")
async def get_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get specific user details"""
    try:
        # Check permissions (admin or own data)
        if (current_user.get("role") != "admin" and 
            current_user["user_id"] != user_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )
        
        # Find user
        user = MOCK_USERS_DB.get(user_id)
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        return {
            "success": True,
            "user": user,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch user"
        )

@router.put("/{user_id}")
async def update_user(
    user_id: str,
    user_updates: UserUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user details (admin only)"""
    try:
        # Check admin permissions
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=403,
                detail="Admin access required to update users"
            )
        
        # Find user
        user = MOCK_USERS_DB.get(user_id)
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Update user fields
        update_data = user_updates.dict(exclude_unset=True)
        user.update(update_data)
        user["updated_at"] = datetime.now().isoformat()
        
        logger.info(f"User {user_id} updated by {current_user['email']}")
        
        return {
            "success": True,
            "user": user,
            "message": "User updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update user"
        )

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete user (admin only)"""
    try:
        # Check admin permissions
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=403,
                detail="Admin access required to delete users"
            )
        
        # Prevent self-deletion
        if current_user["user_id"] == user_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete your own account"
            )
        
        # Find user
        if user_id not in MOCK_USERS_DB:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Delete user
        deleted_user = MOCK_USERS_DB.pop(user_id)
        
        logger.info(f"User {user_id} deleted by {current_user['email']}")
        
        return {
            "success": True,
            "message": f"User {deleted_user['name']} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete user"
        ) 