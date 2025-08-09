#!/usr/bin/env python3
"""
Discord bot client for iRacing → Discord Auto-Results Bot.
"""

import discord
from discord.ext import commands
from config.loader import load_config

# Create the bot with command prefix and intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

def create_discord_bot(config) -> commands.Bot:
    """
    Create and configure the Discord bot.
    
    Args:
        config: Configuration object
        
    Returns:
        commands.Bot: Configured Discord bot instance
    """
    # Create the bot with a command prefix (we'll use slash commands instead)
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    @bot.event
    async def on_ready():
        print(f'{bot.user} has logged in!')
        
        # Register slash commands
        await register_commands(bot)
    
    return bot

async def register_commands(bot):
    """
    Register all slash commands with the Discord bot.
    
    Args:
        bot: Discord bot instance
    """
    # This would normally register commands, but we'll implement this later
    pass
