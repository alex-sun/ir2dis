# src/discord_bot/commands/test_post.py
from discord import app_commands, Interaction

@app_commands.command(name="test_post", description="Post a test embed to the configured channel")
async def test_post(interaction: Interaction):
    await interaction.response.send_message("Posting test embed... (placeholder)", ephemeral=True)
