"""
Database configuration and connection management for the trading system.
"""
import os
import logging
from typing import Optional
from urllib.parse import urlparse

import redis.asyncio as redis
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

# Database Base Model
Base = declarative_base()
metadata = MetaData()

class DatabaseConfig:
    """Database configuration manager"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.postgres_engine = None
        self.async_session_maker = None
        
        # Environment variables
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.database_url = os.getenv('DATABASE_URL', 'sqlite:///./trading_system.db')
        
        # Parse Redis connection
        self._setup_redis_config()
        
        # Setup PostgreSQL
        self._setup_postgres_config()
    
    def _setup_redis_config(self):
        """Setup Redis connection configuration"""
        try:
            parsed = urlparse(self.redis_url)
            self.redis_config = {
                'host': parsed.hostname or 'localhost',
                'port': parsed.port or 6379,
                'password': parsed.password,
                'db': int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0,
                'decode_responses': True,
                'socket_timeout': 5,
                'socket_connect_timeout': 5,
                'retry_on_timeout': True,
                'health_check_interval': 30
            }
            logger.info(f"Redis configured for: {self.redis_config['host']}:{self.redis_config['port']}")
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
                # Production PostgreSQL
                self.postgres_engine = create_engine(
                    self.database_url,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True,
                    pool_recycle=3600
                )
                logger.info("PostgreSQL database configured")
                
            # Create async session maker
            if self.database_url.startswith('postgresql'):
                async_url = self.database_url.replace('postgresql://', 'postgresql+asyncpg://')
                async_engine = create_async_engine(async_url)
                self.async_session_maker = sessionmaker(
                    async_engine, 
                    class_=AsyncSession, 
                    expire_on_commit=False
                )
                
        except Exception as e:
            logger.error(f"Error setting up PostgreSQL: {e}")
    
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
            return None
            
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.postgres_engine
        )
        return SessionLocal()
    
    async def get_async_postgres_session(self) -> Optional[AsyncSession]:
        """Get async PostgreSQL session"""
        if self.async_session_maker is None:
            return None
        return self.async_session_maker()

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

async def get_async_db() -> Optional[AsyncSession]:
    """Dependency for getting async PostgreSQL session"""
    async_db = await db_config.get_async_postgres_session()
    if async_db is None:
        return None
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
            db.execute("SELECT 1")
            health['postgres']['status'] = 'healthy'
            db.close()
    except Exception as e:
        health['postgres']['error'] = str(e)
    
    return health 