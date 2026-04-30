from pathlib import Path
from typing import Dict, Final, Tuple


PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent

# Formatting settings
MAIN_COLOR: Final[int] = 0x000000
THUMBNAIL_URL: Final[str] = "https://avatars.githubusercontent.com/u/277730359?s=280&v=4"
CUT_SUFFIX: Final[str] = "..."
SUMMARY_MAX_DESCRIPTION_LENGTH: Final[int] = 250
SUMMARY_TRUNCATION_SUFFIX: Final[str] = ".."
DATETIME_FALLBACK_SEPARATOR: Final[str] = "T"
DATE_OUTPUT_FORMAT: Final[str] = "%d.%m.%Y"
TIME_OUTPUT_FORMAT: Final[str] = "%H:%M:%S %Z"
DETAILS_FIELD_NAME: Final[str] = "Деталі: "

# Timezone settings
TIMEZONE_NAME: Final[str] = "Europe/Kyiv"
STATUS_MESSAGE_DATETIME_FORMAT: Final[str] = "%d.%m.%Y %H:%M:%S %Z"

# Logger settings
LOGS_DIRECTORY: Final[str] = "logs"
INFO_LOG_FILENAME_SUFFIX: Final[str] = ".info.log"
ERROR_LOG_FILENAME_SUFFIX: Final[str] = ".error.log"
LOGGER_FORMAT: Final[str] = "[%(asctime)s] %(levelname)s у %(module)s: %(message)s"

# Environment and config keys
CONFIG_SECTION_WEBHOOKS: Final[str] = "Webhooks"

WEBHOOK_ENV_BY_KEY: Final[Dict[str, str]] = {
    "PrivateSectorFeed": "WEBHOOK_PRIVATE_SECTOR_FEED",
    "GovermentFeed": "WEBHOOK_GOVERNMENT_FEED",
    "StatusMessages": "WEBHOOK_STATUS_MESSAGES",
}

# CLI settings
SUPPORTED_RSS_COMMANDS: Final[Tuple[str, str]] = ("rss", "rss-sync")
CLI_UNKNOWN_COMMAND_MESSAGE: Final[str] = (
    "Аргумент не розпізнано. Доступні варіанти: rss та rss-sync"
)
CLI_MISSING_COMMAND_MESSAGE: Final[str] = (
    "Будь ласка, вкажіть аргумент, який бот запускати. "
    "Доступні варіанти: rss та rss-sync"
)
REQUIRED_RSS_WEBHOOK_KEYS: Final[Tuple[str, str, str]] = (
    "PrivateSectorFeed",
    "GovermentFeed",
    "StatusMessages",
)

WEBHOOK_KEY_PRIVATE_SECTOR_FEED: Final[str] = "PrivateSectorFeed"
WEBHOOK_KEY_GOVERNMENT_FEED: Final[str] = "GovermentFeed"
WEBHOOK_KEY_STATUS_MESSAGES: Final[str] = "StatusMessages"

# RSS synchronization settings
RSS_FEEDS_CONFIG_FILE_PATH: Final[Path] = PROJECT_ROOT / "OriginFeeds" / "rss_feeds.json"
RSS_PRIVATE_FEEDS_CONFIG_KEY: Final[str] = "private_rss_feed_list"
RSS_GOV_FEEDS_CONFIG_KEY: Final[str] = "gov_rss_feed_list"
PRIVATE_RSS_SOURCE_NAME: Final[str] = "Private RSS Feed"
GOV_RSS_SOURCE_NAME: Final[str] = "Gov RSS Feed"

RSS_STATE_FILE_ENV_KEY: Final[str] = "RSS_STATE_FILE"
RSS_STATE_FILE_DEFAULT: Final[str] = "state/rss_state.json"

RSS_INTERVAL_OVERLAP_MINUTES_ENV_KEY: Final[str] = "RSS_INTERVAL_OVERLAP_MINUTES"
RSS_INTERVAL_OVERLAP_MINUTES_DEFAULT: Final[int] = 120

RSS_FINGERPRINT_RETENTION_DAYS_ENV_KEY: Final[str] = "RSS_FINGERPRINT_RETENTION_DAYS"
RSS_FINGERPRINT_RETENTION_DAYS_DEFAULT: Final[int] = 45

RSS_HTTP_TIMEOUT_SECONDS_ENV_KEY: Final[str] = "RSS_HTTP_TIMEOUT_SECONDS"
RSS_HTTP_TIMEOUT_SECONDS_DEFAULT: Final[int] = 20

RSS_PROGRESS_NOTIFY_EVERY_ENV_KEY: Final[str] = "RSS_PROGRESS_NOTIFY_EVERY"
RSS_PROGRESS_NOTIFY_EVERY_DEFAULT: Final[int] = 15

RSS_BACKFILL_HOURS_ENV_KEY: Final[str] = "RSS_BACKFILL_HOURS"
RSS_BACKFILL_HOURS_DEFAULT: Final[int] = 0

RSS_FORCE_WINDOW_START_UTC_ENV_KEY: Final[str] = "RSS_FORCE_WINDOW_START_UTC"

RSS_HTTP_USER_AGENT: Final[str] = "ThreatIntelligenceDiscordBot/rss-sync"
RSS_EMBEDS_BATCH_SIZE: Final[int] = 10
RSS_BATCH_DELAY_SECONDS: Final[int] = 3
RSS_STATE_SCHEMA_VERSION: Final[int] = 2
