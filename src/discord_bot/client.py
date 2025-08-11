#!/usr/bin/env python3
"""
Discord bot client for iRacing → Discord Auto-Results Bot.
"""

import discord
from discord.ext import commands
from config.loader import load_config
from store.database import get_db
import os

# Create the bot with command prefix and intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

class IR2DISBot(commands.Bot):
    def __init__(self, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config

    async def setup_hook(self) -> None:
        """Set up the bot with commands and configuration."""
        # Register slash commands - moved from on_ready to setup_hook
        await register_commands(self)

def create_discord_bot(config) -> commands.Bot:
    """
    Create and configure the Discord bot.
    
    Args:
        config: Configuration object
        
    Returns:
        commands.Bot: Configured Discord bot instance
    """
    # Create the bot with a command prefix (we'll use slash commands instead)
    bot = IR2DISBot(config, command_prefix='!', intents=intents)
    return bot

async def register_commands(bot):
    """
    Register all slash commands with the Discord bot.
    
    Args:
        bot: Discord bot instance
    """
    # Clear existing commands and register new ones
    try:
        # Create a command tree for registering commands
        # Remove await from these non-coroutine methods (they return None)
        bot.tree.clear_commands(guild=None)  # Clear global commands
        # Use environment variable for guild ID or remove per-guild clearing
        guild_id = os.getenv("DISCORD_GUILD_ID")
        if guild_id:
            bot.tree.clear_commands(guild=discord.Object(id=int(guild_id)))  # Clear guild-specific if needed

        # Register all slash commands
        @bot.tree.command(name="setchannel", description="Set the results channel")
        async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
            """Set the results channel for this server."""
            try:
                db = get_db()
                guild_id = str(interaction.guild.id)
                channel_id = str(channel.id)
                
                # Insert or update guild settings
                db.execute('''
                    INSERT OR REPLACE INTO guild (guild_id, channel_id, timezone) 
                    VALUES (?, ?, ?)
                ''', (guild_id, channel_id, bot.config.timezone_default))
                db.commit()
                
                await interaction.response.send_message(
                    f"✅ Results channel set to {channel.mention}", 
                    ephemeral=True
                )
            except Exception as e:
                print(f"Error in set_channel: {e}")
                await interaction.response.send_message("❌ Error setting channel", ephemeral=True)

        @bot.tree.command(name="track", description="Track a driver")
        async def track_driver(interaction: discord.Interaction, cust_id: int):
            """Track a driver by customer ID."""
            try:
                db = get_db()
                guild_id = str(interaction.guild.id)
                
                # Check if the guild has a channel set up first
                guild_row = db.execute('''
                    SELECT * FROM guild WHERE guild_id = ?
                ''', (guild_id,)).fetchone()
                
                if not guild_row:
                    await interaction.response.send_message(
                        "❌ Please set a results channel first using `/setchannel`", 
                        ephemeral=True
                    )
                    return
                
                # Add the driver to tracking list
                db.execute('''
                    INSERT OR REPLACE INTO tracked_driver (guild_id, cust_id, display_name, active) 
                    VALUES (?, ?, ?, 1)
                ''', (guild_id, cust_id, f"Driver {cust_id}"))
                db.commit()
                
                await interaction.response.send_message(
                    f"✅ Tracking driver with ID {cust_id}", 
                    ephemeral=True
                )
            except Exception as e:
                print(f"Error in track_driver: {e}")
                await interaction.response.send_message("❌ Error tracking driver", ephemeral=True)

        @bot.tree.command(name="untrack", description="Stop tracking a driver")
        async def untrack_driver(interaction: discord.Interaction, cust_id: int):
            """Untrack a driver by customer ID."""
            try:
                db = get_db()
                guild_id = str(interaction.guild.id)
                
                # Remove the driver from tracking list
                db.execute('''
                    DELETE FROM tracked_driver WHERE guild_id = ? AND cust_id = ?
                ''', (guild_id, cust_id))
                db.commit()
                
                await interaction.response.send_message(
                    f"✅ Stopped tracking driver with ID {cust_id}", 
                    ephemeral=True
                )
            except Exception as e:
                print(f"Error in untrack_driver: {e}")
                await interaction.response.send_message("❌ Error stopping track", ephemeral=True)

        @bot.tree.command(name="list", description="List tracked drivers")
        async def list_drivers(interaction: discord.Interaction):
            """List all tracked drivers for this server."""
            try:
                db = get_db()
                guild_id = str(interaction.guild.id)
                
                # Get tracked drivers
                drivers = db.execute('''
                    SELECT cust_id, display_name FROM tracked_driver WHERE guild_id = ? AND active = 1
                ''', (guild_id,)).fetchall()
                
                if not drivers:
                    await interaction.response.send_message("❌ No drivers are currently being tracked", ephemeral=True)
                    return
                
                driver_list = "\n".join([f"• Driver ID: {driver['cust_id']} ({driver['display_name']})" for driver in drivers])
                await interaction.response.send_message(f"📋 Tracked drivers:\n{driver_list}", ephemeral=True)
            except Exception as e:
                print(f"Error in list_drivers: {e}")
                await interaction.response.send_message("❌ Error listing drivers", ephemeral=True)

        @bot.tree.command(name="lastrace", description="Get last race result for a driver")
        async def lastrace(interaction: discord.Interaction, cust_id: int):
            """Get the last race result for a driver."""
            try:
                db = get_db()
                guild_id = str(interaction.guild.id)
                
                # Check if the guild has a channel set up first
                guild_row = db.execute('''
                    SELECT * FROM guild WHERE guild_id = ?
                ''', (guild_id,)).fetchone()
                
                if not guild_row:
                    await interaction.response.send_message(
                        "❌ Please set a results channel first using `/setchannel`", 
                        ephemeral=True
                    )
                    return
                
                # Check if driver is being tracked
                tracked_driver = db.execute('''
                    SELECT * FROM tracked_driver WHERE guild_id = ? AND cust_id = ? AND active = 1
                ''', (guild_id, cust_id)).fetchone()
                
                if not tracked_driver:
                    await interaction.response.send_message(
                        f"❌ Driver with ID {cust_id} is not being tracked. Use `/track {cust_id}` first.", 
                        ephemeral=True
                    )
                    return
                
                # Simulate getting the last race result (in a real implementation, this would fetch from iRacing API)
                await interaction.response.send_message(
                    f"🏁 Last race result for driver ID {cust_id}:\n"
                    f"- This is a placeholder response\n"
                    f"- In a full implementation, this would show actual race data", 
                    ephemeral=True
                )
            except Exception as e:
                print(f"Error in lastrace: {e}")
                await interaction.response.send_message("❌ Error getting last race result", ephemeral=True)

        # Sync commands with Discord API - keep only this awaited call
        await bot.tree.sync()
        print("✅ Slash commands registered successfully")
        
    except Exception as e:
        print(f"Error registering slash commands: {e}")
