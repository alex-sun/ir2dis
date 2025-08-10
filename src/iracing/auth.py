#!/usr/bin/env python3
"""
iRacing authentication module for iRacing → Discord Auto-Results Bot.
Handles login, cookie management, and password hashing.
"""

import hashlib
import json
import os
import requests
from typing import Dict, Optional
from config.loader import load_config

def hash_password(password: str, email: str, hashed: bool = False) -> str:
    """
    Hash the password according to iRacing requirements.
    
    Args:
        password (str): Plain text password
        email (str): User's email address
        hashed (bool): If True, treat password as already hashed
        
    Returns:
        str: Hashed password string
    """
    if hashed:
        return password
    
    # iRacing hashing: base64( SHA256( plainPassword + lower(email) ) )
    email_lower = email.lower()
    combined = password + email_lower
    sha256_hash = hashlib.sha256(combined.encode('utf-8')).digest()
    return sha256_hash.hex()

def load_cookies() -> Optional[Dict]:
    """
    Load saved cookies from file.
    
    Returns:
        Optional[Dict]: Cookies dictionary or None if file doesn't exist
    """
    config = load_config()
    
    if not os.path.exists(config.cookies_path):
        return None
        
    try:
        with open(config.cookies_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading cookies: {e}")
        return None

def save_cookies(cookies: Dict) -> None:
    """
    Save cookies to file.
    
    Args:
        cookies (Dict): Cookies dictionary to save
    """
    config = load_config()
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(config.cookies_path), exist_ok=True)
    
    with open(config.cookies_path, 'w') as f:
        json.dump(cookies, f)

def is_cookie_valid(cookies: Dict) -> bool:
    """
    Check if cookies are still valid (basic check).
    
    Args:
        cookies (Dict): Cookies dictionary
        
    Returns:
        bool: True if cookies appear valid
    """
    # Basic validation - check for common cookie names that should be present
    required_cookies = ['seesion', 'member_id']  # Simplified check
    
    if not cookies:
        return False
    
    # Check if any of the required cookies are present
    for cookie_name in required_cookies:
        if cookie_name in cookies:
            return True
            
    # If no cookies, then not valid
    return False
