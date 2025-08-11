import discord
from discord import app_commands
from discord.ext import commands

class Untrack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="untrack", description="Untrack a driver by ID")
    async def untrack(self, interaction: discord.Interaction, cust_id: str):
        await interaction.response.send_message(f"Untracking driver with ID: {cust_id}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Untrack(bot))
