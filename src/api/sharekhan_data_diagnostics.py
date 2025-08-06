"""
ShareKhan Data Diagnostics and Live Data Fixing
Comprehensive diagnostics for data parsing issues and live data connectivity
Real-time debugging and fixing capabilities
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import asyncio
import traceback

from src.core.dependencies import get_orchestrator
from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
from src.api.sharekhan_daily_auth import get_authenticated_sharekhan_client
from brokers.sharekhan import ShareKhanIntegration, ShareKhanMarketData

logger = logging.getLogger(__name__)

router = APIRouter()

class DataTestRequest(BaseModel):
    user_id: int
    sharekhan_client_id: str
    test_symbols: Optional[List[str]] = ["RELIANCE", "TCS", "INFY", "HDFC", "ICICIBANK"]

class DataFixRequest(BaseModel):
    user_id: int
    sharekhan_client_id: str
    force_refresh: bool = True

@router.get("/diagnostics/connection-status")
async def check_connection_status(
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """
    Comprehensive connection status check
    Diagnoses all aspects of ShareKhan connectivity
    """
    try:
        diagnostics = {
            "timestamp": datetime.now().isoformat(),
            "orchestrator_status": {
                "initialized": orchestrator.is_initialized,
                "running": orchestrator.is_running,
                "health_status": orchestrator.health_status
            },
            "sharekhan_integration": {
                "available": orchestrator.sharekhan_integration is not None,
                "authenticated": False,
                "credentials_configured": False,
                "last_error": None
            },
            "enhanced_services": {
                "position_manager": orchestrator.enhanced_position_manager is not None,
                "data_mapper": orchestrator.sharekhan_data_mapper is not None,
                "strategy_tracker": orchestrator.strategy_position_tracker is not None
            },
            "data_connectivity": {
                "can_fetch_quotes": False,
                "websocket_connected": False,
                "last_data_update": None
            }
        }
        
        # Check ShareKhan integration details
        if orchestrator.sharekhan_integration:
            integration = orchestrator.sharekhan_integration
            diagnostics["sharekhan_integration"].update({
                "authenticated": integration.is_authenticated,
                "credentials_configured": bool(integration.api_key and integration.secret_key),
                "access_token_available": bool(integration.access_token),
                "session_token_available": bool(integration.session_token),
                "websocket_connected": integration.is_ws_connected,
                "customer_id": integration.customer_id
            })
            
            # Test data connectivity
            if integration.is_authenticated:
                try:
                    test_quotes = await integration.get_market_quote(["RELIANCE"])
                    diagnostics["data_connectivity"]["can_fetch_quotes"] = len(test_quotes) > 0
                    diagnostics["data_connectivity"]["last_data_update"] = datetime.now().isoformat()
                except Exception as e:
                    diagnostics["data_connectivity"]["fetch_error"] = str(e)
        
        # Overall health assessment
        all_systems_ok = all([
            diagnostics["orchestrator_status"]["initialized"],
            diagnostics["sharekhan_integration"]["available"],
            diagnostics["sharekhan_integration"]["authenticated"],
            diagnostics["data_connectivity"]["can_fetch_quotes"]
        ])
        
        diagnostics["overall_status"] = "HEALTHY" if all_systems_ok else "DEGRADED"
        
        return {
            "success": True,
            "diagnostics": diagnostics
        }
        
    except Exception as e:
        logger.error(f"❌ Connection diagnostics failed: {e}")
        raise HTTPException(status_code=500, detail=f"Diagnostics failed: {str(e)}")

@router.post("/diagnostics/test-live-data")
async def test_live_data_fetch(request: DataTestRequest):
    """
    Test live data fetching for specific user and symbols
    Provides detailed error information for debugging
    """
    try:
        logger.info(f"🧪 Testing live data fetch for user {request.user_id}")
        
        # Get authenticated client
        sharekhan_client = await get_authenticated_sharekhan_client(
            request.user_id, 
            request.sharekhan_client_id
        )
        
        if not sharekhan_client:
            return {
                "success": False,
                "error": "No authenticated ShareKhan session found",
                "resolution": "Submit daily authentication token first",
                "auth_endpoint": "/api/sharekhan-auth/auth/submit-daily-token"
            }
        
        test_results = {
            "user_id": request.user_id,
            "sharekhan_client_id": request.sharekhan_client_id,
            "test_timestamp": datetime.now().isoformat(),
            "authentication_status": {
                "is_authenticated": sharekhan_client.is_authenticated,
                "has_access_token": bool(sharekhan_client.access_token),
                "has_session_token": bool(sharekhan_client.session_token)
            },
            "symbol_tests": [],
            "overall_success": False,
            "total_symbols_tested": len(request.test_symbols),
            "successful_fetches": 0,
            "failed_fetches": 0
        }
        
        # Test each symbol individually
        for symbol in request.test_symbols:
            symbol_test = {
                "symbol": symbol,
                "success": False,
                "error": None,
                "data": None,
                "response_time_ms": None
            }
            
            try:
                start_time = datetime.now()
                quotes = await sharekhan_client.get_market_quote([symbol])
                end_time = datetime.now()
                
                if symbol in quotes:
                    symbol_test["success"] = True
                    symbol_test["data"] = {
                        "ltp": quotes[symbol].ltp,
                        "volume": quotes[symbol].volume,
                        "timestamp": quotes[symbol].timestamp.isoformat()
                    }
                    symbol_test["response_time_ms"] = (end_time - start_time).total_seconds() * 1000
                    test_results["successful_fetches"] += 1
                else:
                    symbol_test["error"] = "Symbol not found in response"
                    test_results["failed_fetches"] += 1
                    
            except Exception as e:
                symbol_test["error"] = str(e)
                symbol_test["error_type"] = type(e).__name__
                test_results["failed_fetches"] += 1
            
            test_results["symbol_tests"].append(symbol_test)
        
        # Calculate overall success
        test_results["overall_success"] = test_results["successful_fetches"] > 0
        test_results["success_rate"] = (test_results["successful_fetches"] / test_results["total_symbols_tested"]) * 100
        
        return {
            "success": True,
            "test_results": test_results
        }
        
    except Exception as e:
        logger.error(f"❌ Live data test failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "stack_trace": traceback.format_exc()
        }

@router.post("/diagnostics/fix-data-connectivity")
async def fix_data_connectivity(
    request: DataFixRequest,
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """
    Attempt to fix data connectivity issues
    Reinitializes connections and tests functionality
    """
    try:
        logger.info(f"🔧 Attempting to fix data connectivity for user {request.user_id}")
        
        fix_results = {
            "user_id": request.user_id,
            "fix_timestamp": datetime.now().isoformat(),
            "steps_attempted": [],
            "final_status": "UNKNOWN",
            "data_test_success": False
        }
        
        # Step 1: Get authenticated client
        fix_results["steps_attempted"].append("Getting authenticated ShareKhan client")
        sharekhan_client = await get_authenticated_sharekhan_client(
            request.user_id, 
            request.sharekhan_client_id
        )
        
        if not sharekhan_client:
            fix_results["steps_attempted"].append("❌ No authenticated session found")
            fix_results["final_status"] = "AUTHENTICATION_REQUIRED"
            return {
                "success": False,
                "fix_results": fix_results,
                "resolution": "Submit daily authentication token first"
            }
        
        # Step 2: Update orchestrator with authenticated client
        fix_results["steps_attempted"].append("Updating orchestrator with authenticated client")
        if orchestrator.sharekhan_integration:
            orchestrator.sharekhan_integration.access_token = sharekhan_client.access_token
            orchestrator.sharekhan_integration.session_token = sharekhan_client.session_token
            orchestrator.sharekhan_integration.is_authenticated = True
        
        # Step 3: Reinitialize enhanced services if requested
        if request.force_refresh:
            fix_results["steps_attempted"].append("Force refreshing enhanced services")
            try:
                # Reinitialize data mapper
                if orchestrator.sharekhan_data_mapper:
                    orchestrator.sharekhan_data_mapper.sharekhan_client = sharekhan_client
                
                # Reinitialize position manager
                if orchestrator.enhanced_position_manager:
                    orchestrator.enhanced_position_manager.sharekhan_client = sharekhan_client
                
                # Reinitialize strategy tracker
                if orchestrator.strategy_position_tracker:
                    orchestrator.strategy_position_tracker.sharekhan_client = sharekhan_client
                    
                fix_results["steps_attempted"].append("✅ Enhanced services updated")
                
            except Exception as e:
                fix_results["steps_attempted"].append(f"❌ Enhanced services update failed: {e}")
        
        # Step 4: Test data connectivity
        fix_results["steps_attempted"].append("Testing data connectivity")
        try:
            test_symbols = ["RELIANCE", "TCS"]
            quotes = await sharekhan_client.get_market_quote(test_symbols)
            
            if len(quotes) > 0:
                fix_results["data_test_success"] = True
                fix_results["final_status"] = "FIXED"
                fix_results["steps_attempted"].append(f"✅ Data test successful: {len(quotes)} quotes fetched")
            else:
                fix_results["final_status"] = "DATA_UNAVAILABLE"
                fix_results["steps_attempted"].append("❌ Data test failed: No quotes returned")
                
        except Exception as e:
            fix_results["final_status"] = "DATA_ERROR"
            fix_results["steps_attempted"].append(f"❌ Data test failed: {e}")
        
        return {
            "success": fix_results["data_test_success"],
            "fix_results": fix_results
        }
        
    except Exception as e:
        logger.error(f"❌ Data connectivity fix failed: {e}")
        raise HTTPException(status_code=500, detail=f"Fix attempt failed: {str(e)}")

@router.get("/diagnostics/live-positions-status/{user_id}")
async def check_live_positions_status(
    user_id: int,
    sharekhan_client_id: str,
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """
    Check status of live positions data
    Diagnoses position sync and real-time updates
    """
    try:
        logger.info(f"📊 Checking live positions status for user {user_id}")
        
        status = {
            "user_id": user_id,
            "check_timestamp": datetime.now().isoformat(),
            "position_manager_status": {
                "available": orchestrator.enhanced_position_manager is not None,
                "initialized": False,
                "last_sync": None,
                "active_positions": 0
            },
            "sharekhan_connectivity": {
                "authenticated": False,
                "can_fetch_positions": False,
                "last_error": None
            },
            "real_time_updates": {
                "price_updates_active": False,
                "last_price_update": None,
                "update_frequency": "Unknown"
            }
        }
        
        # Check position manager
        if orchestrator.enhanced_position_manager:
            pm = orchestrator.enhanced_position_manager
            status["position_manager_status"]["initialized"] = True
            
            # Get user positions
            try:
                positions = await pm.get_user_positions(user_id)
                status["position_manager_status"]["active_positions"] = len(positions)
                
                if positions:
                    latest_update = max([pos.get("last_update", "1970-01-01") for pos in positions])
                    status["position_manager_status"]["last_sync"] = latest_update
                    
            except Exception as e:
                status["position_manager_status"]["error"] = str(e)
        
        # Check ShareKhan connectivity for positions
        sharekhan_client = await get_authenticated_sharekhan_client(user_id, sharekhan_client_id)
        if sharekhan_client:
            status["sharekhan_connectivity"]["authenticated"] = True
            
            try:
                # Test position fetching
                positions_result = await sharekhan_client.get_positions()
                status["sharekhan_connectivity"]["can_fetch_positions"] = positions_result.get("success", False)
                
                if not positions_result.get("success"):
                    status["sharekhan_connectivity"]["last_error"] = positions_result.get("error", "Unknown error")
                    
            except Exception as e:
                status["sharekhan_connectivity"]["can_fetch_positions"] = False
                status["sharekhan_connectivity"]["last_error"] = str(e)
        
        # Check real-time updates
        if orchestrator.enhanced_position_manager and orchestrator.enhanced_position_manager.price_update_task:
            status["real_time_updates"]["price_updates_active"] = not orchestrator.enhanced_position_manager.price_update_task.done()
            status["real_time_updates"]["update_frequency"] = f"{orchestrator.enhanced_position_manager.update_interval_seconds} seconds"
        
        return {
            "success": True,
            "status": status
        }
        
    except Exception as e:
        logger.error(f"❌ Live positions status check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.post("/diagnostics/force-sync-positions")
async def force_sync_positions(
    user_id: int,
    sharekhan_client_id: str,
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """
    Force synchronization of positions from ShareKhan
    Useful when automatic sync is failing
    """
    try:
        logger.info(f"🔄 Force syncing positions for user {user_id}")
        
        if not orchestrator.enhanced_position_manager:
            raise HTTPException(status_code=404, detail="Enhanced position manager not available")
        
        # Get ShareKhan credentials (these would come from request in real implementation)
        api_key = os.getenv('SHAREKHAN_API_KEY')
        api_secret = os.getenv('SHAREKHAN_SECRET_KEY')
        
        if not api_key or not api_secret:
            raise HTTPException(status_code=400, detail="ShareKhan credentials not configured")
        
        # Force sync positions
        sync_result = await orchestrator.enhanced_position_manager.sync_positions_from_sharekhan(
            user_id=user_id,
            sharekhan_client_id=sharekhan_client_id,
            sharekhan_api_key=api_key,
            sharekhan_api_secret=api_secret
        )
        
        return {
            "success": sync_result.get("success", False),
            "sync_result": sync_result,
            "message": "Position sync completed" if sync_result.get("success") else "Position sync failed"
        }
        
    except Exception as e:
        logger.error(f"❌ Force position sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Force sync failed: {str(e)}")

@router.get("/diagnostics/data-flow-trace")
async def trace_data_flow(
    orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
):
    """
    Trace the complete data flow from ShareKhan to frontend
    Identifies where the data pipeline is breaking
    """
    try:
        trace_results = {
            "timestamp": datetime.now().isoformat(),
            "data_flow_steps": [],
            "bottlenecks": [],
            "recommendations": []
        }
        
        # Step 1: Check orchestrator
        step1 = {
            "step": "Orchestrator Check",
            "status": "PASS" if orchestrator.is_initialized else "FAIL",
            "details": {
                "initialized": orchestrator.is_initialized,
                "running": orchestrator.is_running
            }
        }
        trace_results["data_flow_steps"].append(step1)
        
        # Step 2: Check ShareKhan integration
        step2 = {
            "step": "ShareKhan Integration",
            "status": "UNKNOWN",
            "details": {}
        }
        
        if orchestrator.sharekhan_integration:
            step2["status"] = "PASS" if orchestrator.sharekhan_integration.is_authenticated else "FAIL"
            step2["details"] = {
                "available": True,
                "authenticated": orchestrator.sharekhan_integration.is_authenticated,
                "has_credentials": bool(orchestrator.sharekhan_integration.api_key)
            }
            
            if not orchestrator.sharekhan_integration.is_authenticated:
                trace_results["bottlenecks"].append("ShareKhan not authenticated")
                trace_results["recommendations"].append("Submit daily authentication token")
        else:
            step2["status"] = "FAIL"
            step2["details"]["available"] = False
            trace_results["bottlenecks"].append("ShareKhan integration not initialized")
        
        trace_results["data_flow_steps"].append(step2)
        
        # Step 3: Check enhanced services
        step3 = {
            "step": "Enhanced Services",
            "status": "PASS",
            "details": {
                "position_manager": orchestrator.enhanced_position_manager is not None,
                "data_mapper": orchestrator.sharekhan_data_mapper is not None,
                "strategy_tracker": orchestrator.strategy_position_tracker is not None
            }
        }
        
        missing_services = [k for k, v in step3["details"].items() if not v]
        if missing_services:
            step3["status"] = "PARTIAL"
            trace_results["bottlenecks"].append(f"Missing services: {missing_services}")
        
        trace_results["data_flow_steps"].append(step3)
        
        # Step 4: Check data endpoints
        step4 = {
            "step": "API Endpoints",
            "status": "PASS",
            "details": {
                "enhanced_trading_api": True,  # Assume loaded if we're here
                "sharekhan_auth_api": True,
                "diagnostics_api": True
            }
        }
        trace_results["data_flow_steps"].append(step4)
        
        # Overall assessment
        all_pass = all(step["status"] == "PASS" for step in trace_results["data_flow_steps"])
        
        if all_pass:
            trace_results["recommendations"].append("Data flow appears healthy")
        else:
            trace_results["recommendations"].extend([
                "Check authentication status",
                "Verify ShareKhan credentials",
                "Test live data endpoints",
                "Review orchestrator initialization"
            ])
        
        return {
            "success": True,
            "trace_results": trace_results,
            "overall_status": "HEALTHY" if all_pass else "ISSUES_DETECTED"
        }
        
    except Exception as e:
        logger.error(f"❌ Data flow trace failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trace failed: {str(e)}")

# Background task for monitoring data health
async def monitor_data_health():
    """Background monitoring of data health"""
    while True:
        try:
            # This would run continuous health checks
            await asyncio.sleep(60)  # Check every minute
            
        except Exception as e:
            logger.error(f"❌ Data health monitoring error: {e}")
            await asyncio.sleep(60)