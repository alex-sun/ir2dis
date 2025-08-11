#!/usr/bin/env python3
"""
Unit tests for ResultService deduplication logic.
"""

import asyncio
from unittest.mock import AsyncMock, Mock
import pytest
from src.iracing.service import ResultService, FinishRecord
from src.iracing.api import IRacingClient
from src.iracing.repository import Repository


@pytest.fixture
def mock_ir_client():
    """Create a mock iRacing client."""
    return AsyncMock(spec=IRacingClient)


@pytest.fixture
def mock_repo():
    """Create a mock repository."""
    return AsyncMock(spec=Repository)


@pytest.fixture
def result_service(mock_ir_client, mock_repo):
    """Create a ResultService instance."""
    return ResultService(mock_ir_client, mock_repo)


class TestResultServiceDedupe:
    """Test the ResultService deduplication logic."""

    @pytest.mark.asyncio
    async def test_find_new_finishes_for_tracked_deduplication(self, result_service, mock_repo, mock_ir_client):
        """Test that deduplication works correctly."""
        # Mock data
        mock_repo.list_tracked.return_value = [(123456, "Test Driver")]
        mock_repo.get_last_poll_ts.return_value = 0
        mock_ir_client.search_recent_sessions.return_value = [
            {
                "subsession_id": 789012,
                "series_name": "Test Series",
                "track_name": "Test Track",
                "start_time": "2023-01-01T00:00:00Z",
                "official": True
            }
        ]
        mock_ir_client.get_subsession_results.return_value = {
            "results": [
                {
                    "cust_id": 123456,
                    "display_name": "Test Driver",
                    "car_name": "Test Car",
                    "field_size": 24,
                    "finish_pos": 1,
                    "laps": 50,
                    "incidents": 0,
                    "best_lap_time_s": 89.123,
                    "sof": 1250
                }
            ]
        }
        mock_repo.was_posted.return_value = False  # Not posted yet
        
        # Call the method
        result = await result_service.find_new_finishes_for_tracked()
        
        # Verify results
        assert len(result) == 1
        record = result[0]
        assert record.cust_id == 123456
        assert record.display_name == "Test Driver"
        assert record.subsession_id == 789012

    @pytest.mark.asyncio
    async def test_find_new_finishes_for_tracked_already_posted(self, result_service, mock_repo, mock_ir_client):
        """Test that already posted results are skipped."""
        # Mock data
        mock_repo.list_tracked.return_value = [(123456, "Test Driver")]
        mock_repo.get_last_poll_ts.return_value = 0
        mock_ir_client.search_recent_sessions.return_value = [
            {
                "subsession_id": 789012,
                "series_name": "Test Series",
                "track_name": "Test Track",
                "start_time": "2023-01-01T00:00:00Z",
                "official": True
            }
        ]
        mock_repo.was_posted.return_value = True  # Already posted
        
        # Call the method
        result = await result_service.find_new_finishes_for_tracked()
        
        # Verify no results returned (already posted)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_find_new_finishes_for_tracked_multiple_drivers(self, result_service, mock_repo, mock_ir_client):
        """Test deduplication with multiple drivers."""
        # Mock data for two drivers
        mock_repo.list_tracked.return_value = [
            (123456, "Driver One"),
            (789012, "Driver Two")
        ]
        mock_repo.get_last_poll_ts.side_effect = [0, 0]
        mock_ir_client.search_recent_sessions.side_effect = [
            [
                {
                    "subsession_id": 111111,
                    "series_name": "Test Series",
                    "track_name": "Test Track",
                    "start_time": "2023-01-01T00:00:00Z",
                    "official": True
                }
            ],
            [
                {
                    "subsession_id": 222222,
                    "series_name": "Test Series",
                    "track_name": "Test Track",
                    "start_time": "2023-01-01T00:00:00Z",
                    "official": True
                }
            ]
        ]
        
        # Mock results for both drivers (only first driver should get a result)
        mock_ir_client.get_subsession_results.side_effect = [
            {
                "results": [
                    {
                        "cust_id": 123456,
                        "display_name": "Driver One",
                        "car_name": "Test Car",
                        "field_size": 24,
                        "finish_pos": 1,
                        "laps": 50,
                        "incidents": 0,
                        "best_lap_time_s": 89.123,
                        "sof": 1250
                    }
                ]
            },
            {
                "results": [
                    {
                        "cust_id": 789012,
                        "display_name": "Driver Two",
                        "car_name": "Test Car",
                        "field_size": 24,
                        "finish_pos": 2,
                        "laps": 50,
                        "incidents": 0,
                        "best_lap_time_s": 89.456,
                        "sof": 1230
                    }
                ]
            }
        ]
        
        mock_repo.was_posted.side_effect = [False, False]  # Neither posted yet
        
        # Call the method
        result = await result_service.find_new_finishes_for_tracked()
        
        # Verify both results returned (both drivers have new finishes)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_process_and_post_results_deduplication(self, result_service, mock_repo):
        """Test that process_and_post_results handles deduplication correctly."""
        # Create a sample record
        record = FinishRecord(
            subsession_id=123456,
            cust_id=987654,
            display_name="Test Driver",
            series_name="Test Series",
            track_name="Test Track",
            car_name="Test Car",
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
        
        # Mock repository methods
        mock_repo.get_channel_for_guild.return_value = mock_channel_id
        mock_repo.mark_posted.return_value = None
        mock_repo.was_posted.return_value = False  # Not posted yet
        
        # Call the method
        result = await result_service.process_and_post_results([record], mock_bot)
        
        # Verify results
        assert result == 1  # One post created
        mock_repo.mark_posted.assert_called_once_with(123456, 987654, 1)  # Guild ID should be passed correctly

    @pytest.mark.asyncio
    async def test_process_and_post_results_already_posted(self, result_service, mock_repo):
        """Test that already posted results are not processed again."""
        # Create a sample record
        record = FinishRecord(
            subsession_id=123456,
            cust_id=987654,
            display_name="Test Driver",
            series_name="Test Series",
            track_name="Test Track",
            car_name="Test Car",
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
        
        # Mock repository methods
        mock_repo.was_posted.return_value = True  # Already posted
        
        # Call the method
        result = await result_service.process_and_post_results([record], AsyncMock())
        
        # Verify no posts created (already posted)
        assert result == 0
