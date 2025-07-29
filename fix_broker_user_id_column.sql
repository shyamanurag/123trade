-- FIX DATABASE SCHEMA: Add missing broker_user_id column
-- This fixes the "column broker_user_id of relation users does not exist" error

BEGIN;

-- Check if broker_user_id column exists, add if missing
DO $$
BEGIN
    -- Try to add the column
    BEGIN
        ALTER TABLE users ADD COLUMN broker_user_id VARCHAR(50);
        RAISE NOTICE 'Added broker_user_id column to users table';
    EXCEPTION
        WHEN duplicate_column THEN
            RAISE NOTICE 'broker_user_id column already exists, skipping...';
    END;
END $$;

-- Update existing users to have broker_user_id values
UPDATE users 
SET broker_user_id = COALESCE(broker_user_id, sharekhan_client_id, 'QSW899')
WHERE broker_user_id IS NULL OR broker_user_id = '';

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_users_broker_user_id ON users(broker_user_id);

COMMIT;

SELECT 'broker_user_id column fix completed' as status; 