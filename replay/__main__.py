"""CLI: python -m replay generate | run --agent v2 | export."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from replay.compare import find_regressions, summarize
from replay.harness import run_agent, run_pair
from replay.report import csv_results, markdown_report, write_report
from replay.settings import TICKET_COUNT, TICKET_SEED, tickets_path
from replay.store import get_results, get_run, list_runs
from replay.tickets import ensure_tickets, generate_tickets, save_tickets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="replay",
        description="Historical Shadow Replay Harness (portfolio demo).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    gen = sub.add_parser("generate", help="Write the seeded fictional ticket set")
    gen.add_argument("--out", default=None)
    gen.add_argument("--count", type=int, default=TICKET_COUNT)
    gen.add_argument("--seed", type=int, default=TICKET_SEED)

    run = sub.add_parser("run", help="Shadow-replay tickets through an agent")
    run.add_argument("--agent", default="v2", help="v1, v2, or external (off by default)")
    run.add_argument("--compare", action="store_true", help="Also run v1 and compare")
    run.add_argument("--json", action="store_true")

    sub.add_parser("runs", help="List stored runs")

    export = sub.add_parser("export", help="Export the latest pair (or a run) as Markdown/CSV")
    export.add_argument("--out", default="examples/v1-vs-v2-report.md")
    export.add_argument("--csv", default=None)
    export.add_argument("--run", type=int, default=None, help="Single run id (skip compare)")

    args = parser.parse_args(argv)

    if args.cmd == "generate":
        tickets = generate_tickets(n=args.count, seed=args.seed)
        path = save_tickets(tickets, Path(args.out) if args.out else None)
        print(f"Wrote {len(tickets)} fictional tickets to {path}")
        return 0

    if args.cmd == "run":
        if args.compare or args.agent == "compare":
            pair = run_pair("v1", "v2")
            payload = {
                "baseline": {"run_id": pair["baseline"]["run_id"], "summary": pair["baseline"]["summary"]},
                "candidate": {"run_id": pair["candidate"]["run_id"], "summary": pair["candidate"]["summary"]},
                "regressions": len(find_regressions(pair["baseline"]["results"], pair["candidate"]["results"])),
            }
            print(json.dumps(payload, indent=2) if args.json else _format_pair(pair))
            return 0
        result = run_agent(args.agent)
        if args.json:
            print(json.dumps({"run_id": result["run_id"], "summary": result["summary"]}, indent=2))
        else:
            print(_format_summary(args.agent, result["run_id"], result["summary"]))
        return 0

    if args.cmd == "runs":
        rows = list_runs()
        if not rows:
            print("No runs stored yet. Try: python -m replay run --agent v2")
            return 0
        for row in rows:
            print(
                f"#{row['id']:>3}  {row['started_at']}  {row['agent_id']:<9}  "
                f"gate={row['gate_result']:<5}  policy={row['policy_pass_rate']:.1%}  "
                f"critical={row['critical_violations']}"
            )
        return 0

    if args.cmd == "export":
        if args.run:
            run = get_run(args.run)
            if not run:
                print(f"No run {args.run}", file=sys.stderr)
                return 2
            results = get_results(args.run)
            payload = {"run_id": args.run, "agent_id": run["agent_id"], "results": results, "summary": summarize(results)}
            md = markdown_report(baseline=payload)
        else:
            pair = run_pair("v1", "v2")
            tickets = {t["id"]: t for t in ensure_tickets()}
            md = markdown_report(
                baseline=pair["baseline"],
                candidate=pair["candidate"],
                tickets_by_id=tickets,
            )
            if args.csv:
                Path(args.csv).write_text(csv_results(pair["candidate"]["results"]), encoding="utf-8")
                print(f"Wrote CSV {args.csv}")
        path = write_report(md, Path(args.out))
        print(f"Wrote {path}")
        return 0

    return 1


def _format_summary(agent_id: str, run_id: int, summary: dict) -> str:
    reasons = "\n".join(f"  - {r}" for r in summary.get("gate_reasons") or [])
    return (
        f"Shadow run #{run_id}  agent={agent_id}  tickets={summary['ticket_count']}\n"
        f"  Gate:             {summary['gate_result'].upper()}\n"
        f"  Policy pass rate: {summary['policy_pass_rate']:.1%}\n"
        f"  Critical:         {summary['critical_violations']}\n"
        f"  Similarity:       {summary['avg_similarity']:.2f}\n"
        f"  Escalation recall:{summary['escalation_recall']:.1%}\n"
        f"  Fact pass rate:   {summary['fact_pass_rate']:.1%}\n"
        f"{reasons}"
    )


def _format_pair(pair: dict) -> str:
    left = _format_summary("v1", pair["baseline"]["run_id"], pair["baseline"]["summary"])
    right = _format_summary("v2", pair["candidate"]["run_id"], pair["candidate"]["summary"])
    n_reg = len(find_regressions(pair["baseline"]["results"], pair["candidate"]["results"]))
    return left + "\n\n" + right + f"\n\nRegressions (v2 worse than v1): {n_reg}"


if __name__ == "__main__":
    raise SystemExit(main())
