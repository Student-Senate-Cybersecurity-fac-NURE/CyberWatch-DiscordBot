import sys
from typing import List

from . import config
from .Utils import configure_logger


def verify_required_webhooks(required_webhooks: List[str]) -> None:
    missing_webhooks: List[str] = [
        hook_name
        for hook_name in required_webhooks
        if not config["Webhooks"].get(hook_name)
    ]

    if len(missing_webhooks) > 0:
        sys.exit(
            f"You havent't specified {', '.join(missing_webhooks)} in the .env file"
        )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command: str = sys.argv[1].lower()
        if command not in ["rss", "rss-sync"]:
            sys.exit(
                "Argument not recognized. The possible options are rss and rss-sync"
            )

        verify_required_webhooks(
            [
                "PrivateSectorFeed",
                "GovermentFeed",
                "StatusMessages",
            ]
        )
        from .Bots import RSS as bot

        configure_logger(command)
        bot.run_interval_sync()
    else:
        sys.exit(
            "Please provide an argument for what bot should be run. The possible options are rss and rss-sync"
        )
