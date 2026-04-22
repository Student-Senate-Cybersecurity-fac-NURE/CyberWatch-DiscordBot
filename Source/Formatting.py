from discord import Embed
from typing import List, Dict, Any, Union

from datetime import datetime
import dateutil.parser

from .public_settings import (
    CUT_SUFFIX,
    DATE_OUTPUT_FORMAT,
    DATETIME_FALLBACK_SEPARATOR,
    DETAILS_FIELD_NAME,
    MAIN_COLOR,
    SUMMARY_MAX_DESCRIPTION_LENGTH,
    SUMMARY_TRUNCATION_SUFFIX,
    THUMBNAIL_URL,
    TIME_OUTPUT_FORMAT,
)


def cut_string(string: str, length: int) -> str:
    return (
        string[: (length - len(CUT_SUFFIX))].strip() + CUT_SUFFIX
        if len(string) > length
        else string
    )


def format_datetime(article_datetime: Union[datetime, str]) -> List[str]:
    dt_object: datetime

    if isinstance(article_datetime, datetime):
        dt_object = article_datetime
    else:
        try:
            dt_object = dateutil.parser.isoparse(article_datetime)
        except ValueError:
            return article_datetime.split(DATETIME_FALLBACK_SEPARATOR)

    return [dt_object.strftime(DATE_OUTPUT_FORMAT), dt_object.strftime(TIME_OUTPUT_FORMAT)]


def format_single_article(article: Dict[str, Any]) -> Embed:
    description = ""

    if "summary" in article:
        for text_part in article["summary"].split("."):
            if not (len(description) + len(text_part)) > SUMMARY_MAX_DESCRIPTION_LENGTH:
                description += text_part + "."
            else:
                description += SUMMARY_TRUNCATION_SUFFIX
                break

    source_text = f"**Source**: *{article['source']}*"
    date_text = (
        "**Date**: " + " | *".join(format_datetime(article["publish_date"])) + "*"
    )

    if "link" in article:
        message = Embed(
            title=article["title"],
            url=article["link"],
            color=MAIN_COLOR,
        )
    else:
        message = Embed(
            title=article["title"],
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
        if article["title"]:
            message.set_thumbnail(url=THUMBNAIL_URL)

        message.add_field(
            name=source_text,
            value=date_text,
            inline=False,
        )

    return message
