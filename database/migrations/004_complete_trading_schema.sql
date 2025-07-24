-- Migration: Complete Trading System Schema
-- Version: 004
-- Date: 2024-01-15
-- Description: Add missing orders table and enhance schema for complete order/trade flow

BEGIN;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200),
    initial_capital DECIMAL(15,2) DEFAULT 50000,
    current_balance DECIMAL(15,2) DEFAULT 50000,
    risk_tolerance VARCHAR(20) DEFAULT 'medium',
    is_active BOOLEAN DEFAULT true,
    zerodha_client_id VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(50) PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    broker_order_id VARCHAR(100),
    parent_order_id VARCHAR(50),
    symbol VARCHAR(20) NOT NULL,
    order_type VARCHAR(20) NOT NULL, -- MARKET, LIMIT, STOP, STOP_LIMIT
    side VARCHAR(10) NOT NULL, -- BUY, SELL
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2),
    stop_price DECIMAL(10,2),
    filled_quantity INTEGER DEFAULT 0,
    average_price DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, OPEN, PARTIAL, FILLED, CANCELLED, REJECTED
    execution_strategy VARCHAR(30), -- MARKET, LIMIT, SMART, TWAP, VWAP, ICEBERG
    time_in_force VARCHAR(10) DEFAULT 'DAY', -- DAY, GTC, IOC, FOK
    strategy_name VARCHAR(50),
    signal_id VARCHAR(50),
    fees DECIMAL(8,2) DEFAULT 0,
    slippage DECIMAL(8,2) DEFAULT 0,
    market_impact DECIMAL(8,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    placed_at TIMESTAMP WITH TIME ZONE,
    filled_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB
);

