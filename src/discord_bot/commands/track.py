import discord
from discord import app_commands
from discord.ext import commands

class Track(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="track", description="Track a driver by name or ID")
    async def track(self, interaction: discord.Interaction, driver_name: str):
        try:
            # Access repository from the bot instance
            repository = getattr(self.bot, 'repo', None)
            if not repository:
                await interaction.response.send_message("Database connection error.", ephemeral=True)
                return

            # Look up the driver first to get their cust_id and display_name
            ir_client = getattr(self.bot, 'ir', None)
            if not ir_client:
                await interaction.response.send_message("iRacing client error.", ephemeral=True)
                return

            # Search for drivers by name
            drivers = await ir_client.lookup_driver(driver_name)
            
            if not drivers:
                await interaction.response.send_message(f"No driver found with name '{driver_name}'.", ephemeral=True)
                return
            
            # For simplicity, we'll use the first match (in a real app you might want to let user choose)
            driver = drivers[0]
            cust_id = driver['cust_id']
            display_name = driver['display_name']
            
            # Add to tracked drivers
            await repository.add_tracked_driver(cust_id, display_name)
            
            await interaction.response.send_message(f"✅ Successfully tracking driver: {display_name} (ID: {cust_id})", ephemeral=True)
        except Exception as e:
            print(f"Error in track command: {e}")
            await interaction.response.send_message("An error occurred while tracking the driver.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Track(bot))
