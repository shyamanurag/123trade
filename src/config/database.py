"""
Database configuration and connection management for the trading system.
"""
import os
import logging
from typing import Optional, AsyncGenerator
from urllib.parse import urlparse

import redis.asyncio as redis
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

# Import our precise schema manager
from src.core.database_schema_manager import DatabaseSchemaManager

logger = logging.getLogger(__name__)

# Check if we're in production environment
IS_PRODUCTION = os.getenv('ENVIRONMENT', '').lower() in ['production', 'prod', 'live']
IS_DEPLOYMENT = bool(os.getenv('DATABASE_URL'))  # If DATABASE_URL is set, we're in deployment

# Database Base Model
Base = declarative_base()
metadata = MetaData()

class DatabaseConfig:
    """Database configuration manager"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.postgres_engine = None
        self.async_session_maker = None
        
        # Environment variables - prioritize deployment vars
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        # Use PostgreSQL by default to match production (eliminates schema mismatches)
        default_db_url = 'postgresql://trading_user:trading_password@localhost:5432/trading_system'
        self.database_url = os.getenv('DATABASE_URL') or os.getenv('DB_URL', default_db_url)
        
        # Override with individual components if available (DigitalOcean style)
        if os.getenv('DATABASE_HOST') and not os.getenv('DATABASE_URL'):
            self.database_url = self._build_database_url_from_components()
        
        # Setup configurations
        self._setup_redis_config()
        self._setup_postgres_config()
        
        # Ensure database schema is correct
        self._ensure_precise_database_schema()
        
        # Warn about localhost in production
        if IS_PRODUCTION or IS_DEPLOYMENT:
            if "localhost" in self.redis_url:
                logger.warning("REDIS_URL contains localhost in production - consider updating")
            if "localhost" in self.database_url and not self.database_url.startswith('sqlite'):
                logger.warning("DATABASE_URL contains localhost in production - consider updating")
        else:
            # Development warnings
            if 'localhost' in self.redis_url:
                logger.debug("[DEV WARNING] REDIS_URL is set to localhost. This MUST be overridden in production!")
            if 'localhost' in self.database_url:
                logger.debug("[DEV WARNING] DATABASE_URL is set to localhost. This MUST be overridden in production!")

    def _build_database_url_from_components(self) -> str:
        """Build database URL from individual environment variables"""
        host = os.getenv('DATABASE_HOST', 'localhost')
        port = os.getenv('DATABASE_PORT', '5432')
        name = os.getenv('DATABASE_NAME', 'trading_system')
        user = os.getenv('DATABASE_USER', 'user')
        password = os.getenv('DATABASE_PASSWORD', 'password')
        ssl_mode = os.getenv('DATABASE_SSL', 'prefer')
        
        url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
        if ssl_mode:
            url += f"?sslmode={ssl_mode}"
        
        logger.info(f"Built database URL from components: postgresql://{user}:***@{host}:{port}/{name}")
        return url

    def _ensure_precise_database_schema(self):
        """Ensure database has the precise schema required - this is not a workaround, this is the correct approach"""
        try:
            # Only run schema management for actual databases, not during imports
            if self.postgres_engine is None:
                return
                
            schema_manager = DatabaseSchemaManager(self.database_url)
            result = schema_manager.ensure_precise_schema()
            
            if result['status'] == 'success':
                logger.info("Database schema verified - all tables have precise structure")
                if result.get('actions'):
                    for action in result['actions']:
                        logger.info(f"Schema action: {action}")
            else:
                logger.error(f"Database schema verification failed: {result.get('errors', [])}")
                
        except Exception as e:
            logger.error(f"Error ensuring database schema: {e}")
            # Don't fail initialization - the system can still work with partial schema

    def _setup_redis_config(self):
        """Setup Redis connection configuration"""
        try:
            parsed = urlparse(self.redis_url)
            
            # Check if SSL is required (DigitalOcean Redis)
            ssl_required = 'ondigitalocean.com' in self.redis_url or self.redis_url.startswith('rediss://')
            
            self.redis_config = {
                'host': parsed.hostname or 'localhost',
                'port': parsed.port or 6379,
                'password': parsed.password,
                'db': int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0,
                'decode_responses': True,
                'socket_timeout': 10,
                'socket_connect_timeout': 10,
                'retry_on_timeout': True,
                'health_check_interval': 30,
                'ssl': ssl_required,
                'ssl_cert_reqs': None if ssl_required else 'required',
                'ssl_check_hostname': False if ssl_required else True,
                'ssl_ca_certs': None,
                'ssl_keyfile': None,
                'ssl_certfile': None
            }
            
            logger.info(f"Redis configured for: {self.redis_config['host']}:{self.redis_config['port']} (SSL: {ssl_required})")
        except Exception as e:
            logger.error(f"Error parsing Redis URL: {e}")
            self.redis_config = {
                'host': 'localhost',
                'port': 6379,
                'decode_responses': True
            }
    
    def _setup_postgres_config(self):
        """Setup PostgreSQL connection configuration"""
        try:
            if self.database_url.startswith('sqlite'):
                # Development SQLite
                self.postgres_engine = create_engine(
                    self.database_url,
                    poolclass=StaticPool,
                    connect_args={"check_same_thread": False}
                )
                logger.info("Using SQLite database for development")
            else:
                # Production PostgreSQL - add SSL requirements for DigitalOcean
                connect_args = {}
                if 'ondigitalocean.com' in self.database_url or 'sslmode=require' in self.database_url:
                    connect_args['sslmode'] = 'require'
                
                # CRITICAL FIX: Drastically reduce connection pool for DigitalOcean limits
                self.postgres_engine = create_engine(
                    self.database_url,
                    pool_size=1,          # EMERGENCY FIX: Minimum possible
                    max_overflow=2,       # EMERGENCY FIX: Very small overflow  
                    pool_pre_ping=True,
                    pool_recycle=900,     # 15 minutes - shorter recycle
                    pool_timeout=10,      # Faster timeout to prevent hanging
                    connect_args=connect_args
                )
                logger.info("PostgreSQL database configured with SSL requirements")
                
            # Create async session maker for SQLAlchemy 1.4
            if self.database_url.startswith('postgresql'):
                async_url = self.database_url.replace('postgresql://', 'postgresql+asyncpg://')
                self.async_engine = create_async_engine(async_url)
                
        except Exception as e:
            logger.error(f"Error setting up PostgreSQL: {e}")
            # Set to None so we know there's an issue
            self.postgres_engine = None
    
    async def get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client with connection pooling"""
        if self.redis_client is None:
            try:
                self.redis_client = redis.Redis(**self.redis_config)
                # Test connection
                await self.redis_client.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.redis_client = None
        
        return self.redis_client
    
    async def close_redis(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            logger.info("Redis connection closed")
    
    def get_postgres_session(self):
        """Get PostgreSQL session"""
        if self.postgres_engine is None:
            logger.error("PostgreSQL engine not initialized")
            return None
            
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.postgres_engine
        )
        return SessionLocal()
    
    async def get_async_postgres_session(self) -> Optional[AsyncSession]:
        """Get async PostgreSQL session"""
        if not hasattr(self, 'async_engine') or self.async_engine is None:
            return None
        return AsyncSession(self.async_engine)

