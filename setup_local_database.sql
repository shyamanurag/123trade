-- LOCAL DATABASE SETUP SCRIPT FOR CRYPTO TRADING
-- This script sets up the crypto trading system database locally on Windows
-- Run this script after installing PostgreSQL locally

-- Create the database (run this as postgres user)
-- psql -U postgres -c "CREATE DATABASE trading_system_local;"

-- Create the trading user
-- psql -U postgres -c "CREATE USER trading_user WITH PASSWORD 'trading_password_local';"

-- Grant permissions
-- psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE trading_system_local TO trading_user;"

-- Connect to the database
\c trading_system_local;

-- Create necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set search path
SET search_path TO trading, public;

-- Create users table (enhanced for crypto)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    
    -- Crypto-specific fields
    initial_balance DECIMAL(20,8) DEFAULT 10000,
    current_balance DECIMAL(20,8) DEFAULT 10000,
    api_key_binance VARCHAR(255),
    api_secret_binance VARCHAR(255),
    testnet_mode BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create crypto symbols table
CREATE TABLE IF NOT EXISTS symbols (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    exchange VARCHAR(20) NOT NULL DEFAULT 'BINANCE',
    symbol_type VARCHAR(20) NOT NULL DEFAULT 'SPOT',
    
    -- Crypto-specific parsing fields
    base_asset VARCHAR(10) NOT NULL,
    quote_asset VARCHAR(10) NOT NULL,
    min_qty DECIMAL(20,8) DEFAULT 0.00000001,
    max_qty DECIMAL(20,8) DEFAULT 1000000,
    step_size DECIMAL(20,8) DEFAULT 0.00000001,
    min_price DECIMAL(20,8) DEFAULT 0.00000001,
    max_price DECIMAL(20,8) DEFAULT 1000000,
    tick_size_price DECIMAL(20,8) DEFAULT 0.00000001,
    min_notional DECIMAL(20,8) DEFAULT 10,
    trading_status VARCHAR(20) DEFAULT 'TRADING',
    permissions JSONB DEFAULT '[]',
    filters JSONB DEFAULT '{}',
    
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create crypto market data table
CREATE TABLE IF NOT EXISTS crypto_market_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Price data
    open_price DECIMAL(20,8) NOT NULL,
    high_price DECIMAL(20,8) NOT NULL,
    low_price DECIMAL(20,8) NOT NULL,
    close_price DECIMAL(20,8) NOT NULL,
    
    -- Volume data
    volume DECIMAL(20,8) NOT NULL,
    quote_volume DECIMAL(20,8) NOT NULL,
    
    -- Trading data
    trade_count INTEGER DEFAULT 0,
    taker_buy_volume DECIMAL(20,8) DEFAULT 0,
    taker_buy_quote_volume DECIMAL(20,8) DEFAULT 0,
    
    -- Advanced metrics
    vwap DECIMAL(20,8),
    price_change DECIMAL(20,8) DEFAULT 0,
    price_change_percent DECIMAL(10,4) DEFAULT 0,
    weighted_avg_price DECIMAL(20,8),
    
    -- Market depth (top 5 levels)
    bid_prices DECIMAL(20,8)[] DEFAULT ARRAY[]::DECIMAL[],
    bid_quantities DECIMAL(20,8)[] DEFAULT ARRAY[]::DECIMAL[],
    ask_prices DECIMAL(20,8)[] DEFAULT ARRAY[]::DECIMAL[],
    ask_quantities DECIMAL(20,8)[] DEFAULT ARRAY[]::DECIMAL[],
    
    -- Additional data
    market_cap DECIMAL(30,2),
    circulating_supply DECIMAL(30,8),
    total_supply DECIMAL(30,8),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timestamp)
);

-- Create strategies table
CREATE TABLE IF NOT EXISTS strategies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    parameters JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create trades table (enhanced for crypto)
CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    strategy_id UUID REFERENCES strategies(id) ON DELETE SET NULL,
    symbol VARCHAR(20) NOT NULL,
    base_asset VARCHAR(10),
    quote_asset VARCHAR(10),
    trade_type VARCHAR(10) NOT NULL CHECK (trade_type IN ('BUY', 'SELL')),
    quantity DECIMAL(20,8) NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    order_type VARCHAR(20) NOT NULL DEFAULT 'MARKET',
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    
    -- Crypto-specific fields
    fees_paid DECIMAL(20,8) DEFAULT 0,
    slippage DECIMAL(20,8) DEFAULT 0,
    
    executed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create positions table (enhanced for crypto)
