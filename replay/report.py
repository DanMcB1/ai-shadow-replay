"""Export a replay or a v1-vs-v2 comparison as Markdown or CSV."""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import Any

from replay.compare import find_regressions, pass_rate_by_category, summarize, worst_failures
from replay.settings import COMPANY, GATE_MAX_CRITICAL, GATE_POLICY_PASS_MIN


def _pct(value: float) -> str:
    return f"{value:.1%}"


def markdown_report(
    *,
    baseline: dict[str, Any],
    candidate: dict[str, Any] | None = None,
    tickets_by_id: dict[str, dict] | None = None,
) -> str:
    b_sum = baseline.get("summary") or summarize(baseline["results"])
    lines = [
        f"# Shadow replay report — {COMPANY}",
        "",
        "This is a **portfolio demo** report. The tickets are fictional, the agents "
        "are local mocks, and no customer ever saw these AI replies.",
        "",
        f"## Gate (bar: policy pass ≥ {GATE_POLICY_PASS_MIN:.0%}, critical ≤ {GATE_MAX_CRITICAL})",
        "",
    ]
    if candidate:
        c_sum = candidate.get("summary") or summarize(candidate["results"])
        lines += [
            f"| | **{baseline['agent_id']}** | **{candidate['agent_id']}** |",
            "|---|---|---|",
            f"| Gate | **{b_sum['gate_result'].upper()}** | **{c_sum['gate_result'].upper()}** |",
            f"| Policy pass rate | {_pct(b_sum['policy_pass_rate'])} | {_pct(c_sum['policy_pass_rate'])} |",
            f"| Critical violations | {b_sum['critical_violations']} | {c_sum['critical_violations']} |",
            f"| Avg. similarity to human | {b_sum['avg_similarity']:.2f} | {c_sum['avg_similarity']:.2f} |",
            f"| Escalation recall | {_pct(b_sum['escalation_recall'])} | {_pct(c_sum['escalation_recall'])} |",
            f"| Fact pass rate (≥80%) | {_pct(b_sum['fact_pass_rate'])} | {_pct(c_sum['fact_pass_rate'])} |",
            f"| Tickets | {b_sum['ticket_count']} | {c_sum['ticket_count']} |",
            "",
            "Candidate gate reasons:",
            "",
        ]
        for reason in c_sum.get("gate_reasons") or []:
            lines.append(f"- {reason}")
        lines += ["", "## Pass rate by category (candidate)", ""]
        lines.append("| Category | Tickets | Policy pass | Critical | Similarity |")
        lines.append("|---|---:|---:|---:|---:|")
        for row in pass_rate_by_category(candidate["results"]):
            lines.append(
                f"| {row['category']} | {row['tickets']} | {_pct(row['policy_pass_rate'])} "
                f"| {row['critical']} | {row['avg_similarity']:.2f} |"
            )
        regs = find_regressions(baseline["results"], candidate["results"])
        lines += ["", f"## Regressions ({len(regs)} tickets where {candidate['agent_id']} got worse)", ""]
        if not regs:
            lines.append("None.")
        else:
            lines.append("| Ticket | Category | Why | Baseline overall | Candidate overall |")
            lines.append("|---|---|---|---:|---:|")
            for row in regs:
                lines.append(
                    f"| {row['ticket_id']} | {row['category']} | {'; '.join(row['reasons'])} "
                    f"| {row['baseline_overall']:.2f} | {row['candidate_overall']:.2f} |"
                )
        lines += ["", f"## Worst failures — {baseline['agent_id']} (why the baseline missed the gate)", ""]
        for row in worst_failures(baseline["results"], limit=5):
            human = (tickets_by_id or {}).get(row["ticket_id"], {}).get("human_reply") or row.get("human_reply") or ""
            lines += [
                f"### {row['ticket_id']} · {row.get('category')} · {row.get('story')}",
                "",
                f"- Policy pass: {row.get('policy_pass')} · Critical: {row.get('critical')} "
                f"· Similarity: {row.get('similarity'):.2f} · Overall: {row.get('overall'):.2f}",
            ]
            if row.get("critical_reasons"):
                lines.append("- Critical reasons: " + "; ".join(row["critical_reasons"]))
            lines += [
                "",
                "**Human reply**",
                "",
                f"> {human}",
                "",
                "**AI reply (shadow)**",
                "",
                f"> {row.get('ai_reply')}",
                "",
            ]
    else:
        lines += [
            f"- Agent: **{baseline['agent_id']}**",
            f"- Gate: **{b_sum['gate_result'].upper()}**",
            f"- Policy pass rate: {_pct(b_sum['policy_pass_rate'])}",
            f"- Critical violations: {b_sum['critical_violations']}",
            f"- Avg. similarity: {b_sum['avg_similarity']:.2f}",
            f"- Escalation recall: {_pct(b_sum['escalation_recall'])}",
            "",
        ]
        for reason in b_sum.get("gate_reasons") or []:
            lines.append(f"- {reason}")
    lines.append("")
    return "\n".join(lines)


def csv_results(results: list[dict[str, Any]]) -> str:
    fields = [
        "ticket_id",
        "category",
        "subcategory",
        "store",
        "story",
        "policy_pass",
        "critical",
        "critical_reasons",
        "fact_score",
        "similarity",
        "escalation_ok",
        "tone_pass",
        "length_pass",
        "overall",
    ]
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in results:
        item = {k: row.get(k) for k in fields}
        if isinstance(item.get("critical_reasons"), list):
            item["critical_reasons"] = "; ".join(item["critical_reasons"])
        writer.writerow(item)
    return buf.getvalue()


def write_report(markdown: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path
