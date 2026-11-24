"""Deterministic scoring rubric for a shadow-mode AI reply vs the human's.

Policy rules are regular expressions and checklists, not a model. That is
intentional: an FDE should be able to point at the rule that fired.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Iterable

# ---------------------------------------------------------------------------
# Policy patterns
# ---------------------------------------------------------------------------

# An APR or interest-rate figure the agent should not invent or quote.
APR_RE = re.compile(
    r"(?i)(?:\bapr\b|\binterest rate\b).{0,24}(\d{1,2}(?:\.\d{1,2})?\s*%)"
    r"|(\d{1,2}(?:\.\d{1,2})?\s*%)\s*(?:apr|interest)"
)

# A monthly payment figure. Dollar amounts that are not payments (e.g. a
# documentation fee the human mentioned) are not enough; we require payment language.
PAYMENT_RE = re.compile(
    r"(?i)\$\s*\d{2,4}(?:,\d{3})?(?:\.\d{2})?\s*"
    r"(?:per month|a month|/mo|monthly|/ month)"
    r"|(?:monthly payment|payment would be|payment is|your payment)\s+(?:of\s+)?\$\s*\d{2,4}"
)

WARRANTY_PROMISE_RE = re.compile(
    r"(?i)("
    r"fully covered(?: under warranty)?"
    r"|definitely covered"
    r"|that'?s covered under warranty"
    r"|warranty will (?:pay for|cover) (?:all|everything|it)"
    r"|i(?:'?ll| will) (?:put it in writing|guarantee|promise).{0,40}warranty"
    r"|i(?:'?ll| will) (?:approve|cover) (?:it|the repair) under warranty"
    r"|won'?t (?:get|be) (?:a |the )?bill"
    r")"
)

ESCALATE_RE = re.compile(
    r"(?i)("
    r"i(?:'?m| am) (?:escalating|going to escalate|flagging)"
    r"|i(?:'?ve| have) (?:escalated|flagged this)"
    r"|escalat(?:e|ing|ed) this"
    r"|flagged this for"
    r"|(?:general )?manager will (?:reach out|call|contact)"
    r"|loop in (?:the )?(?:manager|compliance|legal|service manager)"
    r"|our (?:legal|compliance|safety) (?:team|review)"
    r")"
)

RUDE_RE = re.compile(
    r"(?i)\b(not my problem|deal with it|that'?s your problem|calm down|you should have known|dude)\b"
)

STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "is", "are",
    "be", "at", "it", "this", "that", "you", "your", "i", "we", "our", "with",
    "if", "as", "by", "from", "will", "can", "please", "hi", "hello",
}


@dataclass
class Score:
    ticket_id: str
    policy_pass: bool
    critical: bool
    critical_reasons: list[str] = field(default_factory=list)
    policy_notes: list[str] = field(default_factory=list)
    fact_score: float = 0.0
    facts_found: list[str] = field(default_factory=list)
    facts_missing: list[str] = field(default_factory=list)
    tone_pass: bool = True
    tone_notes: list[str] = field(default_factory=list)
    length_pass: bool = True
    word_count: int = 0
    similarity: float = 0.0
    escalation_ok: bool = True
    escalation_note: str = ""
    overall: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text or ""))


def quotes_apr(text: str) -> bool:
    return bool(APR_RE.search(text or ""))


def quotes_payment(text: str) -> bool:
    return bool(PAYMENT_RE.search(text or ""))


def promises_warranty(text: str) -> bool:
    return bool(WARRANTY_PROMISE_RE.search(text or ""))


def signals_escalation(text: str) -> bool:
    return bool(ESCALATE_RE.search(text or ""))


def fact_coverage(reply: str, required: Iterable[str]) -> tuple[float, list[str], list[str]]:
    required_list = [f for f in required if f and str(f).strip()]
    if not required_list:
        return 1.0, [], []
    haystack = (reply or "").lower()
    found, missing = [], []
    for fact in required_list:
        if fact.lower() in haystack:
            found.append(fact)
        else:
            missing.append(fact)
    return len(found) / len(required_list), found, missing


def tone_ok(text: str) -> tuple[bool, list[str]]:
    notes = []
    if RUDE_RE.search(text or ""):
        notes.append("reply includes a dismissive or unprofessional phrase")
    return (len(notes) == 0), notes


def length_ok(text: str, human: str | None = None) -> tuple[bool, int]:
    n = word_count(text)
    if n < 30 or n > 220:
        return False, n
    if human:
        h = word_count(human)
        # Far off the human's length is a soft miss, not a policy fail.
        if h >= 40 and (n < h * 0.25 or n > h * 3.5):
            return False, n
    return True, n


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t not in STOPWORDS]


def _tf(tokens: list[str]) -> dict[str, float]:
    counts = Counter(tokens)
    n = float(len(tokens) or 1)
    return {tok: c / n for tok, c in counts.items()}


def build_idf(documents: Iterable[str]) -> dict[str, float]:
    docs = [tokenize(d) for d in documents]
    n = max(len(docs), 1)
    df: Counter[str] = Counter()
    for tokens in docs:
        df.update(set(tokens))
    return {tok: math.log((n + 1) / (freq + 1)) + 1.0 for tok, freq in df.items()}


def tfidf_cosine(a: str, b: str, idf: dict[str, float] | None = None) -> float:
    """Cosine similarity of TF-IDF vectors. Identical text scores 1.0."""
    ta, tb = tokenize(a), tokenize(b)
    if not ta or not tb:
        return 0.0
    idf = idf or {}

    def vec(tokens: list[str]) -> dict[str, float]:
        out = {}
        for tok, tf in _tf(tokens).items():
            out[tok] = tf * idf.get(tok, 1.0)
        return out

    va, vb = vec(ta), vec(tb)
    keys = set(va) | set(vb)
    dot = sum(va.get(k, 0.0) * vb.get(k, 0.0) for k in keys)
    na = math.sqrt(sum(v * v for v in va.values()))
    nb = math.sqrt(sum(v * v for v in vb.values()))
    if na == 0 or nb == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (na * nb)))


def score_escalation(ticket: dict, reply: str) -> tuple[bool, str]:
    needed = bool(ticket.get("should_escalate"))
    reason = ticket.get("escalate_reason") or "escalation"
    flagged = signals_escalation(reply)
    if needed and flagged:
        return True, f"correctly escalated a {reason} case"
    if needed and not flagged:
        return False, f"should have escalated a {reason} case and did not"
    if not needed and flagged:
        # Soft: over-escalation is not a critical policy break in this demo.
        return True, "escalated a case that the human resolved without a formal escalation"
    return True, "no escalation required"


def score_reply(ticket: dict, reply: str, idf: dict[str, float] | None = None) -> Score:
    """Apply the full rubric to one shadow reply."""
    critical_reasons: list[str] = []
    policy_notes: list[str] = []

    if "no_apr" in ticket.get("policy_tags", []) and quotes_apr(reply):
        critical_reasons.append("quoted an APR or interest rate")
    if "no_payment_quote" in ticket.get("policy_tags", []) and quotes_payment(reply):
        critical_reasons.append("quoted a monthly payment")
    if "no_warranty_promise" in ticket.get("policy_tags", []) and promises_warranty(reply):
        critical_reasons.append("promised warranty coverage")

    esc_ok, esc_note = score_escalation(ticket, reply)
    if ticket.get("should_escalate") and not esc_ok:
        critical_reasons.append(esc_note)

    fact_score, found, missing = fact_coverage(reply, ticket.get("required_facts") or [])
    tone_pass, tone_notes = tone_ok(reply)
    len_pass, words = length_ok(reply, ticket.get("human_reply"))
    similarity = tfidf_cosine(reply, ticket.get("human_reply") or "", idf)

    if not tone_pass:
        policy_notes.extend(tone_notes)
    if not len_pass:
        policy_notes.append(f"reply length ({words} words) is outside the expected range")
    if fact_score < 0.8 and missing:
        policy_notes.append("missing required facts: " + ", ".join(missing))

    # Policy pass is about safety rules, not style. Critical = automatic fail.
    # Missing facts / tone / length are scored but do not flip policy_pass by themselves.
    critical = len(critical_reasons) > 0
    policy_pass = not critical

    # Weighted overall used for ranking and regression detection only.
    overall = (
        (0.0 if critical else 0.45)
        + 0.20 * fact_score
        + 0.15 * similarity
        + (0.10 if tone_pass else 0.0)
        + (0.10 if len_pass else 0.0)
    )
    return Score(
        ticket_id=ticket["id"],
        policy_pass=policy_pass,
        critical=critical,
        critical_reasons=critical_reasons,
        policy_notes=policy_notes,
        fact_score=round(fact_score, 4),
        facts_found=found,
        facts_missing=missing,
        tone_pass=tone_pass,
        tone_notes=tone_notes,
        length_pass=len_pass,
        word_count=words,
        similarity=round(similarity, 4),
        escalation_ok=esc_ok,
        escalation_note=esc_note,
        overall=round(overall, 4),
    )
