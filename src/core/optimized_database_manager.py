"""
Optimized Database Manager
Production-ready database management with connection pooling, health monitoring, and automatic recovery
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, AsyncGenerator, List
from dataclasses import dataclass, field
from urllib.parse import urlparse
import os

import redis.asyncio as redis
from sqlalchemy import create_engine, text, event, MetaData, pool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool, StaticPool
from sqlalchemy.exc import DisconnectionError, OperationalError, TimeoutError as SQLTimeoutError
from prometheus_client import Counter, Histogram, Gauge
import psutil

logger = logging.getLogger(__name__)

# Prometheus metrics
DB_CONNECTIONS_TOTAL = Counter('db_connections_total', 'Total database connections', ['db_type', 'status'])
DB_QUERY_DURATION = Histogram('db_query_duration_seconds', 'Database query duration', ['db_type', 'operation'])
DB_ACTIVE_CONNECTIONS = Gauge('db_active_connections', 'Active database connections', ['db_type'])
DB_POOL_SIZE = Gauge('db_pool_size', 'Database connection pool size', ['db_type'])
DB_HEALTH_STATUS = Gauge('db_health_status', 'Database health status (1=healthy, 0=unhealthy)', ['db_type'])

# Base model
Base = declarative_base()

@dataclass
class DatabaseConfig:
    """Database configuration"""
    database_url: str
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    echo: bool = False
    connect_timeout: int = 10
    query_timeout: int = 30
    health_check_interval: int = 60
    max_retries: int = 3
    retry_delay: float = 1.0

@dataclass  
class RedisConfig:
    """Redis configuration"""
    url: str
    max_connections: int = 10
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    max_retries: int = 3

@dataclass
class HealthMetrics:
    """Database health metrics"""
    is_healthy: bool
    last_check: datetime
    connection_count: int
    active_connections: int
    pool_size: int
    pool_checked_out: int
    pool_overflow: int
    avg_query_time: float
    error_count: int
    uptime: timedelta
    errors: List[str] = field(default_factory=list)

class DatabaseHealthMonitor:
    """Database health monitoring with detailed metrics"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.start_time = datetime.now()
        self.error_count = 0
        self.recent_errors = []
        self.query_times = []
        self.last_health_check = None
        self.is_monitoring = False
        
    async def start_monitoring(self):
        """Start health monitoring loop"""
        self.is_monitoring = True
        asyncio.create_task(self._monitoring_loop())
        
    async def stop_monitoring(self):
        """Stop health monitoring"""
        self.is_monitoring = False
        
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.db_manager.postgres_config.health_check_interval)
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(30)  # Shorter interval on error
                
    async def _perform_health_check(self):
        """Perform comprehensive health check"""
        try:
            start_time = time.time()
            
            # Test PostgreSQL connection
            postgres_healthy = await self._test_postgres_connection()
            
            # Test Redis connection  
            redis_healthy = await self._test_redis_connection()
            
            # Calculate metrics
            check_duration = time.time() - start_time
            self.last_health_check = datetime.now()
            
            # Update Prometheus metrics
            DB_HEALTH_STATUS.labels(db_type='postgresql').set(1 if postgres_healthy else 0)
            DB_HEALTH_STATUS.labels(db_type='redis').set(1 if redis_healthy else 0)
            
            # Log health status
            if postgres_healthy and redis_healthy:
                logger.debug(f"Database health check passed ({check_duration:.3f}s)")
            else:
                logger.warning(f"Database health check failed - PostgreSQL: {postgres_healthy}, Redis: {redis_healthy}")
                
        except Exception as e:
            self.error_count += 1
            self.recent_errors.append(f"{datetime.now()}: {str(e)}")
            self.recent_errors = self.recent_errors[-10:]  # Keep last 10 errors
            logger.error(f"Health check failed: {e}")
            
    async def _test_postgres_connection(self) -> bool:
        """Test PostgreSQL connection"""
        try:
            if self.db_manager.async_session_maker:
                async with self.db_manager.async_session_maker() as session:
                    result = await session.execute(text("SELECT 1"))
                    await result.fetchone()
                return True
            elif self.db_manager.engine:
                with self.db_manager.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                return True
            return False
        except Exception as e:
            logger.warning(f"PostgreSQL health check failed: {e}")
            return False
            
    async def _test_redis_connection(self) -> bool:
        """Test Redis connection"""
        try:
            if self.db_manager.redis_client:
                await self.db_manager.redis_client.ping()
                return True
            return False
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            return False
            
    def get_health_metrics(self) -> HealthMetrics:
        """Get current health metrics"""
        try:
            # Get pool metrics
            pool_metrics = self._get_pool_metrics()
            
            # Calculate average query time
            avg_query_time = sum(self.query_times[-100:]) / len(self.query_times[-100:]) if self.query_times else 0
            
            return HealthMetrics(
                is_healthy=self.last_health_check is not None and 
                          (datetime.now() - self.last_health_check).seconds < 120,
                last_check=self.last_health_check or datetime.now(),
                connection_count=pool_metrics.get('size', 0),
                active_connections=pool_metrics.get('checked_out', 0),
                pool_size=pool_metrics.get('pool_size', 0),
                pool_checked_out=pool_metrics.get('checked_out', 0),
                pool_overflow=pool_metrics.get('overflow', 0),
                avg_query_time=avg_query_time,
                error_count=self.error_count,
                uptime=datetime.now() - self.start_time,
                errors=self.recent_errors.copy()
            )
        except Exception as e:
            logger.error(f"Failed to get health metrics: {e}")
            return HealthMetrics(
                is_healthy=False,
                last_check=datetime.now(),
                connection_count=0,
                active_connections=0,
                pool_size=0,
                pool_checked_out=0,
                pool_overflow=0,
                avg_query_time=0,
                error_count=self.error_count,
                uptime=datetime.now() - self.start_time,
                errors=self.recent_errors.copy()
            )
            
    def _get_pool_metrics(self) -> Dict[str, int]:
        """Get connection pool metrics"""
        try:
            if self.db_manager.engine and hasattr(self.db_manager.engine.pool, 'size'):
                pool = self.db_manager.engine.pool
                return {
                    'size': pool.size(),
                    'checked_out': pool.checkedout(),
                    'overflow': pool.overflow(),
                    'pool_size': getattr(pool, '_pool_size', 0)
                }
        except Exception as e:
            logger.debug(f"Could not get pool metrics: {e}")
        return {}
        
    def record_query_time(self, duration: float):
        """Record query execution time"""
        self.query_times.append(duration)
        if len(self.query_times) > 1000:  # Keep last 1000 query times
            self.query_times = self.query_times[-1000:]

