"""
Database Health API
Provides endpoints for database health monitoring and diagnostics
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime
from database_manager import get_database_manager
from src.core.database_health import get_database_health_monitor

router = APIRouter()

@router.get("/database/health")
async def get_database_health():
    """
    Get comprehensive database health report
    
    Returns detailed health metrics including:
    - Connection pool status
    - Query performance
    - Replication status
    - Cache performance
    - Lock statistics
    - Transaction health
    """
    try:
        db_manager = get_database_manager()
        if not db_manager or not db_manager.is_initialized:
            return {
                "status": "error",
                "message": "Database not initialized",
                "timestamp": datetime.now().isoformat()
            }
        
        health_monitor = get_database_health_monitor(db_manager)
        health_report = await health_monitor.check_health()
        
        return {
            "status": "success",
            "data": health_report.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.get("/database/stats")
async def get_database_stats():
    """
    Get database connection pool statistics
    
    Returns:
    - Pool size and usage
    - Query execution stats
    - Connection errors
    """
    try:
        db_manager = get_database_manager()
        if not db_manager or not db_manager.is_initialized:
            return {
                "status": "error",
                "message": "Database not initialized",
                "timestamp": datetime.now().isoformat()
            }
        
        stats = await db_manager.get_pool_stats()
        
        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@router.post("/database/optimize")
async def optimize_database():
    """
    Run database optimization tasks
    
    Performs:
    - Table statistics update (ANALYZE)
    - Query statistics reset
    """
    try:
        db_manager = get_database_manager()
        if not db_manager or not db_manager.is_initialized:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        await db_manager.optimize_performance()
        
        return {
            "status": "success",
            "message": "Database optimization completed",
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")

@router.get("/database/slow-queries")
async def get_slow_queries():
    """
    Get slow query statistics
    
    Returns queries that exceed performance thresholds
    """
    try:
        db_manager = get_database_manager()
        if not db_manager or not db_manager.is_initialized:
            return {
                "status": "error",
                "message": "Database not initialized",
                "queries": []
            }
        
        async with db_manager.get_connection() as conn:
            # Get slow queries from pg_stat_statements
            slow_queries = await conn.fetch("""
                SELECT 
                    query,
                    calls,
                    mean_exec_time as avg_time_ms,
                    max_exec_time as max_time_ms,
                    total_exec_time as total_time_ms,
                    rows
                FROM pg_stat_statements
                WHERE mean_exec_time > 100  -- queries averaging > 100ms
                ORDER BY mean_exec_time DESC
                LIMIT 20
            """)
            
            queries = [dict(q) for q in slow_queries]
            
            return {
                "status": "success",
                "data": {
                    "queries": queries,
                    "count": len(queries)
                },
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        # pg_stat_statements might not be available
        return {
            "status": "error",
            "message": "Query statistics not available",
            "data": {"queries": [], "count": 0},
            "timestamp": datetime.now().isoformat()
        }

@router.get("/database/connections")
async def get_connection_info():
    """
    Get active database connections information
    
    Returns details about current database connections
    """
    try:
        db_manager = get_database_manager()
        if not db_manager or not db_manager.is_initialized:
            return {
                "status": "error",
                "message": "Database not initialized"
            }
        
        async with db_manager.get_connection() as conn:
            # Get connection information
            connections = await conn.fetch("""
                SELECT 
                    pid,
                    usename,
                    application_name,
                    client_addr,
                    state,
                    query_start,
                    state_change,
                    wait_event_type,
                    wait_event
                FROM pg_stat_activity
                WHERE state != 'idle'
                ORDER BY query_start DESC
            """)
            
            connection_list = [dict(c) for c in connections]
            
            # Convert timestamps to ISO format
            for conn_info in connection_list:
                if conn_info.get('query_start'):
                    conn_info['query_start'] = conn_info['query_start'].isoformat()
                if conn_info.get('state_change'):
                    conn_info['state_change'] = conn_info['state_change'].isoformat()
            
            return {
                "status": "success",
                "data": {
                    "connections": connection_list,
                    "active_count": len(connection_list)
                },
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get connections: {str(e)}") 