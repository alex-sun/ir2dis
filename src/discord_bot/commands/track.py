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

            # Check if input is numeric (cust_id) or text (display name)
            driver_query = driver_name.strip()
            if driver_query.isdigit():
                # Numeric → treat as cust_id
                members = await ir_client.member_get([int(driver_query)])  # returns list
                if not members:
                    await interaction.response.send_message(f"No member with ID {driver_query}", ephemeral=True)
                    return
                cust_id = int(members[0]["cust_id"])
                display_name = members[0].get("display_name") or members[0].get("name") or str(cust_id)
            else:
                # Name (Display Name) → lookup/drivers
                drivers = await ir_client.lookup_driver(driver_query)
                if not drivers:
                    await interaction.response.send_message(f"No driver matched “{driver_query}”", ephemeral=True)
                    return
                cust_id = int(drivers[0]["cust_id"])
                display_name = drivers[0].get("display_name") or drivers[0].get("name") or driver_query
            
            # Add to tracked drivers
            await repository.add_tracked_driver(cust_id, display_name)
            
            await interaction.response.send_message(f"✅ Tracking **{display_name}** (ID {cust_id})", ephemeral=True)
        except Exception as e:
            print(f"Error in track command: {e}")
            await interaction.response.send_message("An error occurred while tracking the driver.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Track(bot))
