from __future__ import annotations

import html
import re
from typing import Any

from app.providers.base import AIResult, ProviderNotConfiguredError

# Wording that leaves an obligation open to argument. Detection is mechanical: these are
# observations about the text, not conclusions about legal effect.
VAGUE_TERMS = (
    "as appropriate",
    "as reasonably necessary",
    "at its sole discretion",
    "best efforts",
    "from time to time",
    "promptly",
    "reasonable efforts",
    "satisfactory",
    "to be agreed",
    "without undue delay",
)

_TOKEN = re.compile(r"[a-z0-9]+")
_SENTENCE = re.compile(r"(?<=[.;:])\s+|\n+")
_STOPWORDS = frozenset(
    """a an and are as at be been by for from has have in into is it its of on or that the
    to was were will with shall this these those which who whom whose any all not no if then
    than such may can must""".split()
)


def _tokens(value: str) -> set[str]:
    return {token for token in _TOKEN.findall((value or "").lower()) if token not in _STOPWORDS}


def _first_sentence(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return ""
    parts = [part.strip() for part in _SENTENCE.split(cleaned) if part.strip()]
    for part in parts:
        if 40 <= len(part) <= 400:
            return part
    return parts[0][:320] if parts else ""


def _sentence_matching(text: str, pattern: str) -> str:
    """Return the single sentence that triggered an observation.

    Quoting the exact sentence, rather than the opening of the clause, keeps the excerpt
    highlightable and lets a later comparison test whether that wording actually changed.
    The longest match wins so a bare heading such as "8. Governing Law" cannot outrank the
    substantive sentence that follows it.
    """

    best = ""
    for sentence in _SENTENCE.split(re.sub(r"[ \t]+", " ", (text or "").strip())):
        candidate = sentence.strip()
        if not candidate or not re.search(pattern, candidate, re.IGNORECASE):
            continue
        if len(candidate) > len(best):
            best = candidate
    return best[:400]


def _matching_clause(quote: str, clauses: list[dict[str, Any]]) -> dict[str, Any] | None:
    quote_tokens = _tokens(quote)
    if not quote_tokens:
        return None
    best: dict[str, Any] | None = None
    best_score = 0.0
    for clause in clauses:
        clause_tokens = _tokens(str(clause.get("text", "")))
        if not clause_tokens:
            continue
        score = len(quote_tokens & clause_tokens) / len(quote_tokens)
        if score > best_score:
            best_score = score
            best = clause
    return best if best_score >= 0.5 else None


def _classify_against_revision(
    quote: str, heading: str, current_text: str, current_clauses: list[dict[str, Any]]
) -> tuple[str, str, int]:
    """Decide whether an earlier concern is still present, using text evidence only."""

    if not quote.strip():
        return "carried_over", "The earlier finding had no quoted text, so it could not be verified against the revision and is retained.", 0
    normalized_quote = re.sub(r"\s+", " ", quote).strip().lower()
    normalized_text = re.sub(r"\s+", " ", current_text).strip().lower()
    if normalized_quote in normalized_text:
        clause = _matching_clause(quote, current_clauses)
        citation = f" (clause {clause.get('heading')})" if clause else ""
        clause_index = int(clause.get("index", 0)) if clause else 0
        return (
            "unresolved",
            f"The wording flagged earlier is still present in the revised text{citation}: “{quote[:200]}”.",
            clause_index,
        )
    quote_tokens = _tokens(quote)
    revised_tokens = _tokens(current_text)
    if quote_tokens and len(quote_tokens & revised_tokens) / len(quote_tokens) >= 0.75:
        clause = _matching_clause(quote, current_clauses)
        replacement = _first_sentence(str(clause.get("text", ""))) if clause else ""
        clause_index = int(clause.get("index", 0)) if clause else 0
        clause_name = f" in clause {clause.get('heading')}" if clause else ""
        if replacement:
            evidence = (
                f"The exact wording was reworded, so most of the flagged terms remain{clause_name}. "
                f'The revised clause reads: "{replacement[:200]}".'
            )
        else:
            evidence = (
                f"The exact wording was reworded, so most of the flagged terms remain{clause_name}."
            )
        return "unresolved", evidence, clause_index
    clause = _matching_clause(quote, current_clauses) or _clause_by_heading(heading, current_clauses)
    clause_index = int(clause.get("index", 0)) if clause else 0
    replacement = _first_sentence(str(clause.get("text", ""))) if clause else ""
    if replacement:
        evidence = (
            "The wording quoted in the earlier version no longer appears in the revised text. "
            f'The nearest revised clause now reads: "{replacement[:200]}".'
        )
    else:
        evidence = "The wording quoted in the earlier version no longer appears anywhere in the revised text."
    return "fixed", evidence, clause_index


def _clause_by_heading(heading: str, clauses: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not heading:
        return None
    target = re.sub(r"\s+", " ", heading).strip().lower()
    for clause in clauses:
        candidate = re.sub(r"\s+", " ", str(clause.get("heading", ""))).strip().lower()
        if candidate and (candidate == target or target in candidate or candidate in target):
            return clause
    return None


# --------------------------------------------------------------------------- structural checks
#
# Each check reads one clause's own wording and returns an observation only when the
# text shows a concrete drafting gap. They are intentionally narrow: the point is to give
# local development a realistic, reproducible signal, never to reach a legal conclusion.

_NUMERIC_DAYS = re.compile(r"\b(\d{2,3})\s*(?:calendar\s+|business\s+)?days\b")
_LONG_PAYMENT_DAYS = 60


def _check_long_payment_period(
    clause: dict[str, Any],
    text: str,
    quote: str,
    heading: str,
    clauses: list[dict[str, Any]],
    combined: str,
) -> dict[str, Any] | None:
    lowered = text.lower()
    if "pay" not in lowered and "invoice" not in lowered and "payment" not in lowered:
        return None
    days = [int(value) for value in _NUMERIC_DAYS.findall(lowered)]
    longest = max(days) if days else 0
    if longest <= _LONG_PAYMENT_DAYS:
        return None
    trigger = _sentence_matching(text, rf"\b{longest}\s*(?:calendar\s+|business\s+)?days\b") or quote
    return {
        "clause_index": clause.get("index"),
        "quote": trigger,
        "title": f"Payment period of {longest} days in {heading}",
        "category": "unusual_obligation",
        "severity": "medium",
        "explanation": (
            f"The clause allows {longest} days before an invoice falls due, and the extracted text "
            "does not shorten that period anywhere else. A long payment window shifts working capital "
            "and delay risk onto whichever party has to fund the work."
        ),
        "severity_explanation": (
            f"Medium: {longest} days is not unusual in isolation, but the figure is well beyond the "
            "30 days most counterparties expect, so it should be a deliberate choice."
        ),
        "suggested_wording": (
            f'Shorten the period, for example: "The Client shall pay each invoice within 30 days of '
            f'the invoice date." (The current text allows {longest} days.)'
        ),
        "suggested_question": f"Is a {longest}-day payment period intended, and can it be reduced to 30 days?",
        "confidence": 0.65,
    }


def _check_non_refundable_fee(
    clause: dict[str, Any],
    text: str,
    quote: str,
    heading: str,
    clauses: list[dict[str, Any]],
    combined: str,
) -> dict[str, Any] | None:
    if "non-refundable" not in text.lower() and "non refundable" not in text.lower():
        return None
    trigger = (
        _sentence_matching(text, r"non[\s-]?refundable") or quote
    )
    return {
        "clause_index": clause.get("index"),
        "quote": trigger,
        "title": f"Fee is non-refundable in {heading}",
        "category": "unusual_obligation",
        "severity": "medium",
        "explanation": (
            "The clause makes the fee non-refundable without tying that consequence to a specific "
            "trigger such as a breach, a missed milestone, or a completed deliverable. As drafted, "
            "the wording does not say what the payer gets in return for losing the money."
        ),
        "severity_explanation": (
            "Medium: non-refundability is common, but an unconditioned version removes the payer's "
            "leverage if the work stalls, so it deserves a deliberate decision."
        ),
        "suggested_wording": (
            'Attach the consequence to an objective event, for example: "Fees paid are non-refundable '
            'once the Agency has commenced work and delivered the agreed design stage."'
        ),
        "suggested_question": "What event must occur before the fee becomes non-refundable?",
        "confidence": 0.6,
    }


def _check_uncapped_liability_exclusion(
    clause: dict[str, Any],
    text: str,
    quote: str,
    heading: str,
    clauses: list[dict[str, Any]],
    combined: str,
) -> dict[str, Any] | None:
    lowered = text.lower()
    if "consequential loss" not in lowered and "indirect" not in lowered:
        return None
    if any(word in lowered for word in ("fraud", "fraudulent misrepresentation", "personal injury")):
        return None
    trigger = _sentence_matching(text, r"consequential loss|indirect or consequential") or quote
    return {
        "clause_index": clause.get("index"),
        "quote": trigger,
        "title": f"Loss exclusion with no carve-out in {heading}",
        "category": "unusual_obligation",
        "severity": "high",
        "explanation": (
            "The clause excludes indirect and consequential loss but the same clause states no "
            "exception. Read literally the exclusion also covers liability that the law would not "
            "normally permit a party to exclude, such as fraud or personal injury."
        ),
        "severity_explanation": (
            "High: an unqualified exclusion is vulnerable, and the party relying on it may find it "
            "does not apply to the claims it was written for."
        ),
        "suggested_wording": (
            'Add: "The limitations in this clause do not apply to fraud, fraudulent misrepresentation, '
            'death or personal injury caused by negligence, or any other liability that cannot '
            'lawfully be limited."'
        ),
        "suggested_question": "Should the loss exclusion be subject to the standard carve-outs?",
        "confidence": 0.7,
    }


def _check_fees_only_liability_cap(
    clause: dict[str, Any],
    text: str,
    quote: str,
    heading: str,
    clauses: list[dict[str, Any]],
    combined: str,
) -> dict[str, Any] | None:
    lowered = text.lower()
    if "limited to the total fees paid" not in lowered and "limited to the fees paid" not in lowered:
        return None
    if re.search(r"greater of|or\s+(?:gbp|usd|eur|£|\$)\s*[\d,]+", lowered):
        return None
    trigger = _sentence_matching(text, r"limited to the (?:total )?fees paid") or quote
    return {
        "clause_index": clause.get("index"),
        "quote": trigger,
        "title": f"Liability capped at fees paid only in {heading}",
        "category": "inconsistent_detail",
        "severity": "medium",
        "explanation": (
            "The cap is expressed only as an amount of fees the paying party has already handed over. "
            "Where very little has been paid the cap is correspondingly tiny, which can leave the "
            "other party exposed on a claim much larger than the payments received so far."
        ),
        "severity_explanation": (
            "Medium: the cap is enforceable in principle, but a cap that falls to zero early in the "
            "engagement is rarely what either party intends."
        ),
        "suggested_wording": (
            'Use a floor as well, for example: "limited to the greater of the total fees paid in the '
            'preceding 6 months or GBP 100,000."'
        ),
        "suggested_question": "Should the liability cap include a minimum amount?",
        "confidence": 0.6,
    }


def _check_governing_law_without_forum(
    clause: dict[str, Any],
    text: str,
    quote: str,
    heading: str,
    clauses: list[dict[str, Any]],
    combined: str,
) -> dict[str, Any] | None:
    lowered = text.lower()
    if "governed by" not in lowered and "governing law" not in lowered:
        return None
    if "exclusive" in combined and "jurisdiction" in combined:
        return None
    trigger = _sentence_matching(text, r"governed by|governing law") or quote
    return {
        "clause_index": clause.get("index"),
        "quote": trigger,
        "title": f"Governing law stated without a forum in {heading}",
        "category": "missing_information",
        "severity": "medium",
        "explanation": (
            "The clause names a system of law, but nothing in the extracted text says which courts "
            "have jurisdiction. Where the parties are in different countries, the applicable rules "
            "and the court that would hear a dispute are then two separate open questions."
        ),
        "severity_explanation": (
            "Medium: the choice of law is stated, so the gap is about forum rather than about the "
            "substantive rules, and is usually closed with one sentence."
        ),
        "suggested_wording": (
            'Add: "and the parties submit to the exclusive jurisdiction of the courts of [jurisdiction]."'
        ),
        "suggested_question": "Which courts should have jurisdiction over a dispute?",
        "confidence": 0.6,
    }


def _check_one_sided_termination(
    clause: dict[str, Any],
    text: str,
    quote: str,
    heading: str,
    clauses: list[dict[str, Any]],
    combined: str,
) -> dict[str, Any] | None:
    lowered = text.lower()
    if "may terminate" not in lowered:
        return None
    party = ""
    for name in re.findall(r"\bthe\s+([a-z]+)\s+may\s+terminate\b", lowered):
        party = name
    if not party:
        return None
    others = {
        other
        for other in re.findall(r"\bthe\s+([a-z]+)\s+may\s+terminate\b", combined)
        if other != party
    }
    if others:
        return None
    trigger = _sentence_matching(text, rf"the\s+{party}\s+may\s+terminate") or quote
    return {
        "clause_index": clause.get("index"),
        "quote": trigger,
        "title": f"Only one party can terminate in {heading}",
        "category": "inconsistent_detail",
        "severity": "medium",
        "explanation": (
            f"The extracted text gives {party} a right to terminate on notice, but no matching right "
            f"for the other party. The same agreement is therefore not symmetrical on exit, and the "
            "party without the right is exposed to being held to it for the full term."
        ),
        "severity_explanation": (
            "Medium: one-sided termination rights are common in vendor contracts, but the asymmetry "
            "should be a decision of the party granting it rather than an accident of drafting."
        ),
        "suggested_wording": (
            'Consider a matching right, for example: "Either party may terminate this Agreement on '
            '30 days written notice to the other."'
        ),
        "suggested_question": "Should the other party have a matching termination right?",
        "confidence": 0.6,
    }


def _check_undefined_term(
    clause: dict[str, Any],
    text: str,
    quote: str,
    heading: str,
    clauses: list[dict[str, Any]],
    combined: str,
) -> dict[str, Any] | None:
    vague = sorted({term for term in VAGUE_TERMS if term in text.lower()})
    if not vague:
        return None
    if re.search(r"\b\d", text):
        # The clause carries at least one measurable anchor, so the soft wording is
        # not standing on its own.
        return None
    trigger = _sentence_matching(text, r"|".join(re.escape(term) for term in vague)) or quote
    return {
        "clause_index": clause.get("index"),
        "quote": trigger,
        "title": f"Undefined term in {heading}",
        "category": "ambiguous_wording",
        "severity": "medium",
        "explanation": (
            f"The wording relies on {', '.join(repr(term) for term in vague[:3])}, and the clause sets "
            "no measurable period, threshold, or test. A reader cannot tell from the text alone when "
            "the obligation is due or what counts as sufficient performance."
        ),
        "severity_explanation": (
            "Medium: the clause is not necessarily objectionable, but the absence of an objective "
            "anchor leaves the parties arguing about standard of performance."
        ),
        "suggested_wording": (
            "Replace the undefined wording with a measurable standard, for example "
            '"within 15 Business Days after written notice", and state who decides.'
        ),
        "suggested_question": "Which measurable deadline or threshold should replace this wording?",
        "confidence": 0.55,
    }


_STRUCTURAL_CHECKS = (
    _check_long_payment_period,
    _check_non_refundable_fee,
    _check_uncapped_liability_exclusion,
    _check_fees_only_liability_cap,
    _check_governing_law_without_forum,
    _check_one_sided_termination,
    _check_undefined_term,
)


class MockAIProvider:
    name = "mock"
    model = "deterministic-development-draft"

    def generate_document(
        self, template: dict[str, Any], fields: dict[str, Any], jurisdiction: str | None
    ) -> AIResult:
        title = str(fields.get("document_title") or template.get("name") or "LegalEase draft")
        missing = [
            str(item.get("label") or item.get("name") or "Required information").lower()
            for item in template.get("fields", [])
            if item.get("required") and not fields.get(item.get("name", ""))
        ]
        sections = list(
            template.get("sections") or ["Purpose and scope", "Terms", "General provisions"]
        )
        rendered: list[str] = []
        for index, section in enumerate(sections, start=1):
            detail_fields = [
                str(item.get("label"))
                for item in template.get("fields", [])
                if fields.get(item.get("name", ""))
            ]
            detail = ", ".join(detail_fields[:4]) if detail_fields else "the information provided"
            rendered.append(
                f"<h2>{index}. {html.escape(section)}</h2>"
                f"<p>This development draft provides a starting point for <strong>{html.escape(section.lower())}</strong> based on {html.escape(detail)}. "
                "Replace bracketed prompts and obtain qualified legal review before signing or relying on this document.</p>"
            )
        content = "".join(rendered)
        data = {
            "title": title,
            "content": content,
            "sections": sections,
            "jurisdiction": jurisdiction or "Not specified",
            "missing_information": missing,
            "assumptions": [
                "This is an AI-assisted starting point, not a completed legal instrument.",
                "The draft assumes the parties will review commercial and legal terms together.",
            ],
            "review_notes": [
                "Confirm names, dates, payment terms, termination rights, and governing law.",
                "Have a qualified lawyer review the document for your jurisdiction and circumstances.",
            ],
        }
        return AIResult(data=data, provider=self.name, model=self.model, raw_text="mock-generated")

    def answer_question(
        self, question: str, context: str = "", history: list[dict[str, str]] | None = None
    ) -> AIResult:
        raise ProviderNotConfiguredError(
            "The assistant is running in mock mode and cannot answer legal questions. "
            "Set AI_PROVIDER=gemini and GEMINI_API_KEY, then restart the API."
        )

    def review_document(self, text: str, filename: str = "uploaded document") -> AIResult:
        excerpt = re.sub(r"\s+", " ", text).strip()[:240]
        findings = [
            {
                "category": "professional_review",
                "severity": "high",
                "excerpt": excerpt,
                "explanation": "Automated review cannot determine whether this document is valid, enforceable, safe, or compliant.",
                "suggested_question": "Which provisions should a qualified lawyer review before signature?",
            },
            {
                "category": "missing_information",
                "severity": "medium",
                "excerpt": "",
                "explanation": "Confirm that all parties, dates, payment obligations, termination terms, and governing law are complete.",
                "suggested_question": "Are the commercial and legal terms complete and consistent across every section?",
            },
        ]
        if len(text.split()) < 80:
            findings.append(
                {
                    "category": "unclear_clause",
                    "severity": "medium",
                    "excerpt": excerpt,
                    "explanation": "The extracted text is short or incomplete; confirm that the upload contains the full document.",
                    "suggested_question": "Does this upload include all pages, schedules, and signature blocks?",
                }
            )
        return AIResult(
            data={
                "summary": "The document was received and assessed for general drafting risks. This is not a legal validity determination.",
                "findings": findings,
            },
            provider=self.name,
            model=self.model,
        )

    def explain_clause(self, clause: str, context: str = "") -> AIResult:
        answer = (
            "In plain English, this clause should be read as a commitment that may create obligations, permissions, or limits. "
            "The exact effect depends on the surrounding definitions and the governing law. Ask a lawyer to explain any term that affects your rights."
        )
        return AIResult(data={"explanation": answer}, provider=self.name, model=self.model)

    def analyze_clauses(
        self,
        clauses: list[dict[str, Any]],
        filename: str = "uploaded document",
        context: str = "",
    ) -> AIResult:
        """Deterministic, text-derived structural observations for local development only.

        Every item below is produced by inspecting the uploaded text. Nothing is asserted about
        legal validity, and no canned conclusion is attached to any document.
        """

        if not clauses:
            raise ProviderNotConfiguredError(
                "No clause text was available to analyse. Configure Gemini for full clause review."
            )
        combined = " ".join(str(item.get("text", "")) for item in clauses).lower()
        findings: list[dict[str, Any]] = []
        for clause in clauses:
            text = str(clause.get("text", ""))
            quote = _first_sentence(text)
            if not quote:
                continue
            heading = str(clause.get("heading") or "the clause")
            for build in _STRUCTURAL_CHECKS:
                finding = build(clause, text, quote, heading, clauses, combined)
                if finding is not None:
                    findings.append(finding)
        if not re.search(r"governing law|governed by|jurisdiction", combined):
            findings.append(
                {
                    "clause_index": clauses[0].get("index"),
                    "quote": _first_sentence(str(clauses[0].get("text", ""))) or str(clauses[0].get("heading", "")),
                    "title": "No governing law identified in the extracted text",
                    "category": "missing_information",
                    "severity": "high",
                    "explanation": (
                        "The extracted text does not state a governing law or jurisdiction. Which "
                        "rules apply to interpretation, and to any dispute mechanism, therefore "
                        "cannot be read from this document."
                    ),
                    "severity_explanation": (
                        "High: the applicable legal framework is unstated, so every other clause "
                        "has to be read under an unknown assumption."
                    ),
                    "suggested_wording": (
                        'Add: "This Agreement is governed by the laws of [jurisdiction], without '
                        'regard to conflict-of-law rules, and the parties submit to the exclusive '
                        'courts of [jurisdiction]."'
                    ),
                    "suggested_question": "Which jurisdiction should govern this agreement?",
                    "confidence": 0.6,
                }
            )
        findings.append(
            {
                "clause_index": clauses[0].get("index"),
                "quote": _first_sentence(str(clauses[0].get("text", ""))) or str(clauses[0].get("heading", "")),
                "title": "Qualified legal review required before reliance",
                "category": "professional_review",
                "severity": "high",
                "explanation": (
                    "Automated clause review cannot determine whether this document is valid, "
                    "enforceable, safe, or compliant in any jurisdiction. A qualified lawyer "
                    "should confirm the commercial and legal terms before signature."
                ),
                "severity_explanation": (
                    "High: the limitation applies to every finding in this review, including the "
                    "structural observations above."
                ),
                "suggested_wording": "",
                "suggested_question": (
                    "Which provisions should a qualified lawyer review before this is signed?"
                ),
                "confidence": 0.9,
            }
        )
        return AIResult(
            data={
                "summary": (
                    f"{len(clauses)} clause(s) were extracted from {filename[:120]} and screened for "
                    "structural drafting gaps. This is a development-mode screening pass and is not "
                    "a legal validity determination."
                ),
                "findings": findings,
            },
            provider=self.name,
            model=self.model,
            raw_text="mock-clause-analysis",
        )

    def compare_versions(
        self,
        previous_findings: list[dict[str, Any]],
        previous_text: str,
        current_text: str,
        current_clauses: list[dict[str, Any]],
    ) -> AIResult:
        """Deterministic text-evidence comparison used for local development and tests."""

        items: list[dict[str, Any]] = []
        for finding in previous_findings:
            quote = str(finding.get("excerpt", ""))
            outcome, evidence, clause_index = _classify_against_revision(
                quote, str(finding.get("clause_heading", "")), current_text, current_clauses
            )
            items.append(
                {
                    "previous_finding_id": finding.get("id"),
                    "outcome": outcome,
                    "clause_index": clause_index,
                    "title": finding.get("title", ""),
                    "category": finding.get("category", "unclear_clause"),
                    "severity": finding.get("severity", "medium"),
                    "evidence": evidence,
                    "summary": (
                        "The wording flagged in the earlier version is still present in the revised text."
                        if outcome in {"unresolved", "carried_over"}
                        else "The earlier wording is no longer present in the revised text."
                    ),
                }
            )
        return AIResult(
            data={"findings": items},
            provider=self.name,
            model=self.model,
            raw_text="mock-version-comparison",
        )

    def answer_finding_question(
        self,
        finding: dict[str, Any],
        question: str,
        clause_text: str = "",
        history: list[dict[str, str]] | None = None,
        request_revision: bool = False,
    ) -> AIResult:
        raise ProviderNotConfiguredError(
            "Clause questions are running in mock mode and cannot be answered. "
            "Set AI_PROVIDER=gemini and GEMINI_API_KEY, then restart the API."
        )

    def check_connection(self) -> tuple[bool, str]:
        return True, "The deterministic mock provider is ready for local development."
