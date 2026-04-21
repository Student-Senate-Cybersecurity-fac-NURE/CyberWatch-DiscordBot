import sys
import os
from typing import Dict, Any

from dotenv import load_dotenv
from discord import SyncWebhook

from .Utils import verify_config_section

# Load environment variables
load_dotenv()

# Need to create folder before running script, as the logger will otherwise throw error
try:
    os.mkdir("logs")
except OSError:
    pass  # Most likely simply means the folder already exists

# Configuration dictionary to replace ConfigParser
config: Dict[str, Dict[str, Any]] = {
    "Webhooks": {
        "PrivateSectorFeed": os.getenv("WEBHOOK_PRIVATE_SECTOR_FEED"),
        "GovermentFeed": os.getenv("WEBHOOK_GOVERNMENT_FEED"),
        "StatusMessages": os.getenv("WEBHOOK_STATUS_MESSAGES"),
    },
    "RSS": {
        "RSSLogFile": os.getenv("RSS_LOG_FILE", "RSSLog.txt"),
    }
}

for section in ["Webhooks"]:
    if section not in config:
        sys.exit(f'Please specify a "{section}" section in the config file')

if verify_config_section(config, "Webhooks"):
    webhooks = {
        hook_name: SyncWebhook.from_url(hook_url)
        for hook_name, hook_url in config["Webhooks"].items()
        if hook_url # Ensure url is not None
    }
