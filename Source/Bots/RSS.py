import os
import requests
import time
import json
import hashlib
from enum import Enum
from datetime import datetime, timedelta, timezone
from pathlib import Path
from email.utils import parsedate_to_datetime
from collections import defaultdict
from typing import cast, List, Dict, Any, Tuple, Optional, Set
import logging

import feedparser  # type: ignore
from dateutil.tz import gettz

from .. import webhooks
from ..Formatting import format_single_article
from ..public_settings import (
    GOV_RSS_SOURCE_NAME,
    TIMEZONE_NAME,
    PRIVATE_RSS_SOURCE_NAME,
    RSS_FEEDS_CONFIG_FILE_PATH,
    RSS_GOV_FEEDS_CONFIG_KEY,
    RSS_PRIVATE_FEEDS_CONFIG_KEY,
    RSS_BACKFILL_HOURS_DEFAULT,
    RSS_BACKFILL_HOURS_ENV_KEY,
    RSS_BATCH_DELAY_SECONDS,
    RSS_EMBEDS_BATCH_SIZE,
    RSS_FINGERPRINT_RETENTION_DAYS_DEFAULT,
    RSS_FINGERPRINT_RETENTION_DAYS_ENV_KEY,
    RSS_FORCE_WINDOW_START_UTC_ENV_KEY,
    RSS_HTTP_TIMEOUT_SECONDS_DEFAULT,
    RSS_HTTP_TIMEOUT_SECONDS_ENV_KEY,
    RSS_HTTP_USER_AGENT,
    RSS_INTERVAL_OVERLAP_MINUTES_DEFAULT,
    RSS_INTERVAL_OVERLAP_MINUTES_ENV_KEY,
    RSS_PROGRESS_NOTIFY_EVERY_DEFAULT,
    RSS_PROGRESS_NOTIFY_EVERY_ENV_KEY,
    RSS_STATE_FILE_DEFAULT,
    RSS_STATE_FILE_ENV_KEY,
    RSS_STATE_SCHEMA_VERSION,
    STATUS_MESSAGE_DATETIME_FORMAT,
    WEBHOOK_KEY_GOVERNMENT_FEED,
    WEBHOOK_KEY_PRIVATE_SECTOR_FEED,
    WEBHOOK_KEY_STATUS_MESSAGES,
)

logger = logging.getLogger("rss")
KYIV_TIMEZONE = gettz(TIMEZONE_NAME) or gettz("Europe/Kiev")

if KYIV_TIMEZONE is None:
    raise RuntimeError(f"Could not resolve timezone: {TIMEZONE_NAME}")


def _normalize_feed_list(raw_feed_list: Any, list_name: str) -> List[List[str]]:
    if not isinstance(raw_feed_list, list):
        logger.warning("%s in %s is not a list", list_name, RSS_FEEDS_CONFIG_FILE_PATH)
        return []

    normalized_feed_list: List[List[str]] = []
    for item in raw_feed_list:
        if not isinstance(item, list) or len(item) != 2:
            continue
        normalized_feed_list.append([str(item[0]), str(item[1])])

    return normalized_feed_list


