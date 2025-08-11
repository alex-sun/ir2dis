from dataclasses import dataclass
from typing import Optional, List, Dict
import logging
from datetime import datetime, timedelta

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
        logger.info("Starting poll cycle to find new finishes")
        
        # Get all tracked drivers
        tracked_drivers = await self.repo.list_tracked()
        if not tracked_drivers:
            logger.info("No tracked drivers found")
            return []
            
        now = int(datetime.utcnow().timestamp())
        new_finishes = []
        
        for cust_id, display_name in tracked_drivers:
            try:
                # Get last poll timestamp or default to 48 hours ago
                last_poll_ts = await self.repo.get_last_poll_ts(cust_id)
                if not last_poll_ts:
                    last_poll_ts = now - (48 * 3600)  # 48 hours ago
                
                logger.info(f"Checking for sessions for driver {display_name} (cust_id: {cust_id}) since {last_poll_ts}")
                
                # Search recent sessions
                sessions = await self.ir.search_recent_sessions(cust_id, last_poll_ts, now)
                logger.info(f"Found {len(sessions)} sessions for driver {display_name}")
                
                for session in sessions:
                    subsession_id = session["subsession_id"]
                    
                    # Check if already posted (deduplication) - this is done per guild
                    # For now we'll return all results and let the poller handle deduplication
                    
                    # Get full session results
                    results = await self.ir.get_subsession_results(subsession_id)
                    if not results:
                        logger.warning(f"No results found for subsession {subsession_id}")
                        continue
                    
                    # Extract driver's row from results
                    driver_row = None
                    for row in results.get("results", []):
                        if row.get("cust_id") == cust_id:
                            driver_row = row
                            break
                    
                    if not driver_row:
                        logger.warning(f"Driver {display_name} (cust_id: {cust_id}) not found in session {subsession_id} results")
                        continue
                    
                    # Create FinishRecord
                    record = FinishRecord(
                        subsession_id=subsession_id,
                        cust_id=cust_id,
                        display_name=display_name,
                        series_name=session.get("series_name", ""),
                        track_name=session.get("track_name", ""),
                        car_name=driver_row.get("car_name", ""),
                        field_size=results.get("field_size", 0),
                        finish_pos=driver_row.get("finish_pos", 0),
                        finish_pos_in_class=driver_row.get("finish_pos_in_class"),
                        class_name=driver_row.get("class_name"),
                        laps=driver_row.get("laps", 0),
                        incidents=driver_row.get("incidents", 0),
                        best_lap_time_s=driver_row.get("best_lap_time_s"),
                        sof=results.get("sof", None),
                        official=session.get("official", False),
                        start_time_utc=session.get("start_time", "")
                    )
                    
                    new_finishes.append(record)
                    
            except Exception as e:
                logger.error(f"Error processing driver {display_name} (cust_id: {cust_id}): {e}")
                continue
        
        # Update last poll timestamp for each driver
        for cust_id, _ in tracked_drivers:
            await self.repo.set_last_poll_ts(cust_id, now)
            
        logger.info(f"Found {len(new_finishes)} new finishes")
        return new_finishes
    
    async def process_and_post_results(self, records: List[FinishRecord], bot) -> int:
        """
        Process and post results to Discord channels.
        
        Args:
            records (List[FinishRecord]): List of finish records to process
            bot: Discord bot instance
            
        Returns:
            int: Number of posts created
        """
        posted_count = 0
        
        # Get all guilds with configured channels
        guild_ids = await self.repo.list_guilds_with_channel()
        
        for record in records:
            try:
                # For each guild, post the result if not already posted
                for guild_id in guild_ids:
                    if not await self.repo.was_posted(record.subsession_id, record.cust_id, guild_id):
                        # Post to Discord channel
                        channel_id = await self.repo.get_channel_for_guild(guild_id)
                        if channel_id:
                            try:
                                await self.post_finish_embed(bot, record, channel_id)
                                # Mark as posted
                                await self.repo.mark_posted(record.subsession_id, record.cust_id, guild_id)
                                posted_count += 1
                                logger.info(f"Posted result for {record.display_name} in guild {guild_id}")
                            except Exception as e:
                                logger.error(f"Failed to post result for {record.display_name}: {e}")
                                
            except Exception as e:
                logger.error(f"Error processing record for {record.display_name}: {e}")
                
        return posted_count
    
    async def post_finish_embed(self, bot, record: FinishRecord, channel_id: int):
        """Post a Discord embed for a finish record."""
        import discord
        color = discord.Color.green() if record.finish_pos <= 3 else (discord.Color.orange() if record.finish_pos <= 10 else discord.Color.red())
        
        # Build description lines
        desc_lines = [
            f"**Series:** {record.series_name} • **Track:** {record.track_name} • **Car:** {record.car_name}",
            f"**Field:** {record.field_size} • **Laps:** {record.laps} • **Inc:** {record.incidents} • **SOF:** {record.sof or '—'}"
        ]
        
        if record.best_lap_time_s:
            desc_lines.append(f"**Best:** {record.best_lap_time_s:.3f}s")
            
        desc_lines.append("Official: ✅" if record.official else "Official: ❌")
        
        embed = discord.Embed(
            title=f"🏁 {record.display_name} — P{record.finish_pos}" + (f" (Class P{record.finish_pos_in_class})" if record.finish_pos_in_class else ""),
            description="\n".join(desc_lines),
            colour=color,
        )
        embed.set_footer(text=f"Subsession {record.subsession_id} • {record.start_time_utc}")
        
        channel = bot.get_channel(int(channel_id))
        if channel is None:
            # fetch if not cached
            channel = await bot.fetch_channel(int(channel_id))
            
        await channel.send(embed=embed)
        
    async def _get_guilds_with_channels(self) -> List[int]:
        """Get all guild IDs that have configured channels."""
        return await self.repo.list_guilds_with_channel()
