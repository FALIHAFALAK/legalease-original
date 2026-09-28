from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.models import FINDING_CATEGORIES, FINDING_SEVERITIES, ReviewFinding

WHITESPACE = re.compile(r"\s+")
TOKEN = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset(
    """a an and are as at be been by for from has have in into is it its of on or that the
    to was were will with shall this these those which who whom whose any all not no if then
    than such may can must you your we our they their there here also more most other""".split()
)

OUTCOME_FIXED = "fixed"
OUTCOME_UNRESOLVED = "unresolved"
OUTCOME_CARRIED_OVER = "carried_over"
OUTCOME_NEW = "new"
VALID_OUTCOMES = (OUTCOME_FIXED, OUTCOME_UNRESOLVED, OUTCOME_CARRIED_OVER, OUTCOME_NEW)

# Token-overlap thresholds used to decide whether two findings describe the same concern.
MATCH_THRESHOLD = 0.34
STRONG_MATCH_THRESHOLD = 0.55
CATEGORY_BONUS = 0.18
EVIDENCE_LENGTH = 1200


def tokens(value: str) -> set[str]:
    return {token for token in TOKEN.findall((value or "").lower()) if token not in STOPWORDS}


def normalize(value: str) -> str:
    return WHITESPACE.sub(" ", value or "").strip().lower()


def similarity(left: str, right: str) -> float:
    left_tokens, right_tokens = tokens(left), tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def finding_signature(finding: ReviewFinding | dict[str, Any]) -> str:
    if isinstance(finding, ReviewFinding):
        return " ".join(
            [
                finding.title,
                finding.category,
                finding.excerpt,
                finding.explanation,
            ]
        )
    return " ".join(
        str(finding.get(key, ""))
        for key in ("title", "category", "excerpt", "explanation", "clause_heading")
    )


def same_category(left: str, right: str) -> bool:
    return normalize(left) == normalize(right)


def pair_score(previous: ReviewFinding, candidate: ReviewFinding) -> float:
    base = max(
        similarity(finding_signature(previous), finding_signature(candidate)),
        similarity(previous.excerpt, candidate.excerpt) * 0.9,
    )
    if same_category(previous.category, candidate.category):
        base += CATEGORY_BONUS
    if normalize(previous.clause_heading) and normalize(previous.clause_heading) == normalize(
        candidate.clause_heading
    ):
        base += 0.1
    return base


@dataclass
class MatchingResult:
    pairs: list[tuple[ReviewFinding, ReviewFinding]] = field(default_factory=list)
    unmatched_previous: list[ReviewFinding] = field(default_factory=list)
    unmatched_current: list[ReviewFinding] = field(default_factory=list)
    scores: dict[tuple[int, int], float] = field(default_factory=dict)


def match_findings(
    previous: list[ReviewFinding], current: list[ReviewFinding]
) -> MatchingResult:
    """Greedily pair earlier findings with the most similar findings in the new analysis."""

    result = MatchingResult()
    taken: set[int] = set()
    candidates: list[tuple[float, int, int]] = []
    for previous_index, previous_finding in enumerate(previous):
        for current_index, current_finding in enumerate(current):
            score = pair_score(previous_finding, current_finding)
            if score >= MATCH_THRESHOLD:
                candidates.append((score, previous_index, current_index))
    for score, previous_index, current_index in sorted(candidates, reverse=True):
        if previous_index in taken or current_index in taken:
            continue
        taken.add(previous_index)
        taken.add(current_index)
        result.pairs.append((previous[previous_index], current[current_index]))
        result.scores[(previous[previous_index].id, current[current_index].id)] = score
    result.unmatched_previous = [
        finding for index, finding in enumerate(previous) if index not in taken
    ]
    result.unmatched_current = [
        finding for index, finding in enumerate(current) if index not in taken
    ]
    return result


def sanitize_outcome(value: Any) -> str | None:
    candidate = normalize(str(value or ""))
    if candidate in VALID_OUTCOMES:
        return candidate
    aliases = {
        "resolved": OUTCOME_FIXED,
        "addressed": OUTCOME_FIXED,
        "still_unresolved": OUTCOME_UNRESOLVED,
        "unchanged": OUTCOME_CARRIED_OVER,
        "carried_over": OUTCOME_CARRIED_OVER,
        "newly_introduced": OUTCOME_NEW,
        "new_issue": OUTCOME_NEW,
    }
    return aliases.get(candidate)


def normalize_category(value: Any) -> str:
    candidate = normalize(str(value or ""))
    return candidate if candidate in FINDING_CATEGORIES else "unclear_clause"


def normalize_severity(value: Any) -> str:
    candidate = normalize(str(value or ""))
    return candidate if candidate in FINDING_SEVERITIES else "medium"


def coerce_confidence(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN
        return None
    return round(min(1.0, max(0.0, number)), 3)
