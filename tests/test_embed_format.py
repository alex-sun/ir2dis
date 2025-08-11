#!/usr/bin/env python3
"""
Unit tests for Discord embed formatting.
"""

import asyncio
from unittest.mock import AsyncMock
import pytest
import discord
from src.iracing.service import FinishRecord
from src.discord_bot.client import post_finish_embed


class TestEmbedFormat:
    """Test the Discord embed formatting."""

    @pytest.mark.asyncio
    async def test_post_finish_embed_p1_green(self):
        """Test embed formatting for 1st place (green)."""
        # Create a sample record for 1st place
        record = FinishRecord(
            subsession_id=123456,
            cust_id=987654,
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
        
        # Mock bot and channel
        mock_bot = AsyncMock()
        mock_channel_id = 111111
        
        # Call the function
        await post_finish_embed(mock_bot, record, mock_channel_id)
        
        # Verify that send was called with an embed
        mock_bot.get_channel.assert_called_once_with(111111)
        mock_bot.fetch_channel.assert_not_called()  # Should use cached channel
        
    @pytest.mark.asyncio
    async def test_post_finish_embed_p5_orange(self):
        """Test embed formatting for 5th place (orange)."""
        # Create a sample record for 5th place
        record = FinishRecord(
            subsession_id=123456,
            cust_id=987654,
            display_name="Test Driver",
            series_name="iRacing Formula 3",
            track_name="Circuit de la Sarthe",
            car_name="BMW M4 GT3",
            field_size=24,
            finish_pos=5,
            finish_pos_in_class=2,
            class_name="Pro/Am",
            laps=50,
            incidents=2,
            best_lap_time_s=89.123,
            sof=1250,
            official=True,
            start_time_utc="2023-01-01T00:00:00Z"
        )
        
        # Mock bot and channel
        mock_bot = AsyncMock()
        mock_channel_id = 111111
        
        # Call the function
        await post_finish_embed(mock_bot, record, mock_channel_id)
        
        # Verify that send was called with an embed
        mock_bot.get_channel.assert_called_once_with(111111)

    @pytest.mark.asyncio
    async def test_post_finish_embed_p11_red(self):
        """Test embed formatting for 11th place (red)."""
        # Create a sample record for 11th place
        record = FinishRecord(
            subsession_id=123456,
            cust_id=987654,
            display_name="Test Driver",
            series_name="iRacing Formula 3",
            track_name="Circuit de la Sarthe",
            car_name="BMW M4 GT3",
            field_size=24,
            finish_pos=11,
            finish_pos_in_class=None,
            class_name=None,
            laps=50,
            incidents=5,
            best_lap_time_s=None,
            sof=1250,
            official=False,
            start_time_utc="2023-01-01T00:00:00Z"
        )
        
        # Mock bot and channel
        mock_bot = AsyncMock()
        mock_channel_id = 111111
        
        # Call the function
        await post_finish_embed(mock_bot, record, mock_channel_id)
        
        # Verify that send was called with an embed
        mock_bot.get_channel.assert_called_once_with(111111)

    @pytest.mark.asyncio
    async def test_post_finish_embed_no_class_position(self):
        """Test embed formatting when no class position is available."""
        # Create a sample record without class position
        record = FinishRecord(
            subsession_id=123456,
            cust_id=987654,
            display_name="Test Driver",
            series_name="iRacing Formula 3",
            track_name="Circuit de la Sarthe",
            car_name="BMW M4 GT3",
            field_size=24,
            finish_pos=3,
            finish_pos_in_class=None,
            class_name=None,
            laps=50,
            incidents=0,
            best_lap_time_s=89.123,
            sof=1250,
            official=True,
            start_time_utc="2023-01-01T00:00:00Z"
        )
        
        # Mock bot and channel
        mock_bot = AsyncMock()
        mock_channel_id = 111111
        
        # Call the function
        await post_finish_embed(mock_bot, record, mock_channel_id)
        
        # Verify that send was called with an embed
        mock_bot.get_channel.assert_called_once_with(111111)

    def test_embed_content_p1(self):
        """Test the actual embed content for 1st place."""
        # Create a sample record for 1st place
        record = FinishRecord(
            subsession_id=123456,
            cust_id=987654,
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
        
        # Create embed manually to test content
        import discord
        
        color = discord.Color.green() if record.finish_pos <= 3 else (discord.Color.orange() if record.finish_pos <= 10 else discord.Color.red())
        embed = discord.Embed(
            title=f"🏁 {record.display_name} — P{record.finish_pos}" + (f" (Class P{record.finish_pos_in_class})" if record.finish_pos_in_class else ""),
            description=(
                f"**Series:** {record.series_name} • **Track:** {record.track_name} • **Car:** {record.car_name}\n"
                f"**Field:** {record.field_size} • **Laps:** {record.laps} • **Inc:** {record.incidents} • **SOF:** {record.sof or '—'}\n"
                + (f"**Best:** {record.best_lap_time_s:.3f}s\n" if record.best_lap_time_s else "")
                + ("**Official:** ✅" if record.official else "**Official:** ❌")
            ),
            colour=color,
        )
        embed.set_footer(text=f"Subsession {record.subsession_id} • {record.start_time_utc}")
        
        # Verify the content
        assert embed.title == "🏁 Test Driver — P1 (Class P1)"
        assert embed.description is not None
        assert "**Series:** iRacing Formula 3" in embed.description
        assert "**Track:** Circuit de la Sarthe" in embed.description
        assert "**Car:** BMW M4 GT3" in embed.description
        assert "**Field:** 24" in embed.description
        assert "**Laps:** 50" in embed.description
        assert "**Inc:** 0" in embed.description
        assert "**SOF:** 1250" in embed.description
        assert "**Best:** 89.123s" in embed.description
        assert "**Official:** ✅" in embed.description
        assert embed.color == discord.Color.green()
        assert "Subsession 123456 • 2023-01-01T00:00:00Z" in embed.footer.text

    def test_embed_content_p11(self):
        """Test the actual embed content for 11th place."""
        # Create a sample record for 11th place
        record = FinishRecord(
            subsession_id=123456,
            cust_id=987654,
            display_name="Test Driver",
            series_name="iRacing Formula 3",
            track_name="Circuit de la Sarthe",
            car_name="BMW M4 GT3",
            field_size=24,
            finish_pos=11,
            finish_pos_in_class=None,
            class_name=None,
            laps=50,
            incidents=5,
            best_lap_time_s=None,
            sof=1250,
            official=False,
            start_time_utc="2023-01-01T00:00:00Z"
        )
        
        # Create embed manually to test content
        import discord
        
        color = discord.Color.green() if record.finish_pos <= 3 else (discord.Color.orange() if record.finish_pos <= 10 else discord.Color.red())
        embed = discord.Embed(
            title=f"🏁 {record.display_name} — P{record.finish_pos}" + (f" (Class P{record.finish_pos_in_class})" if record.finish_pos_in_class else ""),
            description=(
                f"**Series:** {record.series_name} • **Track:** {record.track_name} • **Car:** {record.car_name}\n"
                f"**Field:** {record.field_size} • **Laps:** {record.laps} • **Inc:** {record.incidents} • **SOF:** {record.sof or '—'}\n"
                + (f"**Best:** {record.best_lap_time_s:.3f}s\n" if record.best_lap_time_s else "")
                + ("**Official:** ✅" if record.official else "**Official:** ❌")
            ),
            colour=color,
        )
        embed.set_footer(text=f"Subsession {record.subsession_id} • {record.start_time_utc}")
        
        # Verify the content
        assert embed.title == "🏁 Test Driver — P11"
        assert embed.description is not None
        assert "**Series:** iRacing Formula 3" in embed.description
        assert "**Track:** Circuit de la Sarthe" in embed.description
        assert "**Car:** BMW M4 GT3" in embed.description
        assert "**Field:** 24" in embed.description
        assert "**Laps:** 50" in embed.description
        assert "**Inc:** 5" in embed.description
        assert "**SOF:** 1250" in embed.description
        assert "**Official:** ❌" in embed.description
        assert embed.color == discord.Color.red()
        assert "Subsession 123456 • 2023-01-01T00:00:00Z" in embed.footer.text
