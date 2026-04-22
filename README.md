# Threat Intelligence Discord Bot

The vx-underground Threat Intelligence Discord Bot gets updates from various clearnet domains through RSS feeds.

* Don't want to set it up? [This Threat Intelligence bot is live on Discord now.](https://discord.com/invite/MSjAQe4PUy)
* Written in Python 3.13
* Can run on Windows or Linux
* Requires Discord Webhook
* Easily add or remove domains wanting to be monitored
* RSS synchronization logic is in /Source/Bots/RSS.py

## Getting Started

* Step 1. Make a web hook. Not sure how to make a webhook? [Discord makes it easy!](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks)
* Step 2. Create a .env file based on .env.example. Fill it with the Discord webhooks created in the previous step.
* Step 3. Have internet connection
* Step 4. Run the RSS synchronizer:

```bash
python -m Source rss-sync
```

## Known issues

* Known issues occur when attempting to import RequestsWebhookAdapter from Discord, users noted a fix by doing either

```bash
python3 -m pip install --force-reinstall "discord.py<=1.0.0"

OR

pip install -Iv discord.py==1.7.3
```

## Other notes

* By default this script requires 3 discord web hooks. It pipes output for private sector updates, government updates, and status log output to indicate whether or not it is running.
* For scheduled runs, keep persistent state between runs to avoid duplicates and avoid gaps.

## Adding or removing RSS Feeds to monitor

All monitored RSS feeds are configured in [OriginFeeds/rss_feeds.json](OriginFeeds/rss_feeds.json).

To add a new RSS feed append a new `[url, source_name]` entry under one of the lists:
- `private_rss_feed_list`
- `gov_rss_feed_list`

## Credit

* Original commit, code base, proof-of-concept by [smelly__vx](https://twitter.com/smelly__vx)
* General quality of life improvements and debugging by [Julien Mousqueton](https://github.com/JMousqueton)
* Feature enhancement, standardization, etc. by [hRun](https://github.com/hRun)
* Feature enhancement, standardization, etc. by [come2darkside](https://twitter.com/come2darkside_)
