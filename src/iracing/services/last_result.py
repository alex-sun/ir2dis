"""
Service for fetching the last completed official race result for a driver.
This service reuses the same API calls and logic as the poller to ensure consistency.
"""

from __future__ import annotations
import logging
import time
from typing import Optional, Dict, Any

from iracing.api import IRacingClient, APIError
from iracing.service import FinishRecord

logger = logging.getLogger(__name__)


async def fetch_last_official_result(api: IRacingClient, cust_id: int) -> FinishRecord | None:
    """
    Return the most recent **completed official** race result for the given cust_id,
    shaped exactly like the object the poller passes into the renderer.
    
    Uses the new API endpoints to avoid 404 errors from non-existent /results/search endpoint.
    
    Args:
        api: IRacingClient instance
        cust_id: iRacing customer ID
        
    Returns:
        FinishRecord for the most recent official race, or None if not found
    """
    if cust_id <= 0:
        logger.warning(f"Invalid customer_id provided: {cust_id}")
        return None
    
    try:
        # Get last 10 official races for the member (fast path)
        payload = await api.stats_member_recent_races(cust_id) or {}
        if isinstance(payload, dict):
            rows = payload.get("races", []) or []
        elif isinstance(payload, list):
            rows = payload
        else:
            rows = []
        if not rows:
            logger.info(f"No recent races found for driver {cust_id}")
            return None
        
        # Take the first completed row; shape matches NG stats rows
        latest = rows[0]
        subsession_id = int(latest.get("subsession_id"))
        
        # Fetch full session result (what the poller uses to render embeds)
        results = await api.results_get(subsession_id, include_licenses=False)
        
        # Find this driver's result in the session
        driver_result = None
        for result in results.get("results", []):
            if result.get("cust_id") == cust_id:
                driver_result = result
                break
        
        if not driver_result:
            logger.debug(f"No result found for driver {cust_id} in session {subsession_id}")
            return None

        # Create FinishRecord from the driver's result (same structure as poller)
        record = FinishRecord(
            subsession_id=subsession_id,
            cust_id=cust_id,
            display_name=driver_result.get("display_name", "Unknown"),
            series_name=latest["series_name"],
            track_name=latest["track_name"],
            car_name=driver_result.get("car_name", "Unknown"),
            field_size=results.get("field_size", 0),
            finish_pos=driver_result.get("finish_pos", 0),
            finish_pos_in_class=driver_result.get("finish_pos_in_class"),
            class_name=driver_result.get("class_name"),
            laps=driver_result.get("laps", 0),
            incidents=driver_result.get("incidents", 0),
            best_lap_time_s=driver_result.get("best_lap_time_s"),
            sof=results.get("sof", None),
            official=True,  # We know it's official since we got it from stats/member_recent_races
            start_time_utc=latest["start_time"]
        )
        
        logger.debug(f"Found official result for driver {cust_id} in session {subsession_id}")
        return record
        
    except APIError as e:
        logger.error("Failed to fetch last result for %s: %s", cust_id, e)
        raise
    except Exception as e:
        logger.error("Unexpected error fetching last result for %s: %s", cust_id, e)
        raise


async def fetch_last_official_result_simple(api: IRacingClient, cust_id: int) -> FinishRecord | None:
    """
    Simplified version that directly uses the poller's approach.
    
    This is a more direct implementation of what the poller does internally.
    """
    if cust_id <= 0:
        logger.warning(f"Invalid customer_id provided: {cust_id}")
        return None
    
    try:
        # Get current time
        now = int(time.time())
        
        # Search for recent sessions (same logic as poller)
        start_time_epoch_s = now - (48 * 60 * 60)  # Last 48 hours
        
        logger.debug(f"Searching recent sessions for driver {cust_id} from {start_time_epoch_s} to {now}")
        
        # IRacingClient methods are sync; run them off the event loop
        sessions = await asyncio.to_thread(
            api.search_recent_sessions,
            cust_id=cust_id,
            start_time_epoch_s=start_time_epoch_s,
            end_time_epoch_s=now
        )
        
        logger.debug(f"Found {len(sessions)} recent race sessions for driver {cust_id}")
        
        if not sessions:
            return None
        
        # Process in reverse order to get most recent first
        for session in reversed(sessions):
            subsession_id = session["subsession_id"]
            
            try:
                # IRacingClient methods are sync; run them off the event loop
                results = await asyncio.to_thread(api.get_subsession_results, subsession_id)
                
                # Find this driver's result
                driver_result = None
                for result in results.get("results", []):
                    if result.get("cust_id") == cust_id:
                        driver_result = result
                        break
                
                if driver_result and session.get("official"):
                    record = FinishRecord(
                        subsession_id=subsession_id,
                        cust_id=cust_id,
                        display_name=driver_result.get("display_name", "Unknown"),
                        series_name=session["series_name"],
                        track_name=session["track_name"],
                        car_name=driver_result.get("car_name", "Unknown"),
                        field_size=results.get("field_size", 0),
                        finish_pos=driver_result.get("finish_pos", 0),
                        finish_pos_in_class=driver_result.get("finish_pos_in_class"),
                        class_name=driver_result.get("class_name"),
                        laps=driver_result.get("laps", 0),
                        incidents=driver_result.get("incidents", 0),
                        best_lap_time_s=driver_result.get("best_lap_time_s"),
                        sof=results.get("sof", None),
                        official=session["official"],
                        start_time_utc=session["start_time"]
                    )
                    
                    return record
                    
            except Exception as e:
                logger.error(f"Error processing session {subsession_id}: {e}")
                continue
        
        return None
        
    except APIError as e:
        logger.error("Failed to fetch last result for %s: %s", cust_id, e)
        raise
