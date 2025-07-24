from sqlalchemy import Column, Integer, String, Float, DateTime, Index, ForeignKey, Table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class TickData(Base):
    __tablename__ = 'tick_data'
    __table_args__ = (
        Index('idx_tick_symbol_timestamp', 'symbol', 'timestamp'),
        {'postgresql_partition_by': 'RANGE (timestamp)'}
    )

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    price = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    bid = Column(Float)
    ask = Column(Float)
    bid_volume = Column(Integer)
    ask_volume = Column(Integer)
    additional_data = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)

class MinuteData(Base):
    __tablename__ = 'minute_data'
    __table_args__ = (
        Index('idx_minute_symbol_timestamp', 'symbol', 'timestamp'),
        {'postgresql_partition_by': 'RANGE (timestamp)'}
    )

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    additional_data = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)

class DailyData(Base):
    __tablename__ = 'daily_data'
    __table_args__ = (
        Index('idx_daily_symbol_date', 'symbol', 'date'),
        {'postgresql_partition_by': 'RANGE (date)'}
    )

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    date = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    additional_data = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create partition tables for each data type
def create_partition_tables(engine, start_date, end_date):
    """Create partition tables for the given date range."""
    # Create partitions for tick data
    engine.execute(f"""
        CREATE TABLE IF NOT EXISTS tick_data_{start_date.strftime('%Y%m')}
        PARTITION OF tick_data
        FOR VALUES FROM ('{start_date}') TO ('{end_date}');
    """)

    # Create partitions for minute data
    engine.execute(f"""
        CREATE TABLE IF NOT EXISTS minute_data_{start_date.strftime('%Y%m')}
        PARTITION OF minute_data
        FOR VALUES FROM ('{start_date}') TO ('{end_date}');
    """)

    # Create partitions for daily data
    engine.execute(f"""
        CREATE TABLE IF NOT EXISTS daily_data_{start_date.strftime('%Y%m')}
        PARTITION OF daily_data
        FOR VALUES FROM ('{start_date}') TO ('{end_date}');
    """)

def drop_old_partitions(engine, cutoff_date):
    """Drop partitions older than the cutoff date."""
    # Drop old tick data partitions
    engine.execute(f"""
        DROP TABLE IF EXISTS tick_data_{cutoff_date.strftime('%Y%m')};
    """)

    # Drop old minute data partitions
    engine.execute(f"""
        DROP TABLE IF EXISTS minute_data_{cutoff_date.strftime('%Y%m')};
    """)

    # Drop old daily data partitions
    engine.execute(f"""
        DROP TABLE IF EXISTS daily_data_{cutoff_date.strftime('%Y%m')};
    """) 