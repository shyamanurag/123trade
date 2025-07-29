#!/usr/bin/env python3
"""
IMMEDIATE PRODUCTION DATABASE FIX
Adds the missing broker_user_id column to fix the critical production error.
"""

import os
import psycopg2
from urllib.parse import urlparse

def fix_production_database():
    """Apply immediate fix to production database"""
    print("🚨 APPLYING CRITICAL DATABASE FIX TO PRODUCTION...")
    
    try:
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL', 'postgresql://trading_user:secure_password@db-postgresql-nyc3-23093341-do-user-23093341-0.k.db.ondigitalocean.com:25060/defaultdb?sslmode=require')
        
        if not database_url:
            print("❌ DATABASE_URL not found")
            return False
        
        # Parse database URL
        parsed = urlparse(database_url)
        
        print(f"🔗 Connecting to production database: {parsed.hostname}:{parsed.port}")
        
        # Connect to database
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:] if parsed.path else 'defaultdb',
            sslmode='require'
        )
        
        cursor = conn.cursor()
        
        print("✅ Connected to production database")
        
        # Check if broker_user_id column exists
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'broker_user_id'
        """)
        
        if cursor.fetchone():
            print("✅ broker_user_id column already exists")
        else:
            print("🔧 Adding missing broker_user_id column...")
            cursor.execute("ALTER TABLE users ADD COLUMN broker_user_id VARCHAR(100)")
            print("✅ Added broker_user_id column")
        
        # Ensure PAPER_TRADER_001 user exists
        print("🔧 Ensuring PAPER_TRADER_001 user exists...")
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
        
        # Commit changes
        conn.commit()
        
        # Verify the fix
        cursor.execute("SELECT username, broker_user_id FROM users WHERE username = 'PAPER_TRADER_001'")
        result = cursor.fetchone()
        
        if result:
            print(f"✅ PAPER_TRADER_001 exists with broker_user_id: {result[1]}")
        else:
            print("❌ Failed to create PAPER_TRADER_001 user")
            return False
        
        cursor.close()
        conn.close()
        
        print("🎉 PRODUCTION DATABASE FIXED SUCCESSFULLY!")
        print("🚀 Trading system should now work without database errors")
        return True
        
    except Exception as e:
        print(f"❌ Database fix failed: {e}")
        return False

if __name__ == "__main__":
    success = fix_production_database()
    if success:
        print("\n✅ DATABASE FIX COMPLETE - System should be operational")
    else:
        print("\n❌ DATABASE FIX FAILED - Manual intervention required") 