import os, logging
import discord
from discord import app_commands
from discord.ext import commands

# Import our custom modules - moved to inside the class to avoid circular imports
from iracing.service import FinishRecord
logger = logging.getLogger(__name__)

class IR2DISBot(commands.Bot):
    def __init__(self, repository, iracing_client, intents=None):
        if intents is None:
            intents = discord.Intents.default()
            intents.message_content = True
            intents.guilds = True
        
        # Initialize the bot with our custom repository and iRacing client
        self.repo = repository
        self.ir = iracing_client
        
        super().__init__(command_prefix='!', intents=intents)
        
    async def setup_hook(self) -> None:
        """Setup hook for Discord bot - sync commands."""
        # --- Load all command extensions before syncing ---
        command_extensions = [
            "discord_bot.commands.ping",
            "discord_bot.commands.track", 
            "discord_bot.commands.untrack",
            "discord_bot.commands.list_tracked",
            "discord_bot.commands.set_channel",
            "discord_bot.commands.test_post"
        ]
        
        loaded_extensions = []
        for ext in command_extensions:
            try:
                await self.load_extension(ext)
                logger.info("Loaded extension: %s", ext)
                loaded_extensions.append(ext)
            except Exception as e:
                logger.error("Failed to load extension %s: %s", ext, e)
        
        logger.info("Imported command extensions: %s", loaded_extensions)

        # Diagnostics: list what we're about to sync
        cmds = [c.name for c in self.tree.get_commands(guild=None)]
        logger.info("Commands detected in tree: %s", cmds)
        if not cmds:
            logger.warning("WARNING: No commands were discovered before sync")

        # Global sync (slow to propagate, needed for broad availability)
        try:
            global_synced = await self.tree.sync()
            logger.info("Synced %d GLOBAL commands", len(global_synced))
            
            if len(global_synced) == 0:
                logger.warning("WARNING: No commands were synced! This indicates a fundamental registration issue.")
                
        except Exception as e:
            logger.exception("Global command sync failed: %r", e)

        # Instant per-guild sync for dev/testing ---
        dev_gid = int(os.getenv("DEV_GUILD_ID", "421260739055976468"))
        try:
            guild = discord.Object(id=dev_gid)
            self.tree.copy_global_to(guild=guild)
            guild_synced = await self.tree.sync(guild=guild)
            logger.info("Synced %d commands to GUILD %s", len(guild_synced), dev_gid)
            
            if not guild_synced:
                logger.warning("WARNING: No commands were synced to guild %s", dev_gid)
                
        except Exception as e:
            logger.exception("Guild command sync failed for %s: %r", dev_gid, e)

    async def on_ready(self):
        try:
            app_info = await self.application_info()
            logger.info(
                "Bot ready: user=%s (%s) | application_id=%s | guilds=%d",
                self.user, getattr(self.user, "id", None), app_info.id, len(self.guilds)
            )
        except Exception as e:
            logger.exception("on_ready logging failed: %r", e)

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: Exception):
        logger.exception("App command error: %r", error)
        try:
            if interaction.response.is_done():
                await interaction.followup.send("❌ Command failed.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Command failed.", ephemeral=True)
        except Exception:
            pass

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

# Keep the old client for backward compatibility if needed
class IR2DISClient(discord.Client):
    def __init__(self, repository, iracing_client):
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
