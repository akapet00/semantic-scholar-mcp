# Configuration Reference

All settings are configured via environment variables. The server works out of the box with sensible defaults — you only need to set these if you want to customize behavior.

## API Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `SEMANTIC_SCHOLAR_API_KEY` | API key for higher rate limits | (none) |
| `DISABLE_SSL_VERIFY` | Bypass SSL verification for corporate proxies | `false` |

## Default Limits

| Variable | Description | Default | Max |
|----------|-------------|---------|-----|
| `SS_DEFAULT_SEARCH_LIMIT` | Default limit for paper search results | `10` | `100` |
| `SS_DEFAULT_PAPERS_LIMIT` | Default limit for author papers results | `10` | `1000` |
| `SS_DEFAULT_CITATIONS_LIMIT` | Default limit for citations/references | `50` | `1000` |

## Cache Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `SS_CACHE_ENABLED` | Enable response caching | `true` |
| `SS_CACHE_TTL` | Default cache TTL in seconds | `300` |
| `SS_CACHE_PAPER_TTL` | Paper details cache TTL in seconds | `3600` |

## Retry Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `SS_ENABLE_AUTO_RETRY` | Enable automatic retries | `true` |
| `SS_RETRY_MAX_ATTEMPTS` | Maximum retry attempts | `5` |
| `SS_RETRY_BASE_DELAY` | Initial retry delay in seconds | `1.0` |
| `SS_RETRY_MAX_DELAY` | Maximum delay between retries | `60.0` |

## Circuit Breaker Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `SS_CIRCUIT_FAILURE_THRESHOLD` | Failures before circuit opens | `5` |
| `SS_CIRCUIT_RECOVERY_TIMEOUT` | Seconds before recovery test | `30` |

## Logging Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `SS_LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `SS_LOG_FORMAT` | Log format (`simple` or `detailed`) | `simple` |
