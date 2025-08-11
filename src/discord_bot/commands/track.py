# src/discord_bot/commands/track.py
from discord import app_commands, Interaction

@app_commands.command(name="track", description="Track a driver by name or ID")
async def track(interaction: Interaction, driver_name: str):
    await interaction.response.send_message(f"Tracking driver: {driver_name}", ephemeral=True)
