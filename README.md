# iRacing to Discord Bot (ir2dis)

A Discord bot that tracks iRacing race results and posts them to Discord channels.

## Features

- Tracks drivers by iRacing ID or name
- Polls iRacing Data API for finished race sessions
- Posts rich Discord embeds with race results
- Deduplicates posts across restarts
- Configurable via environment variables
- Resilient with retry logic and rate limiting

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│  Discord    │    │   iRacing    │    │   Database   │
│   Bot       │───▶│   API        │───▶│              │
└─────────────┘    └──────────────┘    └──────────────┘
       │                   │                │
       │                   │                │
       ▼                   ▼                ▼
┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│  Poller     │    │   Service    │    │ Repository   │
│             │    │              │    │              │
└─────────────┘    └──────────────┘    └──────────────┘
```

## Setup

### Prerequisites

- Python 3.11+
- Docker (for running in containerized environment)
- iRacing account with API access
- Discord bot token

### Environment Variables

Create a `.env` file with the following variables:

```powershell
Copy-Item .env.example .env

# iRacing credentials (bot account recommended)
IRACING_EMAIL=your_iracing_email@example.com
IRACING_PASSWORD=your_iracing_password_here

# Discord bot token
DISCORD_TOKEN=your_discord_bot_token

# Polling interval in seconds (default: 120)
POLL_INTERVAL_SECONDS=120

# Logging level (INFO, DEBUG, etc.)
LOG_LEVEL=INFO

# Optional: Specific guild for development
DISCORD_GUILD_ID=your_guild_id
```

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python src/main.py
```

### Running with Docker

```powershell
# Build and run
docker compose -f .\docker-compose.dev.yml up --build
```

## Commands

- `/track <driver>` - Track a driver by name or ID
- `/untrack <cust_id>` - Untrack a driver by ID
- `/list_tracked` - List all tracked drivers
- `/set_channel #channel` - Set the channel for race results
- `/lastrace customer_id:<id>` - Show the last completed official race for an iRacing member
- `/test_post` - Post a test embed to the configured channel

## Database Schema

The bot uses SQLite with the following tables:

1. `tracked_drivers`: Stores tracked driver information
2. `channel_config`: Maps guilds to result channels  
3. `posted_results`: Tracks which results have been posted (deduplication)
4. `poll_state`: Stores polling timestamps for drivers

## Configuration

### Docker Configuration

Add environment variables to your `docker-compose.dev.yml`:

```yaml
services:
  bot:
    build: .
    env_file:
      - .env
    # ... other config
```

## Development

### Testing

Run tests with pytest:

```bash
python src/test_setup.py
```

### Code Structure

- `src/main.py`: Main entry point
- `src/iracing/`: iRacing API integration
- `src/store/`: Database operations  
- `src/discord_bot/`: Discord bot commands and embeds
- `src/poller/`: Polling engine

## License

MIT

### Instant Slash Commands in Dev
Discord can take up to ~1 hour to propagate **global** slash commands. To avoid "Unknown Integration" during development, this repo syncs commands to a specific guild on startup:

1) Set `DEV_GUILD_ID` in `.env` (or rely on the fallback `421260739055976468`).
2) Start the dev stack:
   ```bash
   docker compose -f docker-compose.dev.yml run --rm bot python src/main.py
   ```
3) Check logs for:
   - `Synced N GLOBAL commands`
   - `Synced N commands to GUILD <id>`

You can still invite the bot to **any** server. Global commands remain enabled; the guild sync only makes them appear instantly in the specified guild.
