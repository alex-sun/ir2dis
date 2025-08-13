"""
Unit tests for the lastrace command functionality.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import discord

from iracing.service import FinishRecord
from iracing.api import APIError
from discord_bot.commands.lastrace import lastrace
from discord_bot.embeds.race_result import build_race_result_embed


@pytest.mark.asyncio
class TestLastRaceCommand:
    """Test the /lastrace command functionality."""

    async def test_lastrace_invalid_customer_id(self):
        """Test that invalid customer ID returns proper error."""
        interaction = AsyncMock()
        interaction.client = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        await lastrace(interaction, 0)  # Invalid ID
        
        interaction.followup.send.assert_called_once_with(
            "Invalid customer_id. Please provide a positive numeric ID.", 
            ephemeral=True
        )

    async def test_lastrace_api_client_not_available(self):
        """Test that missing API client returns proper error."""
        interaction = AsyncMock()
        interaction.client = MagicMock()  # No 'ir' attribute
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        await lastrace(interaction, 123456)
        
        interaction.followup.send.assert_called_once_with(
            "iRacing API client is not available.", 
            ephemeral=True
        )

    @patch('discord_bot.commands.lastrace.fetch_last_official_result')
    async def test_lastrace_api_error(self, mock_fetch):
        """Test that API errors are handled gracefully."""
        interaction = AsyncMock()
        interaction.client = MagicMock()
        interaction.client.ir = MagicMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        
        mock_fetch.side_effect = APIError("API Error Test")

        await lastrace(interaction, 123456)
        
        interaction.followup.send.assert_called_once_with(
            "Failed to fetch last race for 123456. Please check the ID and try again.", 
            ephemeral=True
        )

    @patch('discord_bot.commands.lastrace.fetch_last_official_result')
    async def test_lastrace_no_result(self, mock_fetch):
        """Test that no result returns proper message."""
        interaction = AsyncMock()
        interaction.client = MagicMock()
        interaction.client.ir = MagicMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        
        mock_fetch.return_value = None

        await lastrace(interaction, 123456)
        
        interaction.followup.send.assert_called_once_with(
            "No completed official race found for driver ID 123456.", 
            ephemeral=True
        )

    @patch('discord_bot.commands.lastrace.fetch_last_official_result')
    async def test_lastrace_success(self, mock_fetch):
        """Test successful command execution."""
        interaction = AsyncMock()
        interaction.client = MagicMock()
        interaction.client.ir = MagicMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        
        # Create a sample FinishRecord
        record = FinishRecord(
            subsession_id=123456,
            cust_id=123456,
            display_name="Test Driver",
            series_name="iRacing Formula 3",
            track_name="Circuit de la Sarthe",
            car_name="BMW M4 GT3",
            field_size=24,
            finish_pos=1,
            finish_pos_in_class=1,
            class_name="Pro/Am",
            laps=50,
            incidents=0,
            best_lap_time_s=89.123,
            sof=1250,
            official=True,
            start_time_utc="2023-01-01T00:00:00Z"
        )
        
        mock_fetch.return_value = record

        await lastrace(interaction, 123456)
        
        # Should have deferred and sent the embed
        interaction.response.defer.assert_called_once_with(thinking=True)
        assert interaction.followup.send.call_count == 1
        
        # Verify that build_race_result_embed was called with the right record
        call_args = interaction.followup.send.call_args
        assert 'embed' in call_args.kwargs
        embed = call_args.kwargs['embed']
        
        # Verify it's a proper Discord Embed
        assert isinstance(embed, discord.Embed)
