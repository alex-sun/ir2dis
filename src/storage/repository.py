import asyncio
import aiosqlite
import logging
from typing import Optional, List, Tuple
import time

logger = logging.getLogger(__name__)

class Repository:
    def __init__(self, db_path: str = "data/bot.db"):
        self.db_path = db_path
        
    async def _get_db(self) -> aiosqlite.Connection:
        """Get database connection with proper initialization."""
        conn = await aiosqlite.connect(self.db_path)
        # Enable foreign key constraints
        await conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    async def initialize_tables(self):
        """Initialize all required tables if they don't exist."""
        logger.info("Initializing database tables...")
        
        conn = await self._get_db()
        try:
            # Create tracked_drivers table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tracked_drivers (
                    cust_id INTEGER PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create channel_config table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS channel_config (
                    guild_id TEXT PRIMARY KEY,
                    channel_id TEXT NOT NULL,
                    mode TEXT DEFAULT 'production'
                )
            """)
            
            # Create posted_results table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS posted_results (
                    subsession_id INTEGER,
                    cust_id INTEGER,
                    guild_id TEXT,
                    posted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (subsession_id, cust_id, guild_id)
                )
            """)
            
            # Create poll_state table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS poll_state (
                    cust_id INTEGER PRIMARY KEY,
                    last_poll_ts INTEGER NOT NULL DEFAULT 0
                )
            """)
            
            await conn.commit()
            logger.info("Database tables initialized successfully")
        finally:
            await conn.close()
    
    async def add_tracked_driver(self, cust_id: int, display_name: str) -> None:
        """Add a new tracked driver."""
        conn = await self._get_db()
        try:
            await conn.execute(
                "INSERT OR REPLACE INTO tracked_drivers (cust_id, display_name) VALUES (?, ?)",
                (cust_id, display_name)
            )
            await conn.commit()
            logger.info(f"Added/updated tracked driver: {cust_id} ({display_name})")
        except Exception as e:
            logger.error(f"Error adding tracked driver {cust_id}: {e}")
            raise
        finally:
            await conn.close()
    
    async def remove_tracked_driver(self, cust_id: int) -> bool:
        """Remove a tracked driver. Returns True if removed, False if not found."""
        conn = await self._get_db()
        try:
            await conn.execute(
                "DELETE FROM tracked_drivers WHERE cust_id = ?",
                (cust_id,)
            )
            rows_affected = conn.total_changes
            await conn.commit()
            
            if rows_affected > 0:
                logger.info(f"Removed tracked driver: {cust_id}")
                return True
            else:
                logger.debug(f"Driver {cust_id} not found in tracked drivers")
                return False
        except Exception as e:
            logger.error(f"Error removing tracked driver {cust_id}: {e}")
            raise
        finally:
            await conn.close()
    
    async def list_tracked(self) -> List[Tuple[int, str]]:
        """List all tracked drivers."""
        conn = await self._get_db()
        try:
            cursor = await conn.execute(
                "SELECT cust_id, display_name FROM tracked_drivers ORDER BY added_at"
            )
            rows = await cursor.fetchall()
            logger.debug(f"Found {len(rows)} tracked drivers")
            return [(row[0], row[1]) for row in rows]
        except Exception as e:
            logger.error(f"Error listing tracked drivers: {e}")
            raise
        finally:
            await conn.close()
    
    async def get_channel_for_guild(self, guild_id: int) -> Optional[int]:
        """Get the channel ID for a guild."""
        conn = await self._get_db()
        try:
            cursor = await conn.execute(
                "SELECT channel_id FROM channel_config WHERE guild_id = ?",
                (str(guild_id),)
            )
            row = await cursor.fetchone()
            if row:
                logger.debug(f"Found channel {row[0]} for guild {guild_id}")
                return int(row[0])
            else:
                logger.debug(f"No channel found for guild {guild_id}")
                return None
        except Exception as e:
            logger.error(f"Error getting channel for guild {guild_id}: {e}")
            raise
        finally:
            await conn.close()
    
    async def set_channel_for_guild(self, guild_id: int, channel_id: int) -> None:
        """Set the channel ID for a guild."""
        conn = await self._get_db()
        try:
            await conn.execute(
                "INSERT OR REPLACE INTO channel_config (guild_id, channel_id) VALUES (?, ?)",
                (str(guild_id), str(channel_id))
            )
            await conn.commit()
            logger.info(f"Set channel {channel_id} for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error setting channel for guild {guild_id}: {e}")
            raise
        finally:
            await conn.close()
    
    async def mark_posted(self, subsession_id: int, cust_id: int, guild_id: int) -> None:
        """Mark a result as posted."""
        conn = await self._get_db()
        try:
            await conn.execute(
                "INSERT OR REPLACE INTO posted_results (subsession_id, cust_id, guild_id) VALUES (?, ?, ?)",
                (subsession_id, cust_id, str(guild_id))
            )
            await conn.commit()
            logger.debug(f"Marked result as posted: subsession {subsession_id}, driver {cust_id}, guild {guild_id}")
        except Exception as e:
            logger.error(f"Error marking result as posted: {e}")
            raise
        finally:
            await conn.close()
    
    async def was_posted(self, subsession_id: int, cust_id: int, guild_id: int) -> bool:
        """Check if a result was already posted for this (subsession_id, cust_id, guild_id)."""
        conn = await self._get_db()
        try:
            cursor = await conn.execute(
                "SELECT 1 FROM posted_results WHERE subsession_id = ? AND cust_id = ? AND guild_id = ?",
                (subsession_id, cust_id, str(guild_id))
            )
            row = await cursor.fetchone()
            was_posted = row is not None
            logger.debug(f"Result posted check: {was_posted} for subsession {subsession_id}, driver {cust_id}, guild {guild_id}")
            return was_posted
        except Exception as e:
            logger.error(f"Error checking if result was posted: {e}")
            raise
        finally:
            await conn.close()
    
    async def get_last_poll_ts(self, cust_id: int) -> Optional[int]:
        """Get the last poll timestamp for a driver."""
        conn = await self._get_db()
        try:
            cursor = await conn.execute(
                "SELECT last_poll_ts FROM poll_state WHERE cust_id = ?",
                (cust_id,)
            )
            row = await cursor.fetchone()
            if row:
                return int(row[0])
            else:
                logger.debug(f"No poll state found for driver {cust_id}")
                return None
        except Exception as e:
            logger.error(f"Error getting last poll timestamp for driver {cust_id}: {e}")
            raise
        finally:
            await conn.close()
    
    async def set_last_poll_ts(self, cust_id: int, ts: int) -> None:
        """Set the last poll timestamp for a driver."""
        conn = await self._get_db()
        try:
            await conn.execute(
                "INSERT OR REPLACE INTO poll_state (cust_id, last_poll_ts) VALUES (?, ?)",
                (cust_id, ts)
            )
            await conn.commit()
            logger.debug(f"Set last poll timestamp for driver {cust_id}: {ts}")
        except Exception as e:
            logger.error(f"Error setting last poll timestamp for driver {cust_id}: {e}")
            raise
        finally:
            await conn.close()
