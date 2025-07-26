"""
Multi-User API Submission Portal
Handles API requests submitted on behalf of multiple users
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import uuid
import json

from .auth_api import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/multi-user-api", tags=["multi-user-api"])

# Pydantic Models
class MultiUserAPIRequest(BaseModel):
    endpoint: str
    method: str = "GET"
    headers: Dict[str, Any] = {}
    payload: Optional[Dict[str, Any]] = None
    users: List[str]
    description: Optional[str] = None

# Mock request storage
MOCK_API_REQUESTS = []
MOCK_STATISTICS = {
    "total_requests": 0,
    "successful": 0, 
    "failed": 0,
    "active_users": 3
}

@router.post("/")
async def submit_multi_user_api(
    api_request: MultiUserAPIRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Submit API request for multiple users"""
    try:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Create request record
        request_record = {
            "id": request_id,
            "endpoint": api_request.endpoint,
            "method": api_request.method,
            "headers": api_request.headers,
            "payload": api_request.payload,
            "users": api_request.users,
            "user_count": len(api_request.users),
            "description": api_request.description,
            "status": "pending",
            "submitted_by": current_user["email"],
            "created_at": datetime.now().isoformat(),
            "results": []
        }
        
        # Store request
        MOCK_API_REQUESTS.append(request_record)
        
        # Update statistics
        MOCK_STATISTICS["total_requests"] += 1
        
        # Simulate processing (in production, this would be async)
        import asyncio
        asyncio.create_task(process_multi_user_request(request_record))
        
        logger.info(f"Multi-user API request submitted: {request_id} by {current_user['email']}")
        
        return {
            "success": True,
            "request_id": request_id,
            "message": "API request submitted successfully",
            "user_count": len(api_request.users),
            "status": "pending"
        }
        
    except Exception as e:
        logger.error(f"Multi-user API submission error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to submit multi-user API request"
        )

async def process_multi_user_request(request_record: Dict[str, Any]):
    """Process multi-user API request (mock implementation)"""
    try:
        # Simulate processing delay
        import asyncio
        await asyncio.sleep(2)
        
        # Simulate results for each user
        success_rate = 0.8  # 80% success rate
        results = []
        
        for user_id in request_record["users"]:
            success = __import__("random").random() < success_rate
            
            result = {
                "user_id": user_id,
                "status": "success" if success else "failed",
                "response": {
                    "data": f"Mock response for {user_id}",
                    "timestamp": datetime.now().isoformat()
                } if success else None,
                "error": None if success else "Mock API error",
                "processed_at": datetime.now().isoformat()
            }
            results.append(result)
        
        # Update request status
        request_record["status"] = "completed"
        request_record["results"] = results
        request_record["completed_at"] = datetime.now().isoformat()
        
        # Update statistics
        successful_users = sum(1 for r in results if r["status"] == "success")
        MOCK_STATISTICS["successful"] += successful_users
        MOCK_STATISTICS["failed"] += len(results) - successful_users
        
        logger.info(f"Multi-user API request completed: {request_record['id']}")
        
    except Exception as e:
        logger.error(f"Multi-user API processing error: {e}")
        request_record["status"] = "failed"
        request_record["error"] = str(e)

@router.get("/status")
async def get_multi_user_api_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get multi-user API submission status and statistics"""
    try:
        # Get recent requests (last 20)
        recent_requests = sorted(
            MOCK_API_REQUESTS,
            key=lambda x: x["created_at"],
            reverse=True
        )[:20]
        
        # Clean up request data for response
        cleaned_requests = []
        for req in recent_requests:
            cleaned_req = {
                "id": req["id"],
                "endpoint": req["endpoint"],
                "method": req["method"],
                "user_count": req["user_count"],
                "description": req.get("description"),
                "status": req["status"],
                "submitted_by": req["submitted_by"],
                "created_at": req["created_at"],
                "completed_at": req.get("completed_at")
            }
            cleaned_requests.append(cleaned_req)
        
        return {
            "success": True,
            "statistics": MOCK_STATISTICS.copy(),
            "recent_requests": cleaned_requests,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Multi-user API status error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch multi-user API status"
        )

@router.get("/request/{request_id}")
async def get_request_details(
    request_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get detailed information about a specific API request"""
    try:
        # Find request
        request_record = None
        for req in MOCK_API_REQUESTS:
            if req["id"] == request_id:
                request_record = req
                break
        
        if not request_record:
            raise HTTPException(
                status_code=404,
                detail="Request not found"
            )
        
        # Check if user has access (submitted by them or admin)
        if (request_record["submitted_by"] != current_user["email"] and 
            current_user.get("role") != "admin"):
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )
        
        return {
            "success": True,
            "request": request_record,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Request details error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch request details"
        ) 