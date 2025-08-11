import asyncio
import logging
import time
from typing import Optional

from src.iracing.api import IRacingClient
from src.storage.repository import Repository
from src.iracing.service import ResultService, FinishRecord
from discord.ext import commands

logger = logging.getLogger(__name__)

class PollingEngine:
    def __init__(self, repository: Repository, iracing_client: IRacingClient, discord_bot: commands.Bot, interval: int = 120):
        self.repo = repository
        self.ir = iracing_client
        self.bot = discord_bot
        self.interval = interval
        self.running = False
        self.task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the polling engine."""
        logger.info("Polling engine started")
        self.running = True
        
        while self.running:
            try:
                await self._poll_once()
                await asyncio.sleep(self.interval)
            except Exception as e:
                logger.error(f"Error in polling cycle: {e}")
                # Continue polling even if one cycle fails
                await asyncio.sleep(self.interval)
    
    async def stop(self):
        """Stop the polling engine."""
        logger.info("Polling engine stopped")
        self.running = False
        if self.task:
            self.task.cancel()
    
    async def _poll_once(self):
        """Perform a single polling cycle."""
        logger.info("Starting polling cycle")
        
        # Get current time
        now = int(time.time())
        
        # Check if we have any guilds configured with channels
        try:
            # This is a simplified approach - in practice you'd want to check all guilds
            # For now, we'll just log and continue
            pass
        except Exception as e:
            logger.warning(f"Could not verify channel configuration: {e}")
        
        # Get all tracked drivers
        tracked_drivers = await self.repo.list_tracked()
        if not tracked_drivers:
            logger.info("No tracked drivers found, skipping poll cycle")
            return
        
        logger.debug(f"Found {len(tracked_drivers)} tracked drivers")
        
        # Process each driver
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
                
                if not sessions:
                    continue
                
                # Process each session
                processed_sessions = 0
                posted_count = 0
                
                for session in sessions:
                    subsession_id = session["subsession_id"]
                    
                    try:
                        # Check if already posted (deduplication)
                        # For now, we'll check against all guilds - this could be optimized later
                        posted = False  # Simplified approach
                        
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
                                
                                # Get all guilds with configured channels
                                try:
                                    # This is a simplified approach - in practice you'd want to 
                                    # iterate through actual guilds and their channel configurations
                                    pass
                                except Exception as e:
                                    logger.warning(f"Could not get guild configurations: {e}")
                                
                                processed_sessions += 1
                            else:
                                logger.debug(f"No result found for driver {cust_id} in session {subsession_id}")
                        else:
                            logger.debug(f"Session {subsession_id} already posted, skipping")
                            
                    except Exception as e:
                        logger.error(f"Error processing session {subsession_id} for driver {cust_id}: {e}")
                        continue  # Continue with other sessions
                
                # Update last poll timestamp
                await self.repo.set_last_poll_ts(cust_id, now)
                
                if processed_sessions > 0:
                    logger.info(f"Driver {cust_id} - Processed {processed_sessions} sessions")
                    
            except Exception as e:
                logger.error(f"Error processing tracked driver {cust_id}: {e}")
                continue  # Continue with other drivers
        
        logger.info("Polling cycle completed")

# Keep the old polling function for backward compatibility if needed
async def run_poller(repository: Repository, iracing_client: IRacingClient, discord_bot: commands.Bot):
    """Legacy poller function - kept for compatibility."""
    engine = PollingEngine(repository, iracing_client, discord_bot)
    await engine.start()
