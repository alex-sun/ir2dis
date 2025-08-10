#!/usr/bin/env python3
"""
Configuration models for iRacing → Discord Auto-Results Bot.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    """Configuration settings for the bot."""
    
    # Discord settings
    discord_token: str
    
    # iRacing settings
    iracing_email: str
    iracing_password: str
    iracing_password_hashed: bool
    
    # General settings
    timezone_default: str
    poll_interval_seconds: int
    poll_concurrency: int
    
    # Storage settings
    db_url: Optional[str]
    sqlite_path: str
    cookies_path: str
    
    # Logging settings
    log_level: str
    
    # HTTP settings
    user_agent: Optional[str]
