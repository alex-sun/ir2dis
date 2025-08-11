import discord
from discord import app_commands
from discord.ext import commands

class Track(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="track", description="Track a driver by name or ID")
    async def track(self, interaction: discord.Interaction, driver_name: str):
        await interaction.response.send_message(f"Tracking driver: {driver_name}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Track(bot))
