#!/usr/bin/env python3
"""
Repository for iRacing integration - handles database operations for tracking and deduplication.
"""

from typing import Optional, List, Tuple
import sqlite3
from store.database import get_db

class Repository:
    """Repository for managing tracked drivers, channels, posted results, and polling state."""
    
    async def add_tracked_driver(self, cust_id: int, display_name: str) -> None:
        """Add a driver to the tracking list."""
        conn = get_db()
        conn.execute('''
            INSERT OR REPLACE INTO tracked_drivers (cust_id, display_name, added_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (cust_id, display_name))
        conn.commit()
    
    async def remove_tracked_driver(self, cust_id: int) -> bool:
        """Remove a driver from the tracking list.
        
        Returns:
            bool: True if driver was removed, False if not found
        """
        conn = get_db()
        cursor = conn.execute('''
            DELETE FROM tracked_drivers WHERE cust_id = ?
        ''', (cust_id,))
        conn.commit()
        return cursor.rowcount > 0
    
    async def list_tracked(self) -> List[Tuple[int, str]]:
        """List all tracked drivers.
        
        Returns:
            List[Tuple[int, str]]: List of (cust_id, display_name) tuples
        """
        conn = get_db()
        rows = conn.execute('''
            SELECT cust_id, display_name FROM tracked_drivers
        ''').fetchall()
        return [(row['cust_id'], row['display_name']) for row in rows]
    
    async def get_channel_for_guild(self, guild_id: int) -> Optional[int]:
        """Get the channel ID for a guild.
        
        Args:
            guild_id (int): Guild ID
            
        Returns:
            Optional[int]: Channel ID or None if not configured
        """
        conn = get_db()
        row = conn.execute('''
            SELECT channel_id FROM channel_config WHERE guild_id = ?
        ''', (str(guild_id),)).fetchone()
        
        return int(row['channel_id']) if row else None
    
    async def set_channel_for_guild(self, guild_id: int, channel_id: int) -> None:
        """Set the channel ID for a guild.
        
        Args:
            guild_id (int): Guild ID
            channel_id (int): Channel ID
        """
        conn = get_db()
        conn.execute('''
            INSERT OR REPLACE INTO channel_config (guild_id, channel_id)
            VALUES (?, ?)
        ''', (str(guild_id), str(channel_id)))
        conn.commit()
    
    async def mark_posted(self, subsession_id: int, cust_id: int, guild_id: int) -> None:
        """Mark a result as posted to prevent duplicates.
        
        Args:
            subsession_id (int): Subsession ID
            cust_id (int): Customer ID
            guild_id (int): Guild ID
        """
        conn = get_db()
        conn.execute('''
            INSERT OR REPLACE INTO posted_results (subsession_id, cust_id, guild_id, posted_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (subsession_id, cust_id, str(guild_id)))
        conn.commit()
    
    async def was_posted(self, subsession_id: int, cust_id: int, guild_id: int) -> bool:
        """Check if a result was already posted.
        
        Args:
            subsession_id (int): Subsession ID
            cust_id (int): Customer ID
            guild_id (int): Guild ID
            
        Returns:
            bool: True if already posted
        """
        conn = get_db()
        row = conn.execute('''
            SELECT 1 FROM posted_results 
            WHERE subsession_id = ? AND cust_id = ? AND guild_id = ?
        ''', (subsession_id, cust_id, str(guild_id))).fetchone()
        
        return row is not None
    
    async def get_last_poll_ts(self, cust_id: int) -> int:
        """Get the last poll timestamp for a driver.
        
        Args:
            cust_id (int): Customer ID
            
        Returns:
            Optional[int]: Last poll timestamp or 0 if not found
        """
        conn = get_db()
        row = conn.execute('''
            SELECT last_poll_ts FROM poll_state WHERE cust_id = ?
        ''', (cust_id,)).fetchone()
        
        return row['last_poll_ts'] if row else 0
    
    async def set_last_poll_ts(self, cust_id: int, ts: int) -> None:
        """Set the last poll timestamp for a driver.
        
        Args:
            cust_id (int): Customer ID
            ts (int): Timestamp
        """
        conn = get_db()
        conn.execute('''
            INSERT OR REPLACE INTO poll_state (cust_id, last_poll_ts)
            VALUES (?, ?)
        ''', (cust_id, ts))
        conn.commit()
