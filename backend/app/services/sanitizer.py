from __future__ import annotations

import html
import re
from html.parser import HTMLParser

from bleach import clean

ALLOWED_TAGS = ["a", "b", "br", "em", "h1", "h2", "h3", "li", "ol", "p", "strong", "u", "ul"]
ALLOWED_ATTRIBUTES = {"a": ["href", "target", "rel"]}


def sanitize_html(value: str) -> str:
    cleaned = clean(
        value or "",
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols={"http", "https", "mailto"},
        strip=True,
    )
    return cleaned[:200000]


class TextExtractor(HTMLParser):
    block_tags = {"h1", "h2", "h3", "p", "li", "br"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.block_tags:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.block_tags:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        value = "".join(self.parts)
        value = re.sub(r"[ \t]+", " ", value)
        value = re.sub(r"\n\s*\n\s*", "\n\n", value)
        return value.strip()


def html_to_text(value: str) -> str:
    parser = TextExtractor()
    parser.feed(value or "")
    return parser.text()[:200000]


def safe_filename(value: str, fallback: str = "document") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "", value or "").strip(" .")
    return (cleaned[:120] or fallback).replace("..", "_")


def escape_text(value: str) -> str:
    return html.escape(value or "")
