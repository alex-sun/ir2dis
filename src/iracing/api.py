import base64
import hashlib
from typing import Any, Dict, List, Optional
import aiohttp, asyncio, time, os, json, datetime as _dt, pathlib, uuid
import logging

logger = logging.getLogger(__name__)
log = logging.getLogger(__name__)

def _hash_password(raw_password: str, email: str) -> str:
    """Hash password according to iRacing requirements: Base64(SHA256(password + lower(email)))"""
    salted = (raw_password or "") + (email or "").strip().lower()
    digest = hashlib.sha256(salted.encode("utf-8")).digest()
    return base64.b64encode(digest).decode("ascii")

class APIError(Exception):
    """Raised for non-200 or malformed iRacing API responses."""
    pass


class AuthError(APIError):
    """Raised when authentication appears to be invalid/expired."""
    pass

_WIRELOG_ENABLED = os.getenv("IRACING_WIRE_LOG", "0") == "1"
_WIRELOG_DIR = os.getenv("IRACING_WIRE_LOG_DIR", "/app/wirelogs")
if _WIRELOG_ENABLED:
    log.info("Wirelog ENABLED → dir=%s", _WIRELOG_DIR)

def _wirelog_write(step: str, service: str, method: str,
                   req_headers: dict, req_params: dict, req_body: str,
                   resp_status: int, resp_headers: dict, resp_text_preview: str, resp_content: bytes,
                   duration_ms: int, corr: str) -> None:
    if not _WIRELOG_ENABLED:
        return
    try:
        day = _dt.datetime.utcnow().strftime("%Y-%m-%d")
        ts = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%S.%fZ")
        outdir = pathlib.Path(_WIRELOG_DIR) / day
        outdir.mkdir(parents=True, exist_ok=True)
        base = f"{ts}_{corr}_{service}_{method}_{step}_{resp_status}"
        meta_path = outdir / f"{base}.json"
        # request body (best-effort)
        meta = {
            "timestamp": ts,
            "step": step,  # "link" or "download"
            "service": service,
            "method": method,
            "correlation_id": corr,
            "duration_ms": duration_ms,
            "request": {
                "headers": req_headers or {},
                "params": req_params or {},
                "body": req_body,
            },
            "response": {
                "status": resp_status,
                "headers": resp_headers or {},
                "body_preview": resp_text_preview[:5000],
            },
        }
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        # raw body (full bytes)
        body_path = outdir / f"{base}.body"
        try:
            body_path.write_bytes(resp_content or b"")
        except Exception:
            pass
        log.info("Wirelog wrote %s", meta_path)
    except Exception:
        # never break the client due to logging
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
        
    async def login(self, force: bool = False) -> None:
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
                    
                    def _raise_with_body(prefix: str, r):
                        body = ""
                        try:
                            body = (r.text or "")[:200]
                        except Exception:
                            pass
                        raise APIError(f"{prefix}: {r.status} (host={self.BASE_URL}, params={normalized_params}, body={body!r})")
                    
                    # Step 1: request link
                    corr = uuid.uuid4().hex[:8]
                    svc, api_method = (path.split("/", 1) + [""])[:2] if "/" in path else (path, "")
                    
                    start = time.monotonic()
                    async with self.session.get(
                        f"{self.BASE_URL}/data/{path.lstrip('/')}",
                        params=normalized_params,
                        headers={"User-Agent": "IR2DIS Bot"},
                        timeout=aiohttp.ClientTimeout(total=30),
                        allow_redirects=True
                    ) as response:
                        end = time.monotonic()
                        if response.status in (401, 403):
                            # one re-login attempt if available
                            if hasattr(self, "login") and callable(getattr(self, "login")):
                                try:
                                    await self.login(force=True)  # implement force=True to refresh cookies if you can
                                except Exception:
                                    pass
                                response = await self.session.get(
                                    f"{self.BASE_URL}/data/{path.lstrip('/')}",
                                    params=normalized_params,
                                    headers={"User-Agent": "IR2DIS Bot"},
                                    timeout=aiohttp.ClientTimeout(total=30),
                                    allow_redirects=True
                                )
                            if response.status in (401, 403):
                                body = (response.text or "")[:200]
                                raise AuthError(f"Auth required/expired for {path}: {response.status} (params={normalized_params}, body={body!r})")
                        if response.status != 200:
                            _raise_with_body(f"Failed to get download link for {path}", response)
                        
                        # Parse link
                        try:
                            link_data = await response.json()
                        except Exception:
                            _raise_with_body(f"Non-JSON link response for {path}", response)
                        download_link = link_data.get("link")
                        if not download_link:
                            raise APIError(f"No 'link' in response for {path} (host={self.BASE_URL}, params={normalized_params}, body={str(link_data)[:200]!r})")
                        
                        # Log the link step
                        try:
                            req_body = ""
                            try:
                                if hasattr(response.request_info, 'headers'):
                                    req_headers = dict(response.request_info.headers)
                                else:
                                    req_headers = {}
                                resp_text_preview = response.text[:5000] if hasattr(response, 'text') and response.text else ""
                                _wirelog_write("link", svc, api_method,
                                             req_headers, normalized_params, req_body,
                                             response.status, dict(response.headers or {}), 
                                             resp_text_preview, response.content.read() if hasattr(response, 'content') else b"",
                                             int((end - start) * 1000), corr)
                            except Exception:
                                pass
                        except Exception:
                            pass
                    
                    # Step 2: download the payload using the SAME session
                    start2 = time.monotonic()
                    async with self.session.get(
                        download_link,
                        headers={"User-Agent": "IR2DIS Bot"},
                        timeout=aiohttp.ClientTimeout(total=60),
                        allow_redirects=True
                    ) as data_response:
                        end2 = time.monotonic()
                        if data_response.status in (401, 403):
                            # try one re-login here too
                            if hasattr(self, "login") and callable(getattr(self, "login")):
                                try:
                                    await self.login(force=True)
                                except Exception:
                                    pass
                                data_response = await self.session.get(
                                    download_link,
                                    headers={"User-Agent": "IR2DIS Bot"},
                                    timeout=aiohttp.ClientTimeout(total=60),
                                    allow_redirects=True
                                )
                            if data_response.status in (401, 403):
                                body = (data_response.text or "")[:200]
                                raise AuthError(f"Auth required/expired for download of {path}: {data_response.status} (body={body!r})")
                        if data_response.status != 200:
                            _raise_with_body(f"Failed to download payload for {path}", data_response)
                        
                        try:
                            obj = await data_response.json()
                            # Optional: DEBUG one-liner to understand shapes during dev
                            logger.debug("GET %s → type=%s keys=%s",
                                         path, type(obj).__name__,
                                         list(obj.keys())[:5] if isinstance(obj, dict) else "n/a")
                            
                            # Log the download step
                            try:
                                req_headers = {}
                                resp_text_preview = ""
                                try:
                                    resp_text_preview = data_response.text[:5000] if hasattr(data_response, 'text') and data_response.text else ""
                                except Exception:
                                    pass
                                _wirelog_write("download", svc, api_method,
                                             req_headers, None, "",
                                             data_response.status, dict(data_response.headers or {}), 
                                             resp_text_preview, data_response.content.read() if hasattr(data_response, 'content') else b"",
                                             int((end2 - start2) * 1000), corr)
                            except Exception:
                                pass
                            
                            return obj
                        except Exception:
                            _raise_with_body(f"Non-JSON payload for {path}", data_response)
                    
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
    def search_recent_sessions(self, *, cust_id: int, **kwargs):
        """
        Backward-compatible replacement for the old results/search call.
        We now use stats/member_recent_races (official only).
        Accepts legacy kwargs (start_time_epoch_s, end_time_epoch_s, start_time, end_time,
        simsession_type, results_only, include_qualified, include_unofficial, limit, max_results)
        but ignores unsupported filters. Returns a list of rows that include 'subsession_id'.
        """
        # Extract a limit from any legacy key; ignore the rest (we're using "recent official")
        limit = None
        for k in ("limit", "max_results"):
            if k in kwargs and kwargs[k] is not None:
                try:
                    limit = int(kwargs[k])
                except Exception:
                    limit = None
                break

        # Friendly note if someone thinks unofficial/qualified filters apply here
        iu = kwargs.get("include_unofficial")
        iq = kwargs.get("include_qualified")
        if iu or iq:
            logger.debug(
                "search_recent_sessions: ignoring unsupported filters "
                "(include_unofficial=%r, include_qualified=%r) for stats/member_recent_races",
                iu, iq
            )

        # These legacy time keys are accepted but ignored in this shim:
        # start_time_epoch_s, end_time_epoch_s, start_time, end_time, simsession_type, results_only
        payload = self.stats_member_recent_races(cust_id) or {}
        if isinstance(payload, dict):
            rows = payload.get("races", []) or []
        elif isinstance(payload, list):
            rows = payload
        else:
            rows = []
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
