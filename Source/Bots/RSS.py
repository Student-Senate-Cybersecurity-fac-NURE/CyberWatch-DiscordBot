import os
import requests
import time
import json
import hashlib
import re
from enum import Enum
from datetime import datetime, timedelta, timezone
from pathlib import Path
from email.utils import parsedate_to_datetime
from collections import defaultdict
from typing import cast, List, Dict, Any, Tuple, Optional, Set
import logging

import feedparser  # type: ignore

from .. import webhooks
from ..Formatting import format_single_article

logger = logging.getLogger("rss")

RSS_FEEDS_ENV_FILE_PATH = Path(os.getcwd()) / "OriginFeeds" / ".env.rss_feeds"


def _parse_feed_list_from_env_file(file_path: Path, key: str) -> Optional[List[List[str]]]:
    if not file_path.exists():
        return None

    try:
        env_content = file_path.read_text(encoding="utf-8")
    except OSError:
        return None

    matcher = re.search(
        rf"^\s*{re.escape(key)}\s*=\s*'(?P<json>\[[\s\S]*?\])'\s*$",
        env_content,
        re.MULTILINE,
    )
    if matcher is None:
        return None

    raw_json = matcher.group("json")
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError:
        logger.warning("Could not parse %s from %s", key, str(file_path))
        return None

    if not isinstance(parsed, list):
        return None

    normalized_feed_list: List[List[str]] = []
    for item in parsed:
        if not isinstance(item, list) or len(item) != 2:
            continue
        normalized_feed_list.append([str(item[0]), str(item[1])])

    return normalized_feed_list


def _load_feed_list(key: str) -> List[List[str]]:
    env_value = os.getenv(key)
    if env_value is not None:
        try:
            parsed_env_value = json.loads(env_value)
        except json.JSONDecodeError:
            logger.warning("Could not parse %s from environment variable", key)
            return []

        if not isinstance(parsed_env_value, list):
            return []

        normalized_feed_list: List[List[str]] = []
        for item in parsed_env_value:
            if not isinstance(item, list) or len(item) != 2:
                continue
            normalized_feed_list.append([str(item[0]), str(item[1])])

        return normalized_feed_list

    parsed_from_file = _parse_feed_list_from_env_file(RSS_FEEDS_ENV_FILE_PATH, key)
    if parsed_from_file is not None:
        return parsed_from_file

    return []


private_rss_feed_list: List[List[str]] = _load_feed_list("PRIVATE_RSS_FEED_LIST")

gov_rss_feed_list: List[List[str]] = _load_feed_list("GOV_RSS_FEED_LIST")

FeedTypes = Enum("FeedTypes", "RSS")

source_details: Dict[str, Dict[str, Any]] = {
    "Private RSS Feed": {
        "source": private_rss_feed_list,
        "hook": webhooks["PrivateSectorFeed"],
        "type": FeedTypes.RSS,
    },
    "Gov RSS Feed": {
        "source": gov_rss_feed_list,
        "hook": webhooks["GovermentFeed"],
        "type": FeedTypes.RSS,
    },
    "Ransomware News": {
        "source": "https://raw.githubusercontent.com/joshhighet/ransomwatch/main/posts.json",
        "hook": webhooks["RansomwareFeed"],
        "type": FeedTypes.JSON,
    },
}

rss_log_file_path = os.path.join(
    os.getcwd(),
    "Source",
    str(config["RSS"].get("RSSLogFile", "RSSLog.txt")),
)


rss_log = ConfigParser()
rss_log.read(rss_log_file_path)

if not rss_log.has_section("main"):
    rss_log.add_section("main")


def get_ransomware_news(source: str) -> List[Dict[str, Any]]:
    logger.debug("Querying latest ransomware information")
    posts = requests.get(source, timeout=30).json()

    for post in posts:
        post["publish_date"] = post["discovered"]
        post["title"] = "Post: " + post["post_title"]
        post["source"] = post["group_name"]

    return cast(List[Dict[str, Any]], posts)


def get_news_from_rss(rss_item: List[str]) -> List[Any]:
    logger.debug(f"Querying RSS feed at {rss_item[0]}")
    try:
        response = requests.get(
            rss_item[0],
            timeout=RSS_HTTP_TIMEOUT_SECONDS,
            headers={"User-Agent": "ThreatIntelligenceDiscordBot/rss-sync"},
        )
        response.raise_for_status()
    except requests.RequestException as error:
        logger.warning("Failed to fetch RSS feed %s (%s): %s", rss_item[1], rss_item[0], error)
        return []

    feed_entries = feedparser.parse(response.content).entries

    # This is needed to ensure that the oldest articles are proccessed first. See https://github.com/vxunderground/ThreatIntelligenceDiscordBot/issues/9 for reference
    for rss_object in feed_entries:
        rss_object["source"] = rss_item[1]
        rss_object["publish_date"] = _extract_publish_date_from_entry(rss_object)

    return cast(List[Any], feed_entries)


