import discord
from discord import app_commands
from discord.ext import commands

class Untrack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="untrack", description="Untrack a driver by ID")
    async def untrack(self, interaction: discord.Interaction, cust_id: str):
        try:
            # Access repository from the bot instance
            repository = getattr(self.bot, 'repo', None)
            if not repository:
                await interaction.response.send_message("Database connection error.", ephemeral=True)
                return

            # Convert to integer and remove any whitespace
            try:
                cust_id_int = int(cust_id.strip())
            except ValueError:
                await interaction.response.send_message(f"Invalid driver ID format: {cust_id}", ephemeral=True)
                return

            # Remove from tracked drivers
            removed = await repository.remove_tracked_driver(cust_id_int)
            
            if removed:
                await interaction.response.send_message(f"✅ Successfully untracked driver with ID: {cust_id_int}", ephemeral=True)
            else:
                await interaction.response.send_message(f"⚠️ Driver with ID {cust_id_int} was not being tracked.", ephemeral=True)
        except Exception as e:
            print(f"Error in untrack command: {e}")
            await interaction.response.send_message("An error occurred while untracking the driver.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Untrack(bot))
