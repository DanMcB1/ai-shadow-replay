"""Historical Shadow Replay Harness — Streamlit UI.

Run with ./run.sh
Works fully offline. No API key required. Tickets and agents are fictional mocks.
"""

from __future__ import annotations

import difflib

import pandas as pd
import plotly.express as px
import streamlit as st

from replay.compare import find_regressions, pass_rate_by_category, worst_failures
from replay.harness import run_pair
from replay.report import csv_results, markdown_report
from replay.settings import COMPANY, GATE_MAX_CRITICAL, GATE_POLICY_PASS_MIN
from replay.store import get_results, get_run, list_runs
from replay.tickets import ensure_tickets

st.set_page_config(
    page_title="Shadow Replay Harness",
    page_icon="blueprint",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
  .block-container { padding-top: 1.2rem; max-width: 1360px; }
  .demo-banner {
    background: #fff6e5;
    border: 1px solid #e6d2a8;
    color: #5a4500;
    padding: 0.7rem 1rem;
    border-radius: 8px;
    font-size: 0.95rem;
    margin-bottom: 0.8rem;
  }
  .gate-go, .gate-nogo {
    border-radius: 10px;
    padding: 0.85rem 1rem;
    margin: 0 0 0.8rem;
    border: 1px solid;
  }
  .gate-go {
    background: #e8f6f2;
    border-color: #9ad0c4;
    color: #145a50;
  }
  .gate-nogo {
    background: #fdeeee;
    border-color: #e3b3b3;
    color: #7a1f1f;
  }
  .gate-label {
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 700;
    margin: 0 0 0.25rem;
  }
  .fail-card {
    background: #fff;
    border: 1px solid #d5dbe3;
    border-left: 4px solid #1e3a5f;
    border-radius: 10px;
    padding: 0.8rem 1rem 0.7rem;
    margin: 0 0 0.75rem;
  }
  .fail-card.critical { border-left-color: #9b2c2c; }
  .fail-label {
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #4a5a70;
    font-weight: 700;
    margin: 0 0 0.3rem;
  }
  h1 { letter-spacing: -0.02em; }
  div[data-testid="stMetric"] {
    background: #f3f5f8;
    border: 1px solid #d5dbe3;
    border-radius: 10px;
    padding: 8px 12px;
  }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

NAVY = "#1e3a5f"
TEAL = "#2a7f6f"
AMBER = "#c47b2b"
RED = "#9b2c2c"


def _pct(value: float) -> str:
    return f"{value:.1%}"


def _hydrate_run(run: dict) -> dict:
    results = get_results(run["id"])
    tickets = {t["id"]: t for t in ensure_tickets()}
    for row in results:
        ticket = tickets.get(row["ticket_id"]) or {}
        row.setdefault("human_reply", ticket.get("human_reply"))
        row.setdefault("question", ticket.get("question"))
        row.setdefault("customer_name", ticket.get("customer_name"))
    return {
        "run_id": run["id"],
        "agent_id": run["agent_id"],
        "results": results,
        "summary": {
            "ticket_count": run["ticket_count"],
            "policy_pass_rate": run["policy_pass_rate"],
            "critical_violations": run["critical_violations"],
            "avg_similarity": run["avg_similarity"],
            "escalation_recall": run["escalation_recall"],
            "fact_pass_rate": run["fact_pass_rate"],
            "avg_overall": run["avg_overall"],
            "gate_result": run["gate_result"],
            "gate_reasons": __import__("json").loads(run["gate_reasons"] or "[]"),
        },
    }


def _latest_pair() -> tuple[dict | None, dict | None]:
    runs = list_runs()
    v1 = next((r for r in runs if r["agent_id"] == "v1"), None)
    v2 = next((r for r in runs if r["agent_id"] == "v2"), None)
    if not v1 or not v2:
        return None, None
    return _hydrate_run(v1), _hydrate_run(v2)


def _run_pair_now() -> tuple[dict, dict]:
    with st.spinner("Replaying 200 historical tickets in shadow mode… the customer never sees this."):
        pair = run_pair("v1", "v2")
    return pair["baseline"], pair["candidate"]


tickets = ensure_tickets()

with st.sidebar:
    st.header("How this works")
    st.markdown(
        """
Before a new BDC or service assistant takes live customer conversations, you run it against **history** — the same way you'd review call recordings with a new hire.

This harness replays about **200 fictional Lakeside tickets** through two local mock agents in **shadow mode**. The customer never sees the AI reply. A deterministic rubric scores policy, facts, tone, length, similarity to the human, and whether legal or safety cases were escalated.
        """
    )
    st.markdown("---")
    if st.button("Run v1 vs v2 shadow replay", type="primary", use_container_width=True):
        st.session_state["pair"] = _run_pair_now()
        st.rerun()
    st.caption(
        "Default agents are local mocks. An optional OpenAI-compatible / Ollama hook is off unless "
        "`SHADOW_REPLAY_LLM_BASE_URL` is set."
    )
    st.markdown("---")
    st.markdown("**Readiness gate**")
    st.write(f"Policy pass rate ≥ {GATE_POLICY_PASS_MIN:.0%}")
    st.write(f"Critical violations ≤ {GATE_MAX_CRITICAL}")
    st.caption("Critical means quoting an APR or payment, promising warranty coverage, or missing a required legal/safety escalation.")
    st.markdown("---")
    st.caption(f"Portfolio demo for Daniel McBrearty · {COMPANY}")

st.title("Historical Shadow Replay Harness")
st.caption(
    "Replay historical support tickets through a candidate agent in shadow mode, "
    "score it against the human, and decide go or no-go before anything is live."
)
st.markdown(
    '<div class="demo-banner">'
    "<strong>Honest label:</strong> this is a demo for "
    f"{COMPANY}. The ~200 tickets are fictional, generated with a fixed seed. "
    "The default agents are local rule-based mocks, not a production model. "
    "No customer ever sees these replies. The rubric is deterministic (regex and "
    "checklists plus local TF-IDF), not a certified QA process. "
    "The go/no-go bar is a demo threshold, not a customer's policy."
    "</div>",
    unsafe_allow_html=True,
)

if "pair" not in st.session_state:
    existing = _latest_pair()
    if existing[0] and existing[1]:
        st.session_state["pair"] = existing
    else:
        st.session_state["pair"] = _run_pair_now()

baseline, candidate = st.session_state["pair"]
b, c = baseline["summary"], candidate["summary"]
regs = find_regressions(baseline["results"], candidate["results"])
tickets_by_id = {t["id"]: t for t in tickets}


def _gate_card(agent_id: str, summary: dict) -> None:
    kind = "go" if summary["gate_result"] == "go" else "nogo"
    label = "GO — ready to discuss a supervised pilot" if kind == "go" else "NO-GO — not ready for live customers"
    reasons = "".join(f"<div>• {r}</div>" for r in summary.get("gate_reasons") or [])
    st.markdown(
        f'<div class="gate-{kind}"><div class="gate-label">{agent_id} readiness</div>'
        f"<strong>{label}</strong>{reasons}</div>",
        unsafe_allow_html=True,
    )


left, right = st.columns(2)
with left:
    _gate_card(baseline["agent_id"], b)
    r1, r2 = st.columns(2)
    r1.metric("Policy pass", _pct(b["policy_pass_rate"]))
    r2.metric("Critical", b["critical_violations"])
    r3, r4 = st.columns(2)
    r3.metric("Similarity", f"{b['avg_similarity']:.2f}")
    r4.metric("Esc. recall", _pct(b["escalation_recall"]))
with right:
    _gate_card(candidate["agent_id"], c)
    r1, r2 = st.columns(2)
    r1.metric("Policy pass", _pct(c["policy_pass_rate"]), delta=_pct(c["policy_pass_rate"] - b["policy_pass_rate"]))
    r2.metric("Critical", c["critical_violations"], delta=int(c["critical_violations"] - b["critical_violations"]))
    r3, r4 = st.columns(2)
    r3.metric("Similarity", f"{c['avg_similarity']:.2f}", delta=f"{c['avg_similarity'] - b['avg_similarity']:+.2f}")
    r4.metric("Esc. recall", _pct(c["escalation_recall"]), delta=_pct(c["escalation_recall"] - b["escalation_recall"]))

st.caption(
    f"Compared {c['ticket_count']} fictional tickets. Fact pass rate: "
    f"v1 {_pct(b['fact_pass_rate'])} → v2 {_pct(c['fact_pass_rate'])}. "
    f"Regressions (v2 worse than v1): {len(regs)}."
)

tab_cat, tab_reg, tab_fail, tab_ticket, tab_export = st.tabs(
    [
        "Pass rate by category",
        f"Regressions ({len(regs)})",
        "Worst failures",
        "Ticket inspector",
        "Export / history",
    ]
)

with tab_cat:
    rows = []
    for left_row, right_row in zip(
        pass_rate_by_category(baseline["results"]),
        pass_rate_by_category(candidate["results"]),
    ):
        rows.append(
            {
                "category": left_row["category"],
                "agent": "v1",
                "policy_pass_rate": left_row["policy_pass_rate"],
                "critical": left_row["critical"],
            }
        )
        rows.append(
            {
                "category": right_row["category"],
                "agent": "v2",
                "policy_pass_rate": right_row["policy_pass_rate"],
                "critical": right_row["critical"],
            }
        )
    df = pd.DataFrame(rows)
    fig = px.bar(
        df,
        x="category",
        y="policy_pass_rate",
        color="agent",
        barmode="group",
        color_discrete_map={"v1": AMBER, "v2": TEAL},
        labels={"policy_pass_rate": "Policy pass rate", "category": "Category", "agent": "Agent"},
        range_y=[0, 1.05],
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=360,
        legend_title_text="",
        yaxis_tickformat=".0%",
        plot_bgcolor="#f6f7f9",
        paper_bgcolor="#f6f7f9",
    )
    fig.add_hline(y=GATE_POLICY_PASS_MIN, line_dash="dash", line_color=NAVY, annotation_text="90% bar")
    st.plotly_chart(fig, use_container_width=True)
    table = []
    for v1_row, v2_row in zip(
        pass_rate_by_category(baseline["results"]),
        pass_rate_by_category(candidate["results"]),
    ):
        table.append(
            {
                "Category": v1_row["category"],
                "Tickets": v2_row["tickets"],
                "v1 policy pass": _pct(v1_row["policy_pass_rate"]),
                "v2 policy pass": _pct(v2_row["policy_pass_rate"]),
                "v1 critical": v1_row["critical"],
                "v2 critical": v2_row["critical"],
                "v2 similarity": f"{v2_row['avg_similarity']:.2f}",
            }
        )
    st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)

with tab_reg:
    st.markdown("#### Tickets where v2 scored worse than v1")
    st.caption(
        "A regression is an overall-score drop of 0.08 or more, a policy pass that became a fail, "
        "or a new critical violation. In this demo a few confirmation tickets are planted: v1 copies "
        "the exact slot, v2 answers more generally."
    )
    if not regs:
        st.success("No regressions on this pair.")
    else:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Ticket": r["ticket_id"],
                        "Category": r["category"],
                        "Why": "; ".join(r["reasons"]),
                        "v1 overall": f"{r['baseline_overall']:.2f}",
                        "v2 overall": f"{r['candidate_overall']:.2f}",
                        "v1 similarity": f"{r['baseline_similarity']:.2f}",
                        "v2 similarity": f"{r['candidate_similarity']:.2f}",
                    }
                    for r in regs
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
        pick = st.selectbox("Inspect a regression", [r["ticket_id"] for r in regs])
        chosen = next(r for r in regs if r["ticket_id"] == pick)
        human = (tickets_by_id.get(pick) or {}).get("human_reply") or ""
        c1, c2, c3 = st.columns(3)
        c1.markdown("**Human reply**")
        c1.write(human)
        c2.markdown("**v1 (shadow)**")
        c2.write(chosen["baseline_reply"])
        c3.markdown("**v2 (shadow)**")
        c3.write(chosen["candidate_reply"])

