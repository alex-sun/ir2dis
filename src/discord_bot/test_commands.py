# Test file to verify command registration works in this environment
from discord import app_commands, Interaction

# Simple test commands to verify the system works
@app_commands.command(name="test_simple", description="Simple test command")
async def test_simple(interaction: Interaction):
    await interaction.response.send_message("Simple test working!", ephemeral=True)

@app_commands.command(name="verify", description="Verify commands work")
async def verify(interaction: Interaction):
    await interaction.response.send_message("Commands verification working!", ephemeral=True)
