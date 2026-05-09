# AGENTS.md

## Project Overview

**ThreatIntelligenceDiscordBot** is a Python 3.13 RSS-to-Discord webhook aggregator that pulls threat intel from clearnet security RSS feeds and posts them to three Discord webhooks:
- Private Sector Feed
- Government Feed  
- Status Messages

**Entry point**: `python -m Source <command>`

## Commands

- `rss` or `rss-sync` — runs interval-based RSS collection with state persistence
- Commands are case-insensitive

## Execution Flow

```bash
# Development: Run once with manual state reset
python -m Source rss

# Or with explicit state file override
RSS_STATE_FILE=state/custom_state.json python -m Source rss
```

**State file**: `state/rss_state.json` — persisted between runs to track last processed timestamps and sent fingerprints.

**Workflow trigger**: GitHub Actions runs this every 4 hours (`15 */4 * * *`) on the `main` branch, pulling state from a separate `rss-state` branch.

## Configuration

### Environment Variables (`.env`)

| Key | Default | Notes |
|-----|---------|-------|
| `WEBHOOK_PRIVATE_SECTOR_FEED` | — | Required |
| `WEBHOOK_GOVERNMENT_FEED` | — | Required |
| `WEBHOOK_STATUS_MESSAGES` | — | Required |
| `RSS_STATE_FILE` | `state/rss_state.json` | Optional override |
| `RSS_INTERVAL_OVERLAP_MINUTES` | `120` | Overlap buffer for interval windows |
| `RSS_FINGERPRINT_RETENTION_DAYS` | `45` | How long to keep sent fingerprints |
| `RSS_HTTP_TIMEOUT_SECONDS` | `20` | HTTP request timeout |
| `RSS_PROGRESS_NOTIFY_EVERY` | `15` | Progress notification frequency |
| `RSS_BACKFILL_HOURS` | `0` | Hours to backfill if > 0 |
| `RSS_FORCE_WINDOW_START_UTC` | — | Force start time override |

### Feed Configuration

**File**: `OriginFeeds/rss_feeds.json`

```json
{
  "private_rss_feed_list": [["url", "name"], ...],
  "gov_rss_feed_list": [["url", "name"], ...]
}
```

**Default source**: ~90% from David Longenecker's public security RSS list.

### Logs

- `logs/<module>.info.log` — INFO level events
- `logs/<module>.error.log` — ERROR level events

## Architecture

**Pattern**: Interval-based collection with overlap windows to avoid gaps.

**Key files**:
- `Source/Bots/RSS.py` — main sync logic, interval windows, dedup
- `Source/__main__.py` — CLI entrypoint, command routing
- `Source/__init__.py` — env loading, webhook initialization
- `Source/public_settings.py` — constants, env keys, defaults
- `Source/Formatting.py` — Discord embed formatting
- `Source/Utils.py` — logger config, config validation

**State schema v2 fields**:
- `schema_version`
- `created_at_utc`, `updated_at_utc`
- `last_successful_run_at_utc`
- `feeds` — last seen timestamps per feed
- `sent_fingerprints` — SHA256 fingerprints of sent articles

## CI/CD Pipeline Order

1. `bandit` — security scan
2. `mypy` — type check (strict mode)
3. `ruff` — linting
4. `codeql` — SAST analysis

Run locally:

```bash
pip install bandit mypy ruff
bandit -r Source -q
mypy --config-file mypy.ini .
ruff check .
```

## RSS Sync Workflow

```bash
# 1. Ensure .env has all 3 webhook URLs
# 2. Run RSS sync
python -m Source rss

# 3. Check logs
cat logs/rss.info.log
```

**Batching**: Sends max 10 embeds per webhook call with 3s delay between batches.

**Dedup**: Uses SHA256 fingerprints based on feed+ID/guid/link to avoid duplicates.

**Timezone**: All timestamps normalized to Kyiv time (`Europe/Kyiv`).

## Quirks & Gotchas

- **3 webhooks required** by default (private, gov, status). Script exits if missing.
- **State file matters**: Without it, runs start from current time (no backfill).
- **Overlap window**: 120 min default to prevent gaps between interval runs.
- **Fingerprint retention**: 45 days default; older entries pruned automatically.
- **Batch delay**: 3s between embed batches to avoid webhook rate limits.
- **User-Agent**: Set to `ThreatIntelligenceDiscordBot/rss-sync` for requests.

## Adding/Removing Feeds

Edit `OriginFeeds/rss_feeds.json`:

```python
# Add to private feeds
raw_config["private_rss_feed_list"].append(["https://newfeed.com", "New Source"])

# Add to gov feeds
raw_config["gov_rss_feed_list"].append(["https://govfeed.com", "Gov Source"])
```

## Testing

**Run single sync**:

```bash
WEBHOOK_PRIVATE_SECTOR_FEED=https://hook1.com \
WEBHOOK_GOVERNMENT_FEED=https://hook2.com \
WEBHOOK_STATUS_MESSAGES=https://hook3.com \
python -m Source rss
```

**Check logs after run**:

```bash
cat logs/rss.info.log
cat logs/rss.error.log
```

## External Dependencies

- `discord.py` — Discord webhook integration
- `feedparser` — RSS parsing
- `python-dateutil` — timezone-aware datetime parsing
