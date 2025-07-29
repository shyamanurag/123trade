#!/usr/bin/env python3
"""
CRITICAL DATABASE SCHEMA FIX
Fixes the missing broker_user_id column causing production errors
NO FALLBACKS - If it fails, it fails clearly
"""

import os
import sys
import logging
import psycopg2
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_database_schema():
    """Fix missing broker_user_id column - NO FALLBACKS"""
    try:
        logger.info("🔧 FIXING CRITICAL DATABASE SCHEMA ISSUE...")
        
        # Get database URL - FAIL if missing
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise Exception("DATABASE_URL environment variable not set")
        
        # Parse database URL
        parsed = urlparse(database_url)
        
        # Connect to database - FAIL if connection fails
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:] if parsed.path else 'defaultdb',
            sslmode='require'
        )
        
        cursor = conn.cursor()
        
        # Check if broker_user_id column exists
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'broker_user_id'
        """)
        
        if cursor.fetchone():
            logger.info("✅ broker_user_id column already exists")
        else:
            logger.info("🔧 Adding missing broker_user_id column...")
            cursor.execute("ALTER TABLE users ADD COLUMN broker_user_id VARCHAR(100)")
            logger.info("✅ Added broker_user_id column")
        
        # Ensure PAPER_TRADER_001 user exists with proper broker_user_id
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, broker_user_id, is_active, trading_enabled, 
                             full_name, initial_capital, current_balance, sharekhan_client_id)
            VALUES ('PAPER_TRADER_001', 'paper.trader@algoauto.com', 'dummy_hash', 'QSW899', true, true,
                   'Autonomous Paper Trader', 100000.00, 100000.00, 'QSW899')
            ON CONFLICT (username) DO UPDATE SET
                broker_user_id = EXCLUDED.broker_user_id,
                is_active = true,
                trading_enabled = true,
                updated_at = CURRENT_TIMESTAMP
        """)
        
        conn.commit()
        
        # Verify the fix
        cursor.execute("SELECT username, broker_user_id FROM users WHERE username = 'PAPER_TRADER_001'")
        result = cursor.fetchone()
        
        if result:
            logger.info(f"✅ PAPER_TRADER_001 exists with broker_user_id: {result[1]}")
        else:
            raise Exception("Failed to create PAPER_TRADER_001 user")
        
        cursor.close()
        conn.close()
        
        logger.info("✅ DATABASE SCHEMA FIXED SUCCESSFULLY!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database schema fix FAILED: {e}")
        raise e

def verify_fix():
    """Verify the database fix was applied correctly - NO FALLBACKS"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise Exception("DATABASE_URL environment variable not set")
            
        conn = psycopg2.connect(database_url)
        
        with conn.cursor() as cursor:
            # Check if broker_user_id column exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'broker_user_id'
                )
            """)
            result = cursor.fetchone()
            column_exists = result[0] if result else False
            
            if not column_exists:
                raise Exception("broker_user_id column does not exist")
                
            logger.info("✅ VERIFICATION: broker_user_id column exists")
            
            # Check if users have broker_user_id values
            cursor.execute("SELECT COUNT(*) FROM users WHERE broker_user_id IS NULL")
            result = cursor.fetchone()
            null_count = result[0] if result else 0
            
            if null_count > 0:
                raise Exception(f"{null_count} users still have NULL broker_user_id")
                
            logger.info("✅ VERIFICATION: All users have broker_user_id assigned")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Verification FAILED: {e}")
        raise e

if __name__ == "__main__":
    try:
        fix_database_schema()
        verify_fix()
        print("🎉 DATABASE FIX COMPLETED AND VERIFIED!")
    except Exception as e:
        print(f"💥 DATABASE FIX FAILED: {e}")
        sys.exit(1) 