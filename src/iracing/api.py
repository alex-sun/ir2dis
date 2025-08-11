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
        # Use semaphore to limit concurrent requests per client
        self._semaphore = asyncio.Semaphore(4)
        
    async def login(self) -> None:
        """Authenticate and prime cookies. Reuse across calls."""
        logger.info("Starting iRacing authentication...")
        
        # First, get the login page to extract any necessary tokens
        try:
            async with self.session.get(
                "https://members.iracing.com/membership/login",
                headers={"User-Agent": "IR2DIS Bot"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    raise Exception(f"Failed to get login page: {response.status}")
                
                # Extract any CSRF tokens or other required data from the login page
                # For now, we'll proceed with direct authentication
                
        except Exception as e:
            logger.warning(f"Could not fetch login page for token extraction: {e}")
        
        # Perform actual login using form submission
        try:
            async with self.session.post(
                "https://members.iracing.com/membership/authorize",
                data={
                    "username": self.username,
                    "password": self.password,
                    "rememberme": "true"
                },
                headers={"User-Agent": "IR2DIS Bot"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    raise Exception(f"Login failed with status {response.status}")
                
                # Check if login was successful by looking for a redirect or session cookie
                logger.info("iRacing authentication completed successfully")
                
        except Exception as e:
            logger.error(f"Failed to authenticate with iRacing: {e}")
            raise
    
    async def _get_json_via_download(self, path: str, params: Dict[str, Any]) -> Any:
        """
        GET /data/<path>?... -> returns {"link": "..."}; then GET link to obtain JSON payload.
        Retries with exponential backoff on 429/5xx.
        """
        async with self._semaphore:  # Limit concurrent requests
            max_retries = 5
            base_delay = 1.0
            
            for attempt in range(max_retries):
                try:
                    logger.debug(f"Fetching data from {path} (attempt {attempt + 1})")
                    
                    # First, get the download link
                    async with self.session.get(
                        f"https://members.iracing.com/data/{path}",
                        params=params,
                        headers={"User-Agent": "IR2DIS Bot"},
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 429:
                            # Rate limited - implement exponential backoff
                            delay = base_delay * (2 ** attempt) + (attempt * 0.1)  # Add jitter
                            delay = min(delay, 60)  # Cap at 60 seconds
                            logger.warning(f"Rate limited on {path}, retrying in {delay:.2f}s")
                            await asyncio.sleep(delay)
                            continue
                        
                        if response.status >= 500:
                            # Server error - implement exponential backoff
                            delay = base_delay * (2 ** attempt) + (attempt * 0.1)  # Add jitter
                            delay = min(delay, 60)  # Cap at 60 seconds
                            logger.warning(f"Server error on {path}, retrying in {delay:.2f}s")
                            await asyncio.sleep(delay)
                            continue
                        
                        if response.status != 200:
                            raise Exception(f"Failed to get download link for {path}: {response.status}")
                        
                        link_data = await response.json()
                        download_link = link_data.get("link")
                        
                        if not download_link:
                            raise Exception(f"No download link found in response for {path}")
                    
                    # Now fetch the actual JSON data from the download link
                    async with self.session.get(
                        download_link,
                        headers={"User-Agent": "IR2DIS Bot"},
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as data_response:
                        if data_response.status != 200:
                            raise Exception(f"Failed to fetch data from download link: {data_response.status}")
                        
                        return await data_response.json()
                
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Max retries exceeded for {path}: {e}")
                        raise
                    delay = base_delay * (2 ** attempt) + (attempt * 0.1)  # Add jitter
                    delay = min(delay, 60)  # Cap at 60 seconds
                    logger.warning(f"Network error on {path} (attempt {attempt + 1}), retrying in {delay:.2f}s: {e}")
                    await asyncio.sleep(delay)
            
            raise Exception(f"Failed to fetch data from {path} after {max_retries} attempts")
    
    async def search_recent_sessions(
        self, cust_id: int, start_time_epoch_s: int, end_time_epoch_s: int
    ) -> List[Dict[str, Any]]:
        """
        Query results/search for sessions involving cust_id (window ~last 48h).
        Filter to finished 'Race' simsession results.
        Returns list of minimal dicts containing subsession_id, series_name, track, start_time, official, etc.
        """
        logger.debug(f"Searching recent sessions for driver {cust_id}")
        
        params = {
            "custid": cust_id,
            "start_time": start_time_epoch_s,
            "end_time": end_time_epoch_s,
            "simsession_type": 1,  # Race sessions only
            "results_only": True,  # Only finished sessions
            "include_qualified": False,
            "include_unofficial": True,  # Include unofficial results (DNF is allowed)
        }
        
        try:
            data = await self._get_json_via_download("results/search", params)
            
            # Filter to only include race sessions that are finished and have classified results
            sessions = []
            for session in data.get("sessions", []):
                if session.get("simsession_type") == 1:  # Race session
                    # Check if it's a finished session with classified results
                    if (session.get("results") is not None or 
                        session.get("finished") is True or 
                        session.get("status") in ["finished", "classified"]):
                        sessions.append({
                            "subsession_id": session.get("subsession_id"),
                            "series_name": session.get("series_name"),
                            "track_name": session.get("track_name"),
                            "start_time": session.get("start_time"),
                            "official": session.get("official"),
                            "simsession_type": session.get("simsession_type")
                        })
            
            logger.debug(f"Found {len(sessions)} recent race sessions for driver {cust_id}")
            return sessions
            
        except Exception as e:
            logger.error(f"Error searching recent sessions: {e}")
            raise
    
    async def get_subsession_results(self, subsession_id: int) -> Dict[str, Any]:
        """
        Fetch results/get for subsession_id (full result sheet).
        """
        logger.debug(f"Fetching subsession results for {subsession_id}")
        
        params = {
            "subsession_id": subsession_id,
        }
        
        try:
            data = await self._get_json_via_download("results/get", params)
            return data
        except Exception as e:
            logger.error(f"Error fetching subsession results: {e}")
            raise
    
    async def lookup_driver(self, query: str) -> List[Dict[str, Any]]:
        """Use lookup/drivers?search=... -> [{cust_id, display_name, ...}]"""
        logger.debug(f"Looking up driver: {query}")
        
        params = {
            "search": query,
        }
        
        try:
            data = await self._get_json_via_download("lookup/drivers", params)
            
            # Extract relevant fields from the response
            drivers = []
            for driver in data.get("drivers", []):
                drivers.append({
                    "cust_id": driver.get("cust_id"),
                    "display_name": driver.get("display_name"),
                    "username": driver.get("username")
                })
            
            logger.debug(f"Found {len(drivers)} matching drivers for query '{query}'")
            return drivers
            
        except Exception as e:
            logger.error(f"Error looking up driver: {e}")
            raise
