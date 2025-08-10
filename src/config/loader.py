#!/usr/bin/env python3
"""
Configuration loader for iRacing → Discord Auto-Results Bot.
Handles loading from environment variables and config file.
"""

import os
import json
from typing import Optional
from .models import Config

def load_config() -> Config:
    """
    Load configuration from environment variables and config file.
    
    Returns:
        Config: Configuration object with all settings loaded
    """
    # Load from environment variables with defaults
    config = Config(
        discord_token=os.getenv('DISCORD_TOKEN', ''),
        iracing_email=os.getenv('IRACING_EMAIL', ''),
        iracing_password=os.getenv('IRACING_PASSWORD', ''),
        iracing_password_hashed=os.getenv('IRACING_PASSWORD_HASHED', 'false').lower() == 'true',
        timezone_default=os.getenv('TIMEZONE_DEFAULT', 'Europe/Berlin'),
        poll_interval_seconds=int(os.getenv('POLL_INTERVAL_SECONDS', '120')),
        poll_concurrency=int(os.getenv('POLL_CONCURRENCY', '4')),
        db_url=os.getenv('DB_URL'),
        sqlite_path=os.getenv('SQLITE_PATH', 'data/bot.db'),
        cookies_path=os.getenv('COOKIES_PATH', 'data/cookies.json'),
        log_level=os.getenv('LOG_LEVEL', 'info'),
        user_agent=os.getenv('USER_AGENT')
    )
    
    # Validate required fields
    validate_config(config)
    
    # Load optional config file
    config_file_path = 'data/config.json'
    if os.path.exists(config_file_path):
        try:
            with open(config_file_path, 'r') as f:
                file_config = json.load(f)
            
            # Merge file config with environment config (environment takes precedence)
            for key, value in file_config.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                    
        except Exception as e:
            print(f"Warning: Could not load config file {config_file_path}: {e}")
    
    return config

def validate_config(config: Config) -> None:
    """
    Validate that required configuration values are present.
    
    Args:
        config (Config): Configuration object to validate
        
    Raises:
        ValueError: If any required configuration is missing
    """
    if not config.discord_token:
        raise ValueError("DISCORD_TOKEN environment variable is required")
        
    if not config.iracing_email:
        raise ValueError("IRACING_EMAIL environment variable is required")
        
    if not config.iracing_password:
        raise ValueError("IRACING_PASSWORD environment variable is required")
