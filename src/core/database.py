"""
Database manager for the trading system
"""
import logging
import os
import sqlalchemy
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from typing import Optional

logger = logging.getLogger(__name__)

# Database base for models
Base = declarative_base()

class DatabaseManager:
    """Centralized database manager with proper connection pooling for DigitalOcean"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
        
    def initialize(self):
        """Initialize database with optimized connection pooling for DigitalOcean"""
        if self._initialized:
            logger.info("Database already initialized - reusing connection pool")
            return
            
        try:
            logger.info("Attempting to connect to database...")
            
            # Get database URL from environment
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                raise ValueError("DATABASE_URL environment variable not set")
            
            # Log masked URL for debugging
            masked_url = database_url.replace(database_url.split('@')[0].split('//')[1], 'AVNS_LpaPpsdL4CtOii03MnN')
            masked_url = masked_url.replace(database_url.split('@')[1].split('/')[0], '[MASKED]')
            logger.info(f"Database URL (masked): {masked_url}")
            
            # Configure connection args
            connect_args = {}
            if 'sslmode=require' in database_url or database_url.startswith('postgresql'):
                connect_args['sslmode'] = 'require'
                
            logger.info(f"Using connect_args: {connect_args}")
            
            # CRITICAL FIX: Drastically reduce connection pool for DigitalOcean limits
            # DigitalOcean has very limited connection slots - use minimal connections
            self.engine = create_engine(
                database_url,
                pool_size=1,          # EMERGENCY FIX: Minimum possible
                max_overflow=2,       # EMERGENCY FIX: Very small overflow
                pool_pre_ping=True,
                pool_recycle=900,     # 15 minutes - shorter recycle
                pool_timeout=10,      # Faster timeout to prevent hanging
                connect_args=connect_args,
                echo=False,
                pool_reset_on_return='commit'
            )
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info("✅ Database connection pool initialized: 3 connections + 5 overflow")
            logger.info("📊 Optimized for DigitalOcean connection limits")
            
            # Ensure database is ready for paper trading (autonomous)
            self._ensure_database_ready()
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            logger.error("💡 This may be due to connection pool exhaustion")
            logger.error("🔧 Check DigitalOcean database connection limits")
            raise
    
    def _ensure_database_ready(self):
        """Ensure database is ready for paper trading"""
        try:
            if not self.engine:
                logger.error("❌ Cannot ensure database ready - engine not initialized")
                return
                
            logger.info("🔄 Ensuring database is ready for paper trading...")
            
            with self.engine.begin() as conn:
                # First check if users table already has a primary key
                result = conn.execute(text("""
                    SELECT constraint_name, column_name 
                    FROM information_schema.key_column_usage 
                    WHERE table_name = 'users' 
                    AND constraint_name IN (
                        SELECT constraint_name 
                        FROM information_schema.table_constraints 
                        WHERE table_name = 'users' 
                        AND constraint_type = 'PRIMARY KEY'
                    )
                """))
                
                primary_key_info = result.fetchall()
                
                if primary_key_info:
                    logger.info("✅ Users table already has PRIMARY KEY - database ready")
                else:
                    logger.info("🔧 Users table missing PRIMARY KEY - creating schema...")
                    
                    # Create users table with proper PRIMARY KEY
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS users (
                            id SERIAL PRIMARY KEY,
                            username VARCHAR(100) UNIQUE NOT NULL,
                            email VARCHAR(255),
                            password_hash VARCHAR(255),
                            full_name VARCHAR(200),
                            initial_capital DECIMAL(15,2) DEFAULT 50000,
                            current_balance DECIMAL(15,2) DEFAULT 50000,
                            risk_tolerance VARCHAR(20) DEFAULT 'medium',
                            is_active BOOLEAN DEFAULT true,
                            sharekhan_client_id VARCHAR(50),
                            broker_user_id VARCHAR(100),
                            api_key_encrypted TEXT,
                            trading_enabled BOOLEAN DEFAULT true,
                            max_daily_trades INTEGER DEFAULT 100,
                            max_position_size DECIMAL(15,2) DEFAULT 100000,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    
                    # Create other essential tables if they don't exist
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS trades (
                            id SERIAL PRIMARY KEY,
                            trade_id VARCHAR(100) UNIQUE,
                            user_id INTEGER REFERENCES users(id),
                            symbol VARCHAR(50) NOT NULL,
                            side VARCHAR(10) NOT NULL,
                            quantity INTEGER NOT NULL,
                            entry_price DECIMAL(10,2),
                            current_price DECIMAL(10,2),
                            pnl DECIMAL(10,2),
                            pnl_percent DECIMAL(5,2),
                            status VARCHAR(20) DEFAULT 'OPEN',
                            strategy VARCHAR(50),
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            exit_timestamp TIMESTAMP,
                            broker_order_id VARCHAR(100),
                            notes TEXT
                        )
                    """))
                    
                    # Create indexes for performance
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_trades_user_id ON trades(user_id);
                        CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
                        CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
                        CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
                    """))
                    
                    logger.info("✅ Database schema created successfully")
                
                # Always ensure PAPER_TRADER_001 user exists for autonomous operation
                # FIXED: Remove sharekhan_client_id from INSERT to avoid column missing error
                conn.execute(text("""
                    INSERT INTO users (username, email, password_hash, broker_user_id, is_active, trading_enabled, 
                                     full_name, initial_capital, current_balance)
                    VALUES ('PAPER_TRADER_001', 'paper.trader@algoauto.com', 'dummy_hash', 'QSW899', true, true,
                           'Autonomous Paper Trader', 100000.00, 100000.00)
                    ON CONFLICT (username) DO UPDATE SET
                        broker_user_id = EXCLUDED.broker_user_id,
                        is_active = true,
                        trading_enabled = true,
                        updated_at = CURRENT_TIMESTAMP
                """))
                
                logger.info("✅ Database is ready for paper trading!")
                
        except Exception as e:
            logger.error(f"❌ Error ensuring database ready: {e}")
            # Don't raise - app can continue without full database functionality
    
    def _apply_migrations(self):
        """Apply database migrations if needed"""
        try:
            import os
            from pathlib import Path
            
            # Check if we're in production and should apply migrations
            environment = os.getenv('ENVIRONMENT', 'development')
            
            if environment == 'production':
                logger.info("🔄 Production environment detected - skipping auto-migrations")
                logger.info("📝 Database migrations should be applied manually via deployment scripts")
            else:
                logger.info("📝 Development environment - skipping auto-migrations")
                
        except Exception as e:
            logger.error(f"❌ Migration check failed: {e}")
            logger.info("🔄 Continuing without migration")
    
    def get_shared_session(self):
        """Get database session from the shared pool"""
        if not self._initialized:
            self.initialize()
        if not self.SessionLocal:
            raise RuntimeError("Database not properly initialized - SessionLocal is None")
        return self.SessionLocal()
    
    @contextmanager
    def get_session(self):
        """Get database session with context manager - backward compatibility"""
        session = self.get_shared_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def execute_sql(self, sql: str):
        """Execute raw SQL"""
        if not self.engine:
            raise RuntimeError("Database not initialized")
        
        with self.engine.connect() as conn:
            with conn.begin():
                return conn.execute(text(sql))
    
    def get_shared_engine(self):
        """Get the shared database engine for all components"""
        if not self._initialized:
            self.initialize()
        return self.engine
    
    def health_check(self) -> dict:
        """Check database health"""
        try:
            if not self.engine:
                return {"status": "error", "message": "Database not initialized"}
            
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1 as health_check"))
                row = result.fetchone()
                
            return {
                "status": "healthy" if row and row[0] == 1 else "unhealthy",
                "message": "Database connection successful"
            }
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Database health check failed: {str(e)}"
            }

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions for backward compatibility
def get_session():
    """Get database session - backward compatibility"""
    return db_manager.get_session()

def get_engine():
    """Get database engine - backward compatibility"""
    return db_manager.get_shared_engine()

def get_db():
    """Get database session generator - FastAPI style"""
    session = db_manager.get_shared_session()
    try:
        yield session
    finally:
        session.close()

def initialize_database():
    """Initialize database - backward compatibility"""
    return db_manager.initialize()

def execute_sql(sql: str):
    """Execute SQL - backward compatibility"""
    return db_manager.execute_sql(sql) 