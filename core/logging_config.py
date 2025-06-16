"""
Enhanced Logging Configuration Module

Provides structured logging with JSON formatting, log rotation,
log filtering, and sensitive data masking for production environments.
"""

import os
import sys
import logging
import json
import traceback
import socket
import re
import atexit
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Dict, Any, Optional, List, Union, Set, Callable

# Default log format patterns
DEFAULT_TEXT_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s"
DEFAULT_JSON_FORMAT = {
    "timestamp": "%(asctime)s", 
    "level": "%(levelname)s",
    "location": "%(name)s:%(lineno)d",
    "message": "%(message)s"
}

# Default log directory
DEFAULT_LOG_DIR = os.getenv("LOG_DIR", "/var/log/123trade")
DEFAULT_LOG_FILE = os.getenv("LOG_FILE", os.path.join(DEFAULT_LOG_DIR, "app.log"))

# Regular expression patterns for masking sensitive data
MASK_PATTERNS = {
    "password": re.compile(r'(password["\']?\s*[:=]\s*["\']?)(.*?)(["\'])', re.IGNORECASE),
    "api_key": re.compile(r'(api[_-]?key["\']?\s*[:=]\s*["\']?)(.*?)(["\'])', re.IGNORECASE),
    "token": re.compile(r'(token["\']?\s*[:=]\s*["\']?)(.*?)(["\'])', re.IGNORECASE),
    "secret": re.compile(r'(secret["\']?\s*[:=]\s*["\']?)(.*?)(["\'])', re.IGNORECASE),
    "credentials": re.compile(r'(credentials["\']?\s*[:=]\s*["\']?)(.*?)(["\'])', re.IGNORECASE),
    "access_key": re.compile(r'(access[_-]?key["\']?\s*[:=]\s*["\']?)(.*?)(["\'])', re.IGNORECASE),
    "credit_card": re.compile(r'(\d{4})[- ]?(\d{4})[- ]?(\d{4})[- ]?(\d{4})'),
    "email": re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
}


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data in log messages."""

    def __init__(self, patterns: Dict[str, re.Pattern] = None):
        """
        Initialize the filter with patterns for sensitive data.

        Args:
            patterns: Dictionary mapping names to regex patterns for masking.
        """
        super().__init__()
        self.patterns = patterns or MASK_PATTERNS

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter function that masks sensitive information.
        
        Args:
            record: Log record to filter

        Returns:
            bool: Always True to include record, but with modified content
        """
        if isinstance(record.msg, str):
            for name, pattern in self.patterns.items():
                if name in ("credit_card", "email"):
                    record.msg = pattern.sub(r"****", record.msg)
                else:
                    record.msg = pattern.sub(r"\1****\3", record.msg)
                    
        elif isinstance(record.msg, (dict, list, tuple)):
            try:
                # Convert to string, mask, and convert back
                msg_str = json.dumps(record.msg)
                for name, pattern in self.patterns.items():
                    if name in ("credit_card", "email"):
                        msg_str = pattern.sub(r"****", msg_str)
                    else:
                        msg_str = pattern.sub(r"\1****\3", msg_str)
                record.msg = json.loads(msg_str)
            except (TypeError, json.JSONDecodeError):
                # If conversion fails, leave message as-is
                pass
                
        return True


