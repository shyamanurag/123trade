-- Migration: Fix Foreign Key Constraints and Users Table Schema
-- Version: 012
-- Date: 2025-07-16
-- Description: Comprehensive fix for users table schema and foreign key constraints

BEGIN;

-- Step 1: Ensure users table has proper structure with id as primary key
DO $$
DECLARE
    has_id_column BOOLEAN;
    has_primary_key BOOLEAN;
    pk_column_name TEXT;
BEGIN
    -- Check if users table has id column
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'id'
    ) INTO has_id_column;
    
    -- Check what column is the primary key (if any)
    SELECT kcu.column_name INTO pk_column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu 
        ON tc.constraint_name = kcu.constraint_name
    WHERE tc.table_name = 'users' 
    AND tc.constraint_type = 'PRIMARY KEY'
    LIMIT 1;
    
    has_primary_key := (pk_column_name IS NOT NULL);
    
    RAISE NOTICE 'Users table analysis: has_id_column=%, has_primary_key=%, pk_column=%', 
                 has_id_column, has_primary_key, COALESCE(pk_column_name, 'none');
    
    -- Fix the table structure
    IF NOT has_id_column THEN
        -- Add id column as SERIAL PRIMARY KEY
        ALTER TABLE users ADD COLUMN id SERIAL PRIMARY KEY;
        RAISE NOTICE 'Added id column as primary key';
        
    ELSIF has_id_column AND NOT has_primary_key THEN
        -- Make existing id column the primary key
        ALTER TABLE users ADD CONSTRAINT users_pkey PRIMARY KEY (id);
        RAISE NOTICE 'Added primary key constraint to existing id column';
        
    ELSIF has_id_column AND has_primary_key AND pk_column_name != 'id' THEN
        -- Drop existing primary key and make id the primary key
        EXECUTE 'ALTER TABLE users DROP CONSTRAINT ' || (
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'users' AND constraint_type = 'PRIMARY KEY'
        );
        ALTER TABLE users ADD CONSTRAINT users_pkey PRIMARY KEY (id);
        RAISE NOTICE 'Changed primary key from % to id', pk_column_name;
    ELSE
        RAISE NOTICE 'Users table already has proper id primary key';
    END IF;
    
    -- Ensure id column has sequence if it doesn't
    IF has_id_column AND NOT EXISTS (
        SELECT 1 FROM pg_class c 
        JOIN pg_depend d ON d.objid = c.oid 
        JOIN pg_attribute a ON a.attrelid = d.refobjid 
        WHERE c.relkind = 'S' 
        AND a.attname = 'id' 
        AND a.attrelid = (SELECT oid FROM pg_class WHERE relname = 'users')
    ) THEN
        -- Create sequence and set it as default
        CREATE SEQUENCE IF NOT EXISTS users_id_seq;
        ALTER TABLE users ALTER COLUMN id SET DEFAULT nextval('users_id_seq');
        ALTER SEQUENCE users_id_seq OWNED BY users.id;
        
        -- Set the sequence to start after existing data
        PERFORM setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 0) + 1, false);
        RAISE NOTICE 'Created sequence for id column';
    END IF;
END $$;

-- Step 2: Update any NULL id values in existing users
UPDATE users 
SET id = nextval('users_id_seq') 
WHERE id IS NULL;

-- Step 3: Drop paper_trades table if it exists (will be recreated with proper foreign key)
DROP TABLE IF EXISTS paper_trades CASCADE;

-- Step 4: Create paper_trades table with proper foreign key constraint
CREATE TABLE paper_trades (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    action VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL,
    price FLOAT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    status VARCHAR(20) NOT NULL,
    order_id VARCHAR(50),
    pnl FLOAT,
    strategy VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Step 5: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_paper_trades_user_id ON paper_trades(user_id);
CREATE INDEX IF NOT EXISTS idx_paper_trades_symbol ON paper_trades(symbol);
CREATE INDEX IF NOT EXISTS idx_paper_trades_timestamp ON paper_trades(timestamp);

-- Step 6: Ensure default paper trading user exists
INSERT INTO users (
    username, 
    email, 
    password_hash, 
    full_name,
    is_active, 
    trading_enabled,
    initial_capital,
    current_balance,
    risk_tolerance,
    sharekhan_client_id,
    max_daily_trades,
    created_at, 
    updated_at
) VALUES (
    'PAPER_TRADER_001',
    'paper@algoauto.com',
    '$2b$12$dummy.hash.paper.trading',
    'Paper Trading Account',
    true,
    true,
    100000.0,
    100000.0,
    'medium',
    'PAPER',
    1000,
    NOW(),
    NOW()
) ON CONFLICT (username) DO UPDATE SET
    email = EXCLUDED.email,
    is_active = EXCLUDED.is_active,
    trading_enabled = EXCLUDED.trading_enabled,
    updated_at = NOW();

-- Step 7: Verify the fix worked
DO $$
DECLARE
    user_count INTEGER;
    constraint_exists BOOLEAN;
BEGIN
    -- Check user count
    SELECT COUNT(*) INTO user_count FROM users;
    RAISE NOTICE 'Total users after migration: %', user_count;
    
    -- Check foreign key constraint exists
    SELECT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_name = 'paper_trades' 
        AND constraint_type = 'FOREIGN KEY'
    ) INTO constraint_exists;
    
    IF constraint_exists THEN
        RAISE NOTICE '✅ Foreign key constraint properly created';
    ELSE
        RAISE WARNING '⚠️ Foreign key constraint not found';
    END IF;
END $$;

COMMIT;

-- Log completion
SELECT 'Migration 012 completed successfully - Users table and foreign keys fixed' AS migration_status; 