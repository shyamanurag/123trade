-- Migration: Add Missing sharekhan_client_id Column
-- Version: 017
-- Date: 2025-07-29
-- Description: Add sharekhan_client_id column if missing (deployment fix)

BEGIN;

-- Add sharekhan_client_id column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'sharekhan_client_id'
    ) THEN
        ALTER TABLE users ADD COLUMN sharekhan_client_id VARCHAR(50);
        RAISE NOTICE 'Added sharekhan_client_id column to users table';
    ELSE
        RAISE NOTICE 'sharekhan_client_id column already exists in users table';
    END IF;
END $$;

-- Also add broker_user_id if missing (used in some queries)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'broker_user_id'
    ) THEN
        ALTER TABLE users ADD COLUMN broker_user_id VARCHAR(50);
        RAISE NOTICE 'Added broker_user_id column to users table';
    ELSE
        RAISE NOTICE 'broker_user_id column already exists in users table';
    END IF;
END $$;

-- Update paper trading user to not reference missing column
DO $$
BEGIN
    -- Update or insert paper trading user safely
    INSERT INTO users (
        username, 
        email, 
        password_hash, 
        full_name, 
        initial_capital, 
        current_balance, 
        is_active, 
        trading_enabled,
        broker_user_id,
        sharekhan_client_id
    ) VALUES (
        'PAPER_TRADER_001',
        'paper.trader@algoauto.com',
        'dummy_hash',
        'Autonomous Paper Trader',
        100000.00,
        100000.00,
        true,
        true,
        'QSW899',
        'QSW899'
    ) ON CONFLICT (username) DO UPDATE SET
        broker_user_id = EXCLUDED.broker_user_id,
        sharekhan_client_id = EXCLUDED.sharekhan_client_id,
        is_active = true,
        trading_enabled = true,
        updated_at = CURRENT_TIMESTAMP;
        
    RAISE NOTICE 'Paper trading user updated successfully';
END $$;

COMMIT; 