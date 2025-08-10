#!/usr/bin/env python3
"""
iRacing API client for iRacing → Discord Auto-Results Bot.
Handles 2-step data fetching and rate limiting.
"""

import asyncio
import json
import time
import requests
from typing import Dict, Any, Optional
from urllib.parse import urljoin

from .auth import load_cookies, save_cookies, is_cookie_valid, hash_password
from config.loader import load_config
from observability.logger import structured_logger
from observability.metrics import metrics

class IRacingClient:
    """iRacing API client with 2-step fetch pattern."""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.iracing.com"
        self._setup_session()
        
    def _setup_session(self):
        """Setup the session with default headers and cookies."""
        config = load_config()
        
        # Load existing cookies
        cookies = load_cookies()
        if cookies and is_cookie_valid(cookies):
            self.session.cookies.update(cookies)
            
        # Set user agent
        user_agent = config.user_agent or "iRacing-Discord-Bot/1.0"
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
    async def login(self) -> bool:
        """
        Perform login to iRacing if needed.
        
        Returns:
            bool: True if login was successful or already logged in
        """
        config = load_config()
        
        # Check if we already have valid cookies
        cookies = load_cookies()
        if cookies and is_cookie_valid(cookies):
            self.session.cookies.update(cookies)
            structured_logger.info("Using existing cookies")
            return True
            
        # Perform login
        try:
            payload = {
                'email': config.iracing_email.lower(),
                'password': hash_password(config.iracing_password, config.iracing_email, config.iracing_password_hashed)
            }
            
            response = self.session.post(
                urljoin(self.base_url, '/auth/login'),
                json=payload,
                timeout=30
            )
            
            if response.status_code == 401:
                # Login failed
                structured_logger.error("Authentication failed")
                metrics.increment_auth_failures()
                return False
                
            elif response.status_code == 429:
                # Rate limited
                structured_logger.warning("Rate limited during login")
                metrics.increment_rate_limited()
                return False
                
            elif 'captcha' in response.text.lower() or response.status_code == 503:
                # CAPTCHA required - need human intervention
                structured_logger.error("CAPTCHA required for authentication")
                metrics.increment_captcha_required()
                raise Exception("CAPTCHA required. Please login manually via browser from the same IP and restart the bot.")
                
            # Save cookies if successful
            save_cookies(dict(self.session.cookies))
            
            structured_logger.info("Successfully logged in to iRacing")
            return True
            
        except Exception as e:
            structured_logger.error(f"Login error: {e}")
            return False
            
    async def get_json_via_link(self, endpoint: str, params: Optional[Dict] = None) -> Dict[Any, Any]:
        """
        Fetch JSON data using the 2-step pattern (GET -> GET via link).
        
        Args:
            endpoint (str): API endpoint
            params (Dict, optional): Query parameters
            
        Returns:
            Dict: JSON response data
        """
        config = load_config()
        
        # Ensure we're logged in
        if not await self.login():
            raise Exception("Failed to login to iRacing")
            
        try:
            # First step: get the link
            url = urljoin(self.base_url, endpoint)
            if params:
                response = self.session.get(url, params=params, timeout=30)
            else:
                response = self.session.get(url, timeout=30)
                
            response.raise_for_status()
            
            data = response.json()
            
            # Check if we got a link
            if 'link' in data:
                # Second step: fetch the actual data via link
                link_url = urljoin(self.base_url, data['link'])
                response2 = self.session.get(link_url, timeout=30)
                response2.raise_for_status()
                
                result = response2.json()
                metrics.increment_results_fetched()
                return result
                
            else:
                # Already got the direct response
                metrics.increment_results_fetched()
                return data
                
        except requests.exceptions.RequestException as e:
            structured_logger.error(f"HTTP request error: {e}")
            raise
            
        except Exception as e:
            structured_logger.error(f"Data fetch error: {e}")
            raise
            
    async def get_recent_races(self, cust_id: int) -> Dict[Any, Any]:
        """
        Fetch recent races for a customer ID.
        
        Args:
            cust_id (int): Customer ID
            
        Returns:
            Dict: Recent race data
        """
        endpoint = f"/data/member_results/recent/{cust_id}"
        return await self.get_json_via_link(endpoint)
        
    async def get_subsession(self, subsession_id: str) -> Dict[Any, Any]:
        """
        Fetch details for a specific subsession.
        
        Args:
            subsession_id (str): Subsession ID
            
        Returns:
            Dict: Subsession details
        """
        endpoint = f"/data/subsession/{subsession_id}"
        return await self.get_json_via_link(endpoint)
