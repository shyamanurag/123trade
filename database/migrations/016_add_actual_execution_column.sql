-- Migration 016: Add actual_execution column to trades table
-- Fixes: column "actual_execution" of relation "trades" does not exist

-- Add the missing actual_execution column
ALTER TABLE trades ADD COLUMN IF NOT EXISTS actual_execution BOOLEAN DEFAULT FALSE;

-- Add current_price column if it doesn't exist (for real-time P&L)
ALTER TABLE trades ADD COLUMN IF NOT EXISTS current_price DECIMAL(10,2);

-- Add pnl and pnl_percent columns if they don't exist
ALTER TABLE trades ADD COLUMN IF NOT EXISTS pnl DECIMAL(12,2) DEFAULT 0.0;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS pnl_percent DECIMAL(8,4) DEFAULT 0.0;

-- Create index for faster queries on actual executions
CREATE INDEX IF NOT EXISTS idx_trades_actual_execution ON trades(actual_execution);
CREATE INDEX IF NOT EXISTS idx_trades_current_price ON trades(current_price);

-- Update existing trades to mark them as non-actual (sent orders)
UPDATE trades SET actual_execution = FALSE WHERE actual_execution IS NULL;

-- Log the changes
INSERT INTO schema_migrations (version, description, executed_at) 
VALUES (16, 'Add actual_execution and P&L columns for real Sharekhan data sync', NOW())
ON CONFLICT (version) DO NOTHING; 