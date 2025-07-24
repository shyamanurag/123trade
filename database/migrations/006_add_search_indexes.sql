-- Migration: Add Comprehensive Search Indexes and Full-Text Search
-- Version: 006
-- Date: 2024-12-12
-- Description: Add full-text search indexes and search-optimized functions for fast search across all entities

BEGIN;

-- Add GIN indexes for full-text search on symbols table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_symbols_fulltext_search 
ON symbols USING gin(to_tsvector('english', coalesce(symbol, '') || ' ' || coalesce(name, '')));

-- Add trigram indexes for fuzzy search on symbols
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_symbols_symbol_trgm 
ON symbols USING gin(symbol gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_symbols_name_trgm 
ON symbols USING gin(name gin_trgm_ops);

-- Add search-optimized indexes for trades table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_search_composite 
ON trades(user_id, symbol, strategy_name, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_fulltext_search 
ON trades USING gin(to_tsvector('english', coalesce(symbol, '') || ' ' || coalesce(strategy_name, '') || ' ' || coalesce(trade_id, '')));

-- Add search indexes for strategies table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_strategies_fulltext_search 
ON strategies USING gin(to_tsvector('english', coalesce(name, '') || ' ' || coalesce(description, '')));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_strategies_name_trgm 
ON strategies USING gin(name gin_trgm_ops);

-- Add search indexes for users table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_fulltext_search 
ON users USING gin(to_tsvector('english', coalesce(username, '') || ' ' || coalesce(email, '') || ' ' || coalesce(full_name, '')));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_username_trgm 
ON users USING gin(username gin_trgm_ops);

-- Add search indexes for recommendations table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recommendations_fulltext_search 
ON recommendations USING gin(to_tsvector('english', coalesce(symbol, '') || ' ' || coalesce(strategy, '') || ' ' || coalesce(reason, '')));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recommendations_search_composite 
ON recommendations(status, symbol, recommendation_type, created_at DESC);

-- Add search indexes for orders table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_fulltext_search 
ON orders USING gin(to_tsvector('english', coalesce(symbol, '') || ' ' || coalesce(strategy_name, '') || ' ' || coalesce(order_id, '')));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_search_composite 
ON orders(user_id, symbol, status, created_at DESC);

-- Add search indexes for positions table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_search_composite 
ON positions(user_id, symbol, status, updated_at DESC);

-- Add search indexes for market_data table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_data_search_composite 
ON market_data(symbol, provider, timestamp DESC);

-- Create search helper functions
CREATE OR REPLACE FUNCTION search_symbols(search_query TEXT, search_limit INTEGER DEFAULT 20)
RETURNS TABLE (
    symbol VARCHAR(20),
    name VARCHAR(100),
    exchange VARCHAR(20),
    symbol_type VARCHAR(20),
    relevance_score INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.symbol,
        s.name,
        s.exchange,
        s.symbol_type,
        CASE 
            WHEN s.symbol ILIKE search_query || '%' THEN 1
            WHEN s.name ILIKE search_query || '%' THEN 2
            WHEN s.symbol ILIKE '%' || search_query || '%' THEN 3
            WHEN s.name ILIKE '%' || search_query || '%' THEN 4
            ELSE 5
        END as relevance_score
    FROM symbols s
    WHERE s.symbol ILIKE '%' || search_query || '%' 
       OR s.name ILIKE '%' || search_query || '%'
       OR to_tsvector('english', coalesce(s.symbol, '') || ' ' || coalesce(s.name, '')) @@ plainto_tsquery('english', search_query)
    ORDER BY relevance_score, s.symbol
    LIMIT search_limit;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION search_trades(
    search_query TEXT DEFAULT NULL,
    user_filter INTEGER DEFAULT NULL,
    symbol_filter TEXT DEFAULT NULL,
    strategy_filter TEXT DEFAULT NULL,
    status_filter TEXT DEFAULT NULL,
    start_date_filter TIMESTAMP DEFAULT NULL,
    end_date_filter TIMESTAMP DEFAULT NULL,
    search_limit INTEGER DEFAULT 20,
    search_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    trade_id VARCHAR(50),
    user_id INTEGER,
    symbol VARCHAR(20),
    side VARCHAR(10),
    quantity INTEGER,
    price DECIMAL(10,2),
    pnl DECIMAL(10,2),
    status VARCHAR(20),
    strategy_name VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE,
    executed_at TIMESTAMP WITH TIME ZONE,
    username VARCHAR(100),
    total_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.trade_id,
        t.user_id,
        t.symbol,
        t.side,
        t.quantity,
        t.price,
        t.pnl,
        t.status,
        t.strategy_name,
        t.created_at,
        t.executed_at,
        u.username,
        COUNT(*) OVER() as total_count
    FROM trades t
    LEFT JOIN users u ON t.user_id = u.id
    WHERE 
        (search_query IS NULL OR 
         t.symbol ILIKE '%' || search_query || '%' OR 
         t.strategy_name ILIKE '%' || search_query || '%' OR 
         t.trade_id ILIKE '%' || search_query || '%' OR
         to_tsvector('english', coalesce(t.symbol, '') || ' ' || coalesce(t.strategy_name, '') || ' ' || coalesce(t.trade_id, '')) @@ plainto_tsquery('english', search_query))
        AND (user_filter IS NULL OR t.user_id = user_filter)
        AND (symbol_filter IS NULL OR t.symbol = symbol_filter)
        AND (strategy_filter IS NULL OR t.strategy_name ILIKE '%' || strategy_filter || '%')
        AND (status_filter IS NULL OR t.status = status_filter)
        AND (start_date_filter IS NULL OR t.created_at >= start_date_filter)
        AND (end_date_filter IS NULL OR t.created_at <= end_date_filter)
    ORDER BY t.created_at DESC
    LIMIT search_limit OFFSET search_offset;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION search_strategies(
    search_query TEXT DEFAULT NULL,
    is_active_filter BOOLEAN DEFAULT NULL,
    search_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    strategy_id VARCHAR(50),
    name VARCHAR(100),
    description TEXT,
    parameters JSONB,
    is_active BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.strategy_id,
        s.name,
        s.description,
        s.parameters,
        s.is_active,
        s.created_at,
        s.updated_at
    FROM strategies s
    WHERE 
        (search_query IS NULL OR 
         s.name ILIKE '%' || search_query || '%' OR 
         s.description ILIKE '%' || search_query || '%' OR
         to_tsvector('english', coalesce(s.name, '') || ' ' || coalesce(s.description, '')) @@ plainto_tsquery('english', search_query))
        AND (is_active_filter IS NULL OR s.is_active = is_active_filter)
    ORDER BY s.name
    LIMIT search_limit;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION search_recommendations(
    search_query TEXT DEFAULT NULL,
    symbol_filter TEXT DEFAULT NULL,
    recommendation_type_filter TEXT DEFAULT NULL,
    status_filter TEXT DEFAULT NULL,
    search_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    recommendation_id INTEGER,
    symbol VARCHAR(20),
    recommendation_type VARCHAR(20),
    entry_price DECIMAL(10,2),
    target_price DECIMAL(10,2),
    stop_loss DECIMAL(10,2),
    confidence DECIMAL(5,2),
    strategy VARCHAR(50),
    reason TEXT,
    status VARCHAR(20),
    validity_start TIMESTAMP WITH TIME ZONE,
    validity_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.recommendation_id,
        r.symbol,
        r.recommendation_type,
        r.entry_price,
        r.target_price,
        r.stop_loss,
        r.confidence,
        r.strategy,
        r.reason,
        r.status,
        r.validity_start,
        r.validity_end,
        r.created_at
    FROM recommendations r
    WHERE 
        (search_query IS NULL OR 
         r.symbol ILIKE '%' || search_query || '%' OR 
         r.strategy ILIKE '%' || search_query || '%' OR 
         r.reason ILIKE '%' || search_query || '%' OR
         to_tsvector('english', coalesce(r.symbol, '') || ' ' || coalesce(r.strategy, '') || ' ' || coalesce(r.reason, '')) @@ plainto_tsquery('english', search_query))
        AND (symbol_filter IS NULL OR r.symbol = symbol_filter)
        AND (recommendation_type_filter IS NULL OR r.recommendation_type = recommendation_type_filter)
        AND (status_filter IS NULL OR r.status = status_filter)
    ORDER BY r.created_at DESC
    LIMIT search_limit;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION global_search(
    search_query TEXT,
    search_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    entity_type TEXT,
    entity_id TEXT,
    title TEXT,
    description TEXT,
    metadata JSONB,
    relevance_score INTEGER
) AS $$
BEGIN
    RETURN QUERY
    -- Search symbols
    SELECT 
        'symbol' as entity_type,
        s.symbol as entity_id,
        s.symbol || ' - ' || COALESCE(s.name, '') as title,
        s.exchange || ' | ' || s.symbol_type as description,
        jsonb_build_object('exchange', s.exchange, 'type', s.symbol_type, 'lot_size', s.lot_size) as metadata,
        CASE 
            WHEN s.symbol ILIKE search_query || '%' THEN 1
            WHEN s.name ILIKE search_query || '%' THEN 2
            ELSE 3
        END as relevance_score
    FROM symbols s
    WHERE s.symbol ILIKE '%' || search_query || '%' 
       OR s.name ILIKE '%' || search_query || '%'
    
    UNION ALL
    
    -- Search recent trades
    SELECT 
        'trade' as entity_type,
        t.trade_id as entity_id,
        t.symbol || ' ' || t.side || ' ' || t.quantity::text as title,
        'Strategy: ' || COALESCE(t.strategy_name, 'Unknown') || ' | PnL: ' || COALESCE(t.pnl::text, '0') as description,
        jsonb_build_object('symbol', t.symbol, 'side', t.side, 'quantity', t.quantity, 'pnl', t.pnl) as metadata,
        2 as relevance_score
    FROM trades t
    WHERE t.symbol ILIKE '%' || search_query || '%' 
       OR t.strategy_name ILIKE '%' || search_query || '%'
    ORDER BY t.created_at DESC
    LIMIT (search_limit / 4)
    
    UNION ALL
    
    -- Search strategies
    SELECT 
        'strategy' as entity_type,
        s.strategy_id as entity_id,
        s.name as title,
        COALESCE(s.description, 'No description') as description,
        jsonb_build_object('is_active', s.is_active) as metadata,
        1 as relevance_score
    FROM strategies s
    WHERE s.name ILIKE '%' || search_query || '%' 
       OR s.description ILIKE '%' || search_query || '%'
    
    UNION ALL
    
    -- Search recommendations
    SELECT 
        'recommendation' as entity_type,
        r.recommendation_id::text as entity_id,
        r.symbol || ' - ' || r.recommendation_type as title,
        'Entry: ' || r.entry_price::text || ' | Target: ' || COALESCE(r.target_price::text, 'N/A') as description,
        jsonb_build_object('symbol', r.symbol, 'type', r.recommendation_type, 'status', r.status) as metadata,
        2 as relevance_score
    FROM recommendations r
    WHERE r.symbol ILIKE '%' || search_query || '%' 
       OR r.strategy ILIKE '%' || search_query || '%'
    ORDER BY r.created_at DESC
    LIMIT (search_limit / 4)
    
    ORDER BY relevance_score, title
    LIMIT search_limit;
END;
$$ LANGUAGE plpgsql;

-- Create autocomplete function
CREATE OR REPLACE FUNCTION autocomplete_search(
    search_query TEXT,
    category_filter TEXT DEFAULT 'all',
    search_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    value TEXT,
    label TEXT,
    category TEXT,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM (
        -- Symbol autocomplete
        SELECT 
            s.symbol as value,
            s.symbol || CASE WHEN s.name IS NOT NULL THEN ' - ' || s.name ELSE '' END as label,
            'symbol' as category,
            jsonb_build_object('exchange', s.exchange, 'type', s.symbol_type) as metadata
        FROM symbols s
        WHERE (category_filter = 'all' OR category_filter = 'symbols')
          AND (s.symbol ILIKE search_query || '%' OR s.name ILIKE search_query || '%')
        ORDER BY 
            CASE 
                WHEN s.symbol ILIKE search_query || '%' THEN 1
                WHEN s.name ILIKE search_query || '%' THEN 2
                ELSE 3
            END,
            s.symbol
        LIMIT CASE WHEN category_filter = 'symbols' THEN search_limit ELSE search_limit / 2 END
        
        UNION ALL
        
        -- Strategy autocomplete
        SELECT 
            s.name as value,
            s.name as label,
            'strategy' as category,
            jsonb_build_object('is_active', s.is_active) as metadata
        FROM strategies s
        WHERE (category_filter = 'all' OR category_filter = 'strategies')
          AND s.name ILIKE search_query || '%'
        ORDER BY s.name
        LIMIT CASE WHEN category_filter = 'strategies' THEN search_limit ELSE search_limit / 2 END
    ) combined_results
    ORDER BY 
        CASE category
            WHEN 'symbol' THEN 1
            WHEN 'strategy' THEN 2
            ELSE 3
        END,
        label
    LIMIT search_limit;
END;
$$ LANGUAGE plpgsql;

-- Add search analytics table to track popular searches
CREATE TABLE IF NOT EXISTS search_analytics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    search_query TEXT NOT NULL,
    search_category TEXT,
    results_count INTEGER,
    clicked_result TEXT,
    search_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    response_time_ms INTEGER
);

-- Add index for search analytics
CREATE INDEX IF NOT EXISTS idx_search_analytics_query 
ON search_analytics(search_query);

CREATE INDEX IF NOT EXISTS idx_search_analytics_user_timestamp 
ON search_analytics(user_id, search_timestamp DESC);

-- Add search configuration table
CREATE TABLE IF NOT EXISTS search_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(50) UNIQUE NOT NULL,
    config_value JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default search configuration
INSERT INTO search_config (config_key, config_value) VALUES
('search_limits', '{"default": 20, "autocomplete": 10, "max": 100}'),
('search_weights', '{"exact_match": 1.0, "starts_with": 0.8, "contains": 0.6, "fuzzy": 0.4}'),
('search_categories', '["symbols", "trades", "strategies", "recommendations", "users"]'),
('search_filters', '{"enable_date_filter": true, "enable_user_filter": true, "enable_status_filter": true}')
ON CONFLICT (config_key) DO NOTHING;

-- Create trigger to update search config timestamp
CREATE OR REPLACE FUNCTION update_search_config_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_search_config_updated_at
    BEFORE UPDATE ON search_config
    FOR EACH ROW
    EXECUTE FUNCTION update_search_config_timestamp();

-- Add search performance indexes for existing tables
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_symbol_strategy_date 
ON trades(symbol, strategy_name, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_symbol_status_date 
ON orders(symbol, status, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_symbol_user_status 
ON positions(symbol, user_id, status);

-- Add partial indexes for active/recent data
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_recent_active 
ON trades(created_at DESC) WHERE created_at >= NOW() - INTERVAL '30 days';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_active_recent 
ON orders(created_at DESC) WHERE status IN ('PENDING', 'OPEN', 'PARTIAL');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recommendations_active 
ON recommendations(created_at DESC) WHERE status = 'ACTIVE';

COMMIT; 