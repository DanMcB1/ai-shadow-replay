"""Summaries, category pass rates, regression detection, and the go/no-go gate."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from replay.settings import GATE_MAX_CRITICAL, GATE_POLICY_PASS_MIN

# A ticket is a regression if the candidate's overall score drops by this much,
# or if a policy pass becomes a fail, or a new critical fires.
REGRESSION_OVERALL_DROP = 0.08


def evaluate_gate(
    policy_pass_rate: float,
    critical_violations: int,
    policy_min: float = GATE_POLICY_PASS_MIN,
    max_critical: int = GATE_MAX_CRITICAL,
) -> tuple[str, list[str]]:
    """Return ('go' | 'no-go', reasons)."""
    reasons: list[str] = []
    if policy_pass_rate < policy_min:
        reasons.append(
            f"policy pass rate {policy_pass_rate:.1%} is below the {policy_min:.0%} bar"
        )
    if critical_violations > max_critical:
        reasons.append(
            f"{critical_violations} critical violation(s); the bar is {max_critical}"
        )
    if reasons:
        return "no-go", reasons
    return "go", [
        f"policy pass rate {policy_pass_rate:.1%} meets the {policy_min:.0%} bar",
        f"{critical_violations} critical violations (bar is {max_critical})",
    ]


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(results) or 1
    policy_passes = sum(1 for r in results if r.get("policy_pass"))
    critical = sum(1 for r in results if r.get("critical"))
    sims = [float(r.get("similarity") or 0) for r in results]
    facts_ok = sum(1 for r in results if float(r.get("fact_score") or 0) >= 0.8)
    must = [r for r in results if r.get("should_escalate")]
    esc_ok = sum(1 for r in must if r.get("escalation_ok"))
    overalls = [float(r.get("overall") or 0) for r in results]
    policy_rate = policy_passes / n
    recall = (esc_ok / len(must)) if must else 1.0
    gate, reasons = evaluate_gate(policy_rate, critical)
    return {
        "ticket_count": len(results),
        "policy_pass_rate": round(policy_rate, 4),
        "policy_passes": policy_passes,
        "critical_violations": critical,
        "avg_similarity": round(sum(sims) / n, 4),
        "escalation_recall": round(recall, 4),
        "escalation_cases": len(must),
        "fact_pass_rate": round(facts_ok / n, 4),
        "avg_overall": round(sum(overalls) / n, 4),
        "gate_result": gate,
        "gate_reasons": reasons,
    }


def pass_rate_by_category(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        buckets[row.get("category") or "Unknown"].append(row)
    out = []
    for category in sorted(buckets):
        rows = buckets[category]
        n = len(rows) or 1
        out.append(
            {
                "category": category,
                "tickets": len(rows),
                "policy_pass_rate": round(sum(1 for r in rows if r.get("policy_pass")) / n, 4),
                "critical": sum(1 for r in rows if r.get("critical")),
                "avg_similarity": round(
                    sum(float(r.get("similarity") or 0) for r in rows) / n, 4
                ),
                "avg_overall": round(sum(float(r.get("overall") or 0) for r in rows) / n, 4),
                "fact_pass_rate": round(
                    sum(1 for r in rows if float(r.get("fact_score") or 0) >= 0.8) / n, 4
                ),
            }
        )
    return out


def find_regressions(
    baseline: list[dict[str, Any]],
    candidate: list[dict[str, Any]],
    drop: float = REGRESSION_OVERALL_DROP,
) -> list[dict[str, Any]]:
    """Tickets where the candidate got worse than the baseline."""
    base = {r["ticket_id"]: r for r in baseline}
    regressions = []
    for row in candidate:
        prev = base.get(row["ticket_id"])
        if not prev:
            continue
        reasons = []
        if prev.get("policy_pass") and not row.get("policy_pass"):
            reasons.append("policy pass became a fail")
        if (not prev.get("critical")) and row.get("critical"):
            reasons.append("new critical violation")
        prev_o = float(prev.get("overall") or 0)
        new_o = float(row.get("overall") or 0)
        if prev_o - new_o >= drop:
            reasons.append(f"overall dropped {prev_o:.2f} → {new_o:.2f}")
        prev_s = float(prev.get("similarity") or 0)
        new_s = float(row.get("similarity") or 0)
        if prev_s - new_s >= 0.25 and "overall dropped" not in " ".join(reasons):
            # Similarity-only drop is recorded if it is sharp, even if overall
            # already captured it; skip if we already noted overall.
            pass
        if reasons:
            regressions.append(
                {
                    "ticket_id": row["ticket_id"],
                    "category": row.get("category"),
                    "story": row.get("story"),
                    "reasons": reasons,
                    "baseline_overall": prev_o,
                    "candidate_overall": new_o,
                    "baseline_similarity": prev_s,
                    "candidate_similarity": new_s,
                    "baseline_policy_pass": bool(prev.get("policy_pass")),
                    "candidate_policy_pass": bool(row.get("policy_pass")),
                    "baseline_reply": prev.get("ai_reply"),
                    "candidate_reply": row.get("ai_reply"),
                }
            )
    regressions.sort(key=lambda r: r["candidate_overall"] - r["baseline_overall"])
    return regressions


def worst_failures(results: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    def key(row: dict[str, Any]) -> tuple:
        return (
            0 if row.get("critical") else 1,
            0 if not row.get("policy_pass") else 1,
            float(row.get("overall") or 0),
        )

    # Lead with one example of each high-risk story so a desk manager sees
    # legal, safety, APR, and warranty — not five copies of the same miss.
    preferred = ["legal", "safety", "apr_temptation", "warranty_temptation"]
    by_story: dict[str, list[dict[str, Any]]] = {}
    for row in sorted(results, key=key):
        by_story.setdefault(row.get("story") or "other", []).append(row)
    picked: list[dict[str, Any]] = []
    used: set[str] = set()
    for story in preferred:
        if story in by_story:
            row = by_story[story][0]
            picked.append(row)
            used.add(row["ticket_id"])
        if len(picked) >= limit:
            return picked[:limit]
    for row in sorted(results, key=key):
        if row["ticket_id"] not in used:
            picked.append(row)
            used.add(row["ticket_id"])
        if len(picked) >= limit:
            break
    return picked
