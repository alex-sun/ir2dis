# Contributing Guidelines

## Commit Message Standards

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification to ensure consistent, meaningful commit messages that make our history easy to understand and parse.

### Commit Message Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types
- `feat`: New features or functionality
- `fix`: Bug fixes or corrections  
- `docs`: Documentation changes
- `style`: Code style/formatting changes (no functional change)
- `refactor`: Code restructuring without behavior change
- `test`: Adding or modifying tests
- `chore`: Maintenance tasks, build process, tooling
- `perf`: Performance improvements
- `ci`: Continuous Integration changes

### Scopes
- `discord`: Discord bot functionality
- `iracing`: iRacing API integration  
- `poller`: Polling engine and deduplication logic
- `store`: Database layer and migrations
- `config`: Configuration management
- `observability`: Logging and metrics
- `docker`: Containerization changes
- `tests`: Test suite modifications

### Examples

```
feat(poller): add race result deduplication logic

When polling for new race results, we now check against post_history 
table to prevent duplicate messages from being posted to Discord.

This prevents spam in channels when the same result is processed multiple times
due to timing issues or retries.

Closes #45
```

```
fix(discord): handle missing channel configuration gracefully

Previously if a guild had no channel configured, the bot would crash 
when trying to process tracked drivers. Now it properly handles this case
and logs an appropriate message instead of failing.

Fixes #67
```

### Guidelines
1. Use imperative mood ("Add" not "Added")
2. Keep subject line under 50 characters
3. Wrap body at 72 characters
4. Be specific about what changed, why it changed, and how it affects the system
5. Reference issues/PRs in footer (e.g., `Closes #123`)
