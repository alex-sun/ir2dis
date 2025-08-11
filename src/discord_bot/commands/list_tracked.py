# src/discord_bot/commands/list_tracked.py
from discord import app_commands, Interaction

@app_commands.command(name="list_tracked", description="List all tracked drivers")
async def list_tracked(interaction: Interaction):
    await interaction.response.send_message("Listing tracked drivers... (placeholder)", ephemeral=True)
