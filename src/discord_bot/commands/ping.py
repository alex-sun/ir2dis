# src/discord_bot/commands/ping.py
from discord import app_commands, Interaction

@app_commands.command(name="ping", description="Health check")
async def ping(interaction: Interaction):
    await interaction.response.send_message("pong", ephemeral=True)
