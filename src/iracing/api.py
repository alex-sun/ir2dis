from typing import Any, Dict, List, Optional
import aiohttp, asyncio, time
import logging

logger = logging.getLogger(__name__)

class IRacingClient:
    def __init__(self, username: str, password: str, session: Optional[aiohttp.ClientSession] = None):
        self.username = username
        self.password = password
        self.session = session or aiohttp.ClientSession()
        self._cookie_jar = aiohttp.CookieJar()
        
    async def login(self) -> None:
        """Authenticate and prime cookies. Reuse across calls."""
        # This is a simplified implementation - in practice you'd need the full iRacing authentication flow
        logger.info("Logging into iRacing...")
        # For now, we'll assume the session handles auth properly or that we're using a pre-authenticated session
        
    async def _get_json_via_download(self, path: str, params: Dict[str, Any]) -> Any:
        """
        GET /data/<path>?... -> returns {"link": "..."}; then GET link to obtain JSON payload.
        Retries with exponential backoff on 429/5xx.
        """
        retry_count = 0
        max_retries = 5
        base_delay = 1
        
        while True:
            try:
                # First, get the download link
                url = f"https://members.iracing.com/membership/api/data/{path}"
                async with self.session.get(url, params=params) as response:
                    if response.status == 429:
                        delay = min(base_delay * (2 ** retry_count), 60)
                        logger.warning(f"Rate limited, retrying in {delay}s")
                        await asyncio.sleep(delay)
                        retry_count += 1
                        continue
                    elif response.status >= 500:
                        delay = min(base_delay * (2 ** retry_count), 60)
                        logger.warning(f"Server error {response.status}, retrying in {delay}s")
                        await asyncio.sleep(delay)
                        retry_count += 1
                        continue
                    elif response.status != 200:
                        raise Exception(f"HTTP {response.status}: {await response.text()}")
                    
                    data = await response.json()
                    download_url = data.get("link")
                    if not download_url:
                        raise Exception("No download link found in response")
                
                # Then fetch the actual JSON payload
                async with self.session.get(download_url) as response:
                    if response.status == 429:
                        delay = min(base_delay * (2 ** retry_count), 60)
                        logger.warning(f"Rate limited, retrying in {delay}s")
                        await asyncio.sleep(delay)
                        retry_count += 1
                        continue
                    elif response.status >= 500:
                        delay = min(base_delay * (2 ** retry_count), 60)
                        logger.warning(f"Server error {response.status}, retrying in {delay}s")
                        await asyncio.sleep(delay)
                        retry_count += 1
                        continue
                    elif response.status != 200:
                        raise Exception(f"HTTP {response.status}: {await response.text()}")
                    
                    return await response.json()
                    
            except Exception as e:
                if retry_count >= max_retries:
                    logger.error(f"Failed after {max_retries} retries: {e}")
                    raise
                delay = min(base_delay * (2 ** retry_count), 60)
                logger.warning(f"Retrying in {delay}s due to error: {e}")
                await asyncio.sleep(delay)
                retry_count += 1

    async def search_recent_sessions(
        self, cust_id: int, start_time_epoch_s: int, end_time_epoch_s: int
    ) -> List[Dict[str, Any]]:
        """
        Query results/search for sessions involving cust_id (window ~last 48h).
        Filter to finished 'Race' simsession results.
        Returns list of minimal dicts containing subsession_id, series_name, track, start_time, official, etc.
        """
        params = {
            "cust_id": cust_id,
            "start_time": start_time_epoch_s,
            "end_time": end_time_epoch_s,
            "simsession_type": 1,  # Race sessions only
            "results_only": True,
            "include_qualified": False,
            "include_unofficial": False
        }
        
        try:
            data = await self._get_json_via_download("results/search", params)
            return [
                {
                    "subsession_id": session["subsession_id"],
                    "series_name": session.get("series_name"),
                    "track_name": session.get("track_name"),
                    "start_time": session.get("start_time"),
                    "official": session.get("official"),
                    "simsession_type": session.get("simsession_type")
                }
                for session in data.get("sessions", [])
                if session.get("simsession_type") == 1 and session.get("finished") is True
            ]
        except Exception as e:
            logger.error(f"Error searching recent sessions: {e}")
            return []

    async def get_subsession_results(self, subsession_id: int) -> Dict[str, Any]:
        """
        Fetch results/get for subsession_id (full result sheet).
        """
        params = {
            "subsession_id": subsession_id
        }
        
        try:
            return await self._get_json_via_download("results/get", params)
        except Exception as e:
            logger.error(f"Error getting subsession results: {e}")
            return {}

    async def lookup_driver(self, query: str) -> List[Dict[str, Any]]:
        """Use lookup/drivers?search=... -> [{cust_id, display_name, ...}]"""
        params = {
            "search": query
        }
        
        try:
            data = await self._get_json_via_download("lookup/drivers", params)
            return data.get("drivers", [])
        except Exception as e:
            logger.error(f"Error looking up driver: {e}")
            return []
