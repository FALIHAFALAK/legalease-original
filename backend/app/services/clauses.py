from __future__ import annotations

import re
from dataclasses import dataclass, field

# Characters used per estimated page when a source format has no real pagination.
ESTIMATED_PAGE_CHARACTERS = 1800
MAX_CLAUSE_CHARACTERS = 6000
# Joins pages into the flattened text; page spans are computed with the same separator.
PAGE_SEPARATOR = "\n\n"

_WHITESPACE = re.compile(r"\s+")
_NUMBERED_HEADING = re.compile(
    r"^(?:section\s+|article\s+)?"
    r"(?P<number>\d{1,2}(?:\.\d{1,2}){0,3}|\d{1,2}\s*[-–)]|[IVXLC]{1,6})"
    r"[.)\s]\s*"
    r"(?P<title>\S.*)$"
)
_ALL_CAPS = re.compile(r"^[A-Z0-9][A-Z0-9 &/,'()\-–—:;]{2,88}$")
_SENTENCE_END = (".", ";", ",", ":")
_FOOTER_NOISE = re.compile(
    r"^(?:page\s+\d+|\d+\s*\|\s*page\s*\d+|confidential|draft|initials|s\s*[-–]\s*\d.*)$",
    re.IGNORECASE,
)
_MIN_TITLE_WORDS = 2
_MAX_TITLE_WORDS = 14


@dataclass(frozen=True)
class PageSpan:
    """Half-open character range of a single page inside the flattened document text."""

    start: int
    end: int
    number: int


@dataclass(frozen=True)
class Clause:
    """A contract clause located in the extracted text with source page references."""

    index: int
    heading: str
    text: str
    page_start: int
    page_end: int
    page_reference_kind: str
    start_offset: int
    end_offset: int

    @property
    def page_label(self) -> str:
        if self.page_start == self.page_end:
            return f"Page {self.page_start}"
        return f"Pages {self.page_start}-{self.page_end}"

    @property
    def citation(self) -> str:
        return f"{self.heading} ({self.page_label})" if self.heading else self.page_label

    def summary(self, limit: int = 320) -> str:
        collapsed = _WHITESPACE.sub(" ", self.text).strip()
        return collapsed if len(collapsed) <= limit else collapsed[: limit - 1].rstrip() + "…"


@dataclass
class ExtractedDocument:
    """Text extracted from an upload together with its page map."""

    file_type: str
    text: str
    pages: list[str] = field(default_factory=list)
    page_reference_kind: str = "estimated_page"

    @property
    def page_count(self) -> int:
        return max(1, len(self.pages))

    @property
    def word_count(self) -> int:
        return len(self.text.split())


def _looks_like_title_case_line(candidate: str, following: str) -> bool:
    words = candidate.split()
    if not _MIN_TITLE_WORDS <= len(words) <= _MAX_TITLE_WORDS:
        return False
    if not candidate[:1].isupper():
        return False
    next_word = following.strip().split(" ", 1)[0]
    return bool(next_word) and next_word[:1].isupper()


def _is_heading(line: str, following: str) -> bool:
    candidate = line.strip()
    if not candidate or len(candidate) > 90:
        return False
    if not following.strip():
        return False
    if _FOOTER_NOISE.match(candidate):
        return False

    match = _NUMBERED_HEADING.match(candidate)
    if match:
        title = match.group("title").strip()
        if not title:
            return False
        if title.endswith(_SENTENCE_END) and not _ALL_CAPS.match(candidate):
            return False
        return len(title.split()) <= _MAX_TITLE_WORDS
    if _ALL_CAPS.match(candidate):
        return len(candidate.split()) <= _MAX_TITLE_WORDS
    return _looks_like_title_case_line(candidate, following)


def paginate_text(text: str, characters_per_page: int = ESTIMATED_PAGE_CHARACTERS) -> list[str]:
    """Split plain text into estimated pages on paragraph boundaries."""

    if not text.strip():
        return [""]
    pages: list[str] = []
    current: list[str] = []
    size = 0
    for paragraph in (item for item in text.split("\n") if item.strip()):
        if current and size + len(paragraph) > characters_per_page:
            pages.append("\n".join(current))
            current = []
            size = 0
        current.append(paragraph)
        size += len(paragraph) + 1
    if current:
        pages.append("\n".join(current))
    return pages or [""]


def build_page_spans(pages: list[str], separator: str = PAGE_SEPARATOR) -> list[PageSpan]:
    spans: list[PageSpan] = []
    cursor = 0
    for number, page in enumerate(pages, start=1):
        start = cursor
        cursor += len(page) + len(separator)
        spans.append(PageSpan(start=start, end=start + len(page), number=number))
    return spans


def page_for_offset(spans: list[PageSpan], offset: int) -> int:
    for span in spans:
        if span.start <= offset <= span.end:
            return span.number
    return spans[-1].number if spans else 1


def normalize_for_matching(value: str) -> str:
    return _WHITESPACE.sub(" ", value or "").strip().lower()


def _normalized_with_map(text: str) -> tuple[str, list[int]]:
    """Collapse whitespace and lower-case text, mapping each result index to its original index.

    Collapsing a run of whitespace into a single space means an index in the normalized string
    cannot be recovered by counting non-space characters, so the mapping is built as we go.
    """

    chars: list[str] = []
    indices: list[int] = []
    after_space = True
    for index, char in enumerate(text):
        if char.isspace():
            if after_space:
                continue
            after_space = True
            chars.append(" ")
            indices.append(index)
            continue
        after_space = False
        chars.append(char.lower())
        indices.append(index)
    while chars and chars[-1] == " ":
        chars.pop()
        indices.pop()
    return "".join(chars), indices


