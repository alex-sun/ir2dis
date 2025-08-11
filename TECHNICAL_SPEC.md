# Technical Specification for iRacing to Discord Bot

## Overview
This document outlines the technical implementation of the iRacing to Discord bot (ir2dis) that tracks race results and posts them to Discord channels.

## Architecture

### Core Components

1. **Discord Bot** (`src/discord_bot/client.py`)
   - Slash command interface for driver management and configuration
   - Embed formatting and posting functionality
   - Command handling and user interaction

2. **iRacing API Client** (`src/iracing/api.py`)
   - Implements official Data API 2-step "download link" flow
   - Handles authentication, cookie management, and retries
   - Async HTTP requests using aiohttp

3. **Result Service** (`src/iracing/service.py`)
   - Orchestrates polling workflow
   - Result enrichment and DTO creation for Discord
   - Deduplication logic

4. **Storage Layer** (`src/storage/repository.py`)
   - Database persistence for tracked drivers, channel configs, posted results, and poll state
   - SQLite database with proper schema design

5. **Polling Engine** (`src/poller/engine.py`)
   - Scheduled polling of iRacing API
   - Concurrency control and rate limiting
   - Error handling and retry logic

## File Structure

```
src/
├── main.py                 # Main entry point
├── iracing/
│   ├── __init__.py         # Package init
│   ├── api.py              # iRacing API client
│   └── service.py          # Result processing service
├── storage/
│   ├── __init__.py         # Package init
│   └── repository.py       # Database operations
├── discord_bot/
│   ├── __init__.py         # Package init
│   └── client.py           # Discord bot implementation
└── poller/
    ├── __init__.py         # Package init
    └── engine.py           # Polling engine
```

## iRacing API Integration

### Authentication Flow
- Uses 2-step download link flow as per official Data API specification
- Maintains session cookies for subsequent requests
- Implements retry logic with exponential backoff for HTTP 429/5xx errors

### Endpoints Used
1. `lookup/drivers` - Driver name resolution
2. `results/search` - Session search by driver ID and time window
3. `results/get` - Full session results retrieval

## Database Schema

### Tables

1. **tracked_drivers**
   ```sql
   CREATE TABLE IF NOT EXISTS tracked_drivers (
       cust_id INTEGER PRIMARY KEY,
       display_name TEXT,
       added_at TEXT
   );
   ```

2. **channel_config**
   ```sql
   CREATE TABLE IF NOT EXISTS channel_config (
       guild_id TEXT PRIMARY KEY,
       channel_id TEXT NOT NULL,
       mode TEXT DEFAULT 'production'
   );
   ```

3. **posted_results**
   ```sql
   CREATE TABLE IF NOT EXISTS posted_results (
       subsession_id INTEGER,
       cust_id INTEGER,
       guild_id TEXT,
       posted_at TEXT,
       PRIMARY KEY(subsession_id, cust_id, guild_id)
   );
   ```

4. **poll_state**
   ```sql
   CREATE TABLE IF NOT EXISTS poll_state (
       cust_id INTEGER PRIMARY KEY,
       last_poll_ts INTEGER
   );
   ```

## Polling Workflow

### Algorithm
1. For each tracked driver:
   - Determine polling window (last poll timestamp or 48h ago)
   - Search for recent sessions involving the driver
   - Filter to finished Race sessions only
2. For each session:
   - Check if result already posted (deduplication)
   - Fetch full results
   - Extract driver's row
   - Post Discord embed
   - Mark as posted in database
3. Update last poll timestamp

### Concurrency & Rate Limiting
- Uses `asyncio.Semaphore(4)` for API calls
- Processes drivers sequentially to avoid hammering endpoints
- Implements jittered exponential backoff on 429 errors (max 60s)

## Discord Embed Format

### Structure
- **Title**: `🏁 {display_name} — P{finish_pos}{f" (Class P{finish_pos_in_class})" if class}`
- **Description**:
  - Series, Track, Car
  - Field size, Laps, Incidents, SOF
  - Best lap time (if available)
  - Official status indicator
- **Footer**: `Subsession {subsession_id} • {start_time_utc}`
- **Color**: 
  - Green for P1-P3
  - Orange for P4-P10  
  - Red otherwise

## Configuration

### Environment Variables
- `IR_USERNAME` / `IR_PASSWORD`: iRacing credentials
- `DISCORD_TOKEN`: Discord bot token
- `POLL_INTERVAL_SEC`: Polling interval (default: 120)
- `LOG_LEVEL`: Logging verbosity (default: INFO)
- `DEV_GUILD_ID`: Discord guild ID for instant command sync during development

### Docker Integration
- Configured via `docker-compose.dev.yml`
- Volume mounts for code and data persistence

## Error Handling & Resilience

### Retry Logic
- HTTP 429/5xx errors with exponential backoff
- Jittered delays to prevent thundering herd
- Maximum retry duration of 60 seconds

### Graceful Degradation
- Network/auth errors logged but don't crash poller
- Polling continues even if individual driver fails
- Database operations wrapped in error handling

## Testing Strategy

### Unit Tests
1. `test_iracing_api_download_flow.py` - API flow and retry behavior
2. `test_result_service_dedupe.py` - Deduplication logic
3. `test_embed_format.py` - Embed formatting consistency

### Test Fixtures
- JSON samples under `tests/fixtures/`
- Mock data for results/search endpoints

## Deployment

### Local Development
```bash
docker compose -f docker-compose.dev.yml up --build
```

### Production
- Standard Docker deployment with environment configuration
- Database persistence via volume mounts
- Proper logging and monitoring setup

## Security Considerations

- Credentials never logged to console
- Environment variable based configuration
- Bot account recommended for iRacing access
- Rate limiting prevents abuse of APIs
