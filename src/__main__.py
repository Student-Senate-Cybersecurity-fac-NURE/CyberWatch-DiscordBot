import sys

from . import config
from .public_settings import (
    CLI_MISSING_COMMAND_MESSAGE,
    CLI_UNKNOWN_COMMAND_MESSAGE,
    CONFIG_SECTION_WEBHOOKS,
    REQUIRED_RSS_WEBHOOK_KEYS,
    SUPPORTED_RSS_COMMANDS,
)
from .utils import configure_logger


def verify_required_webhooks(required_webhooks: list[str]) -> None:
    missing_webhooks: list[str] = [
        hook_name
        for hook_name in required_webhooks
        if not config[CONFIG_SECTION_WEBHOOKS].get(hook_name)
    ]

    if len(missing_webhooks) > 0:
        sys.exit(
            f"У файлі .env не вказано {', '.join(missing_webhooks)}"
        )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command: str = sys.argv[1].lower()
        if command not in SUPPORTED_RSS_COMMANDS:
            sys.exit(CLI_UNKNOWN_COMMAND_MESSAGE)

        verify_required_webhooks(list(REQUIRED_RSS_WEBHOOK_KEYS))
        from .bots import rss

        configure_logger(command)
        rss.run_interval_sync()
    else:
        sys.exit(CLI_MISSING_COMMAND_MESSAGE)
