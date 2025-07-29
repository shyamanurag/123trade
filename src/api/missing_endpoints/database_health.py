from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from src.config.database import get_database_session
import asyncio

router = APIRouter()

@router.get("/api/system/database-health")
async def get_database_health():
    """Check database health and connection"""
    try:
        async with get_database_session() as session:
            # Test basic query
            result = await session.execute(text("SELECT 1"))
            row = result.fetchone()
            
            # Test users table access
            users_result = await session.execute(text("SELECT COUNT(*) FROM users"))
            user_count = users_result.scalar()
            
            return {
                "success": True,
                "status": "healthy",
                "connection": "active",
                "user_count": user_count,
                "test_query": row[0] if row else None
            }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database health check failed: {str(e)}"
        )
