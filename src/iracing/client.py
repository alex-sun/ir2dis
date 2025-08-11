#!/usr/bin/env python3
"""
iRacing API client for Data API 2.0 with download link flow and retries.
"""

from typing import Any, Dict, List, Optional
import aiohttp
import asyncio
import time
import logging

logger = logging.getLogger(__name__)

class IRacingClient:
    def __init__(self, username: str, password: str, session: Optional[aiohttp.ClientSession] = None):
        self.username = username
        self.password = password
        self.session = session or aiohttp.ClientSession()
        self._cookie_jar = aiohttp.CookieJar()
        # Use a semaphore to limit concurrent requests per client
        self._semaphore = asyncio.Semaphore(4)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
    
    async def login(self) -> None:
        """Authenticate and prime cookies. Reuse across calls."""
        try:
            # First get the login page to acquire session cookies
            async with self._semaphore:
                async with self.session.get('https://members.iracing.com/membersite/login') as response:
                    if response.status != 200:
                        raise Exception(f"Failed to get login page: {response.status}")
            
            # Then post credentials
            login_data = {
                'username': self.username,
                'password': self.password,
                'action': 'login'
            }
            
            async with self._semaphore:
                async with self.session.post('https://members.iracing.com/membersite/login', data=login_data) as response:
                    if response.status != 200:
                        raise Exception(f"Login failed: {response.status}")
                    
            logger.info("iRacing login successful")
        except Exception as e:
            logger.error(f"iRacing login failed: {e}")
            raise
    
    async def _get_json_via_download(self, path: str, params: Dict[str, Any]) -> Any:
        """
        GET /data/<path>?... -> returns {"link": "..."}; then GET link to obtain JSON payload.
        Retries with exponential backoff on 429/5xx.
        """
        max_retries = 5
        base_delay = 1.0
        max_delay = 60.0
        
        for attempt in range(max_retries):
            try:
                url = f'https://members.iracing.com/data/{path}'
                
                async with self._semaphore:
                    async with self.session.get(url, params=params) as response:
                        if response.status == 429:
                            # Rate limited - wait and retry
                            delay = min(base_delay * (2 ** attempt), max_delay)
                            jitter = delay * 0.1  # Add some jitter
                            await asyncio.sleep(delay + jitter)
                            continue
                        elif response.status >= 500:
                            # Server error - wait and retry
                            delay = min(base_delay * (2 ** attempt), max_delay)
                            jitter = delay * 0.1
                            await asyncio.sleep(delay + jitter)
                            continue
                        elif response.status != 200:
                            raise Exception(f"API request failed with status {response.status}: {await response.text()}")
                        
                        data = await response.json()
                
                # If we have a download link, fetch the actual JSON content
                if 'link' in data and data['link']:
                    async with self._semaphore:
                        async with self.session.get(data['link']) as response:
                            if response.status != 200:
                                raise Exception(f"Download failed: {response.status}")
                            return await response.json()
                else:
                    # Direct JSON response
                    return data
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == max_retries - 1:
                    raise
                delay = min(base_delay * (2 ** attempt), max_delay)
                jitter = delay * 0.1
                await asyncio.sleep(delay + jitter)
                continue
            except Exception as e:
                logger.error(f"Error in _get_json_via_download: {e}")
                if attempt == max_retries - 1:
                    raise
                # Wait before retrying for other exceptions
                delay = min(base_delay * (2 ** attempt), max_delay)
                jitter = delay * 0.1
                await asyncio.sleep(delay + jitter)
                continue
        
        raise Exception("Max retries exceeded in _get_json_via_download")
    
    async def search_recent_sessions(
        self, cust_id: int, start_time_epoch_s: int, end_time_epoch_s: int
    ) -> List[Dict[str, Any]]:
        """
        Query results/search for sessions involving cust_id (window ~last 48h).
        Filter to finished 'Race' simsession results.
        Returns list of minimal dicts containing subsession_id, series_name, track, start_time, official, etc.
        """
        try:
            params = {
                'cust_id': cust_id,
                'start_time': start_time_epoch_s,
                'end_time': end_time_epoch_s,
                'simsession_type': 1,  # Race sessions only
                'results_only': True,  # Only finished sessions
                'page_size': 50  # Get up to 50 results
            }
            
            data = await self._get_json_via_download('results/search', params)
            
            # Filter for race sessions that are classified (finished)
            sessions = []
            if 'sessions' in data:
                for session in data['sessions']:
                    # Only include finished Race sessions (simsession_type=1) with a result
                    if (session.get('simsession_type') == 1 and 
                        session.get('results') is not None and
                        session.get('classified', False)):  # Only classified finishes
                        sessions.append({
                            'subsession_id': session['subsession_id'],
                            'series_name': session.get('series_name', ''),
                            'track_name': session.get('track_name', ''),
                            'start_time': session.get('start_time', ''),
                            'official': session.get('official', False)
                        })
            
            return sessions
        except Exception as e:
            logger.error(f"Error in search_recent_sessions: {e}")
            raise
    
    async def get_subsession_results(self, subsession_id: int) -> Dict[str, Any]:
        """
        Fetch results/get for subsession_id (full result sheet).
        """
        try:
            params = {
                'subsession_id': subsession_id
            }
            
            return await self._get_json_via_download('results/get', params)
        except Exception as e:
            logger.error(f"Error in get_subsession_results: {e}")
            raise
    
    async def lookup_driver(self, query: str) -> List[Dict[str, Any]]:
        """Use lookup/drivers?search=... -> [{cust_id, display_name, ...}]"""
        try:
            params = {
                'search': query,
                'page_size': 5
            }
            
            data = await self._get_json_via_download('lookup/drivers', params)
            
            # Return the list of drivers from the response
            if 'drivers' in data:
                return data['drivers']
            else:
                return []
        except Exception as e:
            logger.error(f"Error in lookup_driver: {e}")
            raise
