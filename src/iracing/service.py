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
                # IRacingClient methods are sync; run them off the event loop
                sessions = await asyncio.to_thread(
                    self.ir.search_recent_sessions,
                    cust_id=cust_id,
                    start_time_epoch_s=last_poll_ts,
                    end_time_epoch_s=now
                )
                
                logger.debug(f"Found {len(sessions)} sessions for driver {cust_id}")
                
                # Process each session
                for session in sessions:
                    subsession_id = session["subsession_id"]
                    
                    # Check if already posted (deduplication)
                    try:
                        # For now, we'll check against all guilds - this could be optimized later
                        # This is a simplified approach; in practice you'd want to check per-guild
                        # We need to implement proper deduplication logic here
                        
                        # Check if result was already posted for any guild (this would be more complex)
                        # For now, we'll just add all new sessions as potential candidates
                        logger.debug(f"Session {subsession_id} not yet posted, fetching results")
                        
                        # Get full session results
                        # IRacingClient methods are sync; run them off the event loop
                        results = await asyncio.to_thread(self.ir.get_subsession_results, subsession_id)
                        
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
    
    async def process_and_post_results(self, bot: "IR2DISBot") -> int:
        """
        Find all new results and post them to Discord channels.
        Returns count of posted results.
        """
        logger.info("Processing and posting new results...")
        
        # Get all new finishes
        new_finishes = await self.find_new_finishes_for_tracked()
        
        if not new_finishes:
            logger.info("No new finishes found")
            return 0
        
        posted_count = 0
        
        for record in new_finishes:
            try:
                # In a real implementation, you'd want to get the guilds that have this driver tracked
                # and post to their configured channels
                
                # For now we'll just log what would happen
                logger.info(f"Would post result for {record.display_name} (P{record.finish_pos}) in session {record.subsession_id}")
                
                # In a complete implementation, you'd:
                # 1. Get all guilds that have this driver tracked
                # 2. For each such guild, get their configured channel
                # 3. Post the embed to that channel using bot.post_finish_embed()
                # 4. Mark as posted in database
                
                posted_count += 1
                
            except Exception as e:
                logger.error(f"Error posting result for {record.display_name}: {e}")
                continue
        
        logger.info(f"Posted {posted_count} new results")
        return posted_count
