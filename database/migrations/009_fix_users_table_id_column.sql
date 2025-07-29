-- Migration: Fix Users Table ID Column
-- Version: 009
-- Date: 2025-07-15
-- Description: Fix missing 'id' column in users table that's preventing paper trading

BEGIN;

-- Check if users table exists and has id column
DO $$
BEGIN
    -- Check if users table exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') THEN
        -- Create users table with proper schema if it doesn't exist
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(150) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(200),
            initial_capital DECIMAL(15,2) DEFAULT 50000,
            current_balance DECIMAL(15,2) DEFAULT 50000,
            risk_tolerance VARCHAR(20) DEFAULT 'medium',
            is_active BOOLEAN DEFAULT true,
            sharekhan_client_id VARCHAR(50),
            last_login TIMESTAMP WITH TIME ZONE,
            trading_enabled BOOLEAN DEFAULT true,
            max_daily_trades INTEGER DEFAULT 100,
            max_position_size DECIMAL(15,2) DEFAULT 100000,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Create indexes
        CREATE INDEX idx_users_username ON users(username);
        CREATE INDEX idx_users_email ON users(email);
        
        RAISE NOTICE 'Created users table with id column';
        
    ELSE
        -- Check if id column exists
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'id') THEN
            -- Add missing id column as primary key
            
            -- First, add the id column as SERIAL
            ALTER TABLE users ADD COLUMN id SERIAL;
            
            -- Drop existing primary key if any
            ALTER TABLE users DROP CONSTRAINT IF EXISTS users_pkey;
            
            -- Set the new id column as primary key
            ALTER TABLE users ADD CONSTRAINT users_pkey PRIMARY KEY (id);
            
            RAISE NOTICE 'Added missing id column to existing users table';
        ELSE
            RAISE NOTICE 'Users table already has id column - no fix needed';
        END IF;
    END IF;
    
    -- Ensure at least one user exists for paper trading
    IF NOT EXISTS (SELECT 1 FROM users LIMIT 1) THEN
        -- Insert paper trading user
        INSERT INTO users (
            username, 
            email, 
            password_hash, 
            full_name, 
            initial_capital, 
            current_balance, 
            risk_tolerance, 
            is_active, 
            sharekhan_client_id,
            trading_enabled,
            max_daily_trades,
            max_position_size
        ) VALUES (
            'PAPER_TRADER_001',
            'paper.trader@algoauto.com',
            '$2b$12$dummy.hash.for.paper.trading.user.not.used.for.login',
            'AlgoAuto Paper Trading Master',
            100000.00,
            100000.00,
            'medium',
            true,
            'PAPER_API_KEY',
            true,
            1000,
            500000.00
        );
        
        RAISE NOTICE 'Created paper trading user';
    ELSE
        RAISE NOTICE 'Paper trading user already exists';
    END IF;
    
END $$;

-- Verify the fix
DO $$
DECLARE
    test_result INTEGER;
BEGIN
    -- Test that the problematic query now works
    SELECT id INTO test_result FROM users LIMIT 1;
    RAISE NOTICE 'SUCCESS: SELECT id FROM users query works correctly';
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'FAILED: SELECT id FROM users still failing: %', SQLERRM;
END $$;

COMMIT; 