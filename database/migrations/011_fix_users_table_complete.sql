-- Migration: Complete Fix for Users Table and Paper Trading
-- Version: 011
-- Date: 2025-07-16
-- Description: Adds id column to users table and creates paper trading user

BEGIN;

-- Step 1: Add id column to users table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'id'
    ) THEN
        -- Add id column as SERIAL (auto-incrementing)
        ALTER TABLE users ADD COLUMN id SERIAL;
        RAISE NOTICE 'Added id column to users table';
    ELSE
        RAISE NOTICE 'id column already exists in users table';
    END IF;
END $$;

-- Step 2: Make id the primary key if no primary key exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.table_constraints 
        WHERE table_name = 'users' 
        AND constraint_type = 'PRIMARY KEY'
    ) THEN
        ALTER TABLE users ADD CONSTRAINT users_pkey PRIMARY KEY (id);
        RAISE NOTICE 'Added primary key constraint on id column';
    ELSE
        RAISE NOTICE 'Primary key already exists on users table';
    END IF;
END $$;

-- Step 3: Update existing users to have sequential ids if they don't have them
UPDATE users 
SET id = nextval('users_id_seq') 
WHERE id IS NULL;

-- Step 4: Create paper trading user if it doesn't exist
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
    max_position_size,
    created_at,
    updated_at
) 
SELECT 
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
    500000.00,
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE username = 'PAPER_TRADER_001'
);

-- Step 5: Create a default user with id=1 if no user with id=1 exists
INSERT INTO users (
    id,
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
    max_position_size,
    created_at,
    updated_at
) 
SELECT 
    1,
    'DEFAULT_USER',
    'default@algoauto.com',
    '$2b$12$dummy.hash.for.default.user',
    'Default Trading User',
    100000.00,
    100000.00,
    'medium',
    true,
    'DEFAULT_API_KEY',
    true,
    1000,
    500000.00,
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE id = 1
)
ON CONFLICT (id) DO NOTHING;

-- Step 6: Reset the sequence to ensure future inserts work correctly
SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 1));

-- Step 7: Verify the fix
DO $$
DECLARE
    user_count INTEGER;
    user_with_id_1 INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM users;
    SELECT COUNT(*) INTO user_with_id_1 FROM users WHERE id = 1;
    
    RAISE NOTICE 'Total users in database: %', user_count;
    RAISE NOTICE 'Users with id=1: %', user_with_id_1;
    
    IF user_with_id_1 = 0 THEN
        RAISE EXCEPTION 'Failed to create user with id=1';
    END IF;
END $$;

COMMIT;

-- Verification queries (run these after migration)
-- SELECT id, username, email, trading_enabled FROM users;
-- SELECT COUNT(*) FROM users WHERE id = 1; 