def _collect_interval_articles(
    sync_state: Dict[str, Any],
    run_start_utc: datetime,
    run_end_utc: datetime,
) -> Dict[str, List[Dict[str, Any]]]:
    overlap_delta = timedelta(minutes=RSS_INTERVAL_OVERLAP_MINUTES)
    effective_start = run_start_utc - overlap_delta

    sent_fingerprints = sync_state.get("sent_fingerprints", {})
    already_sent: Set[str] = set(sent_fingerprints.keys())
    seen_in_current_run: Set[str] = set()

    articles_by_source: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for detail_name, details in source_details.items():
        write_status_message(f"Checking {detail_name}")

        if details["type"] == FeedTypes.RSS:
            total_rss_feeds = len(details["source"])
            for index, rss_feed in enumerate(details["source"], start=1):
                if index == 1 or index % RSS_PROGRESS_NOTIFY_EVERY == 0 or index == total_rss_feeds:
                    write_status_message(
                        f"{detail_name}: feed {index}/{total_rss_feeds} ({rss_feed[1]})"
                    )
                raw_articles = get_news_from_rss(rss_feed)
                for raw_article in raw_articles:
                    article = cast(Dict[str, Any], raw_article)
                    published_at = _parse_datetime_utc(article.get("publish_date"))
                    if published_at is None:
                        continue

                    if not (effective_start < published_at <= run_end_utc):
                        continue

                    feed_key = _get_feed_key(
                        detail_name,
                        str(rss_feed[0]),
                        str(rss_feed[1]),
                    )
                    fingerprint = _get_article_fingerprint(article, feed_key)

                    if fingerprint in already_sent or fingerprint in seen_in_current_run:
                        continue

                    seen_in_current_run.add(fingerprint)
                    article["publish_date"] = _format_datetime_utc(published_at)
                    article["_fingerprint"] = fingerprint
                    article["_feed_key"] = feed_key
                    articles_by_source[detail_name].append(article)

    for detail_name, detail_articles in articles_by_source.items():
        detail_articles.sort(key=lambda article: article["publish_date"])
        logger.info(
            "Collected %s unique articles for %s within interval",
            len(detail_articles),
            detail_name,
        )

    return articles_by_source


def _dispatch_interval_articles(
    articles_by_source: Dict[str, List[Dict[str, Any]]],
    sync_state: Dict[str, Any],
    run_end_utc: datetime,
) -> Tuple[int, Dict[str, int]]:
    sent_fingerprints = sync_state.setdefault("sent_fingerprints", {})
    feeds_state = sync_state.setdefault("feeds", {})
    total_dispatched = 0
    dispatched_by_source: Dict[str, int] = defaultdict(int)

    for detail_name, detail_articles in articles_by_source.items():
        hook = source_details[detail_name]["hook"]
        message_payload: List[Any] = []
        payload_articles: List[Dict[str, Any]] = []

        for article in detail_articles:
            message_payload.append(format_single_article(article))
            payload_articles.append(article)

            if len(message_payload) < 10:
                continue

        messages.append(format_single_article(article))
        new_articles.append(article)

    return messages, new_articles


def send_messages(hook: Any, messages: List[Any], articles: List[Any], batch_size: int = 10) -> None:
    logger.debug(f"Sending {len(messages)} messages in batches of {batch_size}")
    for i in range(0, len(messages), batch_size):
        hook.send(embeds=messages[i : i + batch_size])

        for article in articles[i : i + batch_size]:
            rss_log.set("main", article["source"], article["publish_date"])

        time.sleep(3)


def process_source(post_gathering_func: Callable[[Any], List[Any]], source: Any, hook: Any) -> None:
    raw_articles = post_gathering_func(source)

    processed_articles, new_raw_articles = proccess_articles(raw_articles)
    send_messages(hook, processed_articles, new_raw_articles)


def handle_rss_feed_list(rss_feed_list: List[List[str]], hook: Any) -> None:
    for rss_feed in rss_feed_list:
        logger.info(f"Handling RSS feed for {rss_feed[1]}")
        webhooks["StatusMessages"].send(f"> {rss_feed[1]}")

        process_source(get_news_from_rss, rss_feed, hook)


def write_status_message(message: str) -> None:
    webhooks["StatusMessages"].send(f"**{time.ctime()}**: *{message}*")
    logger.info(message)


def clean_up_and_close() -> None:
    logger.critical("Writing last things to rss log file and closing up")
    with open(rss_log_file_path, "w") as f:
        rss_log.write(f)

    sys.exit(0)


def main() -> None:
    logger.debug("Registering clean-up handlers")
    atexit.register(clean_up_and_close)
    signal.signal(signal.SIGTERM, lambda num, frame: clean_up_and_close())

    while True:
        for detail_name, details in source_details.items():
            write_status_message(f"Checking {detail_name}")

            if details["type"] == FeedTypes.JSON:
                process_source(get_ransomware_news, details["source"], details["hook"])
            elif details["type"] == FeedTypes.RSS:
                handle_rss_feed_list(details["source"], details["hook"])

            time.sleep(3)

        logger.debug("Writing new time to rss log file")
        with open(rss_log_file_path, "w") as f:
            rss_log.write(f)

        write_status_message("All done, going to sleep")

        time.sleep(1800)


if __name__ == "__main__":
    main()
