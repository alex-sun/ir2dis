#!/usr/bin/env python3
"""
iRacing Data API client for iRacing → Discord Auto-Results Bot.
Handles 2-step data fetching and rate limiting with async support.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
import aiohttp
from urllib.parse import urljoin

from config.loader import load_config
from observability.logger import structured_logger
from observability.metrics import metrics

class IRacingClient:
    """iRacing API client with 2-step fetch pattern using async/await."""
    
    def __init__(self, username: str, password: str, session: Optional[aiohttp.ClientSession] = None):
        self.username = username
        self.password = password
        self.base_url = "https://www.iracing.com"
        self._session = session
        self._cookies = {}
        
    async def __aenter__(self):
        """Async context manager entry."""
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session and not self._session.closed:
            await self._session.close()
            
    async def login(self) -> None:
        """
        Authenticate and prime cookies. Reuse across calls.
        
        Raises:
            Exception: If authentication fails
        """
        # For now, we'll use the existing auth flow from the old client as a reference,
        # but implement proper async version with session management
        
        config = load_config()
        
        # In a real implementation, this would handle cookie persistence and login
        # For now, we'll just log that we're ready to make requests
        structured_logger.info("iRacing client initialized for authentication")
        
    async def _get_json_via_download(self, path: str, params: Dict[str, Any]) -> Any:
        """
        GET /data/<path>?... -> returns {"link": "..."}; then GET link to obtain JSON payload.
        Retries with exponential backoff on 429/5xx.
        
        Args:
            path (str): API endpoint path
            params (Dict[str, Any]): Query parameters
            
        Returns:
            Any: JSON response data
            
        Raises:
            Exception: If request fails after retries
        """
        if not self._session:
            raise Exception("Client session not initialized")
            
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # First step: get the link
                url = urljoin(self.base_url, path)
                
                async with self._session.get(url, params=params) as response:
                    if response.status == 429:
                        # Rate limited - wait and retry
                        await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                        continue
                        
                    elif response.status >= 500:
                        # Server error - wait and retry
                        await asyncio.sleep(retry_delay * (2 ** attempt))
                        continue
                        
                    elif response.status != 200:
                        raise Exception(f"HTTP {response.status}: {await response.text()}")
                        
                    data = await response.json()
                    
                # Check if we got a link
                if 'link' in data:
                    # Second step: fetch the actual data via link
                    link_url = urljoin(self.base_url, data['link'])
                    async with self._session.get(link_url) as response2:
                        if response2.status != 200:
                            raise Exception(f"HTTP {response2.status}: {await response2.text()}")
                        
                        result = await response2.json()
                        metrics.increment_results_fetched()
                        return result
                        
                else:
                    # Already got the direct response
                    metrics.increment_results_fetched()
                    return data
                    
            except aiohttp.ClientError as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Failed after {max_retries} attempts: {e}")
                await asyncio.sleep(retry_delay * (2 ** attempt))
                
        raise Exception("Max retries exceeded")
        
    async def search_recent_sessions(
        self, cust_id: int, start_time_epoch_s: int, end_time_epoch_s: int
    ) -> List[Dict[str, Any]]:
        """
        Query results/search for sessions involving cust_id (window ~last 48h).
        Filter to finished 'Race' simsession results.
        Returns list of minimal dicts containing subsession_id, series_name, track, start_time, official, etc.
        
        Args:
            cust_id (int): Customer ID
            start_time_epoch_s (int): Start time in seconds since epoch
            end_time_epoch_s (int): End time in seconds since epoch
            
        Returns:
            List[Dict[str, Any]]: List of session information dictionaries
        """
        params = {
            'cust_id': cust_id,
            'start_time': start_time_epoch_s,
            'end_time': end_time_epoch_s,
            'session_type': 1,  # Race sessions only (as per iRacing API)
            'results_only': True
        }
        
        try:
            data = await self._get_json_via_download('/data/results/search', params)
            
            results = []
            if 'sessions' in data:
                for session in data['sessions']:
                    # Filter to finished Race sessions only (not Practice/Qualify)
                    if session.get('session_type') == 1:  # Race
                        results.append({
                            'subsession_id': session['subsession_id'],
                            'series_name': session.get('series_name', ''),
                            'track': session.get('track', {}).get('name', ''),
                            'start_time': session.get('start_time', ''),
                            'official': session.get('official', False),
                            'finish_type': session.get('finish_type', 0)
                        })
            
            return results
            
        except Exception as e:
            structured_logger.error(f"Error searching recent sessions for cust_id {cust_id}: {e}")
            return []
        
    async def get_subsession_results(self, subsession_id: int) -> Dict[str, Any]:
        """
        Fetch results/get for subsession_id (full result sheet).
        
        Args:
            subsession_id (int): Subsession ID
            
        Returns:
            Dict[str, Any]: Full results data
        """
        try:
            params = {'subsession_id': subsession_id}
            return await self._get_json_via_download('/data/results/get', params)
            
        except Exception as e:
            structured_logger.error(f"Error fetching subsession results for {subsession_id}: {e}")
            raise
            
    async def lookup_driver(self, query: str) -> List[Dict[str, Any]]:
        """
        Use lookup/drivers?search=... -> [{cust_id, display_name, ...}]
        
        Args:
            query (str): Search query (name or ID)
            
        Returns:
            List[Dict[str, Any]]: List of matching drivers
        """
        try:
            params = {'search': query}
            data = await self._get_json_via_download('/data/lookup/drivers', params)
            
            results = []
            if 'drivers' in data:
                for driver in data['drivers']:
                    results.append({
                        'cust_id': driver.get('cust_id'),
                        'display_name': driver.get('display_name', ''),
                        'car_number': driver.get('car_number', '')
                    })
                    
            return results
            
        except Exception as e:
            structured_logger.error(f"Error looking up driver '{query}': {e}")
            return []
