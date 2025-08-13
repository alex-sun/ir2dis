import base64
import hashlib
from typing import Any, Dict, List, Optional
import aiohttp, asyncio, time
import logging

logger = logging.getLogger(__name__)

def _hash_password(raw_password: str, email: str) -> str:
    """Hash password according to iRacing requirements: Base64(SHA256(password + lower(email)))"""
    salted = (raw_password or "") + (email or "").strip().lower()
    digest = hashlib.sha256(salted.encode("utf-8")).digest()
    return base64.b64encode(digest).decode("ascii")

class APIError(Exception):
    """Raised for non-200 or malformed iRacing API responses."""
    pass

class IRacingClient:
    AUTH_URL = "https://members-ng.iracing.com/auth"
    BASE_URL = "https://members-ng.iracing.com"  # data API host
    
    def __init__(self, username: str, password: str, session: Optional[aiohttp.ClientSession] = None):
        self.username = username
        self.password = password
        self.session = session or aiohttp.ClientSession()
        # Use semaphore to limit concurrent requests per client
        self._semaphore = asyncio.Semaphore(4)
        
    async def close(self) -> None:
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
        
    async def login(self) -> None:
        """Authenticate with iRacing using the new salted+hashed password flow."""
        logger.info("Starting iRacing authentication...")
        
        # Use the new auth endpoint with salted+hashed password
        payload = {
            "email": self.username,
            "password": _hash_password(self.password, self.username),
        }
        
        try:
            async with self.session.post(
                self.AUTH_URL,
                json=payload,
                allow_redirects=False,
                headers={"User-Agent": "IR2DIS Bot"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    txt = await response.text()
                    raise APIError(f"Auth failed: {response.status} {txt[:200]}")
                
                # Cookies are automatically stored in the session and will be reused
                logger.info("iRacing authentication completed successfully")
                
        except Exception as e:
            logger.error(f"Failed to authenticate with iRacing: {e}")
            raise APIError(f"Failed to authenticate with iRacing: {e}")
    
    def _normalize_params(self, params: Dict[str, Any]) -> Dict[str, str]:
        """Normalize parameters to ensure they are strings, ints, or floats."""
        if not params:
            return {}
        out: Dict[str, str] = {}
        for k, v in params.items():
            if v is None:
                continue
            # Booleans → "true"/"false"
            if isinstance(v, bool):
                out[k] = "true" if v else "false"
                continue
            # Iterables → CSV
            if isinstance(v, (list, tuple, set)):
                out[k] = ",".join(str(x) for x in v)
                continue
            # Everything else → string
            out[k] = str(v)
        return out

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
                    
                    # Normalize params before sending to API
                    normalized_params = self._normalize_params(params)
                    
                    # First, get the download link
                    async with self.session.get(
                        f"{self.BASE_URL}/data/{path.lstrip('/')}",
                        params=normalized_params,
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
                            raise APIError(f"Failed to get download link for {path}: {response.status} (host={self.BASE_URL}, params={normalized_params})")
                        
                        link_data = await response.json()
                        download_link = link_data.get("link")
                        
                        if not download_link:
                            raise APIError(f"No download link found in response for {path}")
                    
                    # Now fetch the actual JSON data from the download link
                    async with self.session.get(
                        download_link,
                        headers={"User-Agent": "IR2DIS Bot"},
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as data_response:
                        if data_response.status != 200:
                            raise Exception(f"Failed to fetch data from download link: {data_response.status}")
                        
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Max retries exceeded for {path}: {e}")
                        raise
                    delay = base_delay * (2 ** attempt) + (attempt * 0.1)  # Add jitter
                    delay = min(delay, 60)  # Cap at 60 seconds
                    logger.warning(f"Network error on {path} (attempt {attempt + 1}), retrying in {delay:.2f}s: {e}")
                    await asyncio.sleep(delay)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Max retries exceeded for {path}: {e}")
                        raise APIError(f"Max retries exceeded for {path}: {e}")
                    delay = base_delay * (2 ** attempt) + (attempt * 0.1)  # Add jitter
                    delay = min(delay, 60)  # Cap at 60 seconds
                    logger.warning(f"Network error on {path} (attempt {attempt + 1}), retrying in {delay:.2f}s: {e}")
                    await asyncio.sleep(delay)
            
            raise APIError(f"Failed to fetch data from {path} after {max_retries} attempts")
    
    # Returns the last 10 OFFICIAL races for a member (fast path for "latest race")
    async def stats_member_recent_races(self, cust_id: int):
        return await self._get_json_via_download("stats/member_recent_races", params={"cust_id": cust_id})
    
    # Fetch full session result once you have a subsession_id
    async def results_get(self, subsession_id: int, include_licenses: bool = False):
        return await self._get_json_via_download("results/get", params={
            "subsession_id": subsession_id,
            "include_licenses": include_licenses
        })

    # --- Back-compat shim for poller ---
    def search_recent_sessions(
        self,
        *,
        cust_id: int,
        start_time: int | None = None,
        end_time: int | None = None,
        simsession_type: int | None = None,
        results_only: bool = True,
        include_qualified: bool = False,
        include_unofficial: bool = True,
        limit: int | None = None,
    ):
        """
        Backward-compatible replacement for the old results/search call.
        We now use stats/member_recent_races (official only) and ignore
        unsupported filters. Returns rows that at least include 'subsession_id',
        which is what the poller needs to fetch full results.
        """
        # For backward compatibility, we'll use the new NG endpoints
        # The old method had many parameters but we can map them appropriately
        rows = self.stats_member_recent_races(cust_id) or []
        if limit is not None and limit >= 0:
            rows = rows[:limit]
        return rows

    def fetch_session_result(self, subsession_id: int):
        """Compatibility wrapper used by poller, calls results/get."""
        return self.results_get(subsession_id)
    
    # OLD (WRONG): endpoint does not exist on NG API - kept for reference only
    # async def search_recent_sessions(
    #     self, cust_id: int, start_time_epoch_s: int, end_time_epoch_s: int
    # ) -> List[Dict[str, Any]]:
    #     """
    #     Query results/search for sessions involving cust_id (window ~last 48h).
    #     Filter to finished 'Race' simsession results.
    #     Returns list of minimal dicts containing subsession_id, series_name, track, start_time, official, etc.
    #     """
    #     logger.debug(f"Searching recent sessions for driver {cust_id}")
    #     
    #     params = {
    #         "custid": cust_id,
    #         "start_time": start_time_epoch_s,
    #         "end_time": end_time_epoch_s,
    #         "simsession_type": 1,  # Race sessions only
    #         "results_only": True,  # Only finished sessions
    #         "include_qualified": False,
    #         "include_unofficial": True,  # Include unofficial results (DNF is allowed)
    #     }
    #     
    #     try:
    #         data = await self._get_json_via_download("results/search", params)
    #         
    #         # Filter to only include race sessions that are finished and have classified results
    #         sessions = []
    #         for session in data.get("sessions", []):
    #             if session.get("simsession_type") == 1:  # Race session
    #                 # Check if it's a finished session with classified results
    #                 if (session.get("results") is not None or 
    #                     session.get("finished") is True or 
    #                     session.get("status") in ["finished", "classified"]):
    #                     sessions.append({
    #                         "subsession_id": session.get("subsession_id"),
    #                         "series_name": session.get("series_name"),
    #                         "track_name": session.get("track_name"),
    #                         "start_time": session.get("start_time"),
    #                         "official": session.get("official"),
    #                         "simsession_type": session.get("simsession_type")
    #                     })
    #         
    #         logger.debug(f"Found {len(sessions)} recent race sessions for driver {cust_id}")
    #         return sessions
    #         
    #     except Exception as e:
    #         logger.error(f"Error searching recent sessions: {e}")
    #         raise
    
    
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
            raise APIError(f"Error fetching subsession results: {e}")
    
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
            raise APIError(f"Error looking up driver: {e}")

    async def member_get(self, cust_ids: list[int] | tuple[int, ...], include_licenses: bool = False) -> List[Dict[str, Any]]:
        """Use member/get?cust_ids=... to get member details by numeric ID"""
        logger.debug(f"Getting members for IDs: {cust_ids}")
        
        ids = ",".join(str(i) for i in cust_ids)
        params = {
            "cust_ids": ids,
            "include_licenses": include_licenses  # This will be normalized by _normalize_params
        }
        
        try:
            data = await self._get_json_via_download("member/get", params)
            
            # Return the list of members from the response
            if 'members' in data:
                return data['members']
            else:
                return []
        except Exception as e:
            logger.error(f"Error getting member details: {e}")
            raise APIError(f"Error getting member details: {e}")
