import discord
from discord import app_commands
from discord.ext import commands

class SetChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set_channel", description="Set the channel for race results")
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        try:
            # Access repository from the bot instance
            repository = getattr(self.bot, 'repo', None)
            if not repository:
                await interaction.response.send_message("Database connection error.", ephemeral=True)
                return

            # Get guild ID and channel ID
            guild_id = interaction.guild.id
            channel_id = channel.id
            
            # Store in database
            await repository.set_channel_for_guild(guild_id, channel_id)
            
            await interaction.response.send_message(f"✅ Set race results channel to {channel.mention}", ephemeral=True)
        except Exception as e:
            print(f"Error in set_channel command: {e}")
            await interaction.response.send_message("An error occurred while setting the channel.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(SetChannel(bot))
