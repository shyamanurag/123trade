"""
Enhanced Trading API
Comprehensive API for enhanced trading features
Order deduplication, position analytics, strategy recommendations, comprehensive reports
100% REAL TRADING - NO SIMULATION
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import date, datetime
import logging

from src.core.dependencies import get_orchestrator
from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter()

# Request Models
class OrderValidationRequest(BaseModel):
    user_id: int
    symbol: str
    quantity: int
    price: float
    side: str = Field(..., description="BUY or SELL")
    order_type: str = Field(default="MARKET", description="MARKET or LIMIT")

class PositionSyncRequest(BaseModel):
    user_id: int
    sharekhan_client_id: str
    sharekhan_api_key: str
    sharekhan_api_secret: str

class RecommendationExecutionRequest(BaseModel):
    recommendation_id: str
    user_approval: bool = True

class ReportGenerationRequest(BaseModel):
    user_id: int
    report_date: Optional[str] = None  # ISO date format

# Enhanced Trading Endpoints

@router.post("/orders/validate-and-submit")
async def validate_and_submit_order(
    request: OrderValidationRequest,
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """
    Validate order through deduplication system and submit if approved
    Prevents duplicate orders and enforces rate limiting
    """
    try:
        logger.info(f"🔍 Validating order: {request.symbol} {request.quantity} {request.side} for user {request.user_id}")
        
        result = await orchestrator.validate_and_submit_order(
            user_id=request.user_id,
            symbol=request.symbol,
            quantity=request.quantity,
            price=request.price,
            side=request.side,
            order_type=request.order_type
        )
        
        if result.get("success"):
            logger.info(f"✅ Order validated and submitted: {result.get('order_id')}")
            return {
                "success": True,
                "message": "Order validated and submitted successfully",
                "data": result
            }
        else:
            logger.warning(f"🚫 Order rejected: {result.get('message')}")
            return {
                "success": False,
                "message": result.get("message", "Order validation failed"),
                "reason": result.get("reason"),
                "details": result
            }
        
    except Exception as e:
        logger.error(f"❌ Order validation error: {e}")
        raise HTTPException(status_code=500, detail=f"Order validation failed: {str(e)}")

@router.get("/positions/{user_id}/analytics")
async def get_position_analytics(
    user_id: int,
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """
    Get comprehensive position analytics for user
    Includes P&L breakdown, portfolio metrics, performance statistics
    """
    try:
        logger.info(f"📊 Getting position analytics for user {user_id}")
        
        result = await orchestrator.get_user_position_analytics(user_id)
        
        if result.get("success"):
            return {
                "success": True,
                "message": "Position analytics retrieved successfully",
                "data": result.get("analytics")
            }
        else:
            raise HTTPException(
                status_code=404, 
                detail=result.get("error", "Position analytics not available")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Position analytics error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get position analytics: {str(e)}")

@router.post("/positions/sync-from-sharekhan")
async def sync_positions_from_sharekhan(
    request: PositionSyncRequest,
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """
    Sync user positions from ShareKhan API
    Fetches real positions and updates database with current P&L
    """
    try:
        logger.info(f"🔄 Syncing positions from ShareKhan for user {request.user_id}")
        
        result = await orchestrator.sync_user_positions_from_sharekhan(
            user_id=request.user_id,
            sharekhan_client_id=request.sharekhan_client_id,
            sharekhan_api_key=request.sharekhan_api_key,
            sharekhan_api_secret=request.sharekhan_api_secret
        )
        
        if result.get("success"):
            logger.info(f"✅ Synced {result.get('positions_count', 0)} positions for user {request.user_id}")
            return {
                "success": True,
                "message": f"Successfully synced {result.get('positions_count', 0)} positions",
                "data": result
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to sync positions from ShareKhan")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Position sync error: {e}")
        raise HTTPException(status_code=500, detail=f"Position sync failed: {str(e)}")

@router.get("/strategies/recommendations/{user_id}")
async def get_strategy_recommendations(
    user_id: int,
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """
    Get real-time strategy recommendations for all user positions
    Analyzes positions through multiple strategies and provides actionable insights
    """
    try:
        logger.info(f"🎯 Getting strategy recommendations for user {user_id}")
        
        result = await orchestrator.get_strategy_recommendations(user_id)
        
        if result.get("success"):
            recommendations = result.get("recommendations", [])
            logger.info(f"✅ Retrieved {len(recommendations)} strategy recommendations")
            
            return {
                "success": True,
                "message": f"Retrieved {len(recommendations)} strategy recommendations",
                "data": {
                    "user_id": user_id,
                    "recommendations_count": len(recommendations),
                    "recommendations": recommendations,
                    "generated_at": datetime.now().isoformat()
                }
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "Strategy recommendations not available")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Strategy recommendations error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get strategy recommendations: {str(e)}")

@router.post("/strategies/execute-recommendation")
async def execute_strategy_recommendation(
    request: RecommendationExecutionRequest,
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """
    Execute a strategy recommendation
    Implements the recommended action (buy/sell/hold/etc) with user approval
    """
    try:
        logger.info(f"⚡ Executing strategy recommendation: {request.recommendation_id}")
        
        result = await orchestrator.execute_strategy_recommendation(
            recommendation_id=request.recommendation_id,
            user_approval=request.user_approval
        )
        
        if result.get("success"):
            logger.info(f"✅ Strategy recommendation executed successfully")
            return {
                "success": True,
                "message": "Strategy recommendation executed successfully",
                "data": result
            }
        else:
            return {
                "success": False,
                "message": result.get("error", "Failed to execute recommendation"),
                "error": result.get("error")
            }
        
    except Exception as e:
        logger.error(f"❌ Recommendation execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Recommendation execution failed: {str(e)}")

@router.post("/reports/comprehensive")
async def generate_comprehensive_report(
    request: ReportGenerationRequest,
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """
    Generate comprehensive trading report
    Includes trades, P&L, positions, funds - all from real ShareKhan data
    """
    try:
        # Parse report date if provided
        report_date = None
        if request.report_date:
            try:
                report_date = datetime.fromisoformat(request.report_date).date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DD)")
        
        logger.info(f"📊 Generating comprehensive report for user {request.user_id}, date: {report_date}")
        
        result = await orchestrator.generate_comprehensive_report(
            user_id=request.user_id,
            report_date=report_date
        )
        
        if result.get("success"):
            report_data = result.get("report")
            logger.info(f"✅ Comprehensive report generated successfully")
            
            return {
                "success": True,
                "message": "Comprehensive report generated successfully",
                "data": {
                    "user_id": request.user_id,
                    "report_date": report_date.isoformat() if report_date else date.today().isoformat(),
                    "report": report_data,
                    "summary": {
                        "trades_count": len(report_data.get("trades", [])),
                        "positions_count": len(report_data.get("positions", [])),
                        "pnl_summary": report_data.get("pnl_summary"),
                        "fund_summary": report_data.get("fund_summary")
                    }
                }
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to generate comprehensive report")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Report generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

@router.get("/system/enhanced-services-status")
async def get_enhanced_services_status(
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """
    Get status of all enhanced trading services
    Shows which components are available and functioning
    """
    try:
        status = orchestrator.get_enhanced_services_status()
        
        return {
            "success": True,
            "message": "Enhanced services status retrieved",
            "data": {
                "services": status,
                "system_ready": status.get("all_services_available", False),
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Enhanced services status error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get services status: {str(e)}")

# Utility Endpoints

@router.get("/orders/deduplication-history/{user_id}")
async def get_order_deduplication_history(
    user_id: int,
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """Get order deduplication history for user"""
    try:
        if not orchestrator.order_deduplication_manager:
            raise HTTPException(status_code=404, detail="Order deduplication manager not available")
        
        history = await orchestrator.order_deduplication_manager.get_order_history(user_id)
        
        return {
            "success": True,
            "message": f"Retrieved {len(history)} order history entries",
            "data": {
                "user_id": user_id,
                "history_count": len(history),
                "history": history
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Order history error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get order history: {str(e)}")

@router.get("/health/enhanced-trading")
async def enhanced_trading_health_check(
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """Health check for enhanced trading system"""
    try:
        services_status = orchestrator.get_enhanced_services_status()
        
        health_status = {
            "status": "healthy" if services_status.get("all_services_available") else "degraded",
            "services": services_status,
            "orchestrator_status": {
                "initialized": orchestrator.is_initialized,
                "running": orchestrator.is_running,
                "health_status": orchestrator.health_status
            },
            "timestamp": datetime.now().isoformat()
        }
        
        status_code = 200 if services_status.get("all_services_available") else 503
        
        return {
            "success": True,
            "health": health_status
        }
        
    except Exception as e:
        logger.error(f"❌ Health check error: {e}")
        return {
            "success": False,
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }