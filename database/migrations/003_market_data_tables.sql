-- Create market data tables with partitioning
CREATE TABLE IF NOT EXISTS tick_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    price FLOAT NOT NULL,
    volume INTEGER NOT NULL,
    bid FLOAT,
    ask FLOAT,
    bid_volume INTEGER,
    ask_volume INTEGER,
    additional_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) PARTITION BY RANGE (timestamp);

CREATE TABLE IF NOT EXISTS minute_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume INTEGER NOT NULL,
    additional_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) PARTITION BY RANGE (timestamp);

CREATE TABLE IF NOT EXISTS daily_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    date TIMESTAMP NOT NULL,
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume INTEGER NOT NULL,
    additional_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) PARTITION BY RANGE (date);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_tick_symbol_timestamp ON tick_data (symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_minute_symbol_timestamp ON minute_data (symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_daily_symbol_date ON daily_data (symbol, date);

-- Create initial partitions for current month
DO $$
DECLARE
    current_month DATE := DATE_TRUNC('month', CURRENT_DATE);
    next_month DATE := current_month + INTERVAL '1 month';
BEGIN
    -- Create partitions for tick data
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS tick_data_%s PARTITION OF tick_data FOR VALUES FROM (%L) TO (%L)',
        TO_CHAR(current_month, 'YYYYMM'),
        current_month,
        next_month
    );

    -- Create partitions for minute data
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS minute_data_%s PARTITION OF minute_data FOR VALUES FROM (%L) TO (%L)',
        TO_CHAR(current_month, 'YYYYMM'),
        current_month,
        next_month
    );

    -- Create partitions for daily data
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS daily_data_%s PARTITION OF daily_data FOR VALUES FROM (%L) TO (%L)',
        TO_CHAR(current_month, 'YYYYMM'),
        current_month,
        next_month
    );
END $$;

-- Create function to automatically create partitions
CREATE OR REPLACE FUNCTION create_market_data_partitions()
RETURNS void AS $$
DECLARE
    current_month DATE := DATE_TRUNC('month', CURRENT_DATE);
    next_month DATE := current_month + INTERVAL '1 month';
BEGIN
    -- Create partitions for tick data
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS tick_data_%s PARTITION OF tick_data FOR VALUES FROM (%L) TO (%L)',
        TO_CHAR(current_month, 'YYYYMM'),
        current_month,
        next_month
    );

    -- Create partitions for minute data
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS minute_data_%s PARTITION OF minute_data FOR VALUES FROM (%L) TO (%L)',
        TO_CHAR(current_month, 'YYYYMM'),
        current_month,
        next_month
    );

    -- Create partitions for daily data
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS daily_data_%s PARTITION OF daily_data FOR VALUES FROM (%L) TO (%L)',
        TO_CHAR(current_month, 'YYYYMM'),
        current_month,
        next_month
    );
END;
$$ LANGUAGE plpgsql;

-- Create function to clean up old partitions
CREATE OR REPLACE FUNCTION cleanup_old_market_data_partitions(retention_days INTEGER)
RETURNS void AS $$
DECLARE
    cutoff_date DATE := CURRENT_DATE - (retention_days || ' days')::INTERVAL;
    partition_date DATE;
BEGIN
    -- Clean up tick data partitions
    FOR partition_date IN
        SELECT DISTINCT DATE_TRUNC('month', timestamp)::DATE
        FROM tick_data
        WHERE timestamp < cutoff_date
    LOOP
        EXECUTE format('DROP TABLE IF EXISTS tick_data_%s', TO_CHAR(partition_date, 'YYYYMM'));
    END LOOP;

    -- Clean up minute data partitions
    FOR partition_date IN
        SELECT DISTINCT DATE_TRUNC('month', timestamp)::DATE
        FROM minute_data
        WHERE timestamp < cutoff_date
    LOOP
        EXECUTE format('DROP TABLE IF EXISTS minute_data_%s', TO_CHAR(partition_date, 'YYYYMM'));
    END LOOP;

    -- Clean up daily data partitions
    FOR partition_date IN
        SELECT DISTINCT DATE_TRUNC('month', date)::DATE
        FROM daily_data
        WHERE date < cutoff_date
    LOOP
        EXECUTE format('DROP TABLE IF EXISTS daily_data_%s', TO_CHAR(partition_date, 'YYYYMM'));
    END LOOP;
END;
$$ LANGUAGE plpgsql; 