class OptimizedDatabaseManager:
    """Optimized database manager with advanced features"""
    
    def __init__(self, postgres_config: DatabaseConfig, redis_config: Optional[RedisConfig] = None):
        self.postgres_config = postgres_config
        self.redis_config = redis_config
        
        # Connection objects
        self.engine = None
        self.async_engine = None
        self.session_maker = None
        self.async_session_maker = None
        self.redis_client = None
        
        # Health monitoring
        self.health_monitor = DatabaseHealthMonitor(self)
        
        # Initialize connections
        self._setup_postgres()
        if redis_config:
            asyncio.create_task(self._setup_redis())
            
    def _setup_postgres(self):
        """Setup PostgreSQL connection with optimized settings"""
        try:
            logger.info("Setting up optimized PostgreSQL connection...")
            
            # Parse database URL
            url_parts = urlparse(self.postgres_config.database_url)
            
            if url_parts.scheme in ['sqlite', 'sqlite3']:
                # SQLite configuration for development
                self.engine = create_engine(
                    self.postgres_config.database_url,
                    poolclass=StaticPool,
                    connect_args={
                        "check_same_thread": False,
                        "timeout": self.postgres_config.connect_timeout
                    },
                    echo=self.postgres_config.echo
                )
                logger.info("Configured SQLite database for development")
                
            else:
                # PostgreSQL configuration for production
                connect_args = {}
                
                # SSL configuration for production
                if url_parts.scheme.startswith('postgresql') and os.getenv('DATABASE_SSL', 'false').lower() == 'true':
                    connect_args.update({
                        'sslmode': 'require',
                        'sslcert': os.getenv('DATABASE_SSL_CERT'),
                        'sslkey': os.getenv('DATABASE_SSL_KEY'),
                        'sslrootcert': os.getenv('DATABASE_SSL_CA')
                    })
                
                # Create engine with optimized settings
                self.engine = create_engine(
                    self.postgres_config.database_url,
                    poolclass=QueuePool,
                    pool_size=self.postgres_config.pool_size,
                    max_overflow=self.postgres_config.max_overflow,
                    pool_timeout=self.postgres_config.pool_timeout,
                    pool_recycle=self.postgres_config.pool_recycle,
                    pool_pre_ping=self.postgres_config.pool_pre_ping,
                    connect_args=connect_args,
                    echo=self.postgres_config.echo,
                    # Additional optimizations
                    isolation_level="READ_COMMITTED",
                    future=True
                )
                
                # Setup async engine
                if url_parts.scheme == 'postgresql':
                    async_url = self.postgres_config.database_url.replace('postgresql://', 'postgresql+asyncpg://')
                    self.async_engine = create_async_engine(
                        async_url,
                        pool_size=self.postgres_config.pool_size,
                        max_overflow=self.postgres_config.max_overflow,
                        pool_timeout=self.postgres_config.pool_timeout,
                        pool_recycle=self.postgres_config.pool_recycle,
                        pool_pre_ping=self.postgres_config.pool_pre_ping,
                        echo=self.postgres_config.echo
                    )
                    self.async_session_maker = async_sessionmaker(
                        self.async_engine,
                        class_=AsyncSession,
                        expire_on_commit=False
                    )
                
                logger.info(f"Configured PostgreSQL with pool_size={self.postgres_config.pool_size}, max_overflow={self.postgres_config.max_overflow}")
            
            # Create session maker
            self.session_maker = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            
            # Setup connection event listeners for monitoring
            self._setup_connection_listeners()
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info("✅ PostgreSQL connection established successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup PostgreSQL: {e}")
            raise
            
    async def _setup_redis(self):
        """Setup Redis connection with optimized settings"""
        try:
            logger.info("Setting up optimized Redis connection...")
            
            # Create Redis client with connection pooling
            self.redis_client = redis.from_url(
                self.redis_config.url,
                max_connections=self.redis_config.max_connections,
                socket_timeout=self.redis_config.socket_timeout,
                socket_connect_timeout=self.redis_config.socket_connect_timeout,
                retry_on_timeout=self.redis_config.retry_on_timeout,
                decode_responses=True,
                health_check_interval=self.redis_config.health_check_interval
            )
            
            # Test connection
            await self.redis_client.ping()
            
            logger.info("✅ Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup Redis: {e}")
            self.redis_client = None
            
    def _setup_connection_listeners(self):
        """Setup SQLAlchemy event listeners for monitoring"""
        
        @event.listens_for(self.engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """Handle new connections"""
            DB_CONNECTIONS_TOTAL.labels(db_type='postgresql', status='connect').inc()
            DB_ACTIVE_CONNECTIONS.labels(db_type='postgresql').inc()
            
        @event.listens_for(self.engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            """Handle connection checkout from pool"""
            DB_CONNECTIONS_TOTAL.labels(db_type='postgresql', status='checkout').inc()
            
        @event.listens_for(self.engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            """Handle connection checkin to pool"""
            DB_CONNECTIONS_TOTAL.labels(db_type='postgresql', status='checkin').inc()
            
        @event.listens_for(self.engine, "close")
        def on_close(dbapi_connection, connection_record):
            """Handle connection close"""
            DB_CONNECTIONS_TOTAL.labels(db_type='postgresql', status='close').inc()
            DB_ACTIVE_CONNECTIONS.labels(db_type='postgresql').dec()
            
        @event.listens_for(self.engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Record query start time"""
            context._query_start_time = time.time()
            
        @event.listens_for(self.engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Record query completion and duration"""
            if hasattr(context, '_query_start_time'):
                duration = time.time() - context._query_start_time
                DB_QUERY_DURATION.labels(db_type='postgresql', operation='query').observe(duration)
                self.health_monitor.record_query_time(duration)
    
    @contextmanager
    def get_session(self):
        """Get synchronous database session with automatic cleanup"""
        if not self.session_maker:
            raise RuntimeError("Database not initialized")
            
        session = self.session_maker()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
            
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get asynchronous database session with automatic cleanup"""
        if not self.async_session_maker:
            raise RuntimeError("Async database not initialized")
            
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Async database session error: {e}")
                raise
                
    async def execute_with_retry(self, operation, max_retries: Optional[int] = None):
        """Execute database operation with automatic retry"""
        max_retries = max_retries or self.postgres_config.max_retries
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return await operation()
            except (DisconnectionError, OperationalError, SQLTimeoutError) as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = self.postgres_config.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Database operation failed after {max_retries + 1} attempts")
                    
        raise last_exception
        
    async def create_tables(self):
        """Create all database tables"""
        try:
            if self.async_engine:
                async with self.async_engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
            elif self.engine:
                Base.metadata.create_all(bind=self.engine)
            else:
                raise RuntimeError("No database engine available")
                
            logger.info("✅ Database tables created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
            raise
            
    async def start_health_monitoring(self):
        """Start health monitoring"""
        await self.health_monitor.start_monitoring()
        logger.info("🏥 Database health monitoring started")
        
    async def stop_health_monitoring(self):
        """Stop health monitoring"""
        await self.health_monitor.stop_monitoring()
        
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        health_metrics = self.health_monitor.get_health_metrics()
        
        return {
            "status": "healthy" if health_metrics.is_healthy else "unhealthy",
            "last_check": health_metrics.last_check.isoformat(),
            "uptime": str(health_metrics.uptime),
            "postgres": {
                "connected": self.engine is not None,
                "pool_size": health_metrics.pool_size,
                "active_connections": health_metrics.active_connections,
                "checked_out": health_metrics.pool_checked_out,
                "overflow": health_metrics.pool_overflow,
                "avg_query_time": health_metrics.avg_query_time
            },
            "redis": {
                "connected": self.redis_client is not None,
                "pool_size": self.redis_config.max_connections if self.redis_config else 0
            },
            "metrics": {
                "error_count": health_metrics.error_count,
                "recent_errors": health_metrics.errors[-5:]  # Last 5 errors
            },
            "system": {
                "memory_usage": psutil.virtual_memory().percent,
                "cpu_usage": psutil.cpu_percent()
            }
        }
        
    async def close(self):
        """Close all database connections"""
        try:
            await self.stop_health_monitoring()
            
            if self.redis_client:
                await self.redis_client.close()
                logger.info("Redis connection closed")
                
            if self.async_engine:
                await self.async_engine.dispose()
                logger.info("Async PostgreSQL engine disposed")
                
            if self.engine:
                self.engine.dispose()
                logger.info("PostgreSQL engine disposed")
                
            logger.info("✅ All database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")

# Factory function for creating optimized database manager
def create_optimized_db_manager() -> OptimizedDatabaseManager:
    """Create optimized database manager with environment-based configuration"""
    
    # PostgreSQL configuration
    database_url = os.getenv("DATABASE_URL", "sqlite:///./trading_system.db")
    
    postgres_config = DatabaseConfig(
        database_url=database_url,
        pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
        pool_pre_ping=os.getenv("DB_POOL_PRE_PING", "true").lower() == "true",
        echo=os.getenv("DB_ECHO", "false").lower() == "true",
        connect_timeout=int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
        query_timeout=int(os.getenv("DB_QUERY_TIMEOUT", "30")),
        health_check_interval=int(os.getenv("DB_HEALTH_CHECK_INTERVAL", "60")),
        max_retries=int(os.getenv("DB_MAX_RETRIES", "3"))
    )
    
    # Redis configuration
    redis_config = None
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        redis_config = RedisConfig(
            url=redis_url,
            max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "10")),
            socket_timeout=int(os.getenv("REDIS_SOCKET_TIMEOUT", "5")),
            socket_connect_timeout=int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5")),
            health_check_interval=int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30")),
            max_retries=int(os.getenv("REDIS_MAX_RETRIES", "3"))
        )
    
    return OptimizedDatabaseManager(postgres_config, redis_config)

# Global instance for FastAPI dependency injection
_db_manager: Optional[OptimizedDatabaseManager] = None

def get_db_manager() -> OptimizedDatabaseManager:
    """Get or create global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = create_optimized_db_manager()
    return _db_manager

def get_db():
    """FastAPI dependency for getting database session"""
    db_manager = get_db_manager()
    with db_manager.get_session() as session:
        yield session

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting async database session"""
    db_manager = get_db_manager()
    async with db_manager.get_async_session() as session:
        yield session 