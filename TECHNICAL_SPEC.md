# iRacing → Discord Auto-Results Bot - Technical Specification

## Project Overview

A Discord bot that automatically posts iRacing race results for tracked drivers into a configured channel. The system is designed with modularity, scalability, and reliability in mind.

## Project Structure

```
ir2dis/
├── src/
│   ├── discord/              # Discord bot modules
│   │   ├── __init__.py
│   │   ├── commands.py       # Slash command handlers
│   │   ├── client.py         # Discord client wrapper
│   │   └── embed_builder.py  # Embed formatting
│   ├── iracing/              # iRacing API integration
│   │   ├── __init__.py
│   │   ├── auth.py           # Authentication and cookie management
│   │   ├── client.py         # API client with 2-step fetch pattern
│   │   └── models.py         # Data models for iRacing responses
│   ├── poller/               # Polling engine
│   │   ├── __init__.py
│   │   ├── engine.py         # Main polling logic
│   │   ├── scheduler.py      # Scheduling and deduplication
│   │   └── backoff.py        # Retry/backoff logic
│   ├── store/                # Database layer
│   │   ├── __init__.py
│   │   ├── database.py       # DB connection manager
│   │   ├── models.py         # ORM models for tables
│   │   ├── migrations.py     # Migration handling
│   │   └── repo.py           # Repository patterns for each table
│   ├── config/               # Configuration management
│   │   ├── __init__.py
│   │   ├── loader.py         # Load from ENV + file
│   │   └── models.py         # Config models
│   ├── observability/        # Logging and metrics
│   │   ├── __init__.py
│   │   ├── logger.py         # Structured logging
│   │   └── metrics.py        # Metrics counters
│   ├── utils/                # Utility functions
│   │   ├── __init__.py
│   │   ├── hash.py           # Password hashing
│   │   └── timezone.py       # Timezone handling
│   └── main.py               # Entry point
├── data/
│   ├── .gitkeep              # Empty placeholder
│   ├── cookies.json          # Cookie persistence
│   └── config.json           # Optional config file
├── tests/                    # Test directory
│   ├── __init__.py
│   ├── test_discord.py
│   ├── test_iracing.py
│   ├── test_poller.py
│   ├── test_store.py
│   └── test_config.py
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Core Implementation Components

### 1. Configuration Management
- Load from ENV variables with fallbacks to config file and defaults
- Validate required parameters (DISCORD_TOKEN, IRACING_EMAIL, IRACING_PASSWORD)
- Support timezone configuration and polling intervals
- Environment variable validation and error handling

### 2. Database Layer (SQLite first)
**Tables:**
- `guild` (guild_id, channel_id, timezone, created_at, updated_at)
- `tracked_driver` (guild_id, cust_id, display_name, active, created_by, created_at)
- `last_seen` (guild_id, cust_id, last_subsession_id, last_finish_at)
- `post_history` (guild_id, subsession_id, message_id, posted_at)
- `auth_state` (id, cookies_json, updated_at)

**Features:**
- Implement all tables as specified in the schema
- Migration system for schema updates
- Repository patterns for each table
- Support for SQLite, MariaDB, and PostgreSQL via environment variables

### 3. iRacing API Integration
**Authentication Module:**
- Password hashing using SHA256 + base64
- Cookie persistence to JSON file
- CAPTCHA detection and error handling
- Session management with proper cleanup

**HTTP Client:**
- 2-step fetch pattern (GET → GET via link)
- Retry logic with exponential backoff
- Rate limit handling
- Connection pooling for concurrent requests

**Data Fetching Methods:**
- `getRecentRaces(cust_id)` - Get recent race results for a driver
- `getSubsession(subsession_id)` - Get detailed subsession information

### 4. Discord Bot
**Slash Commands:**
- `/setchannel #channel` - Set the results channel
- `/track <cust_id>` - Track a driver
- `/untrack <cust_id>` - Stop tracking a driver
- `/list` - List tracked drivers
- `/lastrace <cust_id>` - Get last race result for a driver
- `/settz` (optional) - Set timezone

