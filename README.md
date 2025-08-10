# iRacing → Discord Auto-Results Bot

A Discord bot that automatically posts iRacing race results for tracked drivers into a configured channel.

## Features

- Automatically posts race results to Discord
- Slash commands to manage tracking
- Polling engine with deduplication and backoff
- Cookie persistence to avoid reCAPTCHA
- Dockerized deployment
- Structured logging and metrics
- Support for SQLite, MariaDB, and PostgreSQL databases

## Requirements

- Python 3.9+
- Docker (for containerized deployment)

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Run with Docker**
   ```bash
   docker-compose up -d
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Discord bot token | - |
| `IRACING_EMAIL` | iRacing email | - |
| `IRACING_PASSWORD` | iRacing password | - |
| `IRACING_PASSWORD_HASHED` | If password is already hashed | `false` |
| `TIMEZONE_DEFAULT` | Default timezone for guilds | `Europe/Berlin` |
| `POLL_INTERVAL_SECONDS` | Polling interval in seconds | `120` |
| `POLL_CONCURRENCY` | Max concurrent requests to iRacing | `4` |
| `SQLITE_PATH` | Path to SQLite database file | `data/bot.db` |
| `COOKIES_PATH` | Path to cookie file | `data/cookies.json` |
| `LOG_LEVEL` | Logging level | `info` |

### Slash Commands

- `/setchannel #channel` - Set the results channel
- `/track <cust_id>` - Track a driver
- `/untrack <cust_id>` - Stop tracking a driver
- `/list` - List tracked drivers
- `/lastrace <cust_id>` - Get last race result for a driver

## Architecture

The bot follows a modular architecture:

```
src/
├── discord/     # Discord bot and command handling
├── iracing/     # iRacing API integration
├── poller/      # Polling engine and deduplication logic
├── store/       # Database layer (SQLite)
├── config/      # Configuration management
├── observability/ # Logging and metrics
└── utils/       # Utility functions
```

## Data Model

The bot uses SQLite with the following tables:

- `guild` - Discord guild settings
- `tracked_driver` - Drivers being tracked per guild
- `last_seen` - Last subsession seen for each driver
- `post_history` - Records of posts to prevent duplicates
- `auth_state` - Authentication cookies

## Deployment

### Docker

The bot is designed to be deployed with Docker. The `Dockerfile` and `docker-compose.yml` are provided for easy deployment.

### Manual Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python src/main.py
```

## Security

- Passwords are hashed using iRacing's method
- Cookies are persisted to avoid repeated logins
- Secrets are not logged or stored in plaintext in logs
- Environment variables should be used for sensitive data

## Troubleshooting

### ReCAPTCHA Issues

If you encounter reCAPTCHA challenges:

1. Perform a one-time login via browser from the same egress IP as your bot
2. Restart the bot - it will use the saved cookies

### Database Issues

The database file is stored in `data/bot.db`. If issues occur, you can delete this file to start fresh (note: this will reset all tracking).

## Development

To contribute:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT
