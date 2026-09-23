from datetime import UTC, datetime
from typing import Any

import dateutil.parser
from dateutil.tz import gettz
from discord import Embed

from .public_settings import (
    CUT_SUFFIX,
    DATE_OUTPUT_FORMAT,
    DATETIME_FALLBACK_SEPARATOR,
    DETAILS_FIELD_NAME,
    DISCORD_EMBED_TITLE_MAX_LENGTH,
    MAIN_COLOR,
    RSS_EMBEDS_BATCH_SIZE,
    RSS_EMBEDS_MAX_CHARACTERS,
    SUMMARY_MAX_DESCRIPTION_LENGTH,
    SUMMARY_TRUNCATION_SUFFIX,
    THUMBNAIL_URL,
    TIME_OUTPUT_FORMAT,
    TIMEZONE_NAME,
)

KYIV_TIMEZONE = gettz(TIMEZONE_NAME) or gettz("Europe/Kiev")

if KYIV_TIMEZONE is None:
    raise RuntimeError(f"Не вдалося визначити часовий пояс: {TIMEZONE_NAME}")


def cut_string(string: str, length: int) -> str:
    return (
        string[: (length - len(CUT_SUFFIX))].strip() + CUT_SUFFIX
        if len(string) > length
        else string
    )


def format_datetime(article_datetime: datetime | str) -> list[str]:
    dt_object: datetime

    if isinstance(article_datetime, datetime):
        dt_object = article_datetime
    else:
        try:
            dt_object = dateutil.parser.isoparse(article_datetime)
        except ValueError:
            return article_datetime.split(DATETIME_FALLBACK_SEPARATOR)

    if dt_object.tzinfo is None:
        dt_object = dt_object.replace(tzinfo=UTC)

    kyiv_datetime = dt_object.astimezone(KYIV_TIMEZONE)
    return [
        kyiv_datetime.strftime(DATE_OUTPUT_FORMAT),
        kyiv_datetime.strftime(TIME_OUTPUT_FORMAT),
    ]


def format_single_article(article: dict[str, Any]) -> Embed:
    description = ""

    if "summary" in article:
        for text_part in article["summary"].split("."):
            if not (len(description) + len(text_part)) > SUMMARY_MAX_DESCRIPTION_LENGTH:
                description += text_part + "."
            else:
                description += SUMMARY_TRUNCATION_SUFFIX
                break

    source_text = f"**Джерело**: *{article['source']}*"
    date_text = (
        "**Дата**: " + " | *".join(format_datetime(article["publish_date"])) + "*"
    )

    article_title = cut_string(
        str(article.get("title", "")), DISCORD_EMBED_TITLE_MAX_LENGTH
    )

    if "link" in article:
        message = Embed(
            title=article_title,
            url=article["link"],
            color=MAIN_COLOR,
        )
    else:
        message = Embed(
            title=article_title,
            color=MAIN_COLOR,
        )

    if description and "link" in article:
        message.add_field(name=description, value=article["link"], inline=False)

        message.add_field(
            name=DETAILS_FIELD_NAME,
            value=source_text + "\n" + date_text,
            inline=False,
        )

    else:
        if article_title:
            message.set_thumbnail(url=THUMBNAIL_URL)

        message.add_field(
            name=source_text,
            value=date_text,
            inline=False,
        )

    return message


def count_embed_characters(embed: Embed) -> int:

    def count_value(value: Any) -> int:
        if isinstance(value, str):
            return len(value)
        if isinstance(value, dict):
            return sum(count_value(nested_value) for nested_value in value.values())
        if isinstance(value, list):
            return sum(count_value(item) for item in value)
        return 0

    return count_value(embed.to_dict())


def exceeds_embed_batch_limit(embeds: list[Embed], candidate: Embed) -> bool:

    if len(embeds) >= RSS_EMBEDS_BATCH_SIZE:
        return True

    current_size = sum(count_embed_characters(embed) for embed in embeds)
    return current_size + count_embed_characters(candidate) > RSS_EMBEDS_MAX_CHARACTERS
