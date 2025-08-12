"""
Slash command `/lastrace` that shows the last completed official race for a driver.
This command provides identical output to what the poller posts when it detects a new result.
"""

from __future__ import annotations
import logging
import discord
from discord import app_commands, Interaction
from discord.ext import commands

from iracing.api import IRacingClient, APIError
from iracing.services.last_result import fetch_last_official_result
from discord_bot.embeds.race_result import build_race_result_embed

logger = logging.getLogger(__name__)


@app_commands.command(
    name="lastrace",
    description="Show the last completed official race for an iRacing member (customer_id).",
)
@app_commands.describe(customer_id="iRacing customer ID (digits)")
async def lastrace(interaction: Interaction, customer_id: int):
    """Slash command to show the last completed official race for a driver."""
    await interaction.response.defer(thinking=True)  # Visible loading indicator

    if customer_id <= 0:
        await interaction.followup.send("Invalid customer_id. Please provide a positive numeric ID.", ephemeral=True)
        return

    # Get the IRacingAPI instance from the bot
    bot: commands.Bot = interaction.client  # type: ignore
    api: IRacingClient = getattr(bot, "ir", None)  # Use 'ir' attribute as set in main.py

    if api is None:
        await interaction.followup.send("iRacing API client is not available.", ephemeral=True)
        return

    try:
        result = await fetch_last_official_result(api, customer_id)
    except APIError as e:
        logger.error("lastrace: API error for %s: %s", customer_id, e)
        await interaction.followup.send(f"Failed to fetch last race for {customer_id}. Please check the ID and try again.", ephemeral=True)
        return
    except Exception as e:
        logger.error("lastrace: Unexpected error for %s: %s", customer_id, e)
        await interaction.followup.send(f"An unexpected error occurred while fetching data for {customer_id}.", ephemeral=True)
        return

    if not result:
        await interaction.followup.send(f"No completed official race found for driver ID {customer_id}.", ephemeral=True)
        return

    try:
        embed = build_race_result_embed(result)
        await interaction.followup.send(embed=embed)
        logger.info(f"lastrace: Successfully sent embed for driver {customer_id}")
    except Exception as e:
        logger.error("lastrace: Error sending embed for %s: %s", customer_id, e)
        await interaction.followup.send(f"Failed to format and send race result for {customer_id}.", ephemeral=True)


# Optional: Add a command group if we want to add more related commands later
# lastrace_group = app_commands.Group(name="lastrace", description="Commands related to last races")
# 
# @lastrace_group.command(name="customer", description="Show last race for customer")
# @app_commands.describe(customer_id="iRacing customer ID")
# async def lastrace_customer(interaction: Interaction, customer_id: int):
#     await lastrace(interaction, customer_id)
