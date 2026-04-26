import sys
import os
from pathlib import Path
from typing import Dict, Any

from discord import SyncWebhook

from .Utils import verify_config_section
from .public_settings import (
    CONFIG_SECTION_WEBHOOKS,
    LOGS_DIRECTORY,
    WEBHOOK_ENV_BY_KEY,
)


def _load_environment_variables() -> None:
    """Load environment variables from .env with an optional dotenv dependency."""

    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        env_file_path = Path(".env")
        if not env_file_path.exists():
            return

        for raw_line in env_file_path.read_text(encoding="utf-8").splitlines():
            stripped_line = raw_line.strip()
            if len(stripped_line) == 0 or stripped_line.startswith("#"):
                continue

            if "=" not in stripped_line:
                continue

            key, value = stripped_line.split("=", 1)
            normalized_key = key.strip()
            normalized_value = value.strip().strip('"').strip("'")

            if len(normalized_key) == 0:
                continue

            os.environ.setdefault(normalized_key, normalized_value)
        return

    load_dotenv()

# Load environment variables
_load_environment_variables()

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
