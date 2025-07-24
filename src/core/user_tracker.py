"""
User Tracker for Trading System
Tracks user activity, sessions, and performance
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class UserSession(BaseModel):
    """User session model"""
    session_id: str
    user_id: str
    started_at: datetime
    last_activity: datetime
    is_active: bool = True
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class UserActivity(BaseModel):
    """User activity model"""
    user_id: str
    activity_type: str
    timestamp: datetime
    details: Dict[str, Any] = {}

class UserTracker:
    """Tracks user sessions and activity"""
    
    def __init__(self):
        self.active_sessions: Dict[str, UserSession] = {}
        self.user_activities: List[UserActivity] = []
        
    async def create_session(self, user_id: str, ip_address: str = None, user_agent: str = None) -> str:
        """Create a new user session"""
        session_id = f"session_{user_id}_{int(datetime.utcnow().timestamp())}"
        
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            started_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.active_sessions[session_id] = session
        await self.log_activity(user_id, "session_created", {"session_id": session_id})
        
        return session_id
    
    async def update_activity(self, session_id: str) -> bool:
        """Update session activity"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id].last_activity = datetime.utcnow()
            return True
        return False
    
    async def end_session(self, session_id: str) -> bool:
        """End a user session"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.is_active = False
            await self.log_activity(session.user_id, "session_ended", {"session_id": session_id})
            del self.active_sessions[session_id]
            return True
        return False
    
    async def log_activity(self, user_id: str, activity_type: str, details: Dict[str, Any] = None):
        """Log user activity"""
        activity = UserActivity(
            user_id=user_id,
            activity_type=activity_type,
            timestamp=datetime.utcnow(),
            details=details or {}
        )
        
        self.user_activities.append(activity)
        
        # Keep only last 1000 activities
        if len(self.user_activities) > 1000:
            self.user_activities = self.user_activities[-1000:]
    
    async def get_active_sessions(self) -> List[UserSession]:
        """Get all active sessions"""
        return list(self.active_sessions.values())
    
    async def get_user_activities(self, user_id: str, limit: int = 100) -> List[UserActivity]:
        """Get user activities"""
        user_activities = [a for a in self.user_activities if a.user_id == user_id]
        return user_activities[-limit:]
    
    async def cleanup_expired_sessions(self, expiry_hours: int = 24):
        """Clean up expired sessions"""
        cutoff_time = datetime.utcnow() - timedelta(hours=expiry_hours)
        expired_sessions = [
            session_id for session_id, session in self.active_sessions.items()
            if session.last_activity < cutoff_time
        ]
        
        for session_id in expired_sessions:
            await self.end_session(session_id)
            
        return len(expired_sessions)

# Global user tracker instance
user_tracker = UserTracker()

# API Router
router = APIRouter(prefix="/api/v1/users", tags=["user-tracking"])

@router.get("/sessions")
async def get_active_sessions():
    """Get all active user sessions"""
    try:
        sessions = await user_tracker.get_active_sessions()
        return {
            "status": "success",
            "data": {
                "active_sessions": len(sessions),
                "sessions": [s.dict() for s in sessions]
            }
        }
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sessions")

@router.get("/{user_id}/activities")
async def get_user_activities(user_id: str, limit: int = 50):
    """Get user activities"""
    try:
        activities = await user_tracker.get_user_activities(user_id, limit)
        return {
            "status": "success",
            "data": {
                "user_id": user_id,
                "activities": [a.dict() for a in activities]
            }
        }
    except Exception as e:
        logger.error(f"Error getting user activities: {e}")
        raise HTTPException(status_code=500, detail="Failed to get activities")

@router.post("/cleanup")
async def cleanup_sessions():
    """Clean up expired sessions"""
    try:
        cleaned = await user_tracker.cleanup_expired_sessions()
        return {
            "status": "success",
            "data": {
                "cleaned_sessions": cleaned
            }
        }
    except Exception as e:
        logger.error(f"Error cleaning sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup sessions") 