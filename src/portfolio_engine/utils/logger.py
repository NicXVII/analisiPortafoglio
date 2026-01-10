"""
Logging Framework Module
========================
Centralized logging configuration for the portfolio analysis system.

Features:
- Console output with colored formatting
- File logging with rotation
- Configurable log levels per module
- Structured logging support
- Performance tracking decorators
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
import functools
import time


# ================================================================================
# LOG LEVELS AND CONFIGURATION
# ================================================================================

class LogLevel:
    """Standard log levels with descriptions."""
    DEBUG = logging.DEBUG      # 10: Detailed diagnostic info
    INFO = logging.INFO        # 20: General informational messages
    WARNING = logging.WARNING  # 30: Warning messages
    ERROR = logging.ERROR      # 40: Error messages
    CRITICAL = logging.CRITICAL # 50: Critical errors


# Default configuration
DEFAULT_CONFIG = {
    'console_level': LogLevel.INFO,
    'file_level': LogLevel.DEBUG,
    'log_dir': 'logs',
    'max_file_size': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5,
    'format': '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    'date_format': '%Y-%m-%d %H:%M:%S',
}


# ================================================================================
# CUSTOM FORMATTER WITH COLORS
# ================================================================================

class ColoredFormatter(logging.Formatter):
    """Formatter with ANSI color codes for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        # Add color to levelname
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


# ================================================================================
# LOGGER SETUP
# ================================================================================

def setup_logger(
    name: str,
    console_level: int = DEFAULT_CONFIG['console_level'],
    file_level: int = DEFAULT_CONFIG['file_level'],
    log_dir: str = DEFAULT_CONFIG['log_dir'],
    enable_file_logging: bool = True
) -> logging.Logger:
    """
    Configure and return a logger with console and optional file handlers.
    
    Args:
        name: Logger name (usually __name__ of the module)
        console_level: Minimum level for console output
        file_level: Minimum level for file output
        log_dir: Directory for log files
        enable_file_logging: Whether to enable file logging
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Capture all, filter in handlers
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_formatter = ColoredFormatter(
        fmt=DEFAULT_CONFIG['format'],
        datefmt=DEFAULT_CONFIG['date_format']
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    if enable_file_logging:
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime('%Y%m%d')
        log_file = log_path / f"{name.replace('.', '_')}_{timestamp}.log"
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(file_level)
        file_formatter = logging.Formatter(
            fmt=DEFAULT_CONFIG['format'],
            datefmt=DEFAULT_CONFIG['date_format']
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


# ================================================================================
# PERFORMANCE TRACKING DECORATOR
# ================================================================================

def log_performance(logger: logging.Logger):
    """
    Decorator to log function execution time.
    
    Usage:
        @log_performance(logger)
        def expensive_function():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger.debug(f"Starting {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.info(f"Completed {func.__name__} in {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"Failed {func.__name__} after {elapsed:.2f}s: {e}")
                raise
        
        return wrapper
    return decorator


# ================================================================================
# PROGRESS LOGGING
# ================================================================================

class ProgressLogger:
    """Helper for logging progress of multi-step operations."""
    
    def __init__(self, logger: logging.Logger, total_steps: int, operation: str):
        self.logger = logger
        self.total_steps = total_steps
        self.operation = operation
        self.current_step = 0
        self.start_time = time.time()
    
    def step(self, message: str):
        """Log completion of one step."""
        self.current_step += 1
        progress_pct = (self.current_step / self.total_steps) * 100
        elapsed = time.time() - self.start_time
        
        self.logger.info(
            f"{self.operation} [{self.current_step}/{self.total_steps}] "
            f"({progress_pct:.0f}%) - {message} [elapsed: {elapsed:.1f}s]"
        )
    
    def complete(self):
        """Log completion of entire operation."""
        elapsed = time.time() - self.start_time
        self.logger.info(
            f"{self.operation} COMPLETED in {elapsed:.1f}s "
            f"({self.total_steps} steps)"
        )


# ================================================================================
# MODULE-SPECIFIC LOGGERS
# ================================================================================

def get_logger(module_name: str) -> logging.Logger:
    """
    Get or create a logger for a specific module.
    
    This is the recommended way to get loggers throughout the codebase.
    
    Args:
        module_name: Name of the module (use __name__)
        
    Returns:
        Configured logger instance
        
    Usage:
        from portfolio_engine.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Analysis started")
    """
    return setup_logger(module_name)


# ================================================================================
# SILENCE NOISY LIBRARIES
# ================================================================================

def silence_third_party_loggers():
    """Reduce verbosity of noisy third-party libraries."""
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('yfinance').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)


# Initialize on import
silence_third_party_loggers()


# ================================================================================
# MIGRATION HELPER
# ================================================================================

class PrintToLogAdapter:
    """
    Adapter to gradually migrate from print() to logger.
    
    Usage during migration:
        from portfolio_engine.utils.logger import PrintToLogAdapter
        logger = get_logger(__name__)
        print = PrintToLogAdapter(logger).print
        
        # Now print() calls are logged
        print("This goes to logger.info()")
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def print(self, *args, **kwargs):
        """Drop-in replacement for print() that uses logger."""
        message = ' '.join(str(arg) for arg in args)
        
        # Detect severity from message content
        if any(x in message for x in ['ERROR', '❌', 'FAIL']):
            self.logger.error(message)
        elif any(x in message for x in ['WARNING', '⚠️', 'WARN']):
            self.logger.warning(message)
        elif any(x in message for x in ['DEBUG', '🔍']):
            self.logger.debug(message)
        else:
            self.logger.info(message)
