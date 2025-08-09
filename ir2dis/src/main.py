#!/usr/bin/env python3
"""
iRacing → Discord Auto-Results Bot
Main entry point for the application.
"""

import asyncio
import logging
from config.loader import load_config
from store.database import init_db
from discord.client import create_discord_bot
from poller.engine import poller_engine

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main application entry point."""
    logger.info("Starting iRacing → Discord Auto-Results Bot")
    
    # Load configuration
    config = load_config()
    logger.info("Configuration loaded")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Start the polling engine in a separate task
    poll_task = asyncio.create_task(poller_engine.start_polling())
    logger.info("Polling engine started")
    
    # Create and start Discord bot
    bot = create_discord_bot(config)
    logger.info("Discord bot created")
    
    # Start the bot
    await bot.start(config.discord_token)
    
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        # Stop polling engine
        asyncio.create_task(poller_engine.stop_polling())
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        raise
