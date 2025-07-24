"""
System Health Monitoring API
Provides comprehensive health checks and data consistency validation
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import asyncio
import aiohttp
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health/comprehensive")
async def get_comprehensive_health():
    """
    Comprehensive system health check including:
    - Endpoint availability
    - Data consistency between sources
    - Performance metrics
    """
    try:
        logger.info("🏥 Running comprehensive system health check...")
        
        # Define critical endpoints to check
        endpoints_to_check = [
            {
                "name": "Autonomous Trading",
                "url": "/api/v1/autonomous/status",
                "critical": True,
                "expected_fields": ["is_active", "total_trades", "daily_pnl"]
            },
            {
                "name": "Dashboard Summary", 
                "url": "/api/v1/dashboard/dashboard/summary",
                "critical": True,
                "expected_fields": ["autonomous_trading", "system_metrics"]
            },
            {
                "name": "Trading Control",
                "url": "/api/v1/control/trading/status", 
                "critical": False,
                "expected_fields": ["success"]
            }
        ]
        
        health_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "endpoints": [],
            "data_consistency": [],
            "system_metrics": {},
            "alerts": []
        }
        
        # Test all endpoints
        endpoint_results = []
        autonomous_data = None
        dashboard_data = None
        
        for endpoint in endpoints_to_check:
            try:
                start_time = time.time()
                
                # Make internal request (simplified for demo)
                # In production, you'd make actual HTTP requests
                endpoint_status = await check_endpoint_health(endpoint)
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to ms
                
                endpoint_results.append({
                    "name": endpoint["name"],
                    "url": endpoint["url"],
                    "status": endpoint_status["status"],
                    "response_time_ms": response_time,
                    "critical": endpoint["critical"],
                    "message": endpoint_status.get("message", "OK"),
                    "data": endpoint_status.get("data")
                })
                
                # Store data for consistency checks
                if endpoint["name"] == "Autonomous Trading":
                    autonomous_data = endpoint_status.get("data")
                elif endpoint["name"] == "Dashboard Summary":
                    dashboard_data = endpoint_status.get("data")
                
            except Exception as e:
                endpoint_results.append({
                    "name": endpoint["name"],
                    "url": endpoint["url"], 
                    "status": "error",
                    "response_time_ms": None,
                    "critical": endpoint["critical"],
                    "message": str(e),
                    "data": None
                })
        
        health_results["endpoints"] = endpoint_results
        
        # Data consistency checks
        if autonomous_data and dashboard_data:
            consistency_checks = await check_data_consistency(autonomous_data, dashboard_data)
            health_results["data_consistency"] = consistency_checks
        
        # Calculate system metrics
        healthy_endpoints = len([e for e in endpoint_results if e["status"] == "healthy"])
        total_endpoints = len(endpoint_results)
        critical_failures = len([e for e in endpoint_results if e["critical"] and e["status"] == "error"])
        
        health_results["system_metrics"] = {
            "overall_health_percentage": (healthy_endpoints / total_endpoints) * 100,
            "healthy_endpoints": healthy_endpoints,
            "total_endpoints": total_endpoints,
            "critical_failures": critical_failures,
            "average_response_time": sum([e["response_time_ms"] for e in endpoint_results if e["response_time_ms"]]) / len([e for e in endpoint_results if e["response_time_ms"]]) if endpoint_results else 0
        }
        
        # Generate alerts
        alerts = []
        if critical_failures > 0:
            alerts.append({
                "level": "critical",
                "message": f"{critical_failures} critical endpoint(s) are failing",
                "action_required": "Immediate investigation needed"
            })
        
        # Check for data inconsistencies
        inconsistencies = len([c for c in health_results.get("data_consistency", []) if c.get("status") == "inconsistent"])
        if inconsistencies > 0:
            alerts.append({
                "level": "warning", 
                "message": f"{inconsistencies} data inconsistency issue(s) detected",
                "action_required": "Review data synchronization"
            })
        
        health_results["alerts"] = alerts
        
        # Set overall status
        if critical_failures > 0:
            health_results["overall_status"] = "critical"
        elif inconsistencies > 0 or healthy_endpoints < total_endpoints:
            health_results["overall_status"] = "warning"
        else:
            health_results["overall_status"] = "healthy"
        
        logger.info(f"✅ System health check completed: {health_results['overall_status']}")
        
        return {
            "success": True,
            "data": health_results
        }
        
    except Exception as e:
        logger.error(f"❌ Comprehensive health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def check_endpoint_health(endpoint: Dict) -> Dict:
    """ELIMINATED: Was simulating endpoint health checks instead of making real HTTP requests"""
    # 
    # ELIMINATED FAKE HEALTH CHECKING:
    # ❌ Fake endpoint health simulation that always returned "healthy"
    # ❌ Fake dashboard data (total_trades: 0, daily_pnl: 0)
    # ❌ Simulated HTTP responses without actual network requests
    # ❌ Default "healthy" status that could mask real failures
    # 
    # REAL IMPLEMENTATION NEEDED:
    # - Make actual HTTP requests to check endpoint availability
    # - Verify real response codes and response times
    # - Check actual data integrity from endpoints
    # - Implement real timeout handling and error detection
    
    logger.error(f"CRITICAL: Endpoint health checking requires real HTTP requests for {endpoint['url']}")
    logger.error("Fake endpoint simulation ELIMINATED for safety")
    
    # SAFETY: Return error state to indicate health checking is not functional
    return {
        "status": "error",
        "message": "REAL_HTTP_HEALTH_CHECKING_REQUIRED",
        "error": f"Endpoint health checking eliminated for {endpoint['url']}. Real HTTP requests required for safety.",
        "fake_simulation_eliminated": True
    }

async def check_data_consistency(autonomous_data: Dict, dashboard_data: Dict) -> List[Dict]:
    """Check consistency between data sources"""
    consistency_results = []
    
    try:
        # Extract data safely
        autonomous_trading = autonomous_data or {}
        dashboard_trading = dashboard_data.get("autonomous_trading", {}) if dashboard_data else {}
        
        # Define consistency checks
        checks = [
            {
                "metric": "total_trades",
                "autonomous_value": autonomous_trading.get("total_trades", 0),
                "dashboard_value": dashboard_trading.get("total_trades", 0),
                "tolerance": 0
            },
            {
                "metric": "daily_pnl", 
                "autonomous_value": autonomous_trading.get("daily_pnl", 0),
                "dashboard_value": dashboard_trading.get("daily_pnl", 0),
                "tolerance": 0.01
            },
            {
                "metric": "is_active",
                "autonomous_value": autonomous_trading.get("is_active", False),
                "dashboard_value": dashboard_trading.get("is_active", False), 
                "tolerance": 0
            }
        ]
        
        for check in checks:
            autonomous_val = check["autonomous_value"]
            dashboard_val = check["dashboard_value"]
            
            # Handle boolean comparison
            if isinstance(autonomous_val, bool) and isinstance(dashboard_val, bool):
                is_consistent = autonomous_val == dashboard_val
                difference = 0
            else:
                # Numeric comparison
                autonomous_val = float(autonomous_val) if autonomous_val is not None else 0
                dashboard_val = float(dashboard_val) if dashboard_val is not None else 0
                difference = abs(autonomous_val - dashboard_val)
                is_consistent = difference <= check["tolerance"]
            
            consistency_results.append({
                "metric": check["metric"],
                "status": "consistent" if is_consistent else "inconsistent",
                "autonomous_value": autonomous_val,
                "dashboard_value": dashboard_val,
                "difference": difference,
                "message": "Data matches" if is_consistent else f"Data mismatch detected"
            })
            
    except Exception as e:
        logger.error(f"Error in consistency check: {e}")
        consistency_results.append({
            "metric": "consistency_check",
            "status": "error",
            "message": f"Consistency check failed: {str(e)}"
        })
    
    return consistency_results

@router.get("/health/data-sources")
async def check_data_sources():
    """Quick check of data source consistency"""
    try:
        # Get data from both sources
        from src.core.orchestrator import TradingOrchestrator
        orchestrator = TradingOrchestrator.get_instance()
        autonomous_status = await orchestrator.get_trading_status()
        
        return {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "autonomous_source": {
                "total_trades": autonomous_status.get("total_trades", 0),
                "daily_pnl": autonomous_status.get("daily_pnl", 0),
                "is_active": autonomous_status.get("is_active", False)
            },
            "message": "Data source check completed"
        }
        
    except Exception as e:
        logger.error(f"Data source check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 