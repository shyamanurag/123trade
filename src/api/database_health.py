"""
Database Health API
Provides comprehensive database health monitoring and metrics
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
import logging
import os
import sys
from pathlib import Path
from sqlalchemy import text

# Add core to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from core.optimized_database_manager import (
        get_db_manager,
        OptimizedDatabaseManager,
        HealthMetrics
    )
    DATABASE_MANAGER_AVAILABLE = True
except ImportError as e:
    DATABASE_MANAGER_AVAILABLE = False
    logging.warning(f"Optimized database manager not available: {e}")

router = APIRouter(prefix="/database", tags=["database-health"])
logger = logging.getLogger(__name__)

@router.get("/health", response_model=Dict[str, Any])
async def get_database_health():
    """
    Get comprehensive database health status
    Includes connection pool metrics, query performance, and system health
    """
    if not DATABASE_MANAGER_AVAILABLE:
        return {
            "status": "unavailable",
            "message": "Optimized database manager not available",
            "fallback_mode": True
        }
    
    try:
        db_manager = get_db_manager()
        health_status = await db_manager.get_health_status()
        
        return {
            "timestamp": health_status["last_check"],
            "overall_status": health_status["status"],
            "uptime": health_status["uptime"],
            "postgres": health_status["postgres"],
            "redis": health_status["redis"],
            "performance_metrics": {
                "avg_query_time_ms": health_status["postgres"]["avg_query_time"] * 1000,
                "active_connections": health_status["postgres"]["active_connections"],
                "pool_utilization": (
                    health_status["postgres"]["checked_out"] / 
                    max(health_status["postgres"]["pool_size"], 1)
                ) * 100
            },
            "system_metrics": health_status["system"],
            "error_metrics": health_status["metrics"],
            "recommendations": _generate_health_recommendations(health_status)
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )

@router.get("/metrics", response_model=Dict[str, Any])
async def get_database_metrics():
    """
    Get detailed database performance metrics
    """
    if not DATABASE_MANAGER_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database metrics not available"
        )
    
    try:
        db_manager = get_db_manager()
        health_metrics = db_manager.health_monitor.get_health_metrics()
        
        return {
            "connection_metrics": {
                "total_connections": health_metrics.connection_count,
                "active_connections": health_metrics.active_connections,
                "pool_size": health_metrics.pool_size,
                "pool_checked_out": health_metrics.pool_checked_out,
                "pool_overflow": health_metrics.pool_overflow
            },
            "performance_metrics": {
                "avg_query_time_seconds": health_metrics.avg_query_time,
                "avg_query_time_ms": health_metrics.avg_query_time * 1000,
                "error_count": health_metrics.error_count,
                "uptime_seconds": health_metrics.uptime.total_seconds()
            },
            "health_status": {
                "is_healthy": health_metrics.is_healthy,
                "last_check": health_metrics.last_check.isoformat(),
                "recent_errors": health_metrics.errors[-3:]  # Last 3 errors
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get database metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Metrics retrieval failed: {str(e)}"
        )

@router.post("/test-connection")
async def test_database_connection():
    """
    Test database connection and return detailed results
    """
    if not DATABASE_MANAGER_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection testing not available"
        )
    
    results = {
        "postgres": {"status": "unknown", "details": ""},
        "redis": {"status": "unknown", "details": ""},
        "overall": {"status": "unknown", "message": ""}
    }
    
    try:
        db_manager = get_db_manager()
        
        # Test PostgreSQL connection
        try:
            if db_manager.async_session_maker:
                async with db_manager.async_session_maker() as session:
                    await session.execute(text("SELECT 1 as test"))
                results["postgres"]["status"] = "healthy"
                results["postgres"]["details"] = "Async connection successful"
            elif db_manager.session_maker:
                with db_manager.get_session() as session:
                    session.execute(text("SELECT 1 as test"))
                results["postgres"]["status"] = "healthy"  
                results["postgres"]["details"] = "Sync connection successful"
            else:
                results["postgres"]["status"] = "unavailable"
                results["postgres"]["details"] = "No session maker available"
        except Exception as e:
            results["postgres"]["status"] = "error"
            results["postgres"]["details"] = str(e)
        
        # Test Redis connection
        try:
            if db_manager.redis_client:
                ping_result = await db_manager.redis_client.ping()
                if ping_result:
                    results["redis"]["status"] = "healthy"
                    results["redis"]["details"] = "Ping successful"
                else:
                    results["redis"]["status"] = "error"
                    results["redis"]["details"] = "Ping failed"
            else:
                results["redis"]["status"] = "unavailable"
                results["redis"]["details"] = "Redis client not configured"
        except Exception as e:
            results["redis"]["status"] = "error"
            results["redis"]["details"] = str(e)
        
        # Determine overall status
        postgres_ok = results["postgres"]["status"] == "healthy"
        redis_ok = results["redis"]["status"] in ["healthy", "unavailable"]  # Redis is optional
        
        if postgres_ok and redis_ok:
            results["overall"]["status"] = "healthy"
            results["overall"]["message"] = "All database connections are working"
        elif postgres_ok:
            results["overall"]["status"] = "degraded"
            results["overall"]["message"] = "PostgreSQL working, Redis issues detected"
        else:
            results["overall"]["status"] = "unhealthy"
            results["overall"]["message"] = "PostgreSQL connection failed"
        
        return results
        
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        results["overall"]["status"] = "error"
        results["overall"]["message"] = f"Test failed: {str(e)}"
        return results

@router.get("/pool-status")
async def get_connection_pool_status():
    """
    Get detailed connection pool status
    """
    if not DATABASE_MANAGER_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Connection pool status not available"
        )
    
    try:
        db_manager = get_db_manager()
        health_metrics = db_manager.health_monitor.get_health_metrics()
        
        # Calculate pool utilization
        pool_utilization = 0
        if health_metrics.pool_size > 0:
            pool_utilization = (health_metrics.pool_checked_out / health_metrics.pool_size) * 100
        
        return {
            "pool_configuration": {
                "pool_size": health_metrics.pool_size,
                "max_overflow": db_manager.postgres_config.max_overflow,
                "pool_timeout": db_manager.postgres_config.pool_timeout,
                "pool_recycle": db_manager.postgres_config.pool_recycle
            },
            "current_status": {
                "checked_out_connections": health_metrics.pool_checked_out,
                "overflow_connections": health_metrics.pool_overflow,
                "total_connections": health_metrics.connection_count,
                "pool_utilization_percent": round(pool_utilization, 2)
            },
            "health_indicators": {
                "is_healthy": health_metrics.is_healthy,
                "high_utilization": pool_utilization > 80,
                "overflow_in_use": health_metrics.pool_overflow > 0,
                "recent_errors": len(health_metrics.errors) > 0
            },
            "recommendations": _generate_pool_recommendations(health_metrics, pool_utilization)
        }
        
    except Exception as e:
        logger.error(f"Failed to get pool status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pool status retrieval failed: {str(e)}"
        )

@router.post("/optimize-settings")
async def optimize_database_settings():
    """
    Get optimization recommendations based on current performance
    """
    if not DATABASE_MANAGER_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database optimization not available"
        )
    
    try:
        db_manager = get_db_manager()
        health_status = await db_manager.get_health_status()
        health_metrics = db_manager.health_monitor.get_health_metrics()
        
        recommendations = []
        
        # Analyze connection pool
        pool_utilization = (health_metrics.pool_checked_out / max(health_metrics.pool_size, 1)) * 100
        
        if pool_utilization > 90:
            recommendations.append({
                "category": "connection_pool",
                "priority": "high",
                "issue": "High pool utilization",
                "recommendation": f"Consider increasing pool_size from {health_metrics.pool_size} to {health_metrics.pool_size + 5}",
                "current_value": health_metrics.pool_size,
                "suggested_value": health_metrics.pool_size + 5
            })
        
        if health_metrics.pool_overflow > 0:
            recommendations.append({
                "category": "connection_pool",
                "priority": "medium",
                "issue": "Overflow connections in use",
                "recommendation": "Consider increasing pool_size to avoid overflow connections",
                "current_value": db_manager.postgres_config.max_overflow,
                "suggested_value": db_manager.postgres_config.max_overflow + 5
            })
        
        # Analyze query performance
        if health_metrics.avg_query_time > 1.0:  # More than 1 second average
            recommendations.append({
                "category": "performance",
                "priority": "high",
                "issue": "Slow average query time",
                "recommendation": "Consider adding database indexes or optimizing queries",
                "current_value": f"{health_metrics.avg_query_time:.3f}s",
                "suggested_value": "< 0.1s"
            })
        
        # Analyze system resources
        if health_status["system"]["memory_usage"] > 85:
            recommendations.append({
                "category": "system",
                "priority": "high",
                "issue": "High memory usage",
                "recommendation": "Consider reducing pool_size or upgrading system memory",
                "current_value": f"{health_status['system']['memory_usage']}%",
                "suggested_value": "< 80%"
            })
        
        if health_status["system"]["cpu_usage"] > 80:
            recommendations.append({
                "category": "system",
                "priority": "medium",
                "issue": "High CPU usage",
                "recommendation": "Consider optimizing queries or scaling horizontally",
                "current_value": f"{health_status['system']['cpu_usage']}%",
                "suggested_value": "< 70%"
            })
        
        # Check error rate
        if health_metrics.error_count > 10:
            recommendations.append({
                "category": "reliability",
                "priority": "high",
                "issue": "High error count",
                "recommendation": "Investigate recent errors and consider connection retry settings",
                "current_value": health_metrics.error_count,
                "suggested_value": "< 5"
            })
        
        return {
            "analysis_timestamp": health_metrics.last_check.isoformat(),
            "overall_health": "good" if len(recommendations) == 0 else "needs_attention",
            "recommendations": recommendations,
            "summary": {
                "total_recommendations": len(recommendations),
                "high_priority": len([r for r in recommendations if r["priority"] == "high"]),
                "medium_priority": len([r for r in recommendations if r["priority"] == "medium"]),
                "low_priority": len([r for r in recommendations if r["priority"] == "low"])
            }
        }
        
    except Exception as e:
        logger.error(f"Database optimization analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization analysis failed: {str(e)}"
        )

def _generate_health_recommendations(health_status: Dict[str, Any]) -> List[str]:
    """Generate health recommendations based on status"""
    recommendations = []
    
    if health_status["postgres"]["avg_query_time"] > 0.5:
        recommendations.append("Consider adding database indexes to improve query performance")
    
    pool_utilization = (
        health_status["postgres"]["checked_out"] / 
        max(health_status["postgres"]["pool_size"], 1)
    ) * 100
    
    if pool_utilization > 80:
        recommendations.append("Connection pool utilization is high - consider increasing pool size")
    
    if health_status["system"]["memory_usage"] > 85:
        recommendations.append("System memory usage is high - monitor for potential issues")
    
    if health_status["metrics"]["error_count"] > 5:
        recommendations.append("Error count is elevated - check recent error logs")
    
    if not recommendations:
        recommendations.append("Database health looks good - no immediate action required")
    
    return recommendations

def _generate_pool_recommendations(health_metrics: HealthMetrics, pool_utilization: float) -> List[str]:
    """Generate connection pool recommendations"""
    recommendations = []
    
    if pool_utilization > 90:
        recommendations.append("Pool utilization is very high - increase pool_size")
    elif pool_utilization > 75:
        recommendations.append("Pool utilization is high - monitor closely")
    
    if health_metrics.pool_overflow > 0:
        recommendations.append("Overflow connections in use - consider increasing pool_size")
    
    if health_metrics.error_count > 0:
        recommendations.append("Recent connection errors detected - check logs")
    
    if not recommendations:
        recommendations.append("Connection pool is operating normally")
    
    return recommendations