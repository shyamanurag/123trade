-- Migration: Reset Database
-- Version: 000
-- Date: 2024-01-15
-- Description: Drop and recreate all tables

BEGIN;

-- Drop existing tables in correct order
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS risk_metrics CASCADE;
DROP TABLE IF EXISTS user_metrics CASCADE;
DROP TABLE IF EXISTS recommendations CASCADE;
DROP TABLE IF EXISTS strategies CASCADE;
DROP TABLE IF EXISTS symbols CASCADE;
DROP TABLE IF EXISTS trades CASCADE;
DROP TABLE IF EXISTS positions CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS market_data CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Create users table first
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
    zerodha_client_id VARCHAR(50),
    last_login TIMESTAMP WITH TIME ZONE,
    trading_enabled BOOLEAN DEFAULT true,
    max_daily_trades INTEGER DEFAULT 100,
    max_position_size DECIMAL(15,2) DEFAULT 100000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create positions table
CREATE TABLE positions (
    position_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL,
    entry_price DECIMAL(10,2) NOT NULL,
    current_price DECIMAL(10,2),
    entry_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    exit_time TIMESTAMP WITH TIME ZONE,
    strategy VARCHAR(50),
    status VARCHAR(20) DEFAULT 'open',
    unrealized_pnl DECIMAL(12,2),
    realized_pnl DECIMAL(12,2),
    stop_loss DECIMAL(10,2),
    take_profit DECIMAL(10,2),
    trailing_stop BOOLEAN DEFAULT false,
    trailing_stop_distance DECIMAL(10,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create trades table
CREATE TABLE trades (
    trade_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    position_id INTEGER REFERENCES positions(position_id),
    symbol VARCHAR(20) NOT NULL,
    trade_type VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    order_id VARCHAR(50),
    strategy VARCHAR(50),
    commission DECIMAL(8,2) DEFAULT 0,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create orders table
CREATE TABLE orders (
    order_id VARCHAR(50) PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    broker_order_id VARCHAR(100),
    parent_order_id VARCHAR(50),
    symbol VARCHAR(20) NOT NULL,
    order_type VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2),
    stop_price DECIMAL(10,2),
    filled_quantity INTEGER DEFAULT 0,
    average_price DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'PENDING',
    execution_strategy VARCHAR(30),
    time_in_force VARCHAR(10) DEFAULT 'DAY',
    strategy_name VARCHAR(50),
    signal_id VARCHAR(50),
    fees DECIMAL(8,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    placed_at TIMESTAMP WITH TIME ZONE,
    filled_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create market data table
CREATE TABLE market_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    volume INTEGER,
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    open_price DECIMAL(10,2),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create user metrics table
CREATE TABLE user_metrics (
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

-- Create risk metrics table
CREATE TABLE risk_metrics (
    metric_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    portfolio_value DECIMAL(15,2),
    var_95 DECIMAL(10,2),
    exposure DECIMAL(10,2),
    leverage DECIMAL(5,2),
    risk_level VARCHAR(20),
    alerts JSONB
);

-- Create audit logs table
CREATE TABLE audit_logs (
    log_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id VARCHAR(50),
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_positions_user_id ON positions(user_id);
CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_trades_user_id ON trades(user_id);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_executed_at ON trades(executed_at);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_market_data_symbol ON market_data(symbol);
CREATE INDEX idx_market_data_timestamp ON market_data(timestamp);
CREATE INDEX idx_user_metrics_user_date ON user_metrics(user_id, date);
CREATE INDEX idx_risk_metrics_user_timestamp ON risk_metrics(user_id, timestamp);
CREATE INDEX idx_audit_logs_user_timestamp ON audit_logs(user_id, timestamp);

-- Insert hardcoded master trading user (always recreated after database reset)
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
);

COMMIT; 