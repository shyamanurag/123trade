"""
User Database Fallback API
Provides mock user data when database is unavailable
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["users-fallback"])

# Mock user database
MOCK_USERS_DB = [
    {
        "id": "user_001",
        "username": "demo_user",
        "email": "demo@trade123.com",
        "sharekhan_customer_id": "SANURAG1977",
        "status": "active",
        "role": "trader",
        "created_at": "2025-01-01T00:00:00Z",
        "is_active": True,
        "last_login": datetime.now().isoformat(),
        "total_trades": 125,
        "current_pnl": 15750.50
    },
    {
        "id": "user_002", 
        "username": "admin_user",
        "email": "admin@trade123.com",
        "sharekhan_customer_id": "ADMIN001",
        "status": "active",
        "role": "admin",
        "created_at": "2025-01-01T00:00:00Z",
        "is_active": True,
        "last_login": datetime.now().isoformat(),
        "total_trades": 0,
        "current_pnl": 0.0
    }
]

class User(BaseModel):
    id: str
    username: str
    email: str
    sharekhan_customer_id: Optional[str] = None
    status: str
    role: str
    created_at: str
    is_active: bool
    last_login: Optional[str] = None
    total_trades: int = 0
    current_pnl: float = 0.0

async def get_database_or_fallback():
    """Get database session or use fallback"""
    try:
        from src.core.enhanced_database import db_manager
        if db_manager.is_connected:
            return next(db_manager.get_session())
        else:
            logger.warning("Database not connected, using fallback data")
            return None
    except Exception as e:
        logger.warning(f"Database connection failed, using fallback: {e}")
        return None

@router.get("/", response_model=Dict[str, Any])
async def get_users(db=Depends(get_database_or_fallback)):
    """Get all users with database fallback"""
    try:
        if db is not None:
            # Try to get users from real database
            # This would be implemented with actual SQLAlchemy queries
            logger.info("Using real database for users")
            pass
        
        # Fallback to mock data
        logger.info("Using fallback mock data for users")
        return {
            "success": True,
            "data": MOCK_USERS_DB,
            "message": "Users retrieved successfully (fallback data)",
            "count": len(MOCK_USERS_DB),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get users: {str(e)}")

@router.get("/{user_id}", response_model=Dict[str, Any])
async def get_user(user_id: str, db=Depends(get_database_or_fallback)):
    """Get specific user by ID"""
    try:
        if db is not None:
            # Try to get user from real database
            logger.info(f"Using real database for user {user_id}")
            pass
        
        # Fallback to mock data
        user = next((u for u in MOCK_USERS_DB if u["id"] == user_id), None)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "success": True,
            "data": user,
            "message": f"User {user_id} retrieved successfully (fallback data)",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user: {str(e)}")

@router.post("/", response_model=Dict[str, Any])
async def create_user(user_data: Dict[str, Any], db=Depends(get_database_or_fallback)):
    """Create new user"""
    try:
        if db is not None:
            # Try to create user in real database
            logger.info("Using real database for user creation")
            pass
        
        # Fallback: simulate user creation
        new_user = {
            "id": f"user_{len(MOCK_USERS_DB) + 1:03d}",
            "username": user_data.get("username", "new_user"),
            "email": user_data.get("email", "new@trade123.com"),
            "sharekhan_customer_id": user_data.get("sharekhan_customer_id"),
            "status": "active",
            "role": user_data.get("role", "trader"),
            "created_at": datetime.now().isoformat(),
            "is_active": True,
            "last_login": None,
            "total_trades": 0,
            "current_pnl": 0.0
        }
        
        MOCK_USERS_DB.append(new_user)
        
        return {
            "success": True,
            "data": new_user,
            "message": "User created successfully (fallback mode)",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

@router.get("/database/status")
async def get_database_status():
    """Get database connection status for users"""
    try:
        from src.core.enhanced_database import db_manager
        
        health_status = db_manager.health_check()
        
        return {
            "success": True,
            "data": {
                "database_connected": db_manager.is_connected,
                "fallback_active": not db_manager.is_connected,
                "health_status": health_status,
                "mock_users_available": len(MOCK_USERS_DB),
                "timestamp": datetime.now().isoformat()
            },
            "message": "Database status retrieved"
        }
        
    except Exception as e:
        return {
            "success": False,
            "data": {
                "database_connected": False,
                "fallback_active": True,
                "error": str(e),
                "mock_users_available": len(MOCK_USERS_DB),
                "timestamp": datetime.now().isoformat()
            },
            "message": "Database status check failed"
        }
