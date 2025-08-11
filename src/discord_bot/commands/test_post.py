import discord
from discord import app_commands
from discord.ext import commands

class TestPost(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="test_post", description="Post a test embed to the configured channel")
    async def test_post(self, interaction: discord.Interaction):
        await interaction.response.send_message("Posting test embed... (placeholder)", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(TestPost(bot))