-- Recommendations table (for elite recommendations)
CREATE TABLE IF NOT EXISTS recommendations (
    recommendation_id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    recommendation_type VARCHAR(20) NOT NULL, -- BUY, SELL, HOLD
    entry_price DECIMAL(10,2) NOT NULL,
    target_price DECIMAL(10,2),
    stop_loss DECIMAL(10,2),
    confidence DECIMAL(5,2),
    strategy VARCHAR(50),
    reason TEXT,
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, EXECUTED, EXPIRED, CANCELLED
    validity_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    validity_end TIMESTAMP WITH TIME ZONE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Symbols table (for available trading symbols)
CREATE TABLE IF NOT EXISTS symbols (
    symbol VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100),
    exchange VARCHAR(20),
    symbol_type VARCHAR(20), -- EQUITY, OPTION, FUTURE
    lot_size INTEGER DEFAULT 1,
    tick_size DECIMAL(10,4) DEFAULT 0.01,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Strategies table
CREATE TABLE IF NOT EXISTS strategies (
    strategy_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    parameters JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User metrics table (for performance tracking)
CREATE TABLE IF NOT EXISTS user_metrics (
    metric_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    total_pnl DECIMAL(12,2) DEFAULT 0,
    win_rate DECIMAL(5,2),
    avg_win DECIMAL(10,2),
    avg_loss DECIMAL(10,2),
    sharpe_ratio DECIMAL(5,2),
    max_drawdown DECIMAL(10,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, date)
);

-- Risk metrics table
CREATE TABLE IF NOT EXISTS risk_metrics (
    metric_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    portfolio_value DECIMAL(15,2),
    var_95 DECIMAL(10,2), -- Value at Risk 95%
    exposure DECIMAL(10,2),
    leverage DECIMAL(5,2),
    risk_level VARCHAR(20), -- LOW, MEDIUM, HIGH, CRITICAL
    alerts JSONB
);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50), -- ORDER, TRADE, POSITION
    entity_id VARCHAR(50),
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add foreign key constraints for trades table
ALTER TABLE trades ADD COLUMN IF NOT EXISTS position_id INTEGER REFERENCES positions(position_id);

-- Add missing columns to existing tables
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS trading_enabled BOOLEAN DEFAULT true;
ALTER TABLE users ADD COLUMN IF NOT EXISTS max_daily_trades INTEGER DEFAULT 100;
ALTER TABLE users ADD COLUMN IF NOT EXISTS max_position_size DECIMAL(15,2) DEFAULT 100000;

ALTER TABLE positions ADD COLUMN IF NOT EXISTS stop_loss DECIMAL(10,2);
ALTER TABLE positions ADD COLUMN IF NOT EXISTS take_profit DECIMAL(10,2);
ALTER TABLE positions ADD COLUMN IF NOT EXISTS trailing_stop BOOLEAN DEFAULT false;
ALTER TABLE positions ADD COLUMN IF NOT EXISTS trailing_stop_distance DECIMAL(10,2);

-- Create comprehensive indexes
CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_symbol_status ON orders(symbol, status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_strategy ON orders(strategy_name);
CREATE INDEX IF NOT EXISTS idx_orders_parent ON orders(parent_order_id) WHERE parent_order_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_recommendations_status ON recommendations(status);
CREATE INDEX IF NOT EXISTS idx_recommendations_symbol ON recommendations(symbol);
CREATE INDEX IF NOT EXISTS idx_recommendations_validity ON recommendations(validity_end) WHERE status = 'ACTIVE';

CREATE INDEX IF NOT EXISTS idx_user_metrics_user_date ON user_metrics(user_id, date);
CREATE INDEX IF NOT EXISTS idx_risk_metrics_user_time ON risk_metrics(user_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_time ON audit_logs(user_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);

-- Create views for common queries
CREATE OR REPLACE VIEW user_performance AS
SELECT 
    u.id as user_id,
    u.username,
    u.current_balance,
    COUNT(DISTINCT p.position_id) as open_positions,
    COUNT(DISTINCT t.trade_id) as total_trades,
    COALESCE(SUM(p.unrealized_pnl), 0) as total_unrealized_pnl,
    COALESCE(SUM(p.realized_pnl), 0) as total_realized_pnl
FROM users u
LEFT JOIN positions p ON u.id = p.user_id AND p.status = 'open'
LEFT JOIN trades t ON u.id = t.user_id
GROUP BY u.id, u.username, u.current_balance;

CREATE OR REPLACE VIEW active_orders AS
SELECT 
    o.*,
    u.username,
    u.current_balance
FROM orders o
JOIN users u ON o.user_id = u.id
WHERE o.status IN ('PENDING', 'OPEN', 'PARTIAL');

-- Create functions for data integrity
CREATE OR REPLACE FUNCTION update_user_balance_after_trade()
RETURNS TRIGGER AS $$
BEGIN
    -- Update user balance after trade execution
    UPDATE users 
    SET current_balance = current_balance + 
        CASE 
            WHEN NEW.trade_type = 'sell' THEN NEW.quantity * NEW.price - NEW.commission
            ELSE -(NEW.quantity * NEW.price + NEW.commission)
        END,
        updated_at = NOW()
    WHERE id = NEW.user_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_balance_after_trade
AFTER INSERT ON trades
FOR EACH ROW
EXECUTE FUNCTION update_user_balance_after_trade();

-- Create function to update position P&L
CREATE OR REPLACE FUNCTION calculate_position_pnl()
RETURNS TRIGGER AS $$
BEGIN
    -- Calculate unrealized P&L
    NEW.unrealized_pnl = (NEW.current_price - NEW.entry_price) * NEW.quantity;
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER calculate_pnl_on_update
BEFORE UPDATE OF current_price ON positions
FOR EACH ROW
EXECUTE FUNCTION calculate_position_pnl();

-- Insert hardcoded master trading user (recreated on every deployment)
INSERT INTO users (
    username, 
    email, 
    password_hash, 
    full_name, 
    initial_capital, 
    current_balance, 
    risk_tolerance, 
    is_active, 
    zerodha_client_id,
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
) ON CONFLICT (username) DO UPDATE SET
    email = EXCLUDED.email,
    full_name = EXCLUDED.full_name,
    initial_capital = EXCLUDED.initial_capital,
    current_balance = EXCLUDED.current_balance,
    risk_tolerance = EXCLUDED.risk_tolerance,
    is_active = EXCLUDED.is_active,
    zerodha_client_id = EXCLUDED.zerodha_client_id,
    trading_enabled = EXCLUDED.trading_enabled,
    max_daily_trades = EXCLUDED.max_daily_trades,
    max_position_size = EXCLUDED.max_position_size,
    updated_at = NOW();

COMMIT; 