**Features:**
- Permission checking logic
- Embed building with proper formatting
- Command registration and error handling
- Message posting with proper Discord API integration

### 5. Polling Engine
**Main Features:**
- Main polling loop that runs at configured intervals
- Guild-by-guild processing
- Deduplication logic using post_history table
- New result detection against last_seen data
- Proper error handling and logging
- Bounded concurrency for iRacing requests (4-8 concurrent)

### 6. Observability
**Logging:**
- Structured JSON logging with key events
- Comprehensive event tracking throughout the system

**Metrics:**
- `poll_cycles_total` - Total polling cycles completed
- `results_fetched_total` - Results fetched from iRacing API
- `posts_published_total` - Posts published to Discord
- `dedupe_skips_total` - Duplicates skipped during processing
- `auth_failures_total` - Authentication failures
- `captcha_required_total` - CAPTCHA challenges encountered
- `rate_limited_total` - Rate limit events

**Health Endpoint:**
- Monitoring endpoint for system health checks

### 7. Dockerization
**Dockerfile Features:**
- Multi-stage build for minimal runtime
- Volume mapping for data persistence
- Healthcheck implementation
- Proper environment variable handling

**docker-compose.yml:**
- Service definition with proper volume mounts
- Environment variable configuration
- Network setup for container communication

## Implementation Approach

Following the agent-friendly work plan milestones:

1. **Project Scaffold** - Basic structure and config loading
2. **Database Layer** - All tables and migrations implementation  
3. **iRacing Client** - Auth and data fetching capabilities
4. **Discord Bot** - Commands and message posting functionality
5. **Polling Engine** - Deduplication and processing logic
6. **Packaging** - Dockerization with proper deployment configuration
7. **Testing** - Unit/integration tests for all components

## Key Technical Decisions

### Language & Frameworks
- **Language**: Python 3.9+ for rapid development with good ecosystem support
- **Web Framework**: discord.py or similar for Discord integration
- **Database**: SQLite as default with option to switch to MariaDB/Postgres via environment variable

### Concurrency & Performance
- Bounded pool for iRacing requests (4-8 concurrent)
- Asynchronous processing where appropriate
- Rate limiting and backoff strategies

### Error Handling & Reliability
- Graceful degradation - failures in one driver don't stop others
- Comprehensive error handling with proper logging
- Retry mechanisms with exponential backoff
- Circuit breaker patterns for external services

### Security
- No secrets in logs, password hashing, secure cookie storage
- Environment variables for sensitive data
- Proper session management and cleanup
- Input validation and sanitization

### Persistence & State Management
- Cookies stored in JSON file for authentication persistence
- DB schema with proper indices for performance
- Data migration system for schema evolution
- Volume mapping for Docker deployments

## Architecture Principles

1. **Modularity**: Each component has clear responsibilities and interfaces
2. **Separation of Concerns**: Business logic separated from infrastructure concerns  
3. **Scalability**: Designed to handle multiple guilds and drivers efficiently
4. **Maintainability**: Clear code organization and documentation
5. **Reliability**: Graceful error handling and recovery mechanisms
6. **Observability**: Comprehensive logging and metrics for monitoring

## Data Flow

1. **Configuration Loading** → 2. **Database Initialization** → 3. **Discord Bot Startup** → 4. **Polling Loop** → 5. **iRacing API Requests** → 6. **Data Processing** → 7. **Discord Message Posting**

## Deployment Considerations

### Docker Deployment
- Multi-stage Dockerfile for minimal runtime images
- Volume mounts for persistent data storage
- Environment variable configuration through docker-compose
- Health checks for monitoring and auto-restart capabilities

### Production Requirements
- Proper logging configuration
- Database connection pooling
- Rate limiting to prevent API abuse
- Monitoring and alerting setup
- Backup strategies for critical data

## Testing Strategy

- Unit tests for individual components
- Integration tests for end-to-end functionality  
- Mock testing for external APIs
- Configuration validation tests
- Database migration tests
- Performance testing with simulated load

This technical specification serves as the comprehensive reference for understanding both the project requirements and implementation details. It should be consulted when working on any part of the system to maintain consistency and adherence to design principles.
