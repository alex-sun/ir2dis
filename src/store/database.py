#!/usr/bin/env python3
"""
Database initialization and connection management for iRacing → Discord Auto-Results Bot.
"""

import os
import sqlite3
from typing import Optional
from config.loader import load_config

# Global database connection
_db_connection: Optional[sqlite3.Connection] = None

def get_db() -> sqlite3.Connection:
    """
    Get the global database connection.
    
    Returns:
        sqlite3.Connection: Database connection object
    """
    global _db_connection
    if _db_connection is None:
        config = load_config()
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(config.sqlite_path), exist_ok=True)
        _db_connection = sqlite3.connect(config.sqlite_path)
        _db_connection.row_factory = sqlite3.Row  # Enable column access by name
    return _db_connection

async def init_db() -> None:
    """
    Initialize the database with required tables.
    """
    conn = get_db()
    
    # Create tables for iRacing integration (as per task requirements)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tracked_drivers (
            cust_id INTEGER PRIMARY KEY,
            display_name TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS channel_config (
            guild_id TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL,
            mode TEXT DEFAULT 'production'
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS posted_results (
            subsession_id INTEGER,
            cust_id INTEGER,
            guild_id TEXT,
            posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (subsession_id, cust_id, guild_id)
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS poll_state (
            cust_id INTEGER PRIMARY KEY,
            last_poll_ts INTEGER
        )
    ''')
    
    # Create indices for better performance
    conn.execute('CREATE INDEX IF NOT EXISTS idx_posted_results_subsession ON posted_results(subsession_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_posted_results_cust ON posted_results(cust_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_poll_state_cust ON poll_state(cust_id)')
    
    # Create indices for existing tables (maintaining backward compatibility)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS guild (
            guild_id TEXT PRIMARY KEY,
            channel_id TEXT,
            timezone TEXT DEFAULT 'Europe/Berlin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tracked_driver (
            guild_id TEXT,
            cust_id INTEGER,
            display_name TEXT,
            active BOOLEAN DEFAULT 1,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (guild_id, cust_id),
            FOREIGN KEY (guild_id) REFERENCES guild (guild_id)
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS last_seen (
            guild_id TEXT,
            cust_id INTEGER,
            last_subsession_id TEXT,
            last_finish_at TIMESTAMP,
            PRIMARY KEY (guild_id, cust_id),
            FOREIGN KEY (guild_id) REFERENCES guild (guild_id)
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS post_history (
            guild_id TEXT,
            subsession_id TEXT,
            message_id TEXT,
            posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (guild_id, subsession_id),
            FOREIGN KEY (guild_id) REFERENCES guild (guild_id)
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS auth_state (
            id TEXT PRIMARY KEY DEFAULT '1',
            cookies_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indices for existing tables (maintaining backward compatibility)
    conn.execute('CREATE INDEX IF NOT EXISTS idx_tracked_driver_guild ON tracked_driver(guild_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_post_history_subsession ON post_history(subsession_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_last_seen_guild_cust ON last_seen(guild_id, cust_id)')
    
    # Insert default auth state if it doesn't exist
    conn.execute('''
        INSERT OR IGNORE INTO auth_state (id) VALUES ('1')
    ''')
    
    conn.commit()
    print("Database initialized successfully")

async def close_db() -> None:
    """
    Close the database connection.
    """
    global _db_connection
    if _db_connection is not None:
        _db_connection.close()
        _db_connection = None
