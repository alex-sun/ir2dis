#!/usr/bin/env python3
"""
Polling engine for iRacing → Discord Auto-Results Bot.
Handles polling cycles, deduplication, and posting logic using new architecture.
"""

import asyncio
import time
from typing import List, Dict, Any
from datetime import datetime

from store.database import get_db
from iracing.api import IRacingClient
from iracing.service import ResultService
from iracing.repository import Repository
from observability.logger import structured_logger
from observability.metrics import metrics
from config.loader import load_config
import discord

class PollerEngine:
    """Main polling engine for the bot using new iRacing integration architecture."""
    
    def __init__(self):
        self.running = False
        self.semaphore = asyncio.Semaphore(4)  # Limit concurrent API calls
        self.ir_client = None
        self.result_service = None
        self.repo = None
        
    async def start_polling(self):
        """Start the polling loop."""
        config = load_config()
        self.running = True
        structured_logger.info("Starting polling loop", 
                              poll_interval=config.poll_interval_seconds)
        
        # Initialize clients and services
        try:
            from config.loader import load_config
            config = load_config()
            self.ir_client = IRacingClient(config.iracing_email, config.iracing_password)
            self.repo = Repository()
            self.result_service = ResultService(self.ir_client, self.repo)
        except Exception as e:
            structured_logger.error(f"Failed to initialize clients: {e}")
            return
        
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
        """Execute a single polling cycle using new architecture."""
        structured_logger.info("Starting poll cycle")
        
        try:
            # Get all guilds with configured channels (new method)
            guild_ids = await self.repo.list_guilds_with_channel()
            
            if not guild_ids:
                structured_logger.warning("No guilds with configured channels found")
                return
                
            for guild_id in guild_ids:
                try:
                    await self._process_guild(guild_id)
                except Exception as e:
                    structured_logger.error(f"Error processing guild {guild_id}: {e}")
                    
        except Exception as e:
            structured_logger.error(f"Error in poll cycle: {e}")
            
        structured_logger.info("Poll cycle completed")
    
    async def _process_guild(self, guild_id: int):
        """Process a single guild using new architecture."""
        # Get channel for this guild (new method)
        channel_id = await self.repo.get_channel_for_guild(guild_id)
        if not channel_id:
            structured_logger.warning(f"No channel configured for guild {guild_id}")
            return
            
        try:
            # Find new finishes for tracked drivers in this guild
            new_finishes = await self.result_service.find_new_finishes_for_tracked()
            
            if not new_finishes:
                structured_logger.info("No new finishes found")
                return
                
            # Process and post results (this would be done by Discord integration)
            posted_count = await self.result_service.process_and_post_results(new_finishes)
            metrics.increment_posts_published(posted_count)
            
            structured_logger.info(f"Posted {posted_count} new results for guild {guild_id}")
            
        except Exception as e:
            structured_logger.error(f"Error processing guild {guild_id}: {e}")

# Global instance
poller_engine = PollerEngine()
