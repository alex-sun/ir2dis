# Development Environment Setup

This document explains how to set up and use the development environment for the iRacing → Discord Auto-Results Bot.

## Overview

The development environment uses Docker volume mounting to enable hot-reloading of code changes without rebuilding the container image. This allows for rapid iteration during development.

## Prerequisites

- Docker Desktop installed and running
- Python 3.9+ (for local development if needed)
- Environment variables configured in `.env` file

## Running in Development Mode

To start the bot in development mode with volume mounting:

```bash
docker-compose -f docker-compose.dev.yml up -d
```

This command:
- Uses the `docker-compose.dev.yml` configuration
- Mounts the current directory (`.`) to `/app` in the container
- Maintains the data volume mounting for persistent storage
- Runs the container in detached mode

## Stopping Development Mode

```bash
docker-compose -f docker-compose.dev.yml down
```

## Switching Between Modes

### Production Mode (default)
```bash
docker-compose up -d
```

### Development Mode
```bash
docker-compose -f docker-compose.dev.yml up -d
```

## Benefits of Development Environment

1. **Hot Reloading**: Code changes are immediately reflected in the running container
2. **Fast Iteration**: No need to rebuild images during development
3. **Consistent Environment**: Same Python dependencies and setup as production
4. **Debugging**: Easier to debug issues with live code updates

## Development Workflow

1. Make code changes in your local editor
2. Save files (changes are automatically reflected in container)
3. View logs: `docker-compose -f docker-compose.dev.yml logs -f`
4. Restart container if needed: `docker-compose -f docker-compose.dev.yml restart bot`

## Troubleshooting

### Volume Mounting Issues
If you encounter permission issues with volume mounting:
```bash
# Check file permissions
ls -la

# Ensure Docker has access to the directory
```

### Container Not Starting
Check logs for errors:
```bash
docker-compose -f docker-compose.dev.yml logs bot
```

## Environment Variables

Make sure your `.env` file contains all required variables as specified in `.env.example`.

## Testing Changes

You can test your changes by:
1. Making code modifications locally
2. Verifying they're reflected immediately in the running container
3. Using Discord commands to verify functionality works as expected
