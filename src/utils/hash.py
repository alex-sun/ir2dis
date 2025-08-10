#!/usr/bin/env python3
"""
Utility functions for password hashing.
"""

import hashlib

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
    
    # iRacing hashing: SHA256( plainPassword + lower(email) )
    email_lower = email.lower()
    combined = password + email_lower
    sha256_hash = hashlib.sha256(combined.encode('utf-8')).digest()
    return sha256_hash.hex()
