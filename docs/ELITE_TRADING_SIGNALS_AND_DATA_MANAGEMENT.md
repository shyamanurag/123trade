# Elite Trading Signals and Data Management Documentation

## Overview

This document provides comprehensive information about the elite trading signal generation system, database schema for input data, and data management strategies including cleanup and retention policies to prevent database flooding.

## Table of Contents

1. [Elite Trading Signals](#elite-trading-signals)
2. [Database Schema](#database-schema)
3. [Data Input and Processing](#data-input-and-processing)
4. [Data Retention and Cleanup](#data-retention-and-cleanup)
5. [Performance Optimization](#performance-optimization)

---

## Elite Trading Signals

### 1. Elite Trade Recommendation Engine

The system generates only the highest conviction (10/10) trade opportunities through the `EliteRecommendationEngine`:

#### Key Components:

```python
@dataclass
class EliteTradeRecommendation:
    recommendation_id: str
    timestamp: datetime
    symbol: str
    strategy: str
    direction: str  # 'LONG' or 'SHORT'
    entry_price: float
    stop_loss: float
    primary_target: float
    secondary_target: float
    tertiary_target: float
    confidence_score: float  # Always 10.0
    timeframe: str
    valid_until: datetime
```

#### Signal Generation Process:

1. **Multi-Analyzer Approach** - All must score 9.9+ for signal generation:
   - Technical Analysis
   - Volume Analysis
   - Pattern Recognition
   - Market Regime Analysis
   - Momentum Analysis
   - Smart Money Flow

2. **Confluence Requirements**:
   - All timeframes must align
   - Volume confirmation required
   - Pattern completion verified
   - Market regime favorable
   - Smart money confirmation

3. **Risk Management**:
   - Position sizing: 5% base (adjusted by Kelly Criterion)
   - Risk per trade: 1% maximum
   - Multiple targets (2.5:1, 4:1, 6:1 R:R)

### 2. Strategy Types

- **Momentum Surfer**: Captures trending moves with volume confirmation
- **Volatility Explosion**: Straddle positions during volatility spikes
- **Mean Reversion**: Counter-trend trades at extremes
- **Volume Profile Scalper**: Trades based on volume clusters
- **News Impact Scalper**: Event-driven opportunities

---

## Database Schema

### 1. Core Tables

#### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    initial_capital DECIMAL(15,2) DEFAULT 50000,
    current_balance DECIMAL(15,2) DEFAULT 50000,
    risk_tolerance VARCHAR(20) DEFAULT 'medium',
    is_active BOOLEAN DEFAULT true,
    sharekhan_client_id VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Orders Table
```sql
CREATE TABLE orders (
    order_id VARCHAR(50) PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    broker_order_id VARCHAR(100),
    symbol VARCHAR(20) NOT NULL,
    order_type VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'PENDING',
    strategy_name VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB
);
```

#### Market Data Tables (Partitioned)
```sql
-- Tick Data (1-day retention)
CREATE TABLE tick_data (
    id SERIAL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    price FLOAT NOT NULL,
    volume INTEGER NOT NULL,
    bid FLOAT,
    ask FLOAT,
    additional_data JSONB
) PARTITION BY RANGE (timestamp);

-- Minute Data (7-day retention)
CREATE TABLE minute_data (
    id SERIAL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume INTEGER NOT NULL
) PARTITION BY RANGE (timestamp);

-- Daily Data (365-day retention)
CREATE TABLE daily_data (
    id SERIAL,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume INTEGER NOT NULL
) PARTITION BY RANGE (date);
```

#### Recommendations Table
```sql
CREATE TABLE recommendations (
    recommendation_id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    recommendation_type VARCHAR(20) NOT NULL,
    entry_price DECIMAL(10,2) NOT NULL,
    target_price DECIMAL(10,2),
    stop_loss DECIMAL(10,2),
    confidence DECIMAL(5,2),
    strategy VARCHAR(50),
    status VARCHAR(20) DEFAULT 'ACTIVE',
    validity_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 2. Performance Tables

```sql
CREATE TABLE user_metrics (
    metric_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    date DATE NOT NULL,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    total_pnl DECIMAL(12,2) DEFAULT 0,
    win_rate DECIMAL(5,2),
    sharpe_ratio DECIMAL(5,2),
    max_drawdown DECIMAL(10,2),
    UNIQUE(user_id, date)
);

CREATE TABLE risk_metrics (
    metric_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    portfolio_value DECIMAL(15,2),
    var_95 DECIMAL(10,2),
    exposure DECIMAL(10,2),
    risk_level VARCHAR(20)
);
```

---

## Data Input and Processing

### 1. Data Manager (`src/core/data_manager.py`)

The DataManager handles all incoming market data with:

#### Throttling
- Maximum 100 messages per second
- Sliding window rate limiting
- Queue-based message handling

#### Validation
```python
required_fields = {
    "tick_data": ["timestamp", "symbol", "price", "volume"],
    "minute_data": ["timestamp", "symbol", "open", "high", "low", "close", "volume"],
    "daily_data": ["date", "symbol", "open", "high", "low", "close", "volume"]
}
```

#### Processing Pipeline
1. Rate limit check
2. Data validation
3. Type-specific processing
4. Database storage
5. Partition management

### 2. Real-time Data Flow

```
ShareKhan API → WebSocket → Data Manager → Validation → Database
                    ↓
            Strategy Engines → Signal Generation → Order Execution
```

---

## Data Retention and Cleanup

### 1. Retention Policies

| Data Type | Retention Period | Cleanup Frequency |
|-----------|-----------------|-------------------|
| Tick Data | 1 day | Hourly |
| Minute Data | 7 days | Daily |
| Daily Data | 365 days | Weekly |
| Orders | 7 years | Never (Compliance) |
| Trades | 7 years | Never (Compliance) |
| Positions | 1 year | Monthly |
| Logs | 180 days | Daily |
| Alerts | 5 years | Yearly |

### 2. Automated Cleanup Implementation

#### Database Partitioning
```python
async def _cleanup_old_data(self):
    """Clean up data older than retention periods"""
    for data_type, retention in self.retention_periods.items():
        cutoff_date = now - retention
        
        # Drop old partitions
        await self.db_session.execute(
            f"DROP TABLE IF EXISTS {data_type}_{cutoff_date.strftime('%Y%m')}"
        )
        
        # Create new partitions for next month
        create_partition_tables(self.db_session.get_bind(), now, next_month)
```

#### Redis Cleanup
```python
async def cleanup_old_data(self, user_id: str, days_to_keep: int = 30):
    """Clean up old order and position data from Redis"""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    # Scan and delete old keys
    async for key in self.redis.scan_iter(f"user:{user_id}:orders:*"):
        date_str = key.split(':')[-1]
        if datetime.strptime(date_str, '%Y%m%d') < cutoff_date:
            await self.redis.delete(key)
```

### 3. Archive Strategy

#### Daily Archival Process
```python
class DataRetentionManager:
    async def archive_daily_data(self, date: datetime):
        # Archive orders, trades, positions
        await self._archive_orders(date)
        await self._archive_trades(date)
        
        # Compress and encrypt
        if self.compression_enabled:
            # ZIP compression
        if self.encryption_enabled:
            # AES encryption
```

### 4. Performance Optimization

#### Strategies to Prevent Database Flooding:

1. **Partitioning**: Automatic monthly partitions for time-series data
2. **Indexing**: Strategic indexes on frequently queried columns
3. **Compression**: Archive old data with ZIP compression
4. **Aggregation**: Convert tick data to minute/hourly aggregates
5. **Cold Storage**: Move old data to cheaper storage solutions

#### Monitoring and Alerts:
```python
# Database size monitoring
if database_size > threshold:
    trigger_cleanup()
    send_alert("Database size exceeded threshold")

# Partition count monitoring
if partition_count > max_partitions:
    drop_oldest_partitions()
```

---

## Best Practices

### 1. Data Input
- Validate all incoming data
- Use batch inserts for efficiency
- Implement circuit breakers for data floods
- Monitor data quality metrics

### 2. Storage Optimization
- Use appropriate data types
- Implement table partitioning
- Regular VACUUM and ANALYZE
- Monitor table bloat

### 3. Cleanup Operations
- Schedule during low-activity periods
- Use CASCADE deletes carefully
- Maintain audit trail before deletion
- Test cleanup scripts in staging

### 4. Compliance Considerations
- Never delete regulatory required data
- Maintain encrypted backups
- Document all data retention policies
- Regular compliance audits

---

## Monitoring Dashboard Queries

### Database Health
```sql
-- Table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Partition count
SELECT 
    parent.relname AS parent_table,
    COUNT(*) AS partition_count
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
GROUP BY parent.relname;
```

### Data Quality
```sql
-- Missing data check
SELECT 
    symbol,
    DATE(timestamp) as date,
    COUNT(*) as tick_count,
    COUNT(*) * 100.0 / (6.5 * 60 * 60) as data_completeness
FROM tick_data
WHERE timestamp >= NOW() - INTERVAL '1 day'
GROUP BY symbol, DATE(timestamp);
```

---

## Emergency Procedures

### Database Full
1. Execute emergency cleanup script
2. Drop oldest non-critical partitions
3. Archive to external storage
4. Scale up database resources

### Data Corruption
1. Stop data ingestion
2. Isolate corrupted partitions
3. Restore from latest backup
4. Replay from transaction logs

### Performance Degradation
1. Check running queries
2. Update table statistics
3. Review index usage
4. Consider partition pruning

---

This documentation should be reviewed and updated quarterly to ensure alignment with current system capabilities and regulatory requirements. 