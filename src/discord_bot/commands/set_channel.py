import discord
from discord import app_commands
from discord.ext import commands

class SetChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set_channel", description="Set the channel for race results")
    async def set_channel(self, interaction: discord.Interaction, channel: str):
        await interaction.response.send_message(f"Setting channel for race results: {channel}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(SetChannel(bot))