with tab_fail:
    st.markdown("#### Worst v1 failures (policy and critical first)")
    st.caption("These are the tickets you'd walk through with a desk manager before changing a prompt.")
    for row in worst_failures(baseline["results"], limit=5):
        human = (tickets_by_id.get(row["ticket_id"]) or {}).get("human_reply") or row.get("human_reply") or ""
        question = (tickets_by_id.get(row["ticket_id"]) or {}).get("question") or row.get("question") or ""
        klass = "fail-card critical" if row.get("critical") else "fail-card"
        reasons = "; ".join(row.get("critical_reasons") or []) or "policy soft misses"
        st.markdown(
            f'<div class="{klass}"><div class="fail-label">{row["ticket_id"]} · '
            f'{row.get("category")} · {row.get("story")}</div>'
            f"<div><strong>Customer:</strong> {question}</div></div>",
            unsafe_allow_html=True,
        )
        st.caption(f"Critical: {row.get('critical')} · {reasons} · similarity {row.get('similarity'):.2f}")
        a, bcol = st.columns(2)
        a.markdown("**Human**")
        a.write(human)
        bcol.markdown("**v1 shadow reply**")
        bcol.write(row.get("ai_reply"))
        # A compact word-level hint
        diff = list(
            difflib.unified_diff(
                (human or "").split(),
                (row.get("ai_reply") or "").split(),
                lineterm="",
                n=0,
            )
        )
        if diff:
            with st.expander(f"Word diff vs human — {row['ticket_id']}"):
                st.code("\n".join(diff[:80]), language="diff")