class JsonFormatter(logging.Formatter):
    """
    Formatter for JSON-structured logs suitable for production environments.
    """

    def __init__(self, fmt_dict: Dict[str, str] = None, time_format: str = "%Y-%m-%dT%H:%M:%S.%fZ", **kwargs):
        """
        Initialize the JSON formatter.

        Args:
            fmt_dict: Dictionary of log record attributes to include
            time_format: Format string for the timestamp
            **kwargs: Additional fields to include in every log record
        """
        self.fmt_dict = fmt_dict or DEFAULT_JSON_FORMAT
        self.time_format = time_format
        self.additional_fields = kwargs
        self.hostname = socket.gethostname()

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as JSON.

        Args:
            record: Log record to format

        Returns:
            str: JSON-formatted log string
        """
        log_dict = {}
        
        # Add formatter fields
        for key, value in self.fmt_dict.items():
            if value.startswith("%(") and value.endswith(")s"):
                attr_name = value[2:-2]
                if hasattr(record, attr_name):
                    log_dict[key] = getattr(record, attr_name)
            else:
                log_dict[key] = value % record.__dict__
                
        # Add timestamp explicitly
        log_dict["timestamp"] = self.formatTime(record, self.time_format)
        
        # Add log level explicitly
        log_dict["level"] = record.levelname
        
        # Add standard fields
        log_dict["logger"] = record.name
        log_dict["thread"] = record.thread
        log_dict["thread_name"] = record.threadName
        log_dict["process"] = record.process
        log_dict["hostname"] = self.hostname
        
        # Add exception info if available
        if record.exc_info:
            log_dict["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
            
        # Add additional context from record
        if hasattr(record, "data") and isinstance(record.data, dict):
            log_dict.update(record.data)
            
        # Add static additional fields
        if self.additional_fields:
            log_dict.update(self.additional_fields)
            
        # Handle message field specially
        if isinstance(record.msg, dict):
            log_dict["data"] = record.msg
            if "message" not in record.msg:
                log_dict["message"] = str(record.msg)
        else:
            log_dict["message"] = record.getMessage()
            
        return json.dumps(log_dict)

    def formatException(self, exc_info) -> List[str]:
        """
        Format an exception as a list of strings.

        Args:
            exc_info: Exception info tuple from sys.exc_info()

        Returns:
            List[str]: Formatted exception traceback lines
        """
        formatted = traceback.format_exception(*exc_info)
        return [line.rstrip() for line in formatted]

    def formatTime(self, record, datefmt=None):
        """
        Format the time according to ISO8601.

        Args:
            record: Log record
            datefmt: Date format string

        Returns:
            str: Formatted time string
        """
        dt = datetime.fromtimestamp(record.created)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.isoformat() + "Z"


class ContextAdapter(logging.LoggerAdapter):
    """
    Adapter that allows adding context to log messages.
    
    Example:
        logger = get_logger(__name__)
        logger = ContextAdapter(logger, {"user_id": "123", "request_id": "abc"})
        logger.info("User login")  # Will include the context fields
    """
    
    def __init__(self, logger, extra=None):
        """
        Initialize the adapter with extra context.
        
        Args:
            logger: The logger instance to wrap
            extra: Dictionary with extra context fields
        """
        super().__init__(logger, extra or {})
        
    def process(self, msg, kwargs):
        """
        Process the logging message and keyword arguments.
        
        Args:
            msg: Log message
            kwargs: Keyword arguments for the logging call
            
        Returns:
            tuple: (modified_message, modified_kwargs)
        """
        # Get any data passed in this logging call
        data = kwargs.pop("extra", {}).copy() if "extra" in kwargs else {}
        
        # Add adapter context to the data
        data.update(self.extra)
        
        # Put it back into kwargs
        kwargs["extra"] = {"data": data}
        
        return msg, kwargs


class LogfileRotator:
    """
    Manages log file rotation based on size or time.
    """
    
    def __init__(self, log_file: str, max_size_mb: int = 100, backup_count: int = 10,
                 when: str = "midnight", interval: int = 1):
        """
        Initialize the log file rotator.
        
        Args:
            log_file: Path to the log file
            max_size_mb: Maximum size in megabytes before rotation 
            backup_count: Number of backup files to keep
            when: When to rotate ('S', 'M', 'H', 'D', 'midnight')
            interval: Interval between rotations
        """
        self.log_file = log_file
        self.max_size_mb = max_size_mb
        self.backup_count = backup_count
        self.when = when
        self.interval = interval
        self.size_handler = None
        self.time_handler = None
        
    def get_handlers(self) -> List[logging.Handler]:
        """
        Get the appropriate handlers for log rotation.
        
        Returns:
            List[logging.Handler]: List of configured handlers
        """
        handlers = []
        
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(self.log_file)
        if not os.path.exists(log_dir):
            Path(log_dir).mkdir(parents=True, exist_ok=True)
            
        # Size-based rotation handler
        self.size_handler = RotatingFileHandler(
            filename=self.log_file,
            maxBytes=self.max_size_mb * 1024 * 1024,
            backupCount=self.backup_count
        )
        handlers.append(self.size_handler)
        
        # Time-based rotation handler (optional)
        if self.when:
            self.time_handler = TimedRotatingFileHandler(
                filename=self.log_file,
                when=self.when,
                interval=self.interval,
                backupCount=self.backup_count
            )
            handlers.append(self.time_handler)
            
        return handlers
        
    def register_signal_handler(self):
        """Register a handler to flush logs on shutdown."""
        def flush_handlers():
            if self.size_handler:
                self.size_handler.flush()
            if self.time_handler:
                self.time_handler.flush()
                
        atexit.register(flush_handlers)


class LoggerFactory:
    """
    Factory for creating and configuring loggers.
    """
    
    def __init__(self):
        """Initialize the logger factory."""
        self.initialized = False
        self.default_level = logging.INFO
        self.format_style = "text"
        self.sensitive_data_filter = None
        self.log_file = DEFAULT_LOG_FILE
        
    def setup_logging(
        self,
        level: str = "INFO",
        log_format: str = "text",
        log_file: str = None,
        env: str = None,
        service_name: str = "123trade",
        max_size_mb: int = 100,
        backup_count: int = 10,
        sensitive_data_filtering: bool = True,
        log_to_stdout: bool = True,
    ) -> None:
        """
        Configure the global logging settings.
        
        Args:
            level: Logging level ('DEBUG', 'INFO', etc.)
            log_format: Log format style ('text', 'json')
            log_file: Log file path
            env: Environment ('development', 'production', etc.)
            service_name: Name of the service for identification
            max_size_mb: Maximum log file size before rotation
            backup_count: Number of backup files to keep
            sensitive_data_filtering: Whether to filter sensitive data
            log_to_stdout: Whether to also log to stdout
        """
        # Convert level string to logging level
        numeric_level = getattr(logging, level.upper(), None)
        if not isinstance(numeric_level, int):
            numeric_level = logging.INFO
        
        # Store configuration
        self.default_level = numeric_level
        self.format_style = log_format
        self.log_file = log_file or DEFAULT_LOG_FILE
        
        # Reset root logger
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        root_logger.setLevel(self.default_level)
        
        # Setup handlers
        handlers = []
        
        # Console handler
        if log_to_stdout:
            console_handler = logging.StreamHandler(sys.stdout)
            handlers.append(console_handler)
        
        # File handlers if log_file specified
        if self.log_file:
            rotator = LogfileRotator(
                log_file=self.log_file,
                max_size_mb=max_size_mb,
                backup_count=backup_count
            )
            file_handlers = rotator.get_handlers()
            handlers.extend(file_handlers)
            rotator.register_signal_handler()
        
        # Configure formatters and filters
        env = env or os.getenv("ENVIRONMENT", "development")
        
        # Create formatters based on format style
        if log_format == "json":
            # JSON formatter for structured logging
            formatter = JsonFormatter(
                service=service_name,
                environment=env,
                version=os.getenv("APP_VERSION", "unknown")
            )
        else:
            # Text formatter for development
            formatter = logging.Formatter(DEFAULT_TEXT_FORMAT)
            
        # Apply formatters to handlers
        for handler in handlers:
            handler.setFormatter(formatter)
            
        # Configure filtering for sensitive data
        if sensitive_data_filtering:
            self.sensitive_data_filter = SensitiveDataFilter()
            for handler in handlers:
                handler.addFilter(self.sensitive_data_filter)
            
        # Add handlers to root logger
        for handler in handlers:
            root_logger.addHandler(handler)
            
        # Mark as initialized
        self.initialized = True
        
        # Log initial message
        logger = logging.getLogger(__name__)
        logger.info(
            f"Logging initialized",
            extra={"data": {
                "level": level,
                "format": log_format,
                "service": service_name,
                "environment": env,
                "log_file": self.log_file if self.log_file else "none"
            }}
        )
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger with the given name.
        
        Args:
            name: Logger name (usually __name__)
            
        Returns:
            logging.Logger: Configured logger instance
        """
        if not self.initialized:
            # Lazy initialization with defaults if not explicitly configured
            self.setup_logging(
                level=os.getenv("LOG_LEVEL", "INFO"),
                log_format=os.getenv("LOG_FORMAT", "text"),
                log_file=os.getenv("LOG_FILE", None),
                env=os.getenv("ENVIRONMENT", "development"),
            )
            
        return logging.getLogger(name)
    
    def get_context_logger(self, name: str, context: Dict[str, Any] = None) -> ContextAdapter:
        """
        Get a logger with contextual information.
        
        Args:
            name: Logger name
            context: Context dictionary to include with logs
            
        Returns:
            ContextAdapter: Logger with context capability
        """
        logger = self.get_logger(name)
        return ContextAdapter(logger, context or {})


