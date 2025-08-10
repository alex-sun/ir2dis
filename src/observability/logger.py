#!/usr/bin/env python3
"""
Structured logging for iRacing → Discord Auto-Results Bot.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any

# Set up structured logger
logger = logging.getLogger(__name__)

class StructuredLogger:
    """Structured logger for the application."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def info(self, message: str, **kwargs):
        """Log an info message with structured data."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": message,
            **kwargs
        }
        self.logger.info(json.dumps(log_data))
        
    def error(self, message: str, **kwargs):
        """Log an error message with structured data."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "ERROR",
            "message": message,
            **kwargs
        }
        self.logger.error(json.dumps(log_data))
        
    def warning(self, message: str, **kwargs):
        """Log a warning message with structured data."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "WARNING",
            "message": message,
            **kwargs
        }
        self.logger.warning(json.dumps(log_data))
        
    def debug(self, message: str, **kwargs):
        """Log a debug message with structured data."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "DEBUG",
            "message": message,
            **kwargs
        }
        self.logger.debug(json.dumps(log_data))

# Global instance
structured_logger = StructuredLogger()
