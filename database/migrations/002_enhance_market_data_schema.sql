-- Migration: Enhance Market Data Schema for Multi-Provider Support
-- Version: 002
-- Date: 2024-12-12
-- Description: Add provider support and tick data storage

BEGIN;

-- Add provider column to existing market_data table
ALTER TABLE market_data 
ADD COLUMN IF NOT EXISTS provider VARCHAR(20) DEFAULT 'unknown',
ADD COLUMN IF NOT EXISTS bid DECIMAL(10,4),
ADD COLUMN IF NOT EXISTS ask DECIMAL(10,4),
ADD COLUMN IF NOT EXISTS bid_quantity INTEGER,
ADD COLUMN IF NOT EXISTS ask_quantity INTEGER,
ADD COLUMN IF NOT EXISTS last_traded_quantity INTEGER,
ADD COLUMN IF NOT EXISTS average_traded_price DECIMAL(10,4),
ADD COLUMN IF NOT EXISTS change DECIMAL(10,4),
ADD COLUMN IF NOT EXISTS change_percent DECIMAL(6,2);

-- Create tick data table for high-frequency data
CREATE TABLE IF NOT EXISTS tick_data (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    provider VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    price DECIMAL(10,4) NOT NULL,
    quantity INTEGER,
    bid DECIMAL(10,4),
    ask DECIMAL(10,4),
    bid_quantity INTEGER,
    ask_quantity INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create hypertable for tick_data if using TimescaleDB
-- SELECT create_hypertable('tick_data', 'timestamp', if_not_exists => TRUE);

-- Create provider configuration table
CREATE TABLE IF NOT EXISTS data_providers (
    provider_id SERIAL PRIMARY KEY,
    provider_name VARCHAR(50) UNIQUE NOT NULL,
    provider_type VARCHAR(20) NOT NULL, -- 'market_data', 'broker', 'news'
    is_active BOOLEAN DEFAULT true,
    config JSONB,
    last_connected_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default providers
INSERT INTO data_providers (provider_name, provider_type, config) VALUES
('truedata', 'market_data', '{"port": 8086, "subscription_type": "tick"}'),
('zerodha', 'broker', '{"api_version": "3.0"}')
ON CONFLICT (provider_name) DO NOTHING;

-- Create symbol mapping table for different providers
CREATE TABLE IF NOT EXISTS symbol_mappings (
    id SERIAL PRIMARY KEY,
    standard_symbol VARCHAR(20) NOT NULL,
    provider VARCHAR(20) NOT NULL,
    provider_symbol VARCHAR(50) NOT NULL,
    instrument_token VARCHAR(50),
    exchange VARCHAR(10),
    segment VARCHAR(20),
    is_active BOOLEAN DEFAULT true,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(standard_symbol, provider)
);

-- Insert common symbol mappings
INSERT INTO symbol_mappings (standard_symbol, provider, provider_symbol, exchange) VALUES
('RELIANCE', 'truedata', 'RELIANCE-EQ', 'NSE'),
('RELIANCE', 'zerodha', 'RELIANCE', 'NSE'),
('TCS', 'truedata', 'TCS-EQ', 'NSE'),
('TCS', 'zerodha', 'TCS', 'NSE'),
('NIFTY', 'truedata', 'NIFTY-I', 'NSE'),
('NIFTY', 'zerodha', 'NIFTY 50', 'NSE'),
('BANKNIFTY', 'truedata', 'BANKNIFTY-I', 'NSE'),
('BANKNIFTY', 'zerodha', 'NIFTY BANK', 'NSE')
ON CONFLICT (standard_symbol, provider) DO NOTHING;

-- Create market data aggregation view
CREATE OR REPLACE VIEW latest_market_data AS
SELECT 
    m.symbol,
    m.provider,
    m.price,
    m.volume,
    m.bid,
    m.ask,
    m.high,
    m.low,
    m.open_price,
    m.change,
    m.change_percent,
    m.timestamp,
    sm.standard_symbol
FROM market_data m
LEFT JOIN symbol_mappings sm ON m.symbol = sm.provider_symbol AND m.provider = sm.provider
WHERE m.timestamp = (
    SELECT MAX(timestamp) 
    FROM market_data m2 
    WHERE m2.symbol = m.symbol AND m2.provider = m.provider
);

-- Add indexes for performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_data_provider_symbol_timestamp 
ON market_data(provider, symbol, timestamp DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tick_data_symbol_provider_timestamp 
ON tick_data(symbol, provider, timestamp DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tick_data_timestamp 
ON tick_data(timestamp DESC);

-- Add trigger to update market_data updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_data_providers_updated_at 
BEFORE UPDATE ON data_providers 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMIT; 