CREATE TABLE IF NOT EXISTS positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    base_asset VARCHAR(10),
    quote_asset VARCHAR(10),
    quantity DECIMAL(20,8) NOT NULL,
    entry_price DECIMAL(20,8) NOT NULL,
    current_price DECIMAL(20,8),
    
    -- P&L tracking
    realized_pnl DECIMAL(20,8) DEFAULT 0,
    unrealized_pnl DECIMAL(20,8) DEFAULT 0,
    fees_paid DECIMAL(20,8) DEFAULT 0,
    
    status VARCHAR(20) DEFAULT 'OPEN',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, symbol)
);

-- Create orders table (enhanced for crypto)
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    base_asset VARCHAR(10),
    quote_asset VARCHAR(10),
    order_type VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity DECIMAL(20,8) NOT NULL,
    price DECIMAL(20,8),
    stop_price DECIMAL(20,8),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    broker_order_id VARCHAR(100),
    filled_quantity DECIMAL(20,8) DEFAULT 0,
    average_fill_price DECIMAL(20,8),
    
    -- Execution tracking
    fees DECIMAL(20,8) DEFAULT 0,
    slippage DECIMAL(20,8) DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS audit.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create analytics tables
CREATE TABLE IF NOT EXISTS analytics.performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    total_pnl DECIMAL(20,8) DEFAULT 0,
    max_drawdown DECIMAL(10,4) DEFAULT 0,
    sharpe_ratio DECIMAL(8,4),
    
    -- Crypto-specific metrics
    btc_value DECIMAL(20,8) DEFAULT 0,
    eth_value DECIMAL(20,8) DEFAULT 0,
    alt_value DECIMAL(20,8) DEFAULT 0,
    stablecoin_value DECIMAL(20,8) DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, strategy_id, date)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_crypto_market_data_symbol_timestamp ON crypto_market_data(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_user_id ON trades(user_id);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_created_at ON trades(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_positions_user_id ON positions(user_id);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit.audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit.audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_symbols_exchange ON symbols(exchange);
CREATE INDEX IF NOT EXISTS idx_symbols_base_quote ON symbols(base_asset, quote_asset);

-- Insert default users for local testing
INSERT INTO users (username, email, password_hash, is_admin, initial_balance, current_balance) VALUES
('admin', 'admin@localhost', crypt('admin123', gen_salt('bf')), true, 50000, 50000),
('crypto_trader', 'trader@localhost', crypt('trader123', gen_salt('bf')), false, 10000, 10000)
ON CONFLICT (username) DO NOTHING;

-- CRITICAL: NO HARD-CODED SYMBOLS
-- Symbols should be populated dynamically from exchange APIs
-- This ensures real-time trading pairs and prevents stale data

-- Create a function to populate symbols from exchange API
CREATE OR REPLACE FUNCTION populate_exchange_symbols()
RETURNS void AS $$
BEGIN
    -- This function should be implemented to fetch symbols from Binance API
    -- and populate the symbols table with real-time data
    -- 
    -- Example implementation needed:
    -- 1. Connect to Binance Exchange Info API
    -- 2. Fetch active trading pairs
    -- 3. Insert/update symbols table with current data
    -- 4. Set appropriate min_qty, max_qty, step_size from exchange
    
    RAISE NOTICE 'Symbols should be populated dynamically from exchange API';
    RAISE NOTICE 'Implement exchange API integration for real symbol data';
END;
$$ LANGUAGE plpgsql;

-- Insert crypto trading strategies
INSERT INTO strategies (name, description, parameters) VALUES
('Crypto Momentum Surfer Enhanced', 'AI-enhanced momentum trading for crypto with multi-timeframe analysis', '{"risk_per_trade": 2.0, "max_positions": 3, "timeframes": ["1m", "5m", "15m"]}'),
('Crypto Confluence Amplifier Enhanced', 'Multi-strategy signal aggregation with edge intelligence', '{"min_confluence_signals": 2, "signal_weight_threshold": 0.7}'),
('Crypto News Impact Scalper Enhanced', 'Real-time news and social sentiment scalping', '{"viral_threshold": 0.8, "sentiment_window": 300}'),
('Crypto Volatility Explosion Enhanced', 'Black swan detection and volatility breakout trading', '{"volatility_threshold": 0.05, "black_swan_protection": true}'),
('Crypto Volume Profile Scalper Enhanced', 'Whale tracking and volume profile analysis', '{"whale_threshold": 100000, "volume_spike_multiplier": 3.0}'),
('Crypto Regime Adaptive Controller', 'Market regime detection and strategy adaptation', '{"regime_detection_window": 1440, "adaptation_sensitivity": 0.6}')
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    parameters = EXCLUDED.parameters,
    updated_at = CURRENT_TIMESTAMP;

-- Create functions for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_symbols_updated_at BEFORE UPDATE ON symbols
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_strategies_updated_at BEFORE UPDATE ON strategies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trades_updated_at BEFORE UPDATE ON trades
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_positions_updated_at BEFORE UPDATE ON positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create function for crypto symbol parsing
CREATE OR REPLACE FUNCTION parse_crypto_symbol(symbol_input VARCHAR(20))
RETURNS TABLE(
    symbol VARCHAR(20),
    base_asset VARCHAR(10),
    quote_asset VARCHAR(10),
    exchange VARCHAR(20)
) AS $$
BEGIN
    -- Parse Binance-style symbols (e.g., BTCUSDT)
    IF symbol_input ~ '^[A-Z]+USDT$' THEN
        RETURN QUERY SELECT 
            symbol_input,
            REGEXP_REPLACE(symbol_input, 'USDT$', ''),
            'USDT'::VARCHAR(10),
            'BINANCE'::VARCHAR(20);
    ELSIF symbol_input ~ '^[A-Z]+BTC$' THEN
        RETURN QUERY SELECT 
            symbol_input,
            REGEXP_REPLACE(symbol_input, 'BTC$', ''),
            'BTC'::VARCHAR(10),
            'BINANCE'::VARCHAR(20);
    ELSIF symbol_input ~ '^[A-Z]+ETH$' THEN
        RETURN QUERY SELECT 
            symbol_input,
            REGEXP_REPLACE(symbol_input, 'ETH$', ''),
            'ETH'::VARCHAR(10),
            'BINANCE'::VARCHAR(20);
    ELSE
        -- Default case - assume USDT pair
        RETURN QUERY SELECT 
            symbol_input || 'USDT',
            symbol_input,
            'USDT'::VARCHAR(10),
            'BINANCE'::VARCHAR(20);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create view for crypto portfolio overview
CREATE OR REPLACE VIEW crypto_portfolio_overview AS
SELECT 
    u.id as user_id,
    u.username,
    u.current_balance,
    COUNT(DISTINCT p.id) as open_positions,
    COUNT(DISTINCT CASE WHEN p.symbol LIKE '%USDT' THEN p.symbol END) as usdt_pairs,
    COUNT(DISTINCT CASE WHEN p.symbol LIKE '%BTC' THEN p.symbol END) as btc_pairs,
    COALESCE(SUM(p.unrealized_pnl), 0) as total_unrealized_pnl,
    COALESCE(SUM(p.realized_pnl), 0) as total_realized_pnl,
    COALESCE(SUM(CASE WHEN p.symbol = 'BTCUSDT' THEN p.unrealized_pnl ELSE 0 END), 0) as btc_pnl,
    COALESCE(SUM(CASE WHEN p.symbol = 'ETHUSDT' THEN p.unrealized_pnl ELSE 0 END), 0) as eth_pnl
FROM users u
LEFT JOIN positions p ON u.id = p.user_id AND p.status = 'OPEN'
GROUP BY u.id, u.username, u.current_balance;

-- Grant permissions to trading_user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA trading TO trading_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analytics TO trading_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA audit TO trading_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA trading TO trading_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA analytics TO trading_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA audit TO trading_user;
GRANT USAGE ON SCHEMA trading TO trading_user;
GRANT USAGE ON SCHEMA analytics TO trading_user;
GRANT USAGE ON SCHEMA audit TO trading_user;

-- Commit the changes
COMMIT;

-- Display setup completion message
SELECT 'Crypto database setup completed successfully!' AS message;
SELECT 'Available symbols:' AS info;
SELECT symbol, name, base_asset, quote_asset FROM symbols ORDER BY symbol;
SELECT 'Available strategies:' AS info;
SELECT name, description FROM strategies ORDER BY name; 