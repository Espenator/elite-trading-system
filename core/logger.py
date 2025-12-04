"""
Centralized logging system
"""

import sys
from loguru import logger
import os

def setup_logger():
    """
    Configure the logger for the entire system
    """
    # Remove default handler
    logger.remove()
    
    # Get log level from environment
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    
    # Add console handler (simplified format)
    logger.add(
        sys.stdout,
        colorize=True,
        format="{time:HH:mm:ss} | {level} | {message}",
        level=log_level
    )
    
    # Add file handler
    log_file = "data/logs/system.log"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logger.add(
        log_file,
        rotation="10 MB",
        retention="30 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function} - {message}"
    )
    
    logger.info("Logger initialized")

def get_logger(name: str):
    """
    Get a logger instance for a module
    
    Args:
        name: Module name (usually __name__)
    
    Returns:
        Logger instance
    """
    return logger.bind(name=name)

# Initialize logger on import
setup_logger()

