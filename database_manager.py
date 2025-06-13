"""
Database Connection Pooling Manager
Handles PostgreSQL connections with connection pooling, health monitoring, and performance optimization
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncContextManager
from contextlib import asynccontextmanager
import asyncpg
from asyncpg import Pool, Connection
from dataclasses import dataclass
import json
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    host: str
    port: int
    database: str
    username: str
    password: str
    
    # Connection pool settings - OPTIMIZED FOR DIGITALOCEAN
    min_connections: int = 2  # Reduced for better resource usage
    max_connections: int = 10  # Reduced for cloud deployment
    max_inactive_connection_lifetime: float = 120.0  # 2 minutes
    max_queries: int = 10000
    max_cached_statement_lifetime: int = 120
    
    # Performance settings - CLOUD OPTIMIZED
    command_timeout: int = 15  # Reduced from 30 to 15 seconds
    connect_timeout: int = 10  # Add connection timeout
    server_settings: Optional[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.server_settings is None:
            # Minimal settings for DigitalOcean managed PostgreSQL
            # Removed settings that require superuser privileges
            self.server_settings = {
                'jit': 'off',  # Disable JIT for faster query planning
                'statement_timeout': '15000',  # 15 second timeout
                'idle_in_transaction_session_timeout': '30000'  # 30 second idle timeout
            }

@dataclass
class ConnectionStats:
    """Connection pool statistics"""
    total_connections: int
    active_connections: int
    idle_connections: int
    queries_executed: int
    avg_query_time: float
    slow_queries: int
    connection_errors: int
    last_reset: datetime

class DatabaseManager:
    """Manages PostgreSQL connections with pooling and performance monitoring"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pool: Optional[Pool] = None
        self.is_initialized = False
        
        # Statistics tracking
        self.stats = ConnectionStats(
            total_connections=0,
            active_connections=0,
            idle_connections=0,
            queries_executed=0,
            avg_query_time=0.0,
            slow_queries=0,
            connection_errors=0,
            last_reset=datetime.now()
        )
        
        self.query_times = []
        self.slow_query_threshold = 1.0  # 1 second
        
    async def initialize(self) -> bool:
        """Initialize the database connection pool"""
        try:
            logger.info("Initializing database connection pool...")
            
            # Build connection string
            dsn = f"postgresql://{self.config.username}:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.database}"
            
            # Create connection pool with optimized settings
            self.pool = await asyncpg.create_pool(
                dsn,
                min_size=self.config.min_connections,
                max_size=self.config.max_connections,
                max_inactive_connection_lifetime=self.config.max_inactive_connection_lifetime,
                max_queries=self.config.max_queries,
                command_timeout=self.config.command_timeout,
                timeout=self.config.connect_timeout,
                server_settings=self.config.server_settings,
                init=self._init_connection
            )
            
            # Test connection
            async with self.pool.acquire() as conn:
                version = await conn.fetchval('SELECT version()')
                logger.info(f"✅ Database connected: {version[:50]}...")
                
                # Create necessary tables if they don't exist
                await self._create_tables(conn)
            
            self.is_initialized = True
            self.stats.total_connections = self.config.max_connections
            
            logger.info(f"✅ Database pool initialized with {self.config.min_connections}-{self.config.max_connections} connections")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            return False
    
    async def _init_connection(self, conn: Connection):
        """Initialize each new connection in the pool"""
        try:
            # Set connection-specific settings
            await conn.execute("SET timezone = 'UTC'")
            await conn.execute("SET search_path = public")
            
            # Enable query statistics
            await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
            
        except Exception as e:
            logger.warning(f"Connection initialization warning: {e}")
    
    async def _create_tables(self, conn: Connection):
        """Create necessary database tables"""
        try:
            # Users table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR(50) PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    email VARCHAR(150) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    full_name VARCHAR(200),
                    initial_capital DECIMAL(15,2) DEFAULT 50000,
                    current_balance DECIMAL(15,2) DEFAULT 50000,
                    risk_tolerance VARCHAR(20) DEFAULT 'medium',
                    is_active BOOLEAN DEFAULT true,
                    zerodha_client_id VARCHAR(50),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Positions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    position_id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) REFERENCES users(user_id),
                    symbol VARCHAR(20) NOT NULL,
                    quantity INTEGER NOT NULL,
                    entry_price DECIMAL(10,2) NOT NULL,
                    current_price DECIMAL(10,2),
                    entry_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    exit_time TIMESTAMP WITH TIME ZONE,
                    strategy VARCHAR(50),
                    status VARCHAR(20) DEFAULT 'open',
                    unrealized_pnl DECIMAL(12,2),
                    realized_pnl DECIMAL(12,2),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Trades table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) REFERENCES users(user_id),
                    symbol VARCHAR(20) NOT NULL,
                    trade_type VARCHAR(10) NOT NULL, -- 'buy' or 'sell'
                    quantity INTEGER NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    order_id VARCHAR(50),
                    strategy VARCHAR(50),
                    commission DECIMAL(8,2) DEFAULT 0,
                    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Market data table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    volume INTEGER,
                    high DECIMAL(10,2),
                    low DECIMAL(10,2),
                    open_price DECIMAL(10,2),
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Create indexes for performance
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_positions_user_id ON positions(user_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_user_id ON trades(user_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_executed_at ON trades(executed_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp)")
            
            logger.info("✅ Database tables created/verified")
            
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncContextManager[Connection]:
        """Get a database connection from the pool"""
        if not self.is_initialized:
            raise RuntimeError("Database manager not initialized")
        
        start_time = datetime.now()
        try:
            async with self.pool.acquire() as conn:
                self.stats.active_connections += 1
                yield conn
        except Exception as e:
            self.stats.connection_errors += 1
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            self.stats.active_connections = max(0, self.stats.active_connections - 1)
            
            # Track query time
            query_time = (datetime.now() - start_time).total_seconds()
            self.query_times.append(query_time)
            self.stats.queries_executed += 1
            
            if query_time > self.slow_query_threshold:
                self.stats.slow_queries += 1
            
            # Keep only last 1000 query times for average calculation
            if len(self.query_times) > 1000:
                self.query_times = self.query_times[-1000:]
            
            # Update average query time
            if self.query_times:
                self.stats.avg_query_time = sum(self.query_times) / len(self.query_times)
    
    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results"""
        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def execute_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute a query and return single result"""
        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None
    
    async def execute_scalar(self, query: str, *args) -> Any:
        """Execute a query and return single value"""
        async with self.get_connection() as conn:
            return await conn.fetchval(query, *args)
    
    async def execute_command(self, query: str, *args) -> str:
        """Execute INSERT/UPDATE/DELETE command"""
        async with self.get_connection() as conn:
            return await conn.execute(query, *args)
    
    async def execute_transaction(self, queries: List[tuple]) -> bool:
        """Execute multiple queries in a transaction"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                try:
                    for query, args in queries:
                        await conn.execute(query, *args)
                    return True
                except Exception as e:
                    logger.error(f"Transaction failed: {e}")
                    raise
    
    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        if not self.pool:
            return {'status': 'not_initialized'}
        
        pool_size = self.pool.get_size()
        idle_size = self.pool.get_idle_size()
        
        self.stats.total_connections = pool_size
        self.stats.idle_connections = idle_size
        
        return {
            'pool_size': pool_size,
            'idle_connections': idle_size,
            'active_connections': pool_size - idle_size,
            'max_connections': self.config.max_connections,
            'min_connections': self.config.min_connections,
            'queries_executed': self.stats.queries_executed,
            'avg_query_time_ms': round(self.stats.avg_query_time * 1000, 2),
            'slow_queries': self.stats.slow_queries,
            'connection_errors': self.stats.connection_errors,
            'uptime_hours': (datetime.now() - self.stats.last_reset).total_seconds() / 3600
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            start_time = datetime.now()
            
            async with self.get_connection() as conn:
                # Test basic connectivity
                await conn.fetchval('SELECT 1')
                
                # Check database size
                db_size = await conn.fetchval(
                    "SELECT pg_size_pretty(pg_database_size($1))",
                    self.config.database
                )
                
                # Check active connections
                active_conns = await conn.fetchval(
                    "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
                )
                
                response_time = (datetime.now() - start_time).total_seconds()
                
                return {
                    'status': 'healthy',
                    'response_time_ms': round(response_time * 1000, 2),
                    'database_size': db_size,
                    'active_connections': active_conns,
                    'pool_stats': await self.get_pool_stats()
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'response_time_ms': None
            }
    
    async def optimize_performance(self):
        """Run performance optimization tasks"""
        try:
            async with self.get_connection() as conn:
                # Update table statistics
                await conn.execute("ANALYZE")
                
                # Reset query statistics
                await conn.execute("SELECT pg_stat_statements_reset()")
                
                logger.info("Database performance optimization completed")
                
        except Exception as e:
            logger.error(f"Performance optimization failed: {e}")
    
    async def close(self):
        """Close the database connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            self.is_initialized = False
            logger.info("Database connection pool closed")

# Convenience functions for common operations
class DatabaseOperations:
    """High-level database operations for trading system"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def create_user(self, user_data: Dict[str, Any]) -> bool:
        """Create a new user"""
        try:
            query = """
                INSERT INTO users (user_id, username, email, password_hash, full_name, 
                                 initial_capital, risk_tolerance, zerodha_client_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """
            await self.db.execute_command(
                query,
                user_data['user_id'],
                user_data['username'],
                user_data['email'],
                user_data['password_hash'],
                user_data.get('full_name'),
                user_data.get('initial_capital', 50000),
                user_data.get('risk_tolerance', 'medium'),
                user_data.get('zerodha_client_id')
            )
            return True
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        query = "SELECT * FROM users WHERE user_id = $1"
        return await self.db.execute_one(query, user_id)
    
    async def get_user_positions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all positions for a user"""
        query = """
            SELECT * FROM positions 
            WHERE user_id = $1 AND status = 'open'
            ORDER BY entry_time DESC
        """
        return await self.db.execute_query(query, user_id)
    
    async def create_position(self, position_data: Dict[str, Any]) -> bool:
        """Create a new position"""
        try:
            query = """
                INSERT INTO positions (user_id, symbol, quantity, entry_price, 
                                     strategy, current_price, unrealized_pnl)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """
            await self.db.execute_command(
                query,
                position_data['user_id'],
                position_data['symbol'],
                position_data['quantity'],
                position_data['entry_price'],
                position_data.get('strategy'),
                position_data.get('current_price'),
                position_data.get('unrealized_pnl', 0)
            )
            return True
        except Exception as e:
            logger.error(f"Error creating position: {e}")
            return False
    
    async def update_position_pnl(self, position_id: int, current_price: float, unrealized_pnl: float) -> bool:
        """Update position P&L"""
        try:
            query = """
                UPDATE positions 
                SET current_price = $1, unrealized_pnl = $2, updated_at = NOW()
                WHERE position_id = $3
            """
            await self.db.execute_command(query, current_price, unrealized_pnl, position_id)
            return True
        except Exception as e:
            logger.error(f"Error updating position P&L: {e}")
            return False
    
    async def record_trade(self, trade_data: Dict[str, Any]) -> bool:
        """Record a trade execution"""
        try:
            query = """
                INSERT INTO trades (user_id, symbol, trade_type, quantity, 
                                  price, order_id, strategy, commission)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """
            await self.db.execute_command(
                query,
                trade_data['user_id'],
                trade_data['symbol'],
                trade_data['trade_type'],
                trade_data['quantity'],
                trade_data['price'],
                trade_data.get('order_id'),
                trade_data.get('strategy'),
                trade_data.get('commission', 0)
            )
            return True
        except Exception as e:
            logger.error(f"Error recording trade: {e}")
            return False
    
    async def get_user_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get user analytics for specified period"""
        try:
            # Get total P&L
            total_pnl_query = """
                SELECT COALESCE(SUM(realized_pnl), 0) as total_realized_pnl,
                       COALESCE(SUM(unrealized_pnl), 0) as total_unrealized_pnl
                FROM positions 
                WHERE user_id = $1
            """
            pnl_data = await self.db.execute_one(total_pnl_query, user_id)
            
            # Get trade statistics
            trade_stats_query = """
                SELECT COUNT(*) as total_trades,
                       COUNT(CASE WHEN trade_type = 'buy' THEN 1 END) as buy_trades,
                       COUNT(CASE WHEN trade_type = 'sell' THEN 1 END) as sell_trades,
                       AVG(price) as avg_price
                FROM trades 
                WHERE user_id = $1 AND executed_at >= NOW() - INTERVAL '%s days'
            """ % days
            trade_stats = await self.db.execute_one(trade_stats_query, user_id)
            
            # Get daily P&L for chart
            daily_pnl_query = """
                SELECT DATE(executed_at) as date,
                       SUM(CASE WHEN trade_type = 'sell' THEN quantity * price ELSE -quantity * price END) as daily_pnl
                FROM trades 
                WHERE user_id = $1 AND executed_at >= NOW() - INTERVAL '%s days'
                GROUP BY DATE(executed_at)
                ORDER BY date
            """ % days
            daily_pnl = await self.db.execute_query(daily_pnl_query, user_id)
            
            return {
                'total_realized_pnl': float(pnl_data['total_realized_pnl'] or 0),
                'total_unrealized_pnl': float(pnl_data['total_unrealized_pnl'] or 0),
                'total_trades': trade_stats['total_trades'] or 0,
                'buy_trades': trade_stats['buy_trades'] or 0,
                'sell_trades': trade_stats['sell_trades'] or 0,
                'avg_price': float(trade_stats['avg_price'] or 0),
                'daily_pnl': [
                    {
                        'date': row['date'].isoformat() if row['date'] else '',
                        'pnl': float(row['daily_pnl'] or 0)
                    }
                    for row in daily_pnl
                ]
            }
        except Exception as e:
            logger.error(f"Error getting user analytics: {e}")
            return {}

def get_database_config_from_env() -> DatabaseConfig:
    """Load database configuration from environment variables"""
    # First check if DATABASE_URL is provided (DigitalOcean style)
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        # Parse DATABASE_URL
        # DigitalOcean format: postgresql://doadmin:password@host:25060/defaultdb?sslmode=require
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(database_url)
        
        # Extract SSL mode from query parameters
        query_params = parse_qs(parsed.query)
        ssl_mode = query_params.get('sslmode', ['prefer'])[0]
        
        config = DatabaseConfig(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 25060,  # DigitalOcean default port
            database=parsed.path[1:] if parsed.path else 'defaultdb',  # Remove leading /
            username=parsed.username or 'doadmin',
            password=parsed.password or '',
            min_connections=int(os.getenv('DATABASE_POOL_SIZE', '3')),
            max_connections=int(os.getenv('DATABASE_MAX_OVERFLOW', '5')) + int(os.getenv('DATABASE_POOL_SIZE', '3')),
            command_timeout=int(os.getenv('DB_COMMAND_TIMEOUT', '15')),
            connect_timeout=int(os.getenv('DB_CONNECT_TIMEOUT', '10'))
        )
        
        # Add SSL configuration for DigitalOcean
        if ssl_mode in ['require', 'prefer']:
            config.server_settings = config.server_settings or {}
            config.server_settings.update({
                'sslmode': ssl_mode,
                'jit': 'off',
                'statement_timeout': '15000',
                'idle_in_transaction_session_timeout': '30000'
            })
        
        return config
    else:
        # Fall back to individual environment variables
        return DatabaseConfig(
            host=os.getenv('DATABASE_HOST', 'localhost'),
            port=int(os.getenv('DATABASE_PORT', '5432')),
            database=os.getenv('DATABASE_NAME', 'trading_system'),
            username=os.getenv('DATABASE_USER', 'trading_user'),
            password=os.getenv('DATABASE_PASSWORD', ''),
            min_connections=int(os.getenv('DB_MIN_CONNECTIONS', '2')),
            max_connections=int(os.getenv('DB_MAX_CONNECTIONS', '10')),
            command_timeout=int(os.getenv('DB_COMMAND_TIMEOUT', '15')),
            connect_timeout=int(os.getenv('DB_CONNECT_TIMEOUT', '10'))
        )

# Global database manager instance
database_manager: Optional[DatabaseManager] = None
database_operations: Optional[DatabaseOperations] = None

def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance"""
    return database_manager

def get_database_operations() -> DatabaseOperations:
    """Get the global database operations instance"""
    return database_operations

async def init_database_manager() -> DatabaseManager:
    """Initialize the global database manager"""
    global database_manager, database_operations
    
    config = get_database_config_from_env()
    database_manager = DatabaseManager(config)
    
    if await database_manager.initialize():
        database_operations = DatabaseOperations(database_manager)
        logger.info("✅ Database manager initialized successfully")
        return database_manager
    else:
        raise RuntimeError("Failed to initialize database manager") 