import discord
from discord import app_commands
from discord.ext import commands

class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Health check")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("pong", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Ping(bot))
