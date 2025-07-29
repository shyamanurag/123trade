#!/usr/bin/env python3
"""
URGENT DATABASE MIGRATION 016
Fixes: column "actual_execution" of relation "trades" does not exist
"""

import os
import sys
import logging
from datetime import datetime
import asyncio

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def execute_migration_016():
    """Execute Migration 016: Add actual_execution column - URGENT FIX"""
    try:
        logger.info("🚀 URGENT: Executing Migration 016 to fix actual_execution column")
        
        # Import database connection
        from sqlalchemy import create_engine, text
        
        # Get DATABASE_URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("❌ DATABASE_URL environment variable not found")
            return False
            
        logger.info(f"📊 Connecting to database...")
        
        # Create engine and connect
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
                    VALUES (16, 'Add actual_execution and P&L columns for real ShareKhan data sync', CURRENT_TIMESTAMP)
                    ON CONFLICT (version) DO NOTHING
                """))
                
                # Commit transaction
                trans.commit()
                
                # Verify the columns exist
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = 'trades' 
                    AND column_name IN ('actual_execution', 'current_price', 'pnl', 'pnl_percent')
                    ORDER BY column_name
                """))
                
                columns = result.fetchall()
                
                logger.info("✅ Migration 016 executed successfully!")
                logger.info(f"✅ Updated {updated_rows} existing trades")
                logger.info(f"✅ Created columns: {[col[0] for col in columns]}")
                
                print(f"\n🎯 MIGRATION 016 SUCCESS:")
                print(f"   ✅ Added actual_execution column")
                print(f"   ✅ Added current_price column") 
                print(f"   ✅ Added pnl column")
                print(f"   ✅ Added pnl_percent column")
                print(f"   ✅ Created indexes")
                print(f"   ✅ Updated {updated_rows} existing trades")
                print(f"   ✅ Migration logged in schema_migrations")
                print(f"\n🚀 SHAREKHAN SYNC WILL NOW WORK WITHOUT DATABASE ERRORS!")
                
                return True
                
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Migration 016 failed: {e}")
                print(f"\n❌ MIGRATION 016 FAILED: {e}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Database migration error: {e}")
        print(f"\n❌ DATABASE CONNECTION ERROR: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Migration 016 - Fix ShareKhan Sync Database Schema")
    print("=" * 60)
    
    success = asyncio.run(execute_migration_016())
    
    if success:
        print("\n" + "=" * 60)
        print("✅ MIGRATION 016 COMPLETED SUCCESSFULLY!")
        print("🎯 ShareKhan sync database errors are now FIXED!")
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ MIGRATION 016 FAILED!")
        print("🚨 Database schema issues remain")
        sys.exit(1) 