#!/usr/bin/env python3
"""
Test script to verify wire logging functionality.
This script can be used to manually test if wirelogging is working.
"""

import os
import sys
sys.path.insert(0, 'src')

# Set environment variables for testing
os.environ['IRACING_WIRE_LOG'] = '1'
os.environ['IRACING_WIRE_LOG_DIR'] = './test_wirelogs'

from src.iracing.api import IRacingClient

async def test_wirelog():
    """Test that wire logging is properly configured"""
    print("Testing wire logging configuration...")
    
    # This will trigger the log message if enabled
    client = IRacingClient(
        username="test@example.com",
        password="password"
    )
    
    print(f"Wirelog enabled: {os.getenv('IRACING_WIRE_LOG', '0') == '1'}")
    print(f"Wirelog directory: {os.getenv('IRACING_WIRE_LOG_DIR', '/app/wirelogs')}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_wirelog())
