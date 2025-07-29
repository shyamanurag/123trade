-- EMERGENCY DATABASE SCHEMA FIX
-- Fix for missing sharekhan_client_id column in production

-- Check and add sharekhan_client_id column
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
    END IF;
END $$;

-- Check and add broker_user_id column  
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
    END IF;
END $$;

-- Update existing users with default values
UPDATE users 
SET sharekhan_client_id = 'DEFAULT_CLIENT_' || id::text,
    broker_user_id = 'BROKER_' || id::text
WHERE sharekhan_client_id IS NULL OR broker_user_id IS NULL; 