# Global database instance
db_config = DatabaseConfig()

async def get_redis() -> Optional[redis.Redis]:
    """Dependency for getting Redis client"""
    return await db_config.get_redis_client()

def get_db():
    """Dependency for getting PostgreSQL session"""
    db = db_config.get_postgres_session()
    if db is None:
        return None
    try:
        yield db
    finally:
        db.close()

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async PostgreSQL session"""
    async_db = await db_config.get_async_postgres_session()
    if async_db is None:
        raise RuntimeError("Database session not available")
    try:
        yield async_db
    finally:
        await async_db.close()

# Database health check
async def check_database_health() -> dict:
    """Check health of all database connections"""
    health = {
        'redis': {'status': 'unhealthy', 'error': None},
        'postgres': {'status': 'unhealthy', 'error': None}
    }
    
    # Check Redis
    try:
        redis_client = await get_redis()
        if redis_client:
            await redis_client.ping()
            health['redis']['status'] = 'healthy'
    except Exception as e:
        health['redis']['error'] = str(e)
    
    # Check PostgreSQL
    try:
        db = db_config.get_postgres_session()
        if db:
            db.execute(text("SELECT 1"))
            health['postgres']['status'] = 'healthy'
            db.close()
    except Exception as e:
        health['postgres']['error'] = str(e)
    
    return health 

async def get_async_session() -> AsyncSession:
    """Get async database session for ShareKhan multi-user management"""
    try:
        if db_config.async_session_maker is None:
            logger.warning("Async session maker not initialized")
            return None
        
        async with db_config.async_session_maker() as session:
            return session
    except Exception as e:
        logger.error(f"Failed to get async session: {e}")
        return None 