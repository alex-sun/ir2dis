#!/usr/bin/env python3
"""
Main entry point for the iRacing to Discord bot.
"""

import asyncio
import logging
import os
from typing import Optional

# Import our custom modules
from iracing.api import IRacingClient
from storage.repository import Repository
from discord_bot.client import IR2DISBot
from poller.engine import PollingEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main entry point for the bot."""
    logger.info("Starting iRacing to Discord bot...")
    
    # Load configuration from environment variables
    from config.loader import load_config
    config = load_config()
    ir_username = config.iracing_email
    ir_password = config.iracing_password
    poll_interval_sec = config.poll_interval_seconds
    log_level = config.log_level
    
    # Configure logging level
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Initialize database repository
    repo = Repository()
    
    # Initialize iRacing client
    ir_client = IRacingClient(
        username=ir_username,
        password=ir_password
    )
    
    # Initialize Discord bot
    bot = IR2DISBot(repository=repo, iracing_client=ir_client)
    
    # Initialize polling engine
    poller = PollingEngine(
        repository=repo,
        iracing_client=ir_client,
        discord_bot=bot,
        interval=poll_interval_sec
    )
    
    try:
        # Initialize database tables
        await repo.initialize_tables()
        
        # Login to iRacing
        logger.info("Logging into iRacing...")
        await ir_client.login()
        logger.info("iRacing login successful")
        
        # Start the polling engine in the background
        logger.info(f"Starting polling engine with interval {poll_interval_sec} seconds")
        poller_task = asyncio.create_task(poller.start())
        
        # Run the Discord bot
        discord_token = os.getenv('DISCORD_TOKEN')
        if not discord_token:
            raise ValueError("DISCORD_TOKEN environment variable must be set")
            
        logger.info("Starting Discord bot...")
        await bot.run(discord_token)
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise
    finally:
        # Cleanup tasks
        if 'poller_task' in locals():
            poller_task.cancel()
            try:
                await poller_task
            except asyncio.CancelledError:
                pass

if __name__ == "__main__":
    asyncio.run(main())
