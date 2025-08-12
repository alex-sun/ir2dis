#!/usr/bin/env python3
"""
Unit tests for iRacing API client download flow and retry logic.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from aiohttp import ClientResponse, ClientSession, ClientError
from src.iracing.api import IRacingClient


@pytest.fixture
def mock_session():
    """Create a mock aiohttp session."""
    return AsyncMock(spec=ClientSession)


@pytest.fixture
def iracing_client(mock_session):
    """Create an IRacingClient instance."""
    return IRacingClient("test_user", "test_pass", mock_session)


class TestIRacingAPIDownloadFlow:
    """Test the iRacing API download flow and retry logic."""

    @pytest.mark.asyncio
    async def test_login_success(self, iracing_client, mock_session):
        """Test successful login."""
        # Mock the login response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "login success"
        
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        await iracing_client.login()
        
        assert mock_session.post.called

    @pytest.mark.asyncio
    async def test_get_json_via_download_success(self, iracing_client, mock_session):
        """Test successful download flow."""
        # Mock the first response (link)
        link_response = AsyncMock()
        link_response.status = 200
        link_response.json.return_value = {"link": "https://example.com/data"}
        
        # Mock the second response (actual data)
        data_response = AsyncMock()
        data_response.status = 200
        data_response.json.return_value = {"data": "test"}
        
        mock_session.post.return_value.__aenter__.return_value = link_response
        mock_session.get.return_value.__aenter__.return_value = data_response
        
        result = await iracing_client._get_json_via_download("test/path", {})
        
        assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_get_json_via_download_retry_on_429(self, iracing_client, mock_session):
        """Test retry logic on 429 status."""
        # Mock the first response (link) - returns 429 then success
        link_response = AsyncMock()
        link_response.status = 429
        
        # Mock the second response (actual data)
        data_response = AsyncMock()
        data_response.status = 200
        data_response.json.return_value = {"data": "test"}
        
        mock_session.post.return_value.__aenter__.return_value = link_response
        mock_session.get.return_value.__aenter__.return_value = data_response
        
        # This should retry and eventually succeed
        with patch('asyncio.sleep') as mock_sleep:
            result = await iracing_client._get_json_via_download("test/path", {})
            
        assert result == {"data": "test"}
        assert mock_session.post.call_count >= 2  # Should have retried

    @pytest.mark.asyncio
    async def test_get_json_via_download_retry_on_5xx(self, iracing_client, mock_session):
        """Test retry logic on 5xx status."""
        # Mock the first response (link) - returns 503 then success
        link_response = AsyncMock()
        link_response.status = 503
        
        # Mock the second response (actual data)
        data_response = AsyncMock()
        data_response.status = 200
        data_response.json.return_value = {"data": "test"}
        
        mock_session.post.return_value.__aenter__.return_value = link_response
        mock_session.get.return_value.__aenter__.return_value = data_response
        
        # This should retry and eventually succeed
        with patch('asyncio.sleep') as mock_sleep:
            result = await iracing_client._get_json_via_download("test/path", {})
            
        assert result == {"data": "test"}
        assert mock_session.post.call_count >= 2  # Should have retried

    @pytest.mark.asyncio
    async def test_get_json_via_download_retry_on_network_error(self, iracing_client, mock_session):
        """Test retry logic on network errors."""
        # Mock the first response (link) - raises ClientError then succeeds
        mock_session.post.side_effect = [
            AsyncMock(__aenter__=AsyncMock(side_effect=ClientError("Network error"))),
            AsyncMock(
                __aenter__=AsyncMock(return_value=AsyncMock(
                    status=200,
                    json=AsyncMock(return_value={"link": "https://example.com/data"})
                ))
            )
        ]
        
        # Mock the second response (actual data)
        data_response = AsyncMock()
        data_response.status = 200
        data_response.json.return_value = {"data": "test"}
        mock_session.get.return_value.__aenter__.return_value = data_response
        
        with patch('asyncio.sleep') as mock_sleep:
            result = await iracing_client._get_json_via_download("test/path", {})
            
        assert result == {"data": "test"}
        assert mock_session.post.call_count >= 2  # Should have retried
