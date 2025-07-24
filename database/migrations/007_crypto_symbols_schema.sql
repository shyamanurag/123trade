-- Migration: Crypto Symbols Schema Update
-- Version: 007
-- Date: 2024-01-15
-- Description: Update database schema for crypto symbol parsing and enhanced market data

BEGIN;

-- Drop old stock-focused constraints and data
DELETE FROM symbols WHERE exchange IN ('NSE', 'BSE');

-- Update symbols table for crypto trading
ALTER TABLE symbols 
    DROP COLUMN IF EXISTS lot_size,
    DROP COLUMN IF EXISTS tick_size,
    ADD COLUMN IF NOT EXISTS base_asset VARCHAR(10),
    ADD COLUMN IF NOT EXISTS quote_asset VARCHAR(10),
    ADD COLUMN IF NOT EXISTS min_qty DECIMAL(20,8) DEFAULT 0.00000001,
    ADD COLUMN IF NOT EXISTS max_qty DECIMAL(20,8) DEFAULT 1000000,
    ADD COLUMN IF NOT EXISTS step_size DECIMAL(20,8) DEFAULT 0.00000001,
    ADD COLUMN IF NOT EXISTS min_price DECIMAL(20,8) DEFAULT 0.00000001,
    ADD COLUMN IF NOT EXISTS max_price DECIMAL(20,8) DEFAULT 1000000,
    ADD COLUMN IF NOT EXISTS tick_size_price DECIMAL(20,8) DEFAULT 0.00000001,
    ADD COLUMN IF NOT EXISTS min_notional DECIMAL(20,8) DEFAULT 10,
    ADD COLUMN IF NOT EXISTS trading_status VARCHAR(20) DEFAULT 'TRADING',
    ADD COLUMN IF NOT EXISTS permissions JSONB DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS filters JSONB DEFAULT '{}';

-- Update symbol_type for crypto
UPDATE symbols SET symbol_type = 'SPOT' WHERE symbol_type IN ('EQUITY', 'OPTION', 'FUTURE');

