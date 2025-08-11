# src/discord_bot/commands/untrack.py
from discord import app_commands, Interaction

@app_commands.command(name="untrack", description="Untrack a driver by ID")
async def untrack(interaction: Interaction, cust_id: str):
    await interaction.response.send_message(f"Untracking driver with ID: {cust_id}", ephemeral=True)
