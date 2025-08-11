# src/discord_bot/commands/set_channel.py
from discord import app_commands, Interaction

@app_commands.command(name="set_channel", description="Set the channel for race results")
async def set_channel(interaction: Interaction, channel: str):
    await interaction.response.send_message(f"Setting channel for race results: {channel}", ephemeral=True)
