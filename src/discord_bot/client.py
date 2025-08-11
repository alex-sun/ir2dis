#!/usr/bin/env python3
"""
Discord bot client for iRacing → Discord Auto-Results Bot.
"""

import discord
from discord.ext import commands
from config.loader import load_config
from store.database import get_db
from iracing.api import IRacingClient
from iracing.repository import Repository
from iracing.service import FinishRecord
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
        self.ir_client = None
        self.repo = None

    async def setup_hook(self) -> None:
        """Set up the bot with commands and configuration."""
        # Initialize clients for use in commands
        try:
            from config.loader import load_config
            config = load_config()
            self.ir_client = IRacingClient(config.iracing_email, config.iracing_password)
            self.repo = Repository()
        except Exception as e:
            print(f"Failed to initialize iRacing client: {e}")
        
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
                await bot.repo.set_channel_for_guild(interaction.guild.id, channel.id)
                await interaction.response.send_message(
                    f"✅ Results channel set to {channel.mention}", 
                    ephemeral=True
                )
            except Exception as e:
                print(f"Error in set_channel: {e}")
                await interaction.response.send_message("❌ Error setting channel", ephemeral=True)

        @bot.tree.command(name="track", description="Track a driver")
        async def track_driver(interaction: discord.Interaction, driver: str):
            """Track a driver by customer ID or name."""
            try:
                # Check if the guild has a channel set up first
                channel_id = await bot.repo.get_channel_for_guild(interaction.guild.id)
                if not channel_id:
                    await interaction.response.send_message(
                        "❌ Please set a results channel first using `/setchannel`", 
                        ephemeral=True
                    )
                    return

                # Try to parse as numeric cust_id first
                try:
                    cust_id = int(driver)
                    display_name = f"Driver {cust_id}"
                except ValueError:
                    # Search for driver by name
                    search_results = await bot.ir_client.lookup_driver(driver)
                    if not search_results:
                        await interaction.response.send_message(
                            "❌ No drivers found with that name", 
                            ephemeral=True
                        )
                        return

                    if len(search_results) == 1:
                        cust_id = search_results[0]['cust_id']
                        display_name = search_results[0]['display_name']
                    else:
                        # For multiple results, we'd need a select menu in real implementation
                        # For now, just use the first result
                        cust_id = search_results[0]['cust_id']
                        display_name = search_results[0]['display_name']

                # Check if already tracked
                existing_tracked = await bot.repo.list_tracked()
                if any(cust_id == cust_id_val for cust_id_val, _ in existing_tracked):
                    await interaction.response.send_message(
                        "❌ Driver is already being tracked", 
                        ephemeral=True
                    )
                    return

                # Add the driver to tracking list (new method)
                await bot.repo.add_tracked_driver(cust_id, display_name)
                
                await interaction.response.send_message(
                    f"✅ Tracking driver: {display_name} (ID: {cust_id})", 
                    ephemeral=True
                )
            except Exception as e:
                print(f"Error in track_driver: {e}")
                await interaction.response.send_message("❌ Error tracking driver", ephemeral=True)

        @bot.tree.command(name="untrack", description="Stop tracking a driver")
        async def untrack_driver(interaction: discord.Interaction, cust_id: int):
            """Untrack a driver by customer ID."""
            try:
                # Remove the driver from tracking list (new method)
                removed = await bot.repo.remove_tracked_driver(cust_id)
                if removed:
                    await interaction.response.send_message(
                        f"✅ Stopped tracking driver with ID {cust_id}", 
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "❌ Driver was not being tracked", 
                        ephemeral=True
                    )
            except Exception as e:
                print(f"Error in untrack_driver: {e}")
                await interaction.response.send_message("❌ Error stopping track", ephemeral=True)

        @bot.tree.command(name="list_tracked", description="List tracked drivers")
        async def list_drivers(interaction: discord.Interaction):
            """List all tracked drivers for this server."""
            try:
                # Get tracked drivers (new method)
                tracked = await bot.repo.list_tracked()
                
                if not tracked:
                    await interaction.response.send_message("❌ No drivers are currently being tracked", ephemeral=True)
                    return
                
                driver_list = "\n".join([f"• {display_name} ({cust_id})" for cust_id, display_name in tracked])
                await interaction.response.send_message(f"📋 Tracked drivers:\n{driver_list}", ephemeral=True)
            except Exception as e:
                print(f"Error in list_drivers: {e}")
                await interaction.response.send_message("❌ Error listing drivers", ephemeral=True)

        @bot.tree.command(name="test_post", description="Test posting a sample embed")
        async def test_post(interaction: discord.Interaction):
            """Post a static example embed to the configured channel."""
            try:
                # Get channel for this guild (new method)
                channel_id = await bot.repo.get_channel_for_guild(interaction.guild.id)
                if not channel_id:
                    await interaction.response.send_message(
                        "❌ No results channel set. Please use `/setchannel` first.", 
                        ephemeral=True
                    )
                    return

                # Create a sample embed (this would be replaced with real data in production)
                from datetime import datetime
                record = FinishRecord(
                    subsession_id=1234567,
                    cust_id=987654,
                    display_name="Test Driver",
                    series_name="iRacing Formula 3",
                    track_name="Circuit de la Sarthe",
                    car_name="BMW M4 GT3",
                    field_size=24,
                    finish_pos=1,
                    finish_pos_in_class=1,
                    class_name="Pro/Am",
                    laps=50,
                    incidents=0,
                    best_lap_time_s=89.123,
                    sof=1250,
                    official=True,
                    start_time_utc=datetime.now().isoformat()
                )
                
                await post_finish_embed(bot, record, channel_id)
                await interaction.response.send_message("✅ Test embed posted successfully", ephemeral=True)
            except Exception as e:
                print(f"Error in test_post: {e}")
                await interaction.response.send_message("❌ Error posting test embed", ephemeral=True)

        # Sync commands with Discord API - keep only this awaited call
        await bot.tree.sync()
        print("✅ Slash commands registered successfully")
        
    except Exception as e:
        print(f"Error registering slash commands: {e}")

async def post_finish_embed(bot, record: FinishRecord, channel_id: int):
    """Post a race finish embed to Discord."""
    try:
        import discord
        color = discord.Color.green() if record.finish_pos <= 3 else (discord.Color.orange() if record.finish_pos <= 10 else discord.Color.red())
        embed = discord.Embed(
            title=f"🏁 {record.display_name} — P{record.finish_pos}" + (f" (Class P{record.finish_pos_in_class})" if record.finish_pos_in_class else ""),
            description=(
                f"**Series:** {record.series_name} • **Track:** {record.track_name} • **Car:** {record.car_name}\n"
                f"**Field:** {record.field_size} • **Laps:** {record.laps} • **Inc:** {record.incidents} • **SOF:** {record.sof or '—'}\n"
                + (f"**Best:** {record.best_lap_time_s:.3f}s\n" if record.best_lap_time_s else "")
                + ("**Official:** ✅" if record.official else "**Official:** ❌")
            ),
            colour=color,
        )
        embed.set_footer(text=f"Subsession {record.subsession_id} • {record.start_time_utc}")
        channel = bot.get_channel(int(channel_id))
        if channel is None:
            # fetch if not cached
            channel = await bot.fetch_channel(int(channel_id))
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Error posting embed: {e}")
