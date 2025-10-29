import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

def setup_logger(
    name: str = "travel_agent",
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    max_size: int = 5_242_880,  # 5MB
    backup_count: int = 3
) -> logging.Logger:
    """
    Setup application logger with console and optional file output.
    
    Args:
        name: Logger name (default: travel_agent)
        log_level: Logging level (default: INFO)
        log_file: Optional log file path (default: None)
        max_size: Max size per log file in bytes (default: 5MB)
        backup_count: Number of backup files to keep (default: 3)
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Formatter
    formatter = logging.Formatter(
        '| %(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y/%m/%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger