import discord
from discord import app_commands
from discord.ext import commands

class TestPost(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="test_post", description="Post a test embed to the configured channel")
    async def test_post(self, interaction: discord.Interaction):
        try:
            # Access repository from the bot instance
            repository = getattr(self.bot, 'repo', None)
            if not repository:
                await interaction.response.send_message("Database connection error.", ephemeral=True)
                return

            # Get guild ID and channel configuration
            guild_id = interaction.guild.id
            channel_id = await repository.get_channel_for_guild(guild_id)
            
            if not channel_id:
                await interaction.response.send_message("No channel configured for this server. Use `/set_channel` first.", ephemeral=True)
                return

            # Create a test finish record (mock data)
            from iracing.service import FinishRecord
            test_record = FinishRecord(
                subsession_id=123456,
                cust_id=789012,
                display_name="Test Driver",
                series_name="iRacing Formula 3",
                track_name="Circuit de la Sarthe",
                car_name="BMW M4 GT3",
                field_size=24,
                finish_pos=1,
                finish_pos_in_class=1,
                class_name="Class A",
                laps=50,
                incidents=0,
                best_lap_time_s=98.765,
                sof=1250,
                official=True,
                start_time_utc="2023-06-15T14:30:00Z"
            )
            
            # Post the test embed using the bot's post_finish_embed method
            await self.bot.post_finish_embed(test_record, channel_id)
            
            await interaction.response.send_message("✅ Test embed posted successfully!", ephemeral=True)
        except Exception as e:
            print(f"Error in test_post command: {e}")
            await interaction.response.send_message("An error occurred while posting the test embed.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(TestPost(bot))
