import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
import hashlib

router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)
logger = logging.getLogger(__name__)

def get_database_operations():
    # This is a temporary measure to avoid circular imports.
    # In a real application, this should be moved to a shared database module.
    return None

@router.get("/", summary="Get all users")
async def get_users():
    """Fetch all registered trading users with their basic information"""
    db_ops = get_database_operations()
    if not db_ops:
        return {
            "success": False, 
            "users": [], 
            "total_users": 0,
            "timestamp": datetime.now().isoformat(), 
            "error": "SAFETY: User database disabled - real database required",
            "message": "Mock user data eliminated for safety"
        }
    
    try:
        # ELIMINATED: Mock user response that could mislead about real users
        # ❌ return {"success": True, "users": [], "total_users": 0, "timestamp": datetime.now().isoformat(), "message": "DB query disabled."}
        
        # SAFETY: Return proper error instead of fake success
        logger.error("SAFETY: Mock user data ELIMINATED to prevent fake user information")
        return {
            "success": False, 
            "users": [], 
            "total_users": 0,
            "timestamp": datetime.now().isoformat(),
            "error": "SAFETY: Mock user data disabled - real user database required"
        }
    
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return {"success": False, "users": [], "message": "Unable to fetch users"}

@router.post("/", summary="Add new user")
async def add_user(user_data: dict):
    """Onboard a new user to the trading system"""
    db_ops = get_database_operations()
    if not db_ops:
        raise HTTPException(status_code=503, detail="Database service disabled. Cannot add user.")
    
    try:
        required_fields = ['username', 'email', 'password', 'full_name']
        if not all(field in user_data and user_data[field] for field in required_fields):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # ELIMINATED: Mock user creation that could mislead about real user creation
        # ❌ user_id = f"user_{user_data['username']}_{datetime.now().strftime('%Y%m%d')}"
        # ❌ return {"success": True, "message": f"User {user_data['username']} created successfully", "user_id": user_id}
        
        # SAFETY: Return proper error instead of fake user creation
        logger.error("SAFETY: Mock user creation ELIMINATED to prevent fake user accounts")
        raise HTTPException(status_code=503, detail="SAFETY: Mock user creation disabled - real user database required")
        
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{user_id}", summary="Remove user")
async def remove_user(user_id: str):
    """Remove a user from the trading system"""
    db_ops = get_database_operations()
    if not db_ops:
        return {"success": False, "message": "SAFETY: User removal disabled - real database required"}
        
    try:
        # ELIMINATED: Mock user removal that could mislead about real user operations
        # ❌ logger.info(f"User deactivated: {user_id}")
        # ❌ return {"success": True, "message": "User removed successfully"}
        
        # SAFETY: Return proper error instead of fake user removal
        logger.error("SAFETY: Mock user removal ELIMINATED to prevent fake user operations")
        return {"success": False, "message": "SAFETY: Mock user removal disabled - real user database required"}
    except Exception as e:
        logger.error(f"Error removing user: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove user")

@router.get("/current", summary="Get current user")
async def get_current_user():
    """Get current user information - SAFETY PROTECTED"""
    try:
        # ELIMINATED: Mock current user that could mislead about authentication
        # ❌ return {
        # ❌     "status": "success",
        # ❌     "data": {"username": "admin", "full_name": "Administrator", "email": "admin@trading-system.com", "is_admin": True, "last_login": datetime.now().isoformat(), "permissions": ["read", "write", "admin"]}
        # ❌ }
        
        # SAFETY: Return proper error instead of fake admin user
        logger.error("SAFETY: Mock current user ELIMINATED to prevent fake authentication")
        return {
            "status": "error",
            "error": "SAFETY: Mock current user disabled - real authentication required",
            "message": "Mock admin user eliminated for safety"
        }
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(status_code=500, detail="Failed to get current user") 