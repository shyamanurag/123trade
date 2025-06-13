-- Migration: Add Performance Indexes
-- Version: 001
-- Date: 2024-01-15
-- Description: Add critical indexes for trading system performance

BEGIN;

-- Add indexes for trades table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_user_date 
ON trades(user_id, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_symbol_status 
ON trades(symbol, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_strategy 
ON trades(strategy_name, created_at);

-- Add indexes for orders table  
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_symbol_status 
ON orders(symbol, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_timestamp 
ON orders(user_id, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_strategy_status 
ON orders(strategy_name, status);

-- Add indexes for positions table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_user_symbol 
ON positions(user_id, symbol);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_status_updated 
ON positions(status, updated_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_strategy 
ON positions(strategy_name, created_at);

-- Add indexes for market_data table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_data_symbol_timestamp 
ON market_data(symbol, timestamp);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_data_provider_symbol 
ON market_data(provider, symbol, timestamp);

-- Add indexes for user_metrics table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_metrics_user_date 
ON user_metrics(user_id, date);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_metrics_pnl 
ON user_metrics(date, total_pnl);

-- Add indexes for risk_metrics table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_risk_metrics_user_timestamp 
ON risk_metrics(user_id, timestamp);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_risk_metrics_level 
ON risk_metrics(risk_level, timestamp);

-- Add composite indexes for common queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_user_symbol_date 
ON trades(user_id, symbol, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_status_date 
ON orders(user_id, status, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_user_status_symbol 
ON positions(user_id, status, symbol);

-- Add partial indexes for active records
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_active 
ON orders(user_id, created_at) WHERE status IN ('PENDING', 'PARTIAL');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_open 
ON positions(user_id, symbol, updated_at) WHERE status = 'OPEN';

-- Add indexes for audit trail
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_user_action 
ON audit_logs(user_id, action, timestamp);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_timestamp 
ON audit_logs(timestamp) WHERE action IN ('ORDER_PLACED', 'TRADE_EXECUTED');

COMMIT; 