# Create a singleton factory instance
_factory = LoggerFactory()

# Expose the main functions
setup_logging = _factory.setup_logging
get_logger = _factory.get_logger
get_context_logger = _factory.get_context_logger


class StructuredLogger:
    """
    A structured logger that provides methods for logging different types of events
    with context and metadata.
    """
    
    def __init__(self, name: str):
        """
        Initialize the structured logger.
        
        Args:
            name: Logger name (usually __name__)
        """
        self.logger = get_logger(name)
        self.context = {}
        
    def with_context(self, **context) -> 'StructuredLogger':
        """
        Create a new logger with added context.
        
        Args:
            **context: Context key-value pairs
            
        Returns:
            StructuredLogger: New logger with combined context
        """
        logger = StructuredLogger(self.logger.name)
        logger.context = {**self.context, **context}
        return logger
        
    def _log(self, level: int, event: str, **kwargs):
        """
        Internal logging method.
        
        Args:
            level: Logging level
            event: Event name/description
            **kwargs: Additional event data
        """
        data = {**self.context}
        
        # Extract traceback if provided
        tb = kwargs.pop("traceback", None)
        if tb:
            data["traceback"] = tb
            
        # Add the event type
        data["event"] = event
        
        # Add other kwargs as event data
        data.update(kwargs)
        
        self.logger.log(level, data)
        
    def debug(self, event: str, **kwargs):
        """Log a debug event."""
        self._log(logging.DEBUG, event, **kwargs)
        
    def info(self, event: str, **kwargs):
        """Log an info event."""
        self._log(logging.INFO, event, **kwargs)
        
    def warning(self, event: str, **kwargs):
        """Log a warning event."""
        self._log(logging.WARNING, event, **kwargs)
        
    def error(self, event: str, **kwargs):
        """Log an error event."""
        self._log(logging.ERROR, event, **kwargs)
        
    def critical(self, event: str, **kwargs):
        """Log a critical event."""
        self._log(logging.CRITICAL, event, **kwargs)
        
    def exception(self, event: str, exc_info=True, **kwargs):
        """
        Log an exception event.
        
        Args:
            event: Event description
            exc_info: Exception info (True to use current exception)
            **kwargs: Additional event data
        """
        if exc_info:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            if exc_type is not None:
                tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                kwargs["error_type"] = exc_type.__name__
                kwargs["error_message"] = str(exc_value)
                kwargs["traceback"] = tb_str
                
        self._log(logging.ERROR, event, **kwargs)
        
    def audit(self, event: str, user_id: str = None, **kwargs):
        """
        Log an audit event.
        
        Args:
            event: Audit event name
            user_id: User identifier
            **kwargs: Additional audit data
        """
        audit_data = {"audit_event": True}
        if user_id:
            audit_data["user_id"] = user_id
        
        # Add request context if available
        request_id = self.context.get("request_id")
        if request_id:
            audit_data["request_id"] = request_id
            
        # Add timestamp
        audit_data["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        # Add client IP if available
        client_ip = self.context.get("client_ip")
        if client_ip:
            audit_data["client_ip"] = client_ip
            
        # Add other audit data
        audit_data.update(kwargs)
        
        self._log(logging.INFO, f"AUDIT: {event}", **audit_data)


def get_structured_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger for the given name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        StructuredLogger: Structured logger instance
    """
    return StructuredLogger(name)