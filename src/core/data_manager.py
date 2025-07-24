import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from collections import deque
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..core.config import Settings
from ..models.market_data import TickData, MinuteData, DailyData, create_partition_tables, drop_old_partitions

class DataManager:
    def __init__(self, config: Settings, db_session: AsyncSession):
        self.config = config
        self.db_session = db_session
        self.logger = logging.getLogger("data_manager")
        
        # Throttling settings
        self.max_messages_per_second = 100  # Maximum messages per second
        self.throttle_window = 1.0  # Time window in seconds
        self.message_queue = deque(maxlen=self.max_messages_per_second)
        self.last_cleanup = datetime.now()
        
        # Data retention settings
        self.retention_periods = {
            "tick_data": timedelta(days=1),  # Keep tick data for 1 day
            "minute_data": timedelta(days=7),  # Keep minute data for 7 days
            "daily_data": timedelta(days=365),  # Keep daily data for 1 year
        }
        
        # Data validation settings
        self.required_fields = {
            "tick_data": ["timestamp", "symbol", "price", "volume"],
            "minute_data": ["timestamp", "symbol", "open", "high", "low", "close", "volume"],
            "daily_data": ["date", "symbol", "open", "high", "low", "close", "volume"]
        }
        
        self._is_running = False
        self._cleanup_interval = 3600  # Run cleanup every hour

    async def start(self):
        """Start the data manager background tasks."""
        if not self._is_running:
            self._is_running = True
            asyncio.create_task(self._cleanup_task())
            self.logger.info("Data manager started")

    async def stop(self):
        """Stop the data manager."""
        self._is_running = False
        self.logger.info("Data manager stopped")

    async def process_incoming_data(self, data: Dict[str, Any]) -> bool:
        """
        Process incoming data with throttling and validation.
        Returns True if data was processed, False if throttled.
        """
        try:
            # Check if we need to throttle
            if not self._should_process_message():
                self.logger.warning("Message throttled due to rate limit")
                return False

            # Validate data
            if not self._validate_data(data):
                self.logger.error(f"Invalid data format: {data}")
                return False

            # Process the data
            await self._process_data(data)
            return True

        except Exception as e:
            self.logger.error(f"Error processing data: {str(e)}")
            return False

    def _should_process_message(self) -> bool:
        """Check if a message should be processed based on throttling rules."""
        now = datetime.now()
        
        # Remove old messages from the queue
        while self.message_queue and (now - self.message_queue[0]) > timedelta(seconds=self.throttle_window):
            self.message_queue.popleft()
        
        # Check if we're under the rate limit
        if len(self.message_queue) >= self.max_messages_per_second:
            return False
        
        # Add current message to queue
        self.message_queue.append(now)
        return True

    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate incoming data structure and content."""
        try:
            # Check if data type is specified
            data_type = data.get("type")
            if not data_type or data_type not in self.required_fields:
                return False

            # Check required fields
            required = self.required_fields[data_type]
            if not all(field in data for field in required):
                return False

            # Validate timestamp/date format
            if data_type == "tick_data":
                datetime.fromisoformat(data["timestamp"])
            elif data_type == "minute_data":
                datetime.fromisoformat(data["timestamp"])
            elif data_type == "daily_data":
                datetime.strptime(data["date"], "%Y-%m-%d")

            return True

        except (ValueError, KeyError) as e:
            self.logger.error(f"Data validation error: {str(e)}")
            return False

    async def _process_data(self, data: Dict[str, Any]):
        """Process and store the validated data."""
        try:
            data_type = data["type"]
            
            # Add processing timestamp
            data["processed_at"] = datetime.now().isoformat()
            
            # Store data
            await self._store_data(data_type, data)
            
            self.logger.debug(f"Processed {data_type} for {data.get('symbol')}")

        except Exception as e:
            self.logger.error(f"Error processing data: {str(e)}")
            raise

    async def _store_data(self, data_type: str, data: Dict[str, Any]):
        """Store the processed data in the database."""
        try:
            if data_type == "tick_data":
                db_data = TickData(
                    symbol=data["symbol"],
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    price=data["price"],
                    volume=data["volume"],
                    bid=data.get("bid"),
                    ask=data.get("ask"),
                    bid_volume=data.get("bid_volume"),
                    ask_volume=data.get("ask_volume"),
                    additional_data=data.get("additional_data", {})
                )
            elif data_type == "minute_data":
                db_data = MinuteData(
                    symbol=data["symbol"],
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    open=data["open"],
                    high=data["high"],
                    low=data["low"],
                    close=data["close"],
                    volume=data["volume"],
                    additional_data=data.get("additional_data", {})
                )
            elif data_type == "daily_data":
                db_data = DailyData(
                    symbol=data["symbol"],
                    date=datetime.strptime(data["date"], "%Y-%m-%d"),
                    open=data["open"],
                    high=data["high"],
                    low=data["low"],
                    close=data["close"],
                    volume=data["volume"],
                    additional_data=data.get("additional_data", {})
                )
            else:
                raise ValueError(f"Unknown data type: {data_type}")

            self.db_session.add(db_data)
            await self.db_session.commit()

        except Exception as e:
            await self.db_session.rollback()
            self.logger.error(f"Error storing data: {str(e)}")
            raise

    async def _cleanup_task(self):
        """Background task to clean up old data."""
        while self._is_running:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(self._cleanup_interval)
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {str(e)}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying

    async def _cleanup_old_data(self):
        """Clean up data older than retention periods."""
        try:
            now = datetime.now()
            
            for data_type, retention in self.retention_periods.items():
                cutoff_date = now - retention
                
                # Drop old partitions
                await self.db_session.execute(
                    f"DROP TABLE IF EXISTS {data_type}_{cutoff_date.strftime('%Y%m')}"
                )
                
                # Create new partitions for next month
                next_month = now + timedelta(days=30)
                create_partition_tables(self.db_session.get_bind(), now, next_month)
                
            self.last_cleanup = now
            await self.db_session.commit()
            
        except Exception as e:
            await self.db_session.rollback()
            self.logger.error(f"Error cleaning up old data: {str(e)}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get current data manager statistics."""
        return {
            "messages_processed": len(self.message_queue),
            "last_cleanup": self.last_cleanup.isoformat(),
            "throttle_window": self.throttle_window,
            "max_messages_per_second": self.max_messages_per_second,
            "retention_periods": {
                k: str(v) for k, v in self.retention_periods.items()
            }
        } 