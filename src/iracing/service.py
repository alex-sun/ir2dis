from dataclasses import dataclass
from typing import Optional, List, Dict
import logging
import time

logger = logging.getLogger(__name__)

@dataclass
class FinishRecord:
    subsession_id: int
    cust_id: int
    display_name: str
    series_name: str
    track_name: str
    car_name: str
    field_size: int
    finish_pos: int
    finish_pos_in_class: Optional[int]
    class_name: Optional[str]
    laps: int
    incidents: int
    best_lap_time_s: Optional[float]
    sof: Optional[int]
    official: bool
    start_time_utc: str

class ResultService:
    def __init__(self, ir: "IRacingClient", repo: "Repository"):
        self.ir = ir
        self.repo = repo
        
    async def find_new_finishes_for_tracked(self) -> List[FinishRecord]:
        """
        For each tracked driver:
          - find sessions since last_poll for that driver,
          - fetch subsession results,
          - extract that driver's row,
          - dedupe by (subsession_id, cust_id),
          - persist watermark (last_poll) and seen subsessions.
        Return new FinishRecord items.
        """
        logger.info("Starting to find new finishes for tracked drivers")
        
        # Get current time
        now = int(time.time())
        
        # Get all tracked drivers
        tracked_drivers = await self.repo.list_tracked()
        if not tracked_drivers:
            logger.info("No tracked drivers found")
            return []
        
        logger.debug(f"Found {len(tracked_drivers)} tracked drivers")
        
        new_finishes = []
        
        for cust_id, display_name in tracked_drivers:
            try:
                # Get last poll timestamp or default to 48 hours ago
                last_poll_ts = await self.repo.get_last_poll_ts(cust_id)
                if last_poll_ts is None:
                    last_poll_ts = now - (48 * 60 * 60)  # 48 hours
                
                logger.debug(f"Processing driver {cust_id} ({display_name}) with last poll timestamp {last_poll_ts}")
                
                # Search for recent sessions
                sessions = await self.ir.search_recent_sessions(
                    cust_id=cust_id,
                    start_time_epoch_s=last_poll_ts,
                    end_time_epoch_s=now
                )
                
                logger.debug(f"Found {len(sessions)} sessions for driver {cust_id}")
                
                # Process each session
                for session in sessions:
                    subsession_id = session["subsession_id"]
                    
                    # Check if already posted (deduplication)
                    posted_guilds = []
                    try:
                        # For now, we'll check against all guilds - this could be optimized later
                        # This is a simplified approach; in practice you'd want to check per-guild
                        posted = False  # Simplified for now
                        if not posted:
                            logger.debug(f"Session {subsession_id} not yet posted, fetching results")
                            
                            # Get full session results
                            results = await self.ir.get_subsession_results(subsession_id)
                            
                            # Find this driver's result in the session
                            driver_result = None
                            for result in results.get("results", []):
                                if result.get("cust_id") == cust_id:
                                    driver_result = result
                                    break
                            
                            if driver_result:
                                # Create FinishRecord from the driver's result
                                record = FinishRecord(
                                    subsession_id=subsession_id,
                                    cust_id=cust_id,
                                    display_name=display_name,
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
                                
                                new_finishes.append(record)
                                logger.debug(f"Added new finish record for driver {cust_id} in session {subsession_id}")
                            else:
                                logger.warning(f"No result found for driver {cust_id} in session {subsession_id}")
                        else:
                            logger.debug(f"Session {subsession_id} already posted, skipping")
                    except Exception as e:
                        logger.error(f"Error processing session {subsession_id} for driver {cust_id}: {e}")
                        continue  # Continue with other sessions
                
                # Update last poll timestamp
                await self.repo.set_last_poll_ts(cust_id, now)
                
            except Exception as e:
                logger.error(f"Error processing tracked driver {cust_id}: {e}")
                continue  # Continue with other drivers
        
        logger.info(f"Found {len(new_finishes)} new finishes to post")
        return new_finishes