def find_quote_span(text: str, quote: str) -> tuple[int, int] | None:
    """Locate a quoted excerpt, returning a half-open span in the original text's coordinates.

    Matching tolerates whitespace drift, so the span is translated back to the original text to
    stay usable as ``text[start:end]`` for highlighting.
    """

    target = normalize_for_matching(quote)
    if not target:
        return None
    haystack, indices = _normalized_with_map(text)
    position = haystack.find(target)
    if position < 0:
        words = target.split()
        if len(words) < 4:
            return None
        probe = " ".join(words[: min(6, len(words))])
        position = haystack.find(probe)
        if position < 0:
            return None
        target = probe
    start = indices[position]
    end = indices[position + len(target) - 1] + 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, max(end, start + 1)


def find_quote_offset(text: str, quote: str) -> int | None:
    """Locate a quoted excerpt inside the extracted text, tolerating whitespace drift."""

    span = find_quote_span(text, quote)
    return span[0] if span is not None else None


def quote_still_present(text: str, quote: str, threshold: float = 0.85) -> bool:
    """Decide whether a flagged quote survives in text, for version-comparison evidence.

    An exact (whitespace-tolerant) match is the strong signal. Otherwise the longest run of
    consecutive quote words that survives in order must cover `threshold` of the quote, which
    rejects a short shared opening followed by materially different wording. A single leading
    phrase is deliberately not enough, because "The Agency's aggregate liability is limited to"
    can open sentences that then diverge on the very point that was flagged.
    """

    target = normalize_for_matching(quote)
    if not target:
        return False
    haystack = normalize_for_matching(text)
    if not haystack:
        return False
    if target in haystack:
        return True

    quote_words = target.split()
    if len(quote_words) < 4:
        return haystack.find(target) >= 0
    haystack_words = haystack.split()
    positions: dict[str, list[int]] = {}
    for index, word in enumerate(haystack_words):
        positions.setdefault(word, []).append(index)

    def longest_run(start: int) -> int:
        best = 0
        for first in positions.get(quote_words[start], ()):
            run = 1
            cursor = first
            for offset in range(start + 1, len(quote_words)):
                wanted = quote_words[offset]
                nxt = None
                for candidate in positions.get(wanted, ()):
                    if candidate > cursor:
                        nxt = candidate
                        break
                if nxt is None:
                    break
                cursor = nxt
                run += 1
            if run > best:
                best = run
            if best == len(quote_words) - start:
                break
        return best

    best_run = max(longest_run(start) for start in range(min(len(quote_words), 12)))
    return best_run / len(quote_words) >= threshold


def _locate_body(text: str, body: str, start_hint: int) -> int:
    probe = body[:80]
    position = text.find(probe, start_hint)
    if position >= 0:
        return position
    position = text.find(probe)
    return position if position >= 0 else start_hint


def segment_clauses(document: ExtractedDocument) -> list[Clause]:
    """Split extracted text into clause-level units with source page references."""

    text = document.text
    if not text.strip():
        return []
    pages = document.pages or paginate_text(text)
    spans = build_page_spans(pages)

    boundaries: list[tuple[int, str]] = []
    offset = 0
    for line in text.split("\n"):
        boundaries.append((offset, line))
        offset += len(line) + 1

    starts: list[tuple[int, str]] = []
    for position, (line_offset, line) in enumerate(boundaries):
        # A heading is normally followed by a blank line, so compare against the next
        # line that actually carries text rather than the next physical line.
        following = next(
            (
                next_line
                for _, next_line in boundaries[position + 1 :]
                if next_line.strip()
            ),
            "",
        )
        if _is_heading(line, following):
            starts.append((line_offset, line.strip()))
    if not starts:
        return _chunk_without_headings(text, spans, document.page_reference_kind)
    if len(text[: starts[0][0]].strip()) >= 200:
        starts.insert(0, (0, "Preamble"))

    clauses: list[Clause] = []
    for index, (start_offset, heading) in enumerate(starts):
        end_offset = starts[index + 1][0] if index + 1 < len(starts) else len(text)
        body = text[start_offset:end_offset].strip()[:MAX_CLAUSE_CHARACTERS]
        if not body:
            continue
        resolved_offset = _locate_body(text, body, start_offset)
        clauses.append(
            Clause(
                index=len(clauses) + 1,
                heading=heading[:200],
                text=body,
                page_start=page_for_offset(spans, resolved_offset),
                page_end=page_for_offset(spans, min(len(text) - 1, resolved_offset + len(body))),
                page_reference_kind=document.page_reference_kind,
                start_offset=resolved_offset,
                end_offset=resolved_offset + len(body),
            )
        )
    return clauses


def _chunk_without_headings(
    text: str, spans: list[PageSpan], page_reference_kind: str
) -> list[Clause]:
    paragraphs = [item for item in text.split("\n") if item.strip()]
    if not paragraphs:
        return []
    target = max(1, len(paragraphs) // 6 or 1)
    chunks: list[list[str]] = []
    current: list[str] = []
    for paragraph in paragraphs:
        current.append(paragraph)
        if len(current) >= target:
            chunks.append(current)
            current = []
    if current:
        chunks.append(current)

    clauses: list[Clause] = []
    cursor = 0
    for number, chunk in enumerate(chunks, start=1):
        body = "\n".join(chunk).strip()
        start_offset = _locate_body(text, body, cursor)
        cursor = start_offset + len(body)
        clauses.append(
            Clause(
                index=number,
                heading=f"Section {number}",
                text=body,
                page_start=page_for_offset(spans, start_offset),
                page_end=page_for_offset(spans, min(len(text) - 1, start_offset + len(body))),
                page_reference_kind=page_reference_kind,
                start_offset=start_offset,
                end_offset=start_offset + len(body),
            )
        )
    return clauses
