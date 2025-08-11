import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import logging
from typing import Optional, List
import time

# Import our custom modules
from iracing.api import IRacingClient
from iracing.service import ResultService, FinishRecord
from storage.repository import Repository

logger = logging.getLogger(__name__)

class IR2DISBot(commands.Bot):
    def __init__(self, repository: Repository, iracing_client: IRacingClient):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        # Initialize the bot with our custom repository and iRacing client
        self.repo = repository
        self.ir = iracing_client
        
        super().__init__(command_prefix='!', intents=intents)
        
    async def setup_hook(self):
        """Setup hook for Discord bot - sync commands."""
        logger.info("Setting up bot hooks...")
        
        # Sync application commands
        await self.tree.sync()
        logger.info("Application commands synced")
        
    async def post_finish_embed(self, record: FinishRecord, channel_id: int) -> None:
        """Post a finish embed to Discord."""
        try:
            import discord
            
            # Determine color based on finish position
            if record.finish_pos <= 3:
                color = discord.Color.green()
            elif record.finish_pos <= 10:
                color = discord.Color.orange()
            else:
                color = discord.Color.red()
            
            # Build embed title and description
            title = f"🏁 {record.display_name} — P{record.finish_pos}"
            if record.finish_pos_in_class:
                title += f" (Class P{record.finish_pos_in_class})"
            
            description_lines = [
                f"**Series:** {record.series_name} • **Track:** {record.track_name} • **Car:** {record.car_name}",
                f"**Field:** {record.field_size} • **Laps:** {record.laps} • **Inc:** {record.incidents} • **SOF:** {record.sof or '—'}"
            ]
            
            if record.best_lap_time_s:
                description_lines.append(f"**Best:** {record.best_lap_time_s:.3f}s")
            
            description_lines.append("Official: ✅" if record.official else "Official: ❌")
            
            embed = discord.Embed(
                title=title,
                description="\n".join(description_lines),
                color=color
            )
            
            embed.set_footer(text=f"Subsession {record.subsession_id} • {record.start_time_utc}")
            
            # Get channel and send embed
            channel = self.get_channel(channel_id)
            if not channel:
                logger.warning(f"Channel {channel_id} not found in cache, fetching...")
                try:
                    channel = await self.fetch_channel(channel_id)
                except discord.NotFound:
                    logger.error(f"Channel {channel_id} not found")
                    return
                except Exception as e:
                    logger.error(f"Error fetching channel {channel_id}: {e}")
                    return
            
            await channel.send(embed=embed)
            logger.info(f"Posted embed for driver {record.display_name} in channel {channel_id}")
            
        except Exception as e:
            logger.error(f"Error posting finish embed: {e}")

    @discord.app_commands.command(name="track", description="Track a driver by name or ID")
    async def track(self, interaction: discord.Interaction, driver: str):
        """Track a driver by name or ID."""
        try:
            # Check if the input is numeric (cust_id)
            if driver.isdigit():
                cust_id = int(driver)
                # Look up the driver to get their display_name
                drivers = await self.ir.lookup_driver(str(cust_id))
                if not drivers:
                    await interaction.response.send_message(
                        f"Could not find a driver with ID {cust_id}", 
                        ephemeral=True
                    )
                    return
                display_name = drivers[0]["display_name"]
            else:
                # Search for drivers by name
                drivers = await self.ir.lookup_driver(driver)
                if not drivers:
                    await interaction.response.send_message(
                        f"No drivers found matching '{driver}'", 
                        ephemeral=True
                    )
                    return
                
                # If we have multiple results, show a select menu
                if len(drivers) > 1:
                    # For simplicity in this implementation, we'll just use the first result
                    # In a full implementation, you'd create a proper select menu
                    cust_id = drivers[0]["cust_id"]
                    display_name = drivers[0]["display_name"]
                else:
                    cust_id = drivers[0]["cust_id"]
                    display_name = drivers[0]["display_name"]
            
            # Check if already tracked
            tracked_drivers = await self.repo.list_tracked()
            if any(cust_id == cust_id_for_tracking for cust_id_for_tracking, _ in tracked_drivers):
                await interaction.response.send_message(
                    f"Driver {display_name} is already being tracked", 
                    ephemeral=True
                )
                return
            
            # Add to tracked drivers
            await self.repo.add_tracked_driver(cust_id, display_name)
            
            await interaction.response.send_message(
                f"Successfully tracking driver: {display_name} (ID: {cust_id})", 
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error in /track command: {e}")
            await interaction.response.send_message("An error occurred while processing your request", ephemeral=True)

    @discord.app_commands.command(name="untrack", description="Untrack a driver by ID")
    async def untrack(self, interaction: discord.Interaction, cust_id: int):
        """Untrack a driver by ID."""
        try:
            removed = await self.repo.remove_tracked_driver(cust_id)
            if removed:
                await interaction.response.send_message(
                    f"Successfully stopped tracking driver with ID {cust_id}", 
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"No tracked driver found with ID {cust_id}", 
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error in /untrack command: {e}")
            await interaction.response.send_message("An error occurred while processing your request", ephemeral=True)

    @discord.app_commands.command(name="list_tracked", description="List all tracked drivers")
    async def list_tracked(self, interaction: discord.Interaction):
        """List all tracked drivers."""
        try:
            tracked_drivers = await self.repo.list_tracked()
            if not tracked_drivers:
                await interaction.response.send_message(
                    "No drivers are currently being tracked", 
                    ephemeral=True
                )
                return
            
            # Format the list
            driver_list = "\n".join([f"- {display_name} (ID: {cust_id})" for cust_id, display_name in tracked_drivers])
            
            await interaction.response.send_message(
                f"Currently tracking:\n{driver_list}", 
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in /list_tracked command: {e}")
            await interaction.response.send_message("An error occurred while processing your request", ephemeral=True)

    @discord.app_commands.command(name="set_channel", description="Set the channel for race results")
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the channel for race results."""
        try:
            await self.repo.set_channel_for_guild(interaction.guild_id, channel.id)
            
            # Verify the bot can send messages in this channel
            try:
                test_message = await channel.send("Test message - if you see this, the channel is configured correctly")
                await test_message.delete()
            except discord.Forbidden:
                logger.warning(f"Bot lacks permissions to send messages in channel {channel.id}")
            
            await interaction.response.send_message(
                f"Set race results channel to: {channel.mention}", 
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in /set_channel command: {e}")
            await interaction.response.send_message("An error occurred while processing your request", ephemeral=True)

    @discord.app_commands.command(name="test_post", description="Post a test embed to the configured channel")
    async def test_post(self, interaction: discord.Interaction):
        """Post a test embed to the configured channel."""
        try:
            # Get the configured channel for this guild
            channel_id = await self.repo.get_channel_for_guild(interaction.guild_id)
            if not channel_id:
                await interaction.response.send_message(
                    "No results channel is configured for this server. Use `/set_channel` first.",
                    ephemeral=True
                )
                return
            
            # Create a test finish record
            test_record = FinishRecord(
                subsession_id=123456,
                cust_id=987654,
                display_name="Test Driver",
                series_name="iRacing Formula 3",
                track_name="Circuit de la Sarthe",
                car_name="BMW M4 GT3",
                field_size=24,
                finish_pos=1,
                finish_pos_in_class=1,
                class_name="Pro",
                laps=50,
                incidents=0,
                best_lap_time_s=98.765,
                sof=1250,
                official=True,
                start_time_utc="2023-06-15T14:30:00Z"
            )
            
            # Post the test embed
            await self.post_finish_embed(test_record, channel_id)
            
            await interaction.response.send_message(
                "Test embed posted successfully!", 
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in /test_post command: {e}")
            await interaction.response.send_message("An error occurred while processing your request", ephemeral=True)

# Keep the old client for backward compatibility if needed
class IR2DISClient(discord.Client):
    def __init__(self, repository: Repository, iracing_client: IRacingClient):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        self.repo = repository
        self.ir = iracing_client
        
        super().__init__(intents=intents)
        
    async def setup_hook(self):
        """Setup hook for Discord client."""
        pass

# Export the main bot class
__all__ = ['IR2DISBot']
