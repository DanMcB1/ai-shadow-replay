"""Run a ticket set through a candidate agent in shadow mode and store the run."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from replay.agents import AGENT_LABELS, get_agent
from replay.compare import summarize
from replay.scoring import build_idf, score_reply
from replay.store import insert_results, insert_run
from replay.tickets import ensure_tickets


def run_agent(
    agent_id: str,
    *,
    tickets: list[dict[str, Any]] | None = None,
    db_path: Path | None = None,
    label: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Shadow-replay every ticket. Nothing is sent to a customer."""
    tickets = tickets if tickets is not None else ensure_tickets()
    agent = get_agent(agent_id)
    idf = build_idf(t.get("human_reply") or "" for t in tickets)

    rows: list[dict[str, Any]] = []
    for ticket in tickets:
        reply = agent(ticket)
        score = score_reply(ticket, reply, idf=idf)
        item = score.to_dict()
        item.update(
            {
                "ai_reply": reply,
                "human_reply": ticket.get("human_reply"),
                "question": ticket.get("question"),
                "category": ticket.get("category"),
                "subcategory": ticket.get("subcategory"),
                "store": ticket.get("store"),
                "story": ticket.get("story"),
                "should_escalate": bool(ticket.get("should_escalate")),
                "customer_name": ticket.get("customer_name"),
            }
        )
        rows.append(item)

    summary = summarize(rows)
    run_id = insert_run(
        agent_id=agent_id,
        label=label or AGENT_LABELS.get(agent_id, agent_id),
        ticket_count=len(tickets),
        summary=summary,
        path=db_path,
        notes=notes or "shadow mode — customer never sees the AI output",
    )
    insert_results(run_id, rows, path=db_path)
    return {"run_id": run_id, "agent_id": agent_id, "summary": summary, "results": rows}


def run_pair(
    baseline: str = "v1",
    candidate: str = "v2",
    *,
    tickets: list[dict[str, Any]] | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    tickets = tickets if tickets is not None else ensure_tickets()
    left = run_agent(baseline, tickets=tickets, db_path=db_path)
    right = run_agent(candidate, tickets=tickets, db_path=db_path)
    return {"baseline": left, "candidate": right}