def _load_feed_lists() -> Tuple[List[List[str]], List[List[str]]]:
    if not RSS_FEEDS_CONFIG_FILE_PATH.exists():
        logger.warning("RSS feeds config file is missing: %s", RSS_FEEDS_CONFIG_FILE_PATH)
        return [], []

    try:
        raw_config = json.loads(RSS_FEEDS_CONFIG_FILE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Could not parse RSS feeds config file: %s", RSS_FEEDS_CONFIG_FILE_PATH)
        return [], []

    if not isinstance(raw_config, dict):
        logger.warning("RSS feeds config file must contain a JSON object: %s", RSS_FEEDS_CONFIG_FILE_PATH)
        return [], []

    private_feeds = _normalize_feed_list(
        raw_config.get(RSS_PRIVATE_FEEDS_CONFIG_KEY),
        RSS_PRIVATE_FEEDS_CONFIG_KEY,
    )
    gov_feeds = _normalize_feed_list(
        raw_config.get(RSS_GOV_FEEDS_CONFIG_KEY),
        RSS_GOV_FEEDS_CONFIG_KEY,
    )

    return private_feeds, gov_feeds


private_rss_feed_list, gov_rss_feed_list = _load_feed_lists()

FeedTypes = Enum("FeedTypes", "RSS")

source_details: Dict[str, Dict[str, Any]] = {
    PRIVATE_RSS_SOURCE_NAME: {
        "source": private_rss_feed_list,
        "hook": webhooks[WEBHOOK_KEY_PRIVATE_SECTOR_FEED],
        "type": FeedTypes.RSS,
    },
    GOV_RSS_SOURCE_NAME: {
        "source": gov_rss_feed_list,
        "hook": webhooks[WEBHOOK_KEY_GOVERNMENT_FEED],
        "type": FeedTypes.RSS,
    },
}

RSS_STATE_FILE_PATH = Path(os.getenv(RSS_STATE_FILE_ENV_KEY, RSS_STATE_FILE_DEFAULT))
RSS_INTERVAL_OVERLAP_MINUTES = int(
    os.getenv(
        RSS_INTERVAL_OVERLAP_MINUTES_ENV_KEY,
        str(RSS_INTERVAL_OVERLAP_MINUTES_DEFAULT),
    )
)
RSS_FINGERPRINT_RETENTION_DAYS = int(
    os.getenv(
        RSS_FINGERPRINT_RETENTION_DAYS_ENV_KEY,
        str(RSS_FINGERPRINT_RETENTION_DAYS_DEFAULT),
    )
)
RSS_HTTP_TIMEOUT_SECONDS = int(
    os.getenv(RSS_HTTP_TIMEOUT_SECONDS_ENV_KEY, str(RSS_HTTP_TIMEOUT_SECONDS_DEFAULT))
)
RSS_PROGRESS_NOTIFY_EVERY = int(
    os.getenv(RSS_PROGRESS_NOTIFY_EVERY_ENV_KEY, str(RSS_PROGRESS_NOTIFY_EVERY_DEFAULT))
)
RSS_BACKFILL_HOURS = int(os.getenv(RSS_BACKFILL_HOURS_ENV_KEY, str(RSS_BACKFILL_HOURS_DEFAULT)))


def _format_datetime_kyiv(value: datetime) -> str:
    return value.astimezone(KYIV_TIMEZONE).replace(microsecond=0).isoformat()


def _parse_datetime_utc(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    parsed_value: Optional[datetime] = None
    if isinstance(value, datetime):
        parsed_value = value
    elif isinstance(value, time.struct_time):
        try:
            parsed_value = datetime(
                value.tm_year,
                value.tm_mon,
                value.tm_mday,
                value.tm_hour,
                value.tm_min,
                value.tm_sec,
                tzinfo=timezone.utc,
            )
        except ValueError:
            return None
    elif isinstance(value, (int, float)):
        try:
            parsed_value = datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    elif isinstance(value, str):
        normalized_value = value.strip()
        if len(normalized_value) == 0:
            return None

        try:
            parsed_value = datetime.fromisoformat(
                normalized_value.replace("Z", "+00:00")
            )
        except ValueError:
            try:
                parsed_email_datetime = parsedate_to_datetime(normalized_value)
            except (TypeError, ValueError):
                return None
            else:
                if isinstance(parsed_email_datetime, datetime):
                    parsed_value = parsed_email_datetime

    if parsed_value is None:
        return None

    if parsed_value.tzinfo is None:
        parsed_value = parsed_value.replace(tzinfo=timezone.utc)

    return parsed_value.astimezone(timezone.utc).replace(microsecond=0)


def _default_sync_state() -> Dict[str, Any]:
    now_kyiv = datetime.now(KYIV_TIMEZONE)
    return {
        "schema_version": RSS_STATE_SCHEMA_VERSION,
        "created_at_utc": _format_datetime_kyiv(now_kyiv),
        "updated_at_utc": _format_datetime_kyiv(now_kyiv),
        "last_successful_run_at_utc": None,
        "feeds": {},
        "sent_fingerprints": {},
    }


def _prune_sent_fingerprints(state: Dict[str, Any]) -> None:
    raw_fingerprints = state.get("sent_fingerprints")
    if not isinstance(raw_fingerprints, dict):
        state["sent_fingerprints"] = {}
        return

    cutoff_datetime = datetime.now(KYIV_TIMEZONE) - timedelta(
        days=RSS_FINGERPRINT_RETENTION_DAYS
    )
    pruned: Dict[str, str] = {}

    for fingerprint, sent_at_raw in raw_fingerprints.items():
        parsed_sent_at = _parse_datetime_utc(sent_at_raw)
        if parsed_sent_at is None:
            continue
        if parsed_sent_at >= cutoff_datetime:
            pruned[str(fingerprint)] = _format_datetime_kyiv(parsed_sent_at)

    state["sent_fingerprints"] = pruned


def _load_sync_state() -> Dict[str, Any]:
    if not RSS_STATE_FILE_PATH.exists():
        return _default_sync_state()

    try:
        loaded_state = json.loads(RSS_STATE_FILE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Could not parse rss state file, using defaults")
        return _default_sync_state()

    if not isinstance(loaded_state, dict):
        return _default_sync_state()

    default_state = _default_sync_state()
    state: Dict[str, Any] = {
        "schema_version": RSS_STATE_SCHEMA_VERSION,
        "created_at_utc": loaded_state.get(
            "created_at_utc", default_state["created_at_utc"]
        ),
        "updated_at_utc": loaded_state.get(
            "updated_at_utc", default_state["updated_at_utc"]
        ),
        "last_successful_run_at_utc": loaded_state.get("last_successful_run_at_utc"),
        "feeds": loaded_state.get("feeds", {}),
        "sent_fingerprints": loaded_state.get("sent_fingerprints", {}),
    }

    if not isinstance(state["feeds"], dict):
        state["feeds"] = {}

    _prune_sent_fingerprints(state)
    return state


def _save_sync_state(state: Dict[str, Any]) -> None:
    RSS_STATE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    RSS_STATE_FILE_PATH.write_text(
        json.dumps(state, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _get_feed_key(feed_type: str, feed_url: str, feed_name: str) -> str:
    normalized_key = f"{feed_type}::{feed_name}::{feed_url}".strip().lower()
    return hashlib.sha256(normalized_key.encode("utf-8")).hexdigest()


def _get_article_fingerprint(article: Dict[str, Any], feed_key: str) -> str:
    identity_candidates = [
        article.get("id"),
        article.get("guid"),
        article.get("link"),
    ]

    for candidate in identity_candidates:
        if isinstance(candidate, str) and len(candidate.strip()) > 0:
            fingerprint_input = f"{feed_key}::{candidate.strip()}"
            return hashlib.sha256(fingerprint_input.encode("utf-8")).hexdigest()

    fallback_identity = "::".join(
        [
            str(article.get("title", "")),
            str(article.get("publish_date", "")),
            str(article.get("source", "")),
        ]
    )
    fallback_input = f"{feed_key}::{fallback_identity}"
    return hashlib.sha256(fallback_input.encode("utf-8")).hexdigest()


def _get_window_start(sync_state: Dict[str, Any], run_end_utc: datetime) -> datetime:
    forced_start_raw = os.getenv(RSS_FORCE_WINDOW_START_UTC_ENV_KEY)
    forced_start = _parse_datetime_utc(forced_start_raw)
    if forced_start is not None:
        return forced_start

    if RSS_BACKFILL_HOURS > 0:
        return run_end_utc - timedelta(hours=RSS_BACKFILL_HOURS)

    last_successful_run = _parse_datetime_utc(sync_state.get("last_successful_run_at_utc"))
    if last_successful_run is not None:
        return last_successful_run

    return run_end_utc - timedelta(
        days=run_end_utc.weekday(),
        hours=run_end_utc.hour,
        minutes=run_end_utc.minute,
        seconds=run_end_utc.second,
        microseconds=run_end_utc.microsecond,
    )


def _extract_publish_date_from_entry(rss_object: Any) -> str:
    parsed_publish_date = _parse_datetime_utc(getattr(rss_object, "published_parsed", None))
    if parsed_publish_date is not None:
        return _format_datetime_kyiv(parsed_publish_date)

    parsed_updated_date = _parse_datetime_utc(getattr(rss_object, "updated_parsed", None))
    if parsed_updated_date is not None:
        return _format_datetime_kyiv(parsed_updated_date)

    string_publish_date = _parse_datetime_utc(getattr(rss_object, "published", None))
    if string_publish_date is not None:
        return _format_datetime_kyiv(string_publish_date)

    string_updated_date = _parse_datetime_utc(getattr(rss_object, "updated", None))
    if string_updated_date is not None:
        return _format_datetime_kyiv(string_updated_date)

    return ""


def get_news_from_rss(rss_item: List[str]) -> List[Any]:
    logger.debug(f"Querying RSS feed at {rss_item[0]}")
    try:
        response = requests.get(
            rss_item[0],
            timeout=RSS_HTTP_TIMEOUT_SECONDS,
            headers={"User-Agent": RSS_HTTP_USER_AGENT},
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
                    article["publish_date"] = _format_datetime_kyiv(published_at)
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

            if len(message_payload) < RSS_EMBEDS_BATCH_SIZE:
                continue

            hook.send(embeds=message_payload)
            for sent_article in payload_articles:
                fingerprint = str(sent_article.get("_fingerprint", ""))
                feed_key = str(sent_article.get("_feed_key", ""))
                publish_date = str(sent_article.get("publish_date", ""))

                if len(fingerprint) > 0:
                    sent_fingerprints[fingerprint] = _format_datetime_kyiv(run_end_utc)

                if len(feed_key) > 0:
                    feeds_state[feed_key] = {
                        "last_seen_published_at_utc": publish_date,
                        "last_seen_at_utc": _format_datetime_kyiv(run_end_utc),
                        "source_name": str(sent_article.get("source", "")),
                    }

            total_dispatched += len(payload_articles)
            dispatched_by_source[detail_name] += len(payload_articles)
            message_payload = []
            payload_articles = []
            time.sleep(RSS_BATCH_DELAY_SECONDS)

        if len(message_payload) == 0:
            continue

        hook.send(embeds=message_payload)
        for sent_article in payload_articles:
            fingerprint = str(sent_article.get("_fingerprint", ""))
            feed_key = str(sent_article.get("_feed_key", ""))
            publish_date = str(sent_article.get("publish_date", ""))

            if len(fingerprint) > 0:
                sent_fingerprints[fingerprint] = _format_datetime_kyiv(run_end_utc)

            if len(feed_key) > 0:
                feeds_state[feed_key] = {
                    "last_seen_published_at_utc": publish_date,
                    "last_seen_at_utc": _format_datetime_kyiv(run_end_utc),
                    "source_name": str(sent_article.get("source", "")),
                }

        total_dispatched += len(payload_articles)
        dispatched_by_source[detail_name] += len(payload_articles)
        time.sleep(RSS_BATCH_DELAY_SECONDS)

    return total_dispatched, dict(dispatched_by_source)


def run_interval_sync() -> None:
    run_end_utc = datetime.now(KYIV_TIMEZONE)
    sync_state = _load_sync_state()
    run_start_utc = _get_window_start(sync_state, run_end_utc)

    interval_message = (
        "Starting RSS interval sync from "
        f"{_format_datetime_kyiv(run_start_utc)} to {_format_datetime_kyiv(run_end_utc)}"
    )
    print(interval_message)

    write_status_message(
        interval_message
    )

    interval_articles = _collect_interval_articles(sync_state, run_start_utc, run_end_utc)
    total_candidates = sum(len(articles) for articles in interval_articles.values())
    candidates_by_source = {
        source_name: len(articles)
        for source_name, articles in interval_articles.items()
    }
    logger.info("Collected %s candidate articles for dispatch", total_candidates)
    print(f"Candidates total={total_candidates}; by_source={candidates_by_source}")
    write_status_message(
        "Candidates collected: "
        + ", ".join(
            f"{source_name}={count}"
            for source_name, count in candidates_by_source.items()
        )
    )

    dispatched_count, dispatched_by_source = _dispatch_interval_articles(
        interval_articles, sync_state, run_end_utc
    )
    logger.info("Dispatched %s articles", dispatched_count)
    print(f"Dispatched total={dispatched_count}; by_source={dispatched_by_source}")
    write_status_message(
        "Dispatched articles: "
        + ", ".join(
            f"{source_name}={count}"
            for source_name, count in dispatched_by_source.items()
        )
        + f"; total={dispatched_count}"
    )

    sync_state["schema_version"] = RSS_STATE_SCHEMA_VERSION
    sync_state["last_successful_run_at_utc"] = _format_datetime_kyiv(run_end_utc)
    sync_state["updated_at_utc"] = _format_datetime_kyiv(datetime.now(KYIV_TIMEZONE))
    _prune_sent_fingerprints(sync_state)
    _save_sync_state(sync_state)

    write_status_message("RSS interval sync completed")


def write_status_message(message: str) -> None:
    status_webhook = webhooks.get(WEBHOOK_KEY_STATUS_MESSAGES)
    if status_webhook is not None:
        status_time = datetime.now(KYIV_TIMEZONE).strftime(STATUS_MESSAGE_DATETIME_FORMAT)
        status_webhook.send(f"**{status_time}**: *{message}*")
    logger.info(message)
