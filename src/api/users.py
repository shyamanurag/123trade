"""
Users API - Compatible with frontend expectations
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["users"])

# Mock users that match frontend expectations
USERS_DATABASE = [
    {
        "id": "user_001",
        "username": "demo_user",
        "email": "demo@trade123.com",
        "sharekhan_user_id": "SK001",
        "status": "active",
        "role": "trader",
        "created_at": datetime.now().isoformat(),
        "is_active": True
    },
    {
        "id": "admin_001", 
        "username": "admin_user",
        "email": "admin@trade123.com",
        "sharekhan_user_id": "SK002",
        "status": "active",
        "role": "admin",
        "created_at": datetime.now().isoformat(),
        "is_active": True
    },
    {
        "id": "trader_001",
        "username": "pro_trader",
        "email": "trader@trade123.com", 
        "sharekhan_user_id": "SK003",
        "status": "active",
        "role": "trader",
        "created_at": datetime.now().isoformat(),
        "is_active": True
    }
]

@router.get("/users", summary="Get all users")
async def get_users():
    """Get all users - compatible with frontend expectations"""
    try:
        return {
            "success": True,
            "data": USERS_DATABASE,
            "message": "Users retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(status_code=500, detail="Failed to get users")

@router.get("/users/{user_id}", summary="Get specific user")
async def get_user(user_id: str):
    """Get specific user by ID"""
    try:
        user = next((u for u in USERS_DATABASE if u["id"] == user_id), None)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "success": True,
            "data": user,
            "message": "User retrieved successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user") 