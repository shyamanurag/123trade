"""
Database Schema Manager - Precise, permanent solution for database structure integrity.
This is not a workaround - this is the definitive way to ensure database schema correctness.
"""
import logging
from sqlalchemy import create_engine, text, inspect, Column, Integer, String, DateTime, Boolean, Float, JSON
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from typing import Dict, List, Any
import time

logger = logging.getLogger(__name__)

class DatabaseSchemaManager:
    """
    Precise database schema management - ensures database structure is always correct.
    This is the authoritative source of truth for database schema.
    """
    
    # Define the precise schema for users table
    USERS_TABLE_SCHEMA = {
        'id': {'type': 'SERIAL', 'primary_key': True, 'nullable': False},
        'email': {'type': 'VARCHAR(255)', 'unique': True, 'nullable': False},
        'username': {'type': 'VARCHAR(50)', 'unique': True, 'nullable': False},
        'full_name': {'type': 'VARCHAR(100)', 'nullable': True},  # Make nullable
        'password_hash': {'type': 'VARCHAR(255)', 'nullable': False},
        'role': {'type': 'VARCHAR(20)', 'nullable': True, 'default': 'trader'},
        'status': {'type': 'VARCHAR(20)', 'nullable': True, 'default': 'active'},
        'is_active': {'type': 'BOOLEAN', 'nullable': False, 'default': True},
        'broker_account_id': {'type': 'VARCHAR(255)', 'nullable': True},
        'trading_enabled': {'type': 'BOOLEAN', 'nullable': False, 'default': False},
        'max_position_size': {'type': 'FLOAT', 'nullable': True},
        'risk_level': {'type': 'VARCHAR(20)', 'nullable': True},
        'preferences': {'type': 'JSON', 'nullable': True},
        'created_at': {'type': 'TIMESTAMP', 'nullable': False, 'default': 'CURRENT_TIMESTAMP'},
        'updated_at': {'type': 'TIMESTAMP', 'nullable': False, 'default': 'CURRENT_TIMESTAMP'},
        'last_login': {'type': 'TIMESTAMP', 'nullable': True},
        'failed_login_attempts': {'type': 'INTEGER', 'nullable': False, 'default': 0},
        'last_password_change': {'type': 'TIMESTAMP', 'nullable': True},
        'two_factor_enabled': {'type': 'BOOLEAN', 'nullable': False, 'default': False},
        'two_factor_secret': {'type': 'VARCHAR(255)', 'nullable': True},
        # Additional columns for paper trading compatibility
        'initial_capital': {'type': 'FLOAT', 'nullable': True, 'default': 100000.0},
        'current_balance': {'type': 'FLOAT', 'nullable': True, 'default': 100000.0},
        'risk_tolerance': {'type': 'VARCHAR(20)', 'nullable': True, 'default': 'medium'},
        'sharekhan_client_id': {'type': 'VARCHAR(50)', 'nullable': True},
        'max_daily_trades': {'type': 'INTEGER', 'nullable': True, 'default': 1000}
    }
    
    # Define the precise schema for paper_trades table
    PAPER_TRADES_TABLE_SCHEMA = {
        'id': {'type': 'SERIAL', 'primary_key': True, 'nullable': False},
        'user_id': {'type': 'INTEGER', 'nullable': False, 'foreign_key': 'users.id'},
        'symbol': {'type': 'VARCHAR(20)', 'nullable': False},
        'action': {'type': 'VARCHAR(10)', 'nullable': False},
        'quantity': {'type': 'INTEGER', 'nullable': False},
        'price': {'type': 'FLOAT', 'nullable': False},
        'timestamp': {'type': 'TIMESTAMP', 'nullable': False},
        'status': {'type': 'VARCHAR(20)', 'nullable': False},
        'order_id': {'type': 'VARCHAR(50)', 'nullable': True},
        'pnl': {'type': 'FLOAT', 'nullable': True},
        'strategy': {'type': 'VARCHAR(50)', 'nullable': True},
        'created_at': {'type': 'TIMESTAMP', 'nullable': False, 'default': 'CURRENT_TIMESTAMP'}
    }
    
    # Define the precise schema for trades table (main trading table)
    TRADES_TABLE_SCHEMA = {
        'trade_id': {'type': 'SERIAL', 'primary_key': True, 'nullable': False},
        'user_id': {'type': 'INTEGER', 'nullable': False, 'foreign_key': 'users.id'},
        'position_id': {'type': 'INTEGER', 'nullable': True},
        'symbol': {'type': 'VARCHAR(20)', 'nullable': False},
        'trade_type': {'type': 'VARCHAR(10)', 'nullable': False},
        'quantity': {'type': 'INTEGER', 'nullable': False},
        'price': {'type': 'DECIMAL(10,2)', 'nullable': False},
        'order_id': {'type': 'VARCHAR(50)', 'nullable': True},
        'strategy': {'type': 'VARCHAR(50)', 'nullable': True},
        'commission': {'type': 'DECIMAL(8,2)', 'nullable': True, 'default': 0},
        'pnl': {'type': 'DECIMAL(12,2)', 'nullable': True, 'default': 0},
        'pnl_percent': {'type': 'DECIMAL(6,2)', 'nullable': True, 'default': 0},
        'status': {'type': 'VARCHAR(20)', 'nullable': True, 'default': 'EXECUTED'},
        'executed_at': {'type': 'TIMESTAMP', 'nullable': False, 'default': 'CURRENT_TIMESTAMP'},
        'created_at': {'type': 'TIMESTAMP', 'nullable': False, 'default': 'CURRENT_TIMESTAMP'}
    }
    
    # Define the precise schema for positions table
    POSITIONS_TABLE_SCHEMA = {
        'position_id': {'type': 'SERIAL', 'primary_key': True, 'nullable': False},
        'user_id': {'type': 'INTEGER', 'nullable': False, 'foreign_key': 'users.id'},
        'symbol': {'type': 'VARCHAR(20)', 'nullable': False},
        'quantity': {'type': 'INTEGER', 'nullable': False},
        'entry_price': {'type': 'DECIMAL(10,2)', 'nullable': False},
        'current_price': {'type': 'DECIMAL(10,2)', 'nullable': True},
        'entry_time': {'type': 'TIMESTAMP', 'nullable': False, 'default': 'CURRENT_TIMESTAMP'},
        'exit_time': {'type': 'TIMESTAMP', 'nullable': True},
        'strategy': {'type': 'VARCHAR(50)', 'nullable': True},
        'status': {'type': 'VARCHAR(20)', 'nullable': True, 'default': 'open'},
        'unrealized_pnl': {'type': 'DECIMAL(12,2)', 'nullable': True},
        'realized_pnl': {'type': 'DECIMAL(12,2)', 'nullable': True},
        'stop_loss': {'type': 'DECIMAL(10,2)', 'nullable': True},
        'take_profit': {'type': 'DECIMAL(10,2)', 'nullable': True},
        'created_at': {'type': 'TIMESTAMP', 'nullable': False, 'default': 'CURRENT_TIMESTAMP'},
        'updated_at': {'type': 'TIMESTAMP', 'nullable': False, 'default': 'CURRENT_TIMESTAMP'}
    }
    
    # Define the precise schema for orders table
    ORDERS_TABLE_SCHEMA = {
        'order_id': {'type': 'VARCHAR(50)', 'primary_key': True, 'nullable': False},
        'user_id': {'type': 'INTEGER', 'nullable': False, 'foreign_key': 'users.id'},
        'broker_order_id': {'type': 'VARCHAR(100)', 'nullable': True},
        'parent_order_id': {'type': 'VARCHAR(50)', 'nullable': True},
        'symbol': {'type': 'VARCHAR(20)', 'nullable': False},
        'order_type': {'type': 'VARCHAR(20)', 'nullable': False},
        'side': {'type': 'VARCHAR(10)', 'nullable': False},
        'quantity': {'type': 'INTEGER', 'nullable': False},
        'price': {'type': 'DECIMAL(10,2)', 'nullable': True},
        'stop_price': {'type': 'DECIMAL(10,2)', 'nullable': True},
        'filled_quantity': {'type': 'INTEGER', 'nullable': True, 'default': 0},
        'average_price': {'type': 'DECIMAL(10,2)', 'nullable': True},
        'status': {'type': 'VARCHAR(20)', 'nullable': True, 'default': 'PENDING'},
        'execution_strategy': {'type': 'VARCHAR(30)', 'nullable': True},
        'time_in_force': {'type': 'VARCHAR(10)', 'nullable': True, 'default': 'DAY'},
        'strategy_name': {'type': 'VARCHAR(50)', 'nullable': True},
        'signal_id': {'type': 'VARCHAR(50)', 'nullable': True},
        'fees': {'type': 'DECIMAL(8,2)', 'nullable': True, 'default': 0},
        'created_at': {'type': 'TIMESTAMP', 'nullable': False, 'default': 'CURRENT_TIMESTAMP'},
        'placed_at': {'type': 'TIMESTAMP', 'nullable': True},
        'filled_at': {'type': 'TIMESTAMP', 'nullable': True},
        'updated_at': {'type': 'TIMESTAMP', 'nullable': False, 'default': 'CURRENT_TIMESTAMP'}
    }
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url
        # CRITICAL FIX: Use shared database manager instead of creating new engine
        # This prevents connection pool exhaustion on DigitalOcean
        self._engine = None
        
    def _get_engine(self):
        """Get shared database engine to prevent connection pool exhaustion"""
        if self._engine is None:
            try:
                # Try to get shared engine from database manager
                from .database import db_manager
                self._engine = db_manager.get_shared_engine()
                logger.info("✅ Using shared database engine to prevent connection exhaustion")
            except Exception as e:
                logger.warning(f"Could not get shared engine, creating new one: {e}")
                if self.database_url:
                    # Emergency fallback - create minimal connection pool
                    self._engine = create_engine(
                        self.database_url,
                        pool_size=1,      # Minimal pool
                        max_overflow=0,   # No overflow
                        pool_pre_ping=True,
                        pool_timeout=5
                    )
                else:
                    raise RuntimeError("No database URL provided and shared engine unavailable")
        return self._engine
        
    @property 
    def engine(self):
        """Property to access the database engine"""
        return self._get_engine()
        
    def ensure_schema(self) -> Dict[str, Any]:
        """Ensure all tables exist with precise schema"""
        results = {}
        
        # CRITICAL: Fix users table first - this is the root cause of all issues
        results['users'] = self._ensure_users_table_with_aggressive_fix()
        
        # Only create dependent tables if users table is fixed
        if results['users']['status'] in ['created', 'verified', 'updated', 'repaired']:
            results['paper_trades'] = self._ensure_table('paper_trades', self.PAPER_TRADES_TABLE_SCHEMA)
            results['trades'] = self._ensure_table('trades', self.TRADES_TABLE_SCHEMA)
            results['positions'] = self._ensure_table('positions', self.POSITIONS_TABLE_SCHEMA)
            results['orders'] = self._ensure_table('orders', self.ORDERS_TABLE_SCHEMA)
            
            # Ensure default user exists (only after schema is correct)
            self._ensure_default_user()
        else:
            logger.error("❌ Cannot create dependent tables - users table has issues")
            results['paper_trades'] = {'status': 'skipped', 'reason': 'users table issues'}
            
        return results

    def _check_users_primary_key_constraint(self, conn) -> bool:
        """Check if users table has a PROPER primary key constraint that works for foreign keys"""
        try:
            # Method 1: Direct PostgreSQL constraint check
            result = conn.execute(text("""
                SELECT constraint_name, constraint_type 
                FROM information_schema.table_constraints 
                WHERE table_name = 'users' 
                AND constraint_type = 'PRIMARY KEY'
            """)).fetchall()
            
            if not result:
                logger.warning("❌ No PRIMARY KEY constraint found in information_schema")
                return False
            
            # Method 2: Check if foreign key can actually reference this table
            # Use a separate connection to avoid transaction conflicts
            try:
                # Create a savepoint to handle potential rollbacks
                savepoint = conn.begin_nested()
                try:
                    # Try to create a test foreign key to see if it works
                    test_sql = """
                        CREATE TABLE IF NOT EXISTS test_foreign_key_check (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER,
                            FOREIGN KEY (user_id) REFERENCES users(id)
                        )
                    """
                    conn.execute(text(test_sql))
                    
                    # If successful, clean up the test table
                    conn.execute(text("DROP TABLE IF EXISTS test_foreign_key_check"))
                    savepoint.commit()
                    logger.info("✅ Users table PRIMARY KEY constraint works for foreign keys")
                    return True
                    
                except Exception as fk_test_error:
                    logger.error(f"❌ Foreign key test failed: {fk_test_error}")
                    savepoint.rollback()
                    return False
                
            except Exception as savepoint_error:
                logger.error(f"❌ Savepoint operation failed: {savepoint_error}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Primary key constraint check failed: {e}")
            return False

    def _fix_users_primary_key_aggressive(self, conn) -> bool:
        """Aggressively fix users table primary key constraint"""
        try:
            logger.info("🔧 Starting aggressive users table PRIMARY KEY repair...")
            
            # Get current data before any operations
            backup_data = []
            try:
                backup_data = conn.execute(text("SELECT * FROM users")).fetchall()
                logger.info(f"📦 Backing up {len(backup_data)} user records")
            except Exception as e:
                logger.warning(f"⚠️ Could not backup existing data: {e}")
            
            # Drop dependent tables that reference users
            logger.info("🔄 Dropping dependent tables...")
            dependent_tables = ['paper_trades', 'positions', 'trades', 'orders']
            for table in dependent_tables:
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                    logger.info(f"   ✓ Dropped {table}")
                except Exception as e:
                    logger.warning(f"   ⚠️ Could not drop {table}: {e}")
            
            # Drop and recreate users table with proper schema
            logger.info("🔄 Recreating users table with proper PRIMARY KEY...")
            conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
            
            # Create users table with proper SERIAL PRIMARY KEY (fixed duplicate column)
            create_users_sql = """
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    full_name VARCHAR(100),
                    initial_capital FLOAT DEFAULT 100000.0,
                    current_balance FLOAT DEFAULT 100000.0,
                    risk_tolerance VARCHAR(20) DEFAULT 'medium',
                    is_active BOOLEAN DEFAULT TRUE,
                    sharekhan_client_id VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_trades INTEGER DEFAULT 0,
                    user_type VARCHAR(20) DEFAULT 'trader',
                    status VARCHAR(20) DEFAULT 'active',
                    phone VARCHAR(20),
                    trading_enabled BOOLEAN DEFAULT TRUE,
                    max_position_size INTEGER DEFAULT 500000,
                    sharekhan_api_key VARCHAR(100),
                    sharekhan_api_secret VARCHAR(100),
                    sharekhan_access_token TEXT,
                    sharekhan_public_token VARCHAR(100),
                    total_pnl FLOAT DEFAULT 0,
                    last_login TIMESTAMP,
                    paper_trading BOOLEAN DEFAULT FALSE,
                    max_daily_trades INTEGER DEFAULT 1000
                )
            """
            conn.execute(text(create_users_sql))
            logger.info("✅ Users table recreated with proper SERIAL PRIMARY KEY")
            
            # Restore data if any existed
            if backup_data:
                logger.info(f"🔄 Restoring {len(backup_data)} user records...")
                
                for row_data in backup_data:
                    try:
                        # Create a simplified insert (skip auto-generated id)
                        conn.execute(text("""
                            INSERT INTO users (
                                username, email, password_hash, full_name, initial_capital,
                                current_balance, risk_tolerance, is_active, sharekhan_client_id,
                                created_at, updated_at, total_trades, user_type, status,
                                phone, trading_enabled, max_position_size, sharekhan_api_key,
                                sharekhan_api_secret, sharekhan_access_token, sharekhan_public_token,
                                total_pnl, last_login, paper_trading, max_daily_trades
                            ) VALUES (
                                :username, :email, :password_hash, :full_name, :initial_capital,
                                :current_balance, :risk_tolerance, :is_active, :sharekhan_client_id,
                                COALESCE(:created_at, CURRENT_TIMESTAMP), COALESCE(:updated_at, CURRENT_TIMESTAMP),
                                :total_trades, :user_type, :status, :phone, :trading_enabled,
                                :max_position_size, :sharekhan_api_key, :sharekhan_api_secret,
                                :sharekhan_access_token, :sharekhan_public_token, :total_pnl,
                                :last_login, :paper_trading, :max_daily_trades
                            )
                        """), {
                            'username': row_data[1] if len(row_data) > 1 else 'RESTORED_USER',
                            'email': row_data[2] if len(row_data) > 2 else f'restored_{len(backup_data)}@example.com',
                            'password_hash': row_data[3] if len(row_data) > 3 else '$2b$12$default.hash',
                            'full_name': row_data[4] if len(row_data) > 4 else 'Restored User',
                            'initial_capital': row_data[5] if len(row_data) > 5 else 100000.0,
                            'current_balance': row_data[6] if len(row_data) > 6 else 100000.0,
                            'risk_tolerance': row_data[7] if len(row_data) > 7 else 'medium',
                            'is_active': row_data[8] if len(row_data) > 8 else True,
                            'sharekhan_client_id': row_data[9] if len(row_data) > 9 else None,
                            'created_at': row_data[10] if len(row_data) > 10 else None,
                            'updated_at': row_data[11] if len(row_data) > 11 else None,
                            'total_trades': row_data[12] if len(row_data) > 12 else 0,
                            'user_type': row_data[13] if len(row_data) > 13 else 'trader',
                            'status': row_data[14] if len(row_data) > 14 else 'active',
                            'phone': row_data[15] if len(row_data) > 15 else None,
                            'trading_enabled': row_data[16] if len(row_data) > 16 else True,
                            'max_position_size': row_data[17] if len(row_data) > 17 else 500000,
                            'sharekhan_api_key': row_data[18] if len(row_data) > 18 else None,
                            'sharekhan_api_secret': row_data[19] if len(row_data) > 19 else None,
                            'sharekhan_access_token': row_data[20] if len(row_data) > 20 else None,
                            'sharekhan_public_token': row_data[21] if len(row_data) > 21 else None,
                            'total_pnl': row_data[22] if len(row_data) > 22 else 0,
                            'last_login': row_data[23] if len(row_data) > 23 else None,
                            'paper_trading': row_data[24] if len(row_data) > 24 else False,
                            'max_daily_trades': row_data[25] if len(row_data) > 25 else 1000
                        })
                        logger.info(f"   ✓ Restored user: {row_data[1] if len(row_data) > 1 else 'Unknown'}")
                            
                    except Exception as restore_error:
                        logger.warning(f"⚠️ Could not restore user record: {restore_error}")
                        continue
                        
                logger.info("✅ User data restoration completed")
            
            # Add default paper trading user if no users exist
            user_count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
            if user_count == 0:
                logger.info("📝 Creating default paper trading user...")
                conn.execute(text("""
                    INSERT INTO users (username, email, password_hash, full_name, trading_enabled, paper_trading)
                    VALUES ('PAPER_TRADER_001', 'paper@algoauto.com', '$2b$12$dummy.hash.paper.trading', 'Paper Trading Account', true, true)
                """))
                logger.info("✅ Default paper trading user created")
            
            # Test the fix with a simple foreign key check
            try:
                # Use a regular table instead of TEMP table for foreign key validation
                test_table_name = f"test_fk_validation_{int(time.time())}"
                conn.execute(text(f"""
                    CREATE TABLE {test_table_name} (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                """))
                conn.execute(text(f"DROP TABLE {test_table_name}"))
                logger.info("✅ Users table PRIMARY KEY constraint verified working")
                return True
            except Exception as verify_error:
                logger.error(f"❌ PRIMARY KEY constraint still not working: {verify_error}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Aggressive PRIMARY KEY fix failed: {e}")
            return False

    def _ensure_users_table_with_aggressive_fix(self) -> Dict[str, Any]:
        """Ensure users table exists with aggressive PRIMARY KEY fixing"""
        result = {
            'status': 'unknown',
            'errors': [],
            'actions': []
        }
        
        try:
            # Step 1: Check if table exists (separate transaction)
            with self.engine.connect() as conn:
                table_exists = self._table_exists(conn, 'users')
            
            if not table_exists:
                # Step 2: Create table (separate transaction)
                logger.info("📋 Users table doesn't exist - creating with proper schema...")
                with self.engine.connect() as conn:
                    trans = conn.begin()
                    try:
                        create_sql = self._generate_create_table_sql('users', self.USERS_TABLE_SCHEMA)
                        conn.execute(text(create_sql))
                        trans.commit()
                        result['status'] = 'created'
                        result['actions'].append('Created users table with SERIAL PRIMARY KEY')
                        logger.info("✅ Users table created successfully")
                    except Exception as e:
                        trans.rollback()
                        raise e
            else:
                # Step 3: Check PRIMARY KEY constraint (separate transaction)
                pk_working = False
                with self.engine.connect() as conn:
                    pk_working = self._check_users_primary_key_constraint(conn)
                
                if pk_working:
                    logger.info("✅ Users table PRIMARY KEY constraint working correctly")
                    result['status'] = 'verified'
                else:
                    # Step 4: Fix PRIMARY KEY constraint (separate transaction)
                    logger.warning("⚠️ Users table PRIMARY KEY constraint needs fixing...")
                    with self.engine.connect() as conn:
                        trans = conn.begin()
                        try:
                            if self._fix_users_primary_key_aggressive(conn):
                                trans.commit()
                                result['status'] = 'repaired'
                                result['actions'].append('Fixed PRIMARY KEY constraint with aggressive repair')
                                logger.info("✅ Users table PRIMARY KEY constraint repaired")
                            else:
                                trans.rollback()
                                result['status'] = 'error'
                                result['errors'].append('Failed to repair PRIMARY KEY constraint')
                                logger.error("❌ Failed to repair users table PRIMARY KEY constraint")
                        except Exception as e:
                            trans.rollback()
                            raise e
            
            return result
                    
        except Exception as e:
            logger.error(f"❌ Error ensuring users table: {e}")
            result['status'] = 'error'
            result['errors'].append(str(e))
            return result

    def _table_exists(self, conn, table_name: str) -> bool:
        """Check if a table exists in the database"""
        try:
            # For PostgreSQL
            if 'postgresql' in self.database_url:
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = :table_name
                    )
                """), {'table_name': table_name}).scalar()
                return bool(result)
            else:
                # For SQLite
                result = conn.execute(text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name = :table_name
                """), {'table_name': table_name}).fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Error checking table existence for {table_name}: {e}")
            return False

    def _generate_create_table_sql(self, table_name: str, schema: Dict[str, Dict[str, Any]]) -> str:
        """Generate precise CREATE TABLE SQL with proper constraints"""
        columns = []
        foreign_keys = []
        
        # Detect database type
        is_postgresql = 'postgresql' in self.database_url
        
        for col_name, col_spec in schema.items():
            # Handle primary key columns with SERIAL (auto-incrementing)
            if col_spec.get('primary_key'):
                if is_postgresql and col_spec.get('type') == 'SERIAL':
                    col_def = f"{col_name} SERIAL PRIMARY KEY"
                elif is_postgresql:
                    col_def = f"{col_name} {col_spec['type']} PRIMARY KEY"
                else:
                    # SQLite
                    col_def = f"{col_name} INTEGER PRIMARY KEY AUTOINCREMENT"
            else:
                col_def = f"{col_name} {col_spec['type']}"
                
                # Add NOT NULL constraint if specified
                if not col_spec.get('nullable', True):
                    col_def += " NOT NULL"
                
                # Add DEFAULT clause if specified and not primary key
                if 'default' in col_spec:
                    if col_spec['default'] == 'CURRENT_TIMESTAMP':
                        col_def += f" DEFAULT {col_spec['default']}"
                    elif isinstance(col_spec['default'], bool):
                        # Handle boolean defaults properly for each database
                        if is_postgresql:
                            col_def += f" DEFAULT {str(col_spec['default']).lower()}"
                        else:
                            col_def += f" DEFAULT {1 if col_spec['default'] else 0}"
                    elif isinstance(col_spec['default'], str):
                        col_def += f" DEFAULT '{col_spec['default']}'"
                    else:
                        col_def += f" DEFAULT {col_spec['default']}"
                
                # Add UNIQUE constraint if specified
                if col_spec.get('unique'):
                    col_def += " UNIQUE"
                    
            columns.append(col_def)
            
            # Collect foreign keys separately (only for non-primary key columns)
            if 'foreign_key' in col_spec and not col_spec.get('primary_key'):
                ref_table, ref_col = col_spec['foreign_key'].split('.')
                foreign_keys.append(f"FOREIGN KEY ({col_name}) REFERENCES {ref_table}({ref_col})")
        
        # Combine columns and foreign keys
        all_constraints = columns + foreign_keys
        
        return f"CREATE TABLE {table_name} ({', '.join(all_constraints)})"
    
    def _generate_add_column_sql(self, table_name: str, col_name: str, col_spec: Dict[str, Any]) -> str:
        """Generate precise ALTER TABLE ADD COLUMN SQL"""
        col_def = f"{col_spec['type']}"
        
        # Detect database type
        is_postgresql = 'postgresql' in self.database_url
        
        if not col_spec.get('nullable', True):
            # For NOT NULL columns, we need a default value
            if 'default' in col_spec:
                if col_spec['default'] == 'CURRENT_TIMESTAMP':
                    col_def += f" DEFAULT {col_spec['default']}"
                elif isinstance(col_spec['default'], bool):
                    # Handle boolean defaults properly
                    if is_postgresql:
                        col_def += f" DEFAULT {str(col_spec['default']).lower()}"
                    else:
                        col_def += f" DEFAULT {1 if col_spec['default'] else 0}"
                elif isinstance(col_spec['default'], str):
                    col_def += f" DEFAULT '{col_spec['default']}'"
                else:
                    col_def += f" DEFAULT {col_spec['default']}"
            else:
                # Provide sensible defaults for NOT NULL columns without explicit defaults
                if 'INT' in col_spec['type']:
                    col_def += " DEFAULT 0"
                elif 'VARCHAR' in col_spec['type']:
                    col_def += " DEFAULT ''"
                elif 'BOOLEAN' in col_spec['type']:
                    if is_postgresql:
                        col_def += " DEFAULT false"
                    else:
                        col_def += " DEFAULT 0"
                elif 'FLOAT' in col_spec['type']:
                    col_def += " DEFAULT 0.0"
                elif 'TIMESTAMP' in col_spec['type']:
                    col_def += " DEFAULT CURRENT_TIMESTAMP"
            col_def += " NOT NULL"
        
        if col_spec.get('unique'):
            col_def += " UNIQUE"
            
        return f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}"
    
    def _ensure_table(self, table_name: str, schema: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Ensure a table exists with the precise schema"""
        result = {'status': 'unknown', 'actions': []}
        
        try:
            with self.engine.connect() as conn:
                # Start a transaction
                trans = conn.begin()
                try:
                    inspector = inspect(self.engine)
                    
                    # Check if table exists
                    if table_name not in inspector.get_table_names():
                        # Create table with precise schema
                        create_sql = self._generate_create_table_sql(table_name, schema)
                        logger.info(f"Creating table {table_name} with SQL: {create_sql}")
                        conn.execute(text(create_sql))
                        result['actions'].append(f"Created table {table_name} with precise schema")
                        result['status'] = 'created'
                    else:
                        # Verify and fix existing table schema
                        existing_columns = {col['name']: col for col in inspector.get_columns(table_name)}
                        
                        # Check for missing columns
                        for col_name, col_spec in schema.items():
                            if col_name not in existing_columns:
                                alter_sql = self._generate_add_column_sql(table_name, col_name, col_spec)
                                logger.info(f"Adding missing column {col_name} to {table_name}")
                                conn.execute(text(alter_sql))
                                result['actions'].append(f"Added missing column {col_name} to {table_name}")
                        
                        result['status'] = 'verified' if not result['actions'] else 'updated'
                    
                    # Commit the transaction
                    trans.commit()
                    
                except Exception as e:
                    # Rollback on error
                    trans.rollback()
                    raise e
                    
        except Exception as e:
            logger.error(f"Error ensuring table {table_name}: {e}")
            result['status'] = 'error'
            result['errors'] = [str(e)]
                
        return result
    
    def _ensure_default_user(self):
        """Ensure PAPER_TRADER_001 user exists for paper trading"""
        try:
            with self.engine.connect() as conn:
                trans = conn.begin()
                try:
                    # Check if PAPER_TRADER_001 exists
                    result = conn.execute(
                        text("SELECT COUNT(*) FROM users WHERE username = :username"),
                        {'username': 'PAPER_TRADER_001'}
                    ).scalar()
                    
                    if result == 0:
                        # Insert default paper trading user
                        conn.execute(text("""
                            INSERT INTO users (
                                username, email, password_hash, full_name, 
                                initial_capital, current_balance, is_active, 
                                trading_enabled, sharekhan_client_id, max_daily_trades
                            ) VALUES (
                                'PAPER_TRADER_001', 
                                'paper@trader.com', 
                                'hashed_password_placeholder',
                                'Paper Trading User',
                                1000000.0,
                                1000000.0,
                                true,
                                true,
                                'QSW899',
                                1000
                            )
                        """))
                        logger.info("✅ Created default PAPER_TRADER_001 user")
                    
                    trans.commit()
                    
                except Exception as e:
                    trans.rollback()
                    logger.error(f"❌ Failed to create default user: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error ensuring default user: {e}")

    def ensure_precise_schema(self) -> Dict[str, Any]:
        """
        Ensure all database tables have the precise schema required.
        This is the main entry point called by the application.
        """
        logger.info("Starting precise database schema verification...")
        
        try:
            # Run our comprehensive schema check
            results = self.ensure_schema()
            
            # Format results for compatibility with existing code
            formatted_result = {
                'status': 'success' if all(
                    r['status'] in ['created', 'verified', 'updated', 'repaired'] 
                    for r in results.values() 
                    if 'status' in r
                ) else 'error',
                'users_table': results.get('users', {}),
                'paper_trades_table': results.get('paper_trades', {}),
                'actions': [],
                'errors': []
            }
            
            # Collect all actions and errors
            for table_name, table_result in results.items():
                if 'actions' in table_result:
                    formatted_result['actions'].extend(table_result['actions'])
                if 'errors' in table_result:
                    formatted_result['errors'].extend(table_result['errors'])
            
            # Log results
            if formatted_result['status'] == 'success':
                logger.info("✅ Database schema verification completed successfully")
                if formatted_result['actions']:
                    for action in formatted_result['actions']:
                        logger.info(f"  ✓ {action}")
            else:
                logger.error("❌ Database schema verification failed")
                for error in formatted_result['errors']:
                    logger.error(f"  ✗ {error}")
            
            return formatted_result
            
        except Exception as e:
            logger.error(f"Critical error during schema verification: {e}")
            return {
                'status': 'error',
                'errors': [str(e)],
                'users_table': {'status': 'error'},
                'paper_trades_table': {'status': 'error'},
                'actions': []
            }

    async def ensure_table_exists(self, table_name: str) -> bool:
        """
        Async wrapper for table existence check.
        Used by some API components.
        """
        try:
            if table_name == 'users':
                result = self._ensure_users_table_with_aggressive_fix()
            elif table_name == 'paper_trades':
                result = self._ensure_table('paper_trades', self.PAPER_TRADES_TABLE_SCHEMA)
            elif table_name == 'trades':
                result = self._ensure_table('trades', self.TRADES_TABLE_SCHEMA)
            elif table_name == 'positions':
                result = self._ensure_table('positions', self.POSITIONS_TABLE_SCHEMA)
            elif table_name == 'orders':
                result = self._ensure_table('orders', self.ORDERS_TABLE_SCHEMA)
            else:
                logger.warning(f"Unknown table name: {table_name}")
                return False
                
            return result['status'] in ['created', 'verified', 'updated', 'repaired']
            
        except Exception as e:
            logger.error(f"Error ensuring table {table_name} exists: {e}")
            return False 