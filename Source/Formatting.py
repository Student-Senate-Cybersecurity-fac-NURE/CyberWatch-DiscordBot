from discord import Embed
from typing import List, Dict, Any, Union

from datetime import datetime
import dateutil.parser


MAIN_COLOR = 0x000000
THUMBNAIL_URL = "https://avatars.githubusercontent.com/u/277730359?s=280&v=4"


def cut_string(string: str, length: int) -> str:
    return (string[: (length - 3)].strip() + "...") if len(string) > length else string


def format_datetime(article_datetime: Union[datetime, str]) -> List[str]:
    dt_object: datetime

    if isinstance(article_datetime, datetime):
        dt_object = article_datetime
    else:
        try:
            dt_object = dateutil.parser.isoparse(article_datetime)
        except ValueError:
            return article_datetime.split("T")

    return [dt_object.strftime("%d, %b %Y"), dt_object.strftime("%H:%M")]


def format_single_article(article: Dict[str, Any]) -> Embed:
    description = ""

    if "summary" in article:
        for text_part in article["summary"].split("."):
            if not (len(description) + len(text_part)) > 250:
                description += text_part + "."
            else:
                description += ".."
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
            name="Details: ",
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
