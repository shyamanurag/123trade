"""
Database Health Monitoring System
Provides comprehensive health checks, performance monitoring, and alerting
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import asyncpg
from enum import Enum

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

@dataclass
class HealthMetric:
    """Individual health metric"""
    name: str
    value: Any
    status: HealthStatus
    message: str
    timestamp: datetime
    
@dataclass
class HealthReport:
    """Complete health report"""
    overall_status: HealthStatus
    metrics: List[HealthMetric]
    timestamp: datetime
    duration_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "overall_status": self.overall_status.value,
            "metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "status": m.status.value,
                    "message": m.message,
                    "timestamp": m.timestamp.isoformat()
                }
                for m in self.metrics
            ],
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms
        }

class DatabaseHealthMonitor:
    """Monitors database health and performance"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.thresholds = {
            "connection_pool_usage": 0.8,  # 80% pool usage warning
            "query_time_ms": 1000,  # 1 second slow query
            "active_connections": 50,  # Max active connections warning
            "database_size_gb": 10,  # Database size warning
            "replication_lag_seconds": 5,  # Replication lag warning
            "cache_hit_ratio": 0.9,  # Cache hit ratio threshold
            "deadlock_count": 5,  # Deadlock count warning
            "transaction_rollback_ratio": 0.1  # 10% rollback ratio warning
        }
        
    async def check_health(self) -> HealthReport:
        """Perform comprehensive health check"""
        start_time = datetime.now()
        metrics = []
        
        # Run all health checks
        checks = [
            self._check_connectivity(),
            self._check_connection_pool(),
            self._check_query_performance(),
            self._check_database_size(),
            self._check_replication_status(),
            self._check_cache_performance(),
            self._check_locks_and_deadlocks(),
            self._check_transaction_health(),
            self._check_index_health(),
            self._check_table_bloat()
        ]
        
        # Execute all checks concurrently
        results = await asyncio.gather(*checks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Health check failed: {result}")
                metrics.append(HealthMetric(
                    name="error",
                    value=str(result),
                    status=HealthStatus.CRITICAL,
                    message=f"Health check error: {result}",
                    timestamp=datetime.now()
                ))
            elif isinstance(result, HealthMetric):
                metrics.append(result)
            elif isinstance(result, list):
                metrics.extend(result)
        
        # Determine overall status
        overall_status = self._calculate_overall_status(metrics)
        
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return HealthReport(
            overall_status=overall_status,
            metrics=metrics,
            timestamp=datetime.now(),
            duration_ms=duration_ms
        )
    
    async def _check_connectivity(self) -> HealthMetric:
        """Check basic database connectivity"""
        try:
            async with self.db_manager.get_connection() as conn:
                result = await conn.fetchval("SELECT 1")
                if result == 1:
                    return HealthMetric(
                        name="connectivity",
                        value=True,
                        status=HealthStatus.HEALTHY,
                        message="Database connection successful",
                        timestamp=datetime.now()
                    )
                else:
                    return HealthMetric(
                        name="connectivity",
                        value=False,
                        status=HealthStatus.CRITICAL,
                        message="Database returned unexpected result",
                        timestamp=datetime.now()
                    )
        except Exception as e:
            return HealthMetric(
                name="connectivity",
                value=False,
                status=HealthStatus.CRITICAL,
                message=f"Database connection failed: {e}",
                timestamp=datetime.now()
            )
    
    async def _check_connection_pool(self) -> HealthMetric:
        """Check connection pool health"""
        try:
            stats = await self.db_manager.get_pool_stats()
            pool_usage = stats['active_connections'] / stats['max_connections']
            
            if pool_usage > self.thresholds['connection_pool_usage']:
                status = HealthStatus.WARNING
                message = f"High connection pool usage: {pool_usage:.1%}"
            else:
                status = HealthStatus.HEALTHY
                message = f"Connection pool healthy: {stats['active_connections']}/{stats['max_connections']} connections"
            
            return HealthMetric(
                name="connection_pool",
                value={
                    "usage_percent": pool_usage * 100,
                    "active": stats['active_connections'],
                    "max": stats['max_connections']
                },
                status=status,
                message=message,
                timestamp=datetime.now()
            )
        except Exception as e:
            return HealthMetric(
                name="connection_pool",
                value=None,
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check connection pool: {e}",
                timestamp=datetime.now()
            )
    
    async def _check_query_performance(self) -> HealthMetric:
        """Check query performance metrics"""
        try:
            async with self.db_manager.get_connection() as conn:
                # Get slow query statistics
                slow_queries = await conn.fetch("""
                    SELECT query, calls, mean_exec_time, max_exec_time
                    FROM pg_stat_statements
                    WHERE mean_exec_time > $1
                    ORDER BY mean_exec_time DESC
                    LIMIT 5
                """, self.thresholds['query_time_ms'])
                
                if slow_queries:
                    status = HealthStatus.WARNING
                    message = f"Found {len(slow_queries)} slow queries"
                else:
                    status = HealthStatus.HEALTHY
                    message = "Query performance is good"
                
                return HealthMetric(
                    name="query_performance",
                    value={
                        "slow_query_count": len(slow_queries),
                        "threshold_ms": self.thresholds['query_time_ms']
                    },
                    status=status,
                    message=message,
                    timestamp=datetime.now()
                )
        except Exception as e:
            # pg_stat_statements might not be available
            return HealthMetric(
                name="query_performance",
                value=None,
                status=HealthStatus.UNKNOWN,
                message="Query performance stats not available",
                timestamp=datetime.now()
            )
    
    async def _check_database_size(self) -> HealthMetric:
        """Check database size"""
        try:
            async with self.db_manager.get_connection() as conn:
                size_bytes = await conn.fetchval(
                    "SELECT pg_database_size(current_database())"
                )
                size_gb = size_bytes / (1024 ** 3)
                
                if size_gb > self.thresholds['database_size_gb']:
                    status = HealthStatus.WARNING
                    message = f"Database size is large: {size_gb:.2f} GB"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"Database size: {size_gb:.2f} GB"
                
                return HealthMetric(
                    name="database_size",
                    value={"size_gb": size_gb, "size_bytes": size_bytes},
                    status=status,
                    message=message,
                    timestamp=datetime.now()
                )
        except Exception as e:
            return HealthMetric(
                name="database_size",
                value=None,
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check database size: {e}",
                timestamp=datetime.now()
            )
    
    async def _check_replication_status(self) -> HealthMetric:
        """Check replication status and lag"""
        try:
            async with self.db_manager.get_connection() as conn:
                # Check if this is a replica
                is_replica = await conn.fetchval("SELECT pg_is_in_recovery()")
                
                if is_replica:
                    # Get replication lag
                    lag = await conn.fetchval("""
                        SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))
                    """)
                    
                    if lag and lag > self.thresholds['replication_lag_seconds']:
                        status = HealthStatus.WARNING
                        message = f"High replication lag: {lag:.1f} seconds"
                    else:
                        status = HealthStatus.HEALTHY
                        message = f"Replication lag: {lag:.1f} seconds"
                    
                    value = {"is_replica": True, "lag_seconds": lag}
                else:
                    status = HealthStatus.HEALTHY
                    message = "Primary database (no replication)"
                    value = {"is_replica": False}
                
                return HealthMetric(
                    name="replication",
                    value=value,
                    status=status,
                    message=message,
                    timestamp=datetime.now()
                )
        except Exception as e:
            return HealthMetric(
                name="replication",
                value=None,
                status=HealthStatus.UNKNOWN,
                message="Replication status unknown",
                timestamp=datetime.now()
            )
    
    async def _check_cache_performance(self) -> HealthMetric:
        """Check cache hit ratio"""
        try:
            async with self.db_manager.get_connection() as conn:
                cache_stats = await conn.fetchrow("""
                    SELECT 
                        sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as cache_hit_ratio
                    FROM pg_statio_user_tables
                """)
                
                hit_ratio = cache_stats['cache_hit_ratio'] or 0
                
                if hit_ratio < self.thresholds['cache_hit_ratio']:
                    status = HealthStatus.WARNING
                    message = f"Low cache hit ratio: {hit_ratio:.1%}"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"Good cache hit ratio: {hit_ratio:.1%}"
                
                return HealthMetric(
                    name="cache_performance",
                    value={"hit_ratio": hit_ratio},
                    status=status,
                    message=message,
                    timestamp=datetime.now()
                )
        except Exception as e:
            return HealthMetric(
                name="cache_performance",
                value=None,
                status=HealthStatus.UNKNOWN,
                message="Cache stats not available",
                timestamp=datetime.now()
            )
    
    async def _check_locks_and_deadlocks(self) -> List[HealthMetric]:
        """Check for locks and deadlocks"""
        metrics = []
        
        try:
            async with self.db_manager.get_connection() as conn:
                # Check active locks
                lock_count = await conn.fetchval("""
                    SELECT COUNT(*) 
                    FROM pg_locks 
                    WHERE NOT granted
                """)
                
                if lock_count > 0:
                    status = HealthStatus.WARNING
                    message = f"Found {lock_count} waiting locks"
                else:
                    status = HealthStatus.HEALTHY
                    message = "No waiting locks"
                
                metrics.append(HealthMetric(
                    name="locks",
                    value={"waiting_locks": lock_count},
                    status=status,
                    message=message,
                    timestamp=datetime.now()
                ))
                
                # Check deadlock count (from pg_stat_database)
                deadlocks = await conn.fetchval("""
                    SELECT deadlocks 
                    FROM pg_stat_database 
                    WHERE datname = current_database()
                """)
                
                if deadlocks > self.thresholds['deadlock_count']:
                    status = HealthStatus.WARNING
                    message = f"High deadlock count: {deadlocks}"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"Deadlock count: {deadlocks}"
                
                metrics.append(HealthMetric(
                    name="deadlocks",
                    value={"count": deadlocks},
                    status=status,
                    message=message,
                    timestamp=datetime.now()
                ))
                
        except Exception as e:
            metrics.append(HealthMetric(
                name="locks_and_deadlocks",
                value=None,
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check locks: {e}",
                timestamp=datetime.now()
            ))
        
        return metrics
    
    async def _check_transaction_health(self) -> HealthMetric:
        """Check transaction health"""
        try:
            async with self.db_manager.get_connection() as conn:
                stats = await conn.fetchrow("""
                    SELECT 
                        xact_commit,
                        xact_rollback,
                        CASE 
                            WHEN xact_commit + xact_rollback > 0 
                            THEN xact_rollback::float / (xact_commit + xact_rollback)
                            ELSE 0
                        END as rollback_ratio
                    FROM pg_stat_database 
                    WHERE datname = current_database()
                """)
                
                rollback_ratio = stats['rollback_ratio']
                
                if rollback_ratio > self.thresholds['transaction_rollback_ratio']:
                    status = HealthStatus.WARNING
                    message = f"High rollback ratio: {rollback_ratio:.1%}"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"Transaction health good, rollback ratio: {rollback_ratio:.1%}"
                
                return HealthMetric(
                    name="transactions",
                    value={
                        "commits": stats['xact_commit'],
                        "rollbacks": stats['xact_rollback'],
                        "rollback_ratio": rollback_ratio
                    },
                    status=status,
                    message=message,
                    timestamp=datetime.now()
                )
        except Exception as e:
            return HealthMetric(
                name="transactions",
                value=None,
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check transactions: {e}",
                timestamp=datetime.now()
            )
    
    async def _check_index_health(self) -> HealthMetric:
        """Check index health and usage"""
        try:
            async with self.db_manager.get_connection() as conn:
                # Find unused indexes
                unused_indexes = await conn.fetch("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_scan
                    FROM pg_stat_user_indexes
                    WHERE idx_scan = 0
                    AND indexrelname NOT LIKE '%_pkey'
                    LIMIT 5
                """)
                
                if unused_indexes:
                    status = HealthStatus.WARNING
                    message = f"Found {len(unused_indexes)} unused indexes"
                else:
                    status = HealthStatus.HEALTHY
                    message = "All indexes are being used"
                
                return HealthMetric(
                    name="index_health",
                    value={"unused_count": len(unused_indexes)},
                    status=status,
                    message=message,
                    timestamp=datetime.now()
                )
        except Exception as e:
            return HealthMetric(
                name="index_health",
                value=None,
                status=HealthStatus.UNKNOWN,
                message="Index stats not available",
                timestamp=datetime.now()
            )
    
    async def _check_table_bloat(self) -> HealthMetric:
        """Check for table bloat"""
        try:
            async with self.db_manager.get_connection() as conn:
                # Simple bloat check - tables with high dead tuple ratio
                bloated_tables = await conn.fetch("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_dead_tup,
                        n_live_tup,
                        CASE 
                            WHEN n_live_tup > 0 
                            THEN n_dead_tup::float / n_live_tup 
                            ELSE 0 
                        END as dead_ratio
                    FROM pg_stat_user_tables
                    WHERE n_dead_tup > 1000
                    AND n_live_tup > 0
                    AND n_dead_tup::float / n_live_tup > 0.1
                    LIMIT 5
                """)
                
                if bloated_tables:
                    status = HealthStatus.WARNING
                    message = f"Found {len(bloated_tables)} bloated tables"
                else:
                    status = HealthStatus.HEALTHY
                    message = "No significant table bloat detected"
                
                return HealthMetric(
                    name="table_bloat",
                    value={"bloated_count": len(bloated_tables)},
                    status=status,
                    message=message,
                    timestamp=datetime.now()
                )
        except Exception as e:
            return HealthMetric(
                name="table_bloat",
                value=None,
                status=HealthStatus.UNKNOWN,
                message="Bloat stats not available",
                timestamp=datetime.now()
            )
    
    def _calculate_overall_status(self, metrics: List[HealthMetric]) -> HealthStatus:
        """Calculate overall health status from individual metrics"""
        if not metrics:
            return HealthStatus.UNKNOWN
        
        # Count status levels
        status_counts = {
            HealthStatus.CRITICAL: 0,
            HealthStatus.WARNING: 0,
            HealthStatus.HEALTHY: 0,
            HealthStatus.UNKNOWN: 0
        }
        
        for metric in metrics:
            status_counts[metric.status] += 1
        
        # Determine overall status
        if status_counts[HealthStatus.CRITICAL] > 0:
            return HealthStatus.CRITICAL
        elif status_counts[HealthStatus.WARNING] > 2:
            return HealthStatus.CRITICAL
        elif status_counts[HealthStatus.WARNING] > 0:
            return HealthStatus.WARNING
        elif status_counts[HealthStatus.UNKNOWN] > len(metrics) / 2:
            return HealthStatus.UNKNOWN
        else:
            return HealthStatus.HEALTHY

# Create global instance
_health_monitor: Optional[DatabaseHealthMonitor] = None

def get_database_health_monitor(db_manager) -> DatabaseHealthMonitor:
    """Get or create database health monitor instance"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = DatabaseHealthMonitor(db_manager)
    return _health_monitor 