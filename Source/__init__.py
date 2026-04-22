import sys
import os
from typing import Dict, Any

from dotenv import load_dotenv
from discord import SyncWebhook

from .Utils import verify_config_section
from .public_settings import (
    CONFIG_SECTION_RSS,
    CONFIG_SECTION_WEBHOOKS,
    LOGS_DIRECTORY,
    RSS_LOG_FILE_CONFIG_KEY,
    RSS_LOG_FILE_DEFAULT,
    RSS_LOG_FILE_ENV_KEY,
    WEBHOOK_ENV_BY_KEY,
)

# Load environment variables
load_dotenv()

# Need to create folder before running script, as the logger will otherwise throw error
try:
    os.mkdir(LOGS_DIRECTORY)
except OSError:
    pass  # Most likely simply means the folder already exists

# Configuration dictionary to replace ConfigParser
config: Dict[str, Dict[str, Any]] = {
    CONFIG_SECTION_WEBHOOKS: {
        hook_name: os.getenv(env_var_name)
        for hook_name, env_var_name in WEBHOOK_ENV_BY_KEY.items()
    },
    CONFIG_SECTION_RSS: {
        RSS_LOG_FILE_CONFIG_KEY: os.getenv(RSS_LOG_FILE_ENV_KEY, RSS_LOG_FILE_DEFAULT),
    }
}

for section in [CONFIG_SECTION_WEBHOOKS]:
    if section not in config:
        sys.exit(f'Please specify a "{section}" section in the config file')

if verify_config_section(config, CONFIG_SECTION_WEBHOOKS):
    webhooks = {
        hook_name: SyncWebhook.from_url(hook_url)
        for hook_name, hook_url in config[CONFIG_SECTION_WEBHOOKS].items()
        if hook_url # Ensure url is not None
    }
