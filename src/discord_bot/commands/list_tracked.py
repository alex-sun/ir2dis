import discord
from discord import app_commands
from discord.ext import commands

class ListTracked(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="list_tracked", description="List all tracked drivers")
    async def list_tracked(self, interaction: discord.Interaction):
        await interaction.response.send_message("Listing tracked drivers... (placeholder)", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ListTracked(bot))
