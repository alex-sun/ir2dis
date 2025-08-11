# src/discord_bot/commands/__init__.py
# src/discord_bot/commands/__init__.py
"""
Command modules for the Discord bot.
This file ensures all command modules are properly imported.
"""

# Import all command modules to make them available to the bot
from . import ping
from . import track
from . import untrack
from . import list_tracked
from . import set_channel
from . import test_post
from . import test_commands

# Export all commands
__all__ = [
    'ping',
    'track', 
    'untrack',
    'list_tracked',
    'set_channel',
    'test_post',
    'test_commands'
]