-- Create crypto_market_data table for enhanced crypto data
CREATE TABLE IF NOT EXISTS crypto_market_data (
    id SERIAL PRIMARY KEY,
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
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(symbol, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create crypto_tick_data for real-time data
CREATE TABLE IF NOT EXISTS crypto_tick_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Tick data
    price DECIMAL(20,8) NOT NULL,
    quantity DECIMAL(20,8) NOT NULL,
    
    -- Order book
    best_bid DECIMAL(20,8),
    best_ask DECIMAL(20,8),
    bid_quantity DECIMAL(20,8),
    ask_quantity DECIMAL(20,8),
    
    -- Trade info
    trade_id VARCHAR(50),
    is_buyer_maker BOOLEAN,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) PARTITION BY RANGE (timestamp);

-- Insert major crypto symbols with proper parsing
INSERT INTO symbols (
    symbol, name, exchange, symbol_type, 
    base_asset, quote_asset, min_qty, max_qty, step_size,
    min_price, max_price, tick_size_price, min_notional,
    is_active
) VALUES 
    ('BTCUSDT', 'Bitcoin', 'BINANCE', 'SPOT', 'BTC', 'USDT', 0.00001, 9000, 0.00001, 0.01, 1000000, 0.01, 10, true),
    ('ETHUSDT', 'Ethereum', 'BINANCE', 'SPOT', 'ETH', 'USDT', 0.00001, 90000, 0.00001, 0.01, 100000, 0.01, 10, true),
    ('ADAUSDT', 'Cardano', 'BINANCE', 'SPOT', 'ADA', 'USDT', 0.1, 90000000, 0.1, 0.0001, 1000, 0.0001, 10, true),
    ('DOTUSDT', 'Polkadot', 'BINANCE', 'SPOT', 'DOT', 'USDT', 0.01, 900000, 0.01, 0.001, 10000, 0.001, 10, true),
    ('LINKUSDT', 'Chainlink', 'BINANCE', 'SPOT', 'LINK', 'USDT', 0.01, 900000, 0.01, 0.001, 10000, 0.001, 10, true),
    ('BNBUSDT', 'Binance Coin', 'BINANCE', 'SPOT', 'BNB', 'USDT', 0.001, 90000, 0.001, 0.01, 10000, 0.01, 10, true),
    ('SOLUSDT', 'Solana', 'BINANCE', 'SPOT', 'SOL', 'USDT', 0.001, 900000, 0.001, 0.001, 10000, 0.001, 10, true),
    ('MATICUSDT', 'Polygon', 'BINANCE', 'SPOT', 'MATIC', 'USDT', 0.1, 90000000, 0.1, 0.0001, 1000, 0.0001, 10, true),
    ('AVAXUSDT', 'Avalanche', 'BINANCE', 'SPOT', 'AVAX', 'USDT', 0.001, 900000, 0.001, 0.001, 10000, 0.001, 10, true),
    ('ATOMUSDT', 'Cosmos', 'BINANCE', 'SPOT', 'ATOM', 'USDT', 0.001, 900000, 0.001, 0.001, 10000, 0.001, 10, true)
ON CONFLICT (symbol) DO UPDATE SET
    name = EXCLUDED.name,
    base_asset = EXCLUDED.base_asset,
    quote_asset = EXCLUDED.quote_asset,
    min_qty = EXCLUDED.min_qty,
    max_qty = EXCLUDED.max_qty,
    step_size = EXCLUDED.step_size,
    min_price = EXCLUDED.min_price,
    max_price = EXCLUDED.max_price,
    tick_size_price = EXCLUDED.tick_size_price,
    min_notional = EXCLUDED.min_notional,
    updated_at = NOW();

-- Create comprehensive indexes for crypto data
CREATE INDEX IF NOT EXISTS idx_crypto_market_data_symbol_timestamp ON crypto_market_data(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_crypto_market_data_timestamp ON crypto_market_data(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_crypto_tick_data_symbol_timestamp ON crypto_tick_data(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_symbols_exchange ON symbols(exchange);
CREATE INDEX IF NOT EXISTS idx_symbols_base_quote ON symbols(base_asset, quote_asset);
CREATE INDEX IF NOT EXISTS idx_symbols_type ON symbols(symbol_type);

-- Create partitions for crypto market data (current and next month)
DO $$
DECLARE
    current_month DATE := DATE_TRUNC('month', CURRENT_DATE);
    next_month DATE := current_month + INTERVAL '1 month';
BEGIN
    -- Create partitions for crypto market data
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS crypto_market_data_%s PARTITION OF crypto_market_data FOR VALUES FROM (%L) TO (%L)',
        TO_CHAR(current_month, 'YYYYMM'),
        current_month,
        next_month
    );

    -- Create partitions for crypto tick data
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS crypto_tick_data_%s PARTITION OF crypto_tick_data FOR VALUES FROM (%L) TO (%L)',
        TO_CHAR(current_month, 'YYYYMM'),
        current_month,
        next_month
    );
END $$;

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

-- Create function to get crypto market data with enhanced metrics
CREATE OR REPLACE FUNCTION get_crypto_market_summary(symbol_param VARCHAR(20))
RETURNS TABLE(
    symbol VARCHAR(20),
    current_price DECIMAL(20,8),
    price_change_24h DECIMAL(20,8),
    price_change_percent_24h DECIMAL(10,4),
    volume_24h DECIMAL(20,8),
    high_24h DECIMAL(20,8),
    low_24h DECIMAL(20,8),
    market_cap DECIMAL(30,2),
    last_updated TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cmd.symbol,
        cmd.close_price,
        cmd.price_change,
        cmd.price_change_percent,
        cmd.volume,
        cmd.high_price,
        cmd.low_price,
        cmd.market_cap,
        cmd.timestamp
    FROM crypto_market_data cmd
    WHERE cmd.symbol = symbol_param
    ORDER BY cmd.timestamp DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Update user metrics table for crypto trading
ALTER TABLE user_metrics 
    ADD COLUMN IF NOT EXISTS crypto_portfolio_value DECIMAL(20,8) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS btc_value DECIMAL(20,8) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS eth_value DECIMAL(20,8) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS alt_value DECIMAL(20,8) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS stablecoin_value DECIMAL(20,8) DEFAULT 0;

-- Create view for crypto portfolio overview
CREATE OR REPLACE VIEW crypto_portfolio_overview AS
SELECT 
    u.id as user_id,
    u.username,
    u.current_balance,
    COUNT(DISTINCT p.position_id) as open_positions,
    COUNT(DISTINCT CASE WHEN p.symbol LIKE '%USDT' THEN p.symbol END) as usdt_pairs,
    COUNT(DISTINCT CASE WHEN p.symbol LIKE '%BTC' THEN p.symbol END) as btc_pairs,
    COALESCE(SUM(p.unrealized_pnl), 0) as total_unrealized_pnl,
    COALESCE(SUM(p.realized_pnl), 0) as total_realized_pnl,
    COALESCE(SUM(CASE WHEN p.symbol = 'BTCUSDT' THEN p.unrealized_pnl ELSE 0 END), 0) as btc_pnl,
    COALESCE(SUM(CASE WHEN p.symbol = 'ETHUSDT' THEN p.unrealized_pnl ELSE 0 END), 0) as eth_pnl
FROM users u
LEFT JOIN positions p ON u.id = p.user_id AND p.status = 'open'
GROUP BY u.id, u.username, u.current_balance;

-- Create indexes for the new view
CREATE INDEX IF NOT EXISTS idx_positions_symbol_status ON positions(symbol, status);
CREATE INDEX IF NOT EXISTS idx_positions_user_symbol ON positions(user_id, symbol);

COMMIT; 