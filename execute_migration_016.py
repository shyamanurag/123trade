#!/usr/bin/env python3
"""
Execute Migration 016: Add actual_execution column
Fixes: column "actual_execution" of relation "trades" does not exist
"""

import os
import logging
import asyncio
from sqlalchemy import create_engine, text
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def execute_migration_016():
    """Execute migration 016 to add actual_execution column"""
    try:
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("❌ DATABASE_URL environment variable not set")
            return False
        
        logger.info("🚀 Executing Migration 016: Add actual_execution column")
        logger.info(f"🔗 Database: {database_url.split('@')[1] if '@' in database_url else 'local'}")
        
        # Create engine
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                logger.info("📊 Adding actual_execution column...")
                conn.execute(text("ALTER TABLE trades ADD COLUMN IF NOT EXISTS actual_execution BOOLEAN DEFAULT FALSE"))
                
                logger.info("📊 Adding current_price column...")
                conn.execute(text("ALTER TABLE trades ADD COLUMN IF NOT EXISTS current_price DECIMAL(10,2)"))
                
                logger.info("📊 Adding pnl column...")
                conn.execute(text("ALTER TABLE trades ADD COLUMN IF NOT EXISTS pnl DECIMAL(12,2) DEFAULT 0.0"))
                
                logger.info("📊 Adding pnl_percent column...")
                conn.execute(text("ALTER TABLE trades ADD COLUMN IF NOT EXISTS pnl_percent DECIMAL(8,4) DEFAULT 0.0"))
                
                logger.info("📊 Creating indexes...")
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_trades_actual_execution ON trades(actual_execution)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_trades_current_price ON trades(current_price)"))
                
                logger.info("📊 Updating existing trades...")
                result = conn.execute(text("UPDATE trades SET actual_execution = FALSE WHERE actual_execution IS NULL"))
                updated_rows = result.rowcount
                logger.info(f"✅ Updated {updated_rows} existing trades")
                
                # Create schema_migrations table if it doesn't exist
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        description TEXT,
                        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Log the migration
                conn.execute(text("""
                    INSERT INTO schema_migrations (version, description, executed_at) 
                    VALUES (16, 'Add actual_execution and P&L columns for real ShareKhan data sync', :executed_at)
                    ON CONFLICT (version) DO NOTHING
                """), {'executed_at': datetime.now()})
                
                # Commit transaction
                trans.commit()
                logger.info("✅ Migration 016 executed successfully!")
                
                # Verify the columns exist
                logger.info("🔍 Verifying column creation...")
                result = conn.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'trades' 
                    AND column_name IN ('actual_execution', 'current_price', 'pnl', 'pnl_percent')
                    ORDER BY column_name
                """))
                
                columns = result.fetchall()
                logger.info(f"✅ Verified columns: {[col[0] for col in columns]}")
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Migration failed: {e}")
                trans.rollback()
                return False
                
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(execute_migration_016())
    if success:
        print("🎉 Migration 016 completed successfully!")
        exit(0)
    else:
        print("💥 Migration 016 failed!")
        exit(1) 