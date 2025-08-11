import os, logging, importlib, pkgutil
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
        # --- 0) Auto-import command modules so decorators run before sync ---
        imported = []
        for package_name in ("discord_bot.commands", "discord_bot.cogs"):
            try:
                pkg = importlib.import_module(package_name)
            except Exception:
                continue
            if hasattr(pkg, "__path__"):
                for m in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
                    importlib.import_module(m.name)
                    imported.append(m.name)
        if imported:
            logger.info("Imported command modules: %s", imported)
        else:
            logger.info("No command modules auto-imported")

        # --- 1) If nothing registered yet, add a minimal fallback /ping ---
        if not self.tree.get_commands(guild=None):
            @self.tree.command(name="ping", description="Health check")
            async def _ping(interaction: discord.Interaction):
                await interaction.response.send_message("pong", ephemeral=True)
            logger.warning("No commands detected; registered fallback /ping")

        # Log which commands we currently see
        for cmd in self.tree.get_commands(guild=None):
            logger.info("Command present (global tree): /%s", cmd.name)

        # --- 2) Global sync (slow to propagate, needed for broad availability) ---
        try:
            global_synced = await self.tree.sync()
            logger.info("Synced %d GLOBAL commands", len(global_synced))
        except Exception as e:
            logger.exception("Global command sync failed: %r", e)

        # --- 3) Instant per-guild sync for dev/testing ---
        dev_gid = int(os.getenv("DEV_GUILD_ID", "421260739055976468"))
        try:
            guild = discord.Object(id=dev_gid)
            self.tree.copy_global_to(guild=guild)
            guild_synced = await self.tree.sync(guild=guild)
            logger.info("Synced %d commands to GUILD %s", len(guild_synced), dev_gid)
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
