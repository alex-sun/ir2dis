#!/usr/bin/env python3
"""
Polling engine for iRacing → Discord Auto-Results Bot.
Handles polling cycles, deduplication, and posting logic.
"""

import asyncio
import time
from typing import List, Dict, Any
from datetime import datetime

from store.database import get_db
from iracing.client import IRacingClient
from discord_bot.client import create_discord_bot
from observability.logger import structured_logger
from observability.metrics import metrics
from config.loader import load_config

class PollerEngine:
    """Main polling engine for the bot."""
    
    def __init__(self):
        self.iracing_client = IRacingClient()
        self.running = False
        
    async def start_polling(self):
        """Start the polling loop."""
        config = load_config()
        self.running = True
        
        structured_logger.info("Starting polling loop", 
                              poll_interval=config.poll_interval_seconds)
        
        while self.running:
            try:
                await self._poll_cycle()
                metrics.increment_poll_cycle()
                
                # Wait for next cycle
                await asyncio.sleep(config.poll_interval_seconds)
                
            except Exception as e:
                structured_logger.error(f"Error in polling cycle: {e}")
                # Even on error, continue the loop
                await asyncio.sleep(config.poll_interval_seconds)
    
    async def stop_polling(self):
        """Stop the polling loop."""
        self.running = False
        structured_logger.info("Polling loop stopped")
        
    async def _poll_cycle(self):
        """Execute a single polling cycle."""
        structured_logger.info("Starting poll cycle")
        
        # Get all guilds with configured channels
        db = get_db()
        guilds = db.execute('''
            SELECT guild_id, channel_id, timezone 
            FROM guild 
            WHERE channel_id IS NOT NULL
        ''').fetchall()
        
        for row in guilds:
            guild_id = row['guild_id']
            channel_id = row['channel_id']
            timezone = row['timezone']
            
            try:
                await self._process_guild(guild_id, channel_id, timezone)
            except Exception as e:
                structured_logger.error(f"Error processing guild {guild_id}: {e}")
                
        structured_logger.info("Poll cycle completed")
    
    async def _process_guild(self, guild_id: str, channel_id: str, timezone: str):
        """Process a single guild."""
        db = get_db()
        
        # Get tracked drivers for this guild
        tracked_drivers = db.execute('''
            SELECT cust_id, display_name 
            FROM tracked_driver 
            WHERE guild_id = ? AND active = 1
        ''', (guild_id,)).fetchall()
        
        for driver_row in tracked_drivers:
            cust_id = driver_row['cust_id']
            
            try:
                await self._process_driver(guild_id, channel_id, timezone, cust_id)
            except Exception as e:
                structured_logger.error(f"Error processing driver {cust_id} for guild {guild_id}: {e}")
    
    async def _process_driver(self, guild_id: str, channel_id: str, timezone: str, cust_id: int):
        """Process a single driver."""
        db = get_db()
        
        # Get last seen subsession for this driver
        last_seen = db.execute('''
            SELECT last_subsession_id 
            FROM last_seen 
            WHERE guild_id = ? AND cust_id = ?
        ''', (guild_id, cust_id)).fetchone()
        
        # Get recent races from iRacing
        try:
            races_data = await self.iracing_client.get_recent_races(cust_id)
            
            if not races_data or 'results' not in races_data:
                return
                
            # Process each race result
            for race in races_data['results']:
                subsession_id = str(race['subsession_id'])
                
                # Check if this race was already posted
                existing_post = db.execute('''
                    SELECT * FROM post_history 
                    WHERE guild_id = ? AND subsession_id = ?
                ''', (guild_id, subsession_id)).fetchone()
                
                if existing_post:
                    metrics.increment_dedupe_skips()
                    continue
                    
                # Check if this is a new race (not seen before)
                if last_seen and last_seen['last_subsession_id'] == subsession_id:
                    continue
                    
                # Fetch detailed subsession data
                try:
                    subsession_data = await self.iracing_client.get_subsession(subsession_id)
                    
                    # Validate that it's an official result (not warmup/practice)
                    if not self._is_official_result(subsession_data):
                        continue
                        
                    # Build and post the message
                    # Note: This is a placeholder - actual implementation would need Discord integration
                    structured_logger.info("New race result found",
                                          guild_id=guild_id,
                                          cust_id=cust_id,
                                          subsession_id=subsession_id)
                    
                    # Record this as posted (in a real implementation, we'd post to Discord here)
                    db.execute('''
                        INSERT OR REPLACE INTO post_history 
                        (guild_id, subsession_id, message_id, posted_at) 
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (guild_id, subsession_id, "placeholder"))
                    
                    # Update last seen
                    db.execute('''
                        INSERT OR REPLACE INTO last_seen 
                        (guild_id, cust_id, last_subsession_id, last_finish_at) 
                        VALUES (?, ?, ?, ?)
                    ''', (guild_id, cust_id, subsession_id, datetime.now()))
                    
                    metrics.increment_posts_published()
                    
                except Exception as e:
                    structured_logger.error(f"Error fetching subsession details: {e}")
                    continue
                    
        except Exception as e:
            structured_logger.error(f"Error fetching recent races for driver {cust_id}: {e}")
    
    def _is_official_result(self, subsession_data: Dict) -> bool:
        """Check if a subsession is an official result (not warmup/practice)."""
        # This is a simplified check - in practice we'd look at the session type
        # and possibly other criteria to determine if it's an official result
        
        # In real implementation, this would check things like:
        # - Session type (official race vs practice/warmup)
        # - Number of laps completed
        # - If it's a final result
        return True  # Simplified for now

# Global instance
poller_engine = PollerEngine()
