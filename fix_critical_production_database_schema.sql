-- CRITICAL FIX: Add missing broker_user_id column to users table
-- This fixes the "column broker_user_id of relation users does not exist" error

BEGIN;

-- Add the missing broker_user_id column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'broker_user_id'
    ) THEN
        ALTER TABLE users ADD COLUMN broker_user_id VARCHAR(100);
        RAISE NOTICE 'Added broker_user_id column to users table';
    ELSE
        RAISE NOTICE 'broker_user_id column already exists';
    END IF;
END $$;

-- Ensure all other essential columns exist
DO $$
BEGIN
    -- Check and add sharekhan_client_id if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'sharekhan_client_id'
    ) THEN
        ALTER TABLE users ADD COLUMN sharekhan_client_id VARCHAR(50);
        RAISE NOTICE 'Added sharekhan_client_id column to users table';
    END IF;
    
    -- Check and add trading_enabled if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'trading_enabled'
    ) THEN
        ALTER TABLE users ADD COLUMN trading_enabled BOOLEAN DEFAULT true;
        RAISE NOTICE 'Added trading_enabled column to users table';
    END IF;
    
    -- Check and add is_active if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'is_active'
    ) THEN
        ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT true;
        RAISE NOTICE 'Added is_active column to users table';
    END IF;
END $$;

-- Now ensure PAPER_TRADER_001 user exists with correct broker_user_id
INSERT INTO users (username, email, password_hash, broker_user_id, is_active, trading_enabled, 
                 full_name, initial_capital, current_balance, sharekhan_client_id)
VALUES ('PAPER_TRADER_001', 'paper.trader@algoauto.com', 'dummy_hash', 'QSW899', true, true,
       'Autonomous Paper Trader', 100000.00, 100000.00, 'QSW899')
ON CONFLICT (username) DO UPDATE SET
    broker_user_id = EXCLUDED.broker_user_id,
    is_active = true,
    trading_enabled = true,
    updated_at = CURRENT_TIMESTAMP;

COMMIT;

-- Verify the fix
SELECT username, broker_user_id, sharekhan_client_id, trading_enabled, is_active 
FROM users 
WHERE username = 'PAPER_TRADER_001'; 