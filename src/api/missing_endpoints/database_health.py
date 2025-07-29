from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from src.core.database import get_database_session
import asyncio

router = APIRouter()

@router.get("/api/system/database-health")
async def get_database_health():
    """Check database health and connection"""
    try:
        # Get database session from the correct module
        session = get_database_session()
        
        # Test basic query
        result = session.execute(text("SELECT 1"))
        row = result.fetchone()
        
        # Test users table access
        users_result = session.execute(text("SELECT COUNT(*) FROM users"))
        user_count = users_result.scalar()
        
        session.close()
        
        return {
            "success": True,
            "status": "healthy",
            "connection": "active",
            "user_count": user_count,
            "test_query": row[0] if row else None
        }
    except Exception as e:
        return {
            "success": False,
            "status": "unhealthy", 
            "connection": "failed",
            "error": str(e),
            "message": "Database health check failed"
        }
