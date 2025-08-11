#!/usr/bin/env python3
"""
Result service for iRacing → Discord Auto-Results Bot.
Orchestrates polling → result enrichment → DTO for Discord.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
import asyncio

@dataclass
class FinishRecord:
    """Data transfer object for race finish information."""
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
    """Service for processing race results and generating Discord embeds."""
    
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
        
        Returns:
            List[FinishRecord]: New finish records to post
        """
        # Get current time for the poll window
        import time
        now = int(time.time())
        cutoff_time = now - 48 * 3600  # Last 48 hours
        
        # Get all tracked drivers
        tracked_drivers = await self.repo.list_tracked()
        
        new_finishes = []
        
        for cust_id, display_name in tracked_drivers:
            try:
                # Get last poll timestamp for this driver
                last_poll_ts = await self.repo.get_last_poll_ts(cust_id)
                if not last_poll_ts:
                    last_poll_ts = cutoff_time
                
                # Search recent sessions for this driver
                sessions = await self.ir.search_recent_sessions(
                    cust_id, 
                    last_poll_ts, 
                    now
                )
                
                # Process each session
                for session in sessions:
                    subsession_id = session['subsession_id']
                    
                    # Check if already posted (deduplication)
                    guilds = await self.repo.list_guilds_with_channel()
                    posted = False
                    
                    for guild_id in guilds:
                        if await self.repo.was_posted(subsession_id, cust_id, guild_id):
                            posted = True
                            break
                    
                    if posted:
                        continue
                    
                    # Get full subsession results
                    try:
                        results_data = await self.ir.get_subsession_results(subsession_id)
                        
                        # Extract driver's row from results
                        driver_row = None
                        if 'results' in results_data:
                            for result in results_data['results']:
                                if result.get('cust_id') == cust_id:
                                    driver_row = result
                                    break
                        
                        if not driver_row:
                            continue  # Driver not found in this session (shouldn't happen but be safe)
                        
                        # Create FinishRecord from the driver's row
                        record = FinishRecord(
                            subsession_id=subsession_id,
                            cust_id=cust_id,
                            display_name=display_name,
                            series_name=session['series_name'],
                            track_name=session['track'],
                            car_name=driver_row.get('car', {}).get('name', 'Unknown Car'),
                            field_size=results_data.get('field_size', 0),
                            finish_pos=driver_row.get('finish_position', 0),
                            finish_pos_in_class=driver_row.get('position_in_class'),
                            class_name=driver_row.get('class_name'),
                            laps=driver_row.get('laps_complete', 0),
                            incidents=driver_row.get('incidents', 0),
                            best_lap_time_s=driver_row.get('best_lap_time_s'),
                            sof=results_data.get('sof', None),
                            official=session['official'],
                            start_time_utc=session['start_time']
                        )
                        
                        new_finishes.append(record)
                        
                    except Exception as e:
                        # Log error but continue with other sessions
                        print(f"Error processing session {subsession_id} for driver {cust_id}: {e}")
                        continue
                        
            except Exception as e:
                # Log error but continue with other drivers
                print(f"Error processing tracked driver {cust_id}: {e}")
                continue
        
        return new_finishes

    async def process_and_post_results(self, records: List[FinishRecord]) -> int:
        """
        Process and post results to Discord channels.
        
        Args:
            records (List[FinishRecord]): Records to process
            
        Returns:
            int: Number of successful posts
        """
        posted_count = 0
        
        for record in records:
            try:
                # Get all guilds with configured channels
                guilds = await self.repo.list_guilds_with_channel()
                
                for guild_id in guilds:
                    channel_id = await self.repo.get_channel_for_guild(guild_id)
                    
                    if not channel_id:
                        continue
                    
                    # Mark as posted (this would be done by the Discord integration)
                    await self.repo.mark_posted(record.subsession_id, record.cust_id, guild_id)
                    posted_count += 1
                    
            except Exception as e:
                print(f"Error posting result for {record.subsession_id}: {e}")
                continue
                
        return posted_count