with tab_ticket:
    st.markdown("#### Look up any ticket")
    ids = [t["id"] for t in tickets]
    default = regs[0]["ticket_id"] if regs else ids[0]
    tid = st.selectbox("Ticket id", ids, index=ids.index(default) if default in ids else 0)
    ticket = tickets_by_id[tid]
    v1_row = next(r for r in baseline["results"] if r["ticket_id"] == tid)
    v2_row = next(r for r in candidate["results"] if r["ticket_id"] == tid)
    st.write(
        f"{ticket['store']} · {ticket['category']} / {ticket['subcategory']} · "
        f"{ticket['channel']} · CSAT {ticket['csat']} · {ticket['handle_time_min']} min · "
        f"story `{ticket['story']}`"
    )
    st.markdown("**Customer question**")
    st.write(ticket["question"])
    c1, c2, c3 = st.columns(3)
    c1.markdown("**Human (historical)**")
    c1.write(ticket["human_reply"])
    c2.markdown("**v1 shadow**")
    c2.write(v1_row["ai_reply"])
    c2.caption(
        f"policy={'pass' if v1_row['policy_pass'] else 'fail'} · "
        f"critical={bool(v1_row['critical'])} · sim={v1_row['similarity']:.2f}"
    )
    c3.markdown("**v2 shadow**")
    c3.write(v2_row["ai_reply"])
    c3.caption(
        f"policy={'pass' if v2_row['policy_pass'] else 'fail'} · "
        f"critical={bool(v2_row['critical'])} · sim={v2_row['similarity']:.2f}"
    )

with tab_export:
    st.markdown("#### Export this comparison")
    md = markdown_report(baseline=baseline, candidate=candidate, tickets_by_id=tickets_by_id)
    st.download_button("Download Markdown report", md, file_name="shadow-replay-report.md", mime="text/markdown")
    st.download_button(
        "Download v2 results CSV",
        csv_results(candidate["results"]),
        file_name="shadow-replay-v2.csv",
        mime="text/csv",
    )
    st.markdown("#### Stored runs")
    history = list_runs()
    if history:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Run": r["id"],
                        "When (UTC)": r["started_at"],
                        "Agent": r["agent_id"],
                        "Gate": r["gate_result"],
                        "Policy pass": _pct(r["policy_pass_rate"] or 0),
                        "Critical": r["critical_violations"],
                        "Similarity": f"{(r['avg_similarity'] or 0):.2f}",
                    }
                    for r in history
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No stored runs yet.")
