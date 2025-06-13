"""
Unified Logging System for Trading Application
Combines structured JSON logging with color console output and Prometheus metrics
"""

import logging
import logging.handlers
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram

# Prometheus metrics for logging
log_counter = Counter(
    'trading_system_logs_total',
    'Total number of logs',
    ['level', 'component']
)

log_latency = Histogram(
    'trading_system_log_latency_seconds',
    'Logging latency in seconds',
    ['level']
)


class StructuredJSONFormatter(logging.Formatter):
    """JSON formatter for structured logging with enhanced metadata"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": os.getpid(),
            "thread_id": record.thread
        }
        
        # Add component identification
        component = getattr(record, 'component', record.name.split('.')[0])
        log_data["component"] = component
        
        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_data["correlation_id"] = record.correlation_id
            
        # Add user context if present
        if hasattr(record, 'user_id'):
            log_data["user_id"] = record.user_id
            
        # Add extra fields if present
        if hasattr(record, "extra"):
            log_data.update(record.extra)
            
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
            
        return json.dumps(log_data, default=str)


class ColoredConsoleFormatter(logging.Formatter):
    """Enhanced console formatter with colors and trading-specific context"""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format with colors and enhanced context"""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Build context string
        context_parts = []
        if hasattr(record, 'component'):
            context_parts.append(f"[{record.component}]")
        if hasattr(record, 'user_id'):
            context_parts.append(f"[user:{record.user_id}]")
        if hasattr(record, 'correlation_id'):
            context_parts.append(f"[corr:{record.correlation_id[:8]}]")
            
        context = " ".join(context_parts)
        context_str = f" {context}" if context else ""
        
        # Format message
        formatted = (
            f"{color}%(asctime)s - %(name)s - %(levelname)s{reset}"
            f"{context_str} - %(message)s"
        )
        
        formatter = logging.Formatter(formatted)
        return formatter.format(record)


class PrometheusLogHandler(logging.Handler):
    """Custom handler to collect logging metrics for Prometheus"""
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit log record and update metrics"""
        try:
            component = getattr(record, 'component', record.name.split('.')[0])
            with log_latency.labels(level=record.levelname).time():
                log_counter.labels(
                    level=record.levelname,
                    component=component
                ).inc()
        except Exception:
            self.handleError(record)


class TradingLoggerAdapter(logging.LoggerAdapter):
    """Enhanced logger adapter for trading system context"""
    
    def __init__(self, logger: logging.Logger, extra: Dict[str, Any]):
        super().__init__(logger, extra or {})
        
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Process the log message and add trading context"""
        extra = kwargs.get("extra", {})
        if self.extra:
            extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs
        
    def trading_event(self, event_type: str, data: Dict[str, Any], **kwargs):
        """Log trading-specific events"""
        self.info(
            f"Trading event: {event_type}",
            extra={"event_type": event_type, "event_data": data},
            **kwargs
        )
        
    def security_event(self, event_type: str, data: Dict[str, Any], **kwargs):
        """Log security-specific events"""
        self.warning(
            f"Security event: {event_type}",
            extra={"event_type": event_type, "event_data": data},
            **kwargs
        )


def setup_logging(
    log_dir: str = "logs",
    log_level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_prometheus: bool = True,
    enable_console_colors: bool = True
) -> None:
    """
    Set up unified logging configuration
    
    Args:
        log_dir: Directory to store log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: Maximum size of each log file before rotation
        backup_count: Number of backup files to keep
        enable_prometheus: Whether to enable Prometheus metrics
        enable_console_colors: Whether to enable colored console output
    """
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    if enable_console_colors:
        console_handler.setFormatter(ColoredConsoleFormatter())
    else:
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
    
    root_logger.addHandler(console_handler)
    
    # Main application log file (structured JSON)
    main_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / "trading_system.log",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    main_handler.setLevel(numeric_level)
    main_handler.setFormatter(StructuredJSONFormatter())
    root_logger.addHandler(main_handler)
    
    # Error-only log file
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / "errors.log",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(StructuredJSONFormatter())
    root_logger.addHandler(error_handler)
    
    # Trading events log
    trading_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / "trading_events.log",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    trading_handler.setLevel(logging.INFO)
    trading_handler.setFormatter(StructuredJSONFormatter())
    
    # Add filter for trading events only
    trading_handler.addFilter(lambda record: hasattr(record, 'event_type'))
    root_logger.addHandler(trading_handler)
    
    # Prometheus metrics handler
    if enable_prometheus:
        prometheus_handler = PrometheusLogHandler()
        prometheus_handler.setLevel(logging.INFO)
        root_logger.addHandler(prometheus_handler)
    
    # Configure specific loggers
    loggers_config = {
        "trading": {"level": numeric_level, "component": "trading"},
        "risk": {"level": numeric_level, "component": "risk"},
        "broker": {"level": numeric_level, "component": "broker"},
        "strategy": {"level": numeric_level, "component": "strategy"},
        "data": {"level": numeric_level, "component": "data"},
        "webhook": {"level": numeric_level, "component": "webhook"},
        "security": {"level": numeric_level, "component": "security"},
        "monitoring": {"level": numeric_level, "component": "monitoring"}
    }
    
    for logger_name, config in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(config["level"])
        logger.propagate = True


def get_logger(name: str, component: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance with optional component context
    
    Args:
        name: Logger name
        component: Component identifier for filtering and metrics
        
    Returns:
        logging.Logger: Logger instance
    """
    logger = logging.getLogger(name)
    if component:
        # Add component as default extra data
        logger = TradingLoggerAdapter(logger, {"component": component})
    return logger


def get_trading_logger(
    component: str,
    user_id: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> TradingLoggerAdapter:
    """
    Get a trading-specific logger with context
    
    Args:
        component: Component name (risk, trading, etc.)
        user_id: User ID for user-specific logging
        correlation_id: Correlation ID for request tracking
        
    Returns:
        TradingLoggerAdapter: Enhanced logger adapter
    """
    logger = logging.getLogger(f"trading.{component}")
    context = {"component": component}
    
    if user_id:
        context["user_id"] = user_id
    if correlation_id:
        context["correlation_id"] = correlation_id
        
    return TradingLoggerAdapter(logger, context)


# Convenience function for backward compatibility
create_logger_adapter = get_trading_logger 