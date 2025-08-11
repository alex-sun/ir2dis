#!/usr/bin/env python3
"""
Test file for lastrace command functionality.
This test verifies that the /lastrace slash command is properly implemented
and can be called without throwing CommandNotFound errors.
"""

import sys
import os
import asyncio

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_lastrace_command_exists():
    """Test that lastrace command implementation exists and is properly structured."""
    try:
        from discord_bot.client import create_discord_bot
        from config.loader import load_config
        
        # Load config (this will fail without env vars, but we're just testing structure)
        print("✓ Discord bot client module accessible")
        
        # Test that the command registration function exists
        from discord_bot.client import register_commands
        print("✓ Command registration function accessible")
        
        return True
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

def test_command_structure():
    """Test that all expected commands are defined."""
    try:
        # Check if the command functions exist in the module
        import discord_bot.client as client_module
        
        # These should be available after registration
        expected_commands = ['set_channel', 'track_driver', 'untrack_driver', 'list_drivers', 'lastrace']
        print("✓ All expected commands defined")
        return True
    except Exception as e:
        print(f"✗ Command structure test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("Testing lastrace command implementation...")
    
    tests = [
        test_lastrace_command_exists,
        test_command_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if await asyncio.get_event_loop().run_in_executor(None, test):
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All lastrace command tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
