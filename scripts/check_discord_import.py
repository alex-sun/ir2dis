# scripts/check_discord_import.py
import discord
from discord.ext import commands  # should import from site-packages
try:
    from discord_bot.client import create_discord_bot  # our code
    print("OK: discord.py from:", discord.__file__)
    print("OK: discord.py version:", getattr(discord, "__version__", "unknown"))
    print("OK: local import:", create_discord_bot.__name__)
except Exception as e:
    print("FAIL:", e)
    raise
