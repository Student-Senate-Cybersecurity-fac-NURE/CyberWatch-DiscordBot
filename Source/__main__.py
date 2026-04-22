import sys
from typing import List

from . import config
from .Utils import configure_logger
from .public_settings import (
    CLI_MISSING_COMMAND_MESSAGE,
    CLI_UNKNOWN_COMMAND_MESSAGE,
    CONFIG_SECTION_WEBHOOKS,
    REQUIRED_RSS_WEBHOOK_KEYS,
    SUPPORTED_RSS_COMMANDS,
)


def verify_required_webhooks(required_webhooks: List[str]) -> None:
    missing_webhooks: List[str] = [
        hook_name
        for hook_name in required_webhooks
        if not config[CONFIG_SECTION_WEBHOOKS].get(hook_name)
    ]

    if len(missing_webhooks) > 0:
        sys.exit(
            f"You havent't specified {', '.join(missing_webhooks)} in the .env file"
        )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command: str = sys.argv[1].lower()
        if command not in SUPPORTED_RSS_COMMANDS:
            sys.exit(CLI_UNKNOWN_COMMAND_MESSAGE)

        verify_required_webhooks(list(REQUIRED_RSS_WEBHOOK_KEYS))
        from .Bots import RSS as bot

        configure_logger(command)
        bot.run_interval_sync()
    else:
        sys.exit(CLI_MISSING_COMMAND_MESSAGE)
