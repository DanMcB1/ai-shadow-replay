"""SQLite store for replay runs so results stay comparable over time."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from replay.settings import db_path as default_db_path


def connect(path: Path | None = None) -> sqlite3.Connection:
    target = Path(path or default_db_path())
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            label TEXT,
            ticket_count INTEGER NOT NULL,
            policy_pass_rate REAL,
            critical_violations INTEGER,
            avg_similarity REAL,
            escalation_recall REAL,
            fact_pass_rate REAL,
            avg_overall REAL,
            gate_result TEXT,
            gate_reasons TEXT,
            notes TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            ticket_id TEXT NOT NULL,
            category TEXT,
            subcategory TEXT,
            store TEXT,
            story TEXT,
            should_escalate INTEGER,
            ai_reply TEXT,
            policy_pass INTEGER,
            critical INTEGER,
            critical_reasons TEXT,
            fact_score REAL,
            facts_missing TEXT,
            tone_pass INTEGER,
            length_pass INTEGER,
            similarity REAL,
            escalation_ok INTEGER,
            overall REAL,
            FOREIGN KEY (run_id) REFERENCES runs(id)
        )
        """
    )
    return conn


def insert_run(
    *,
    agent_id: str,
    label: str,
    ticket_count: int,
    summary: dict[str, Any],
    path: Path | None = None,
    notes: str = "",
) -> int:
    conn = connect(path)
    try:
        cur = conn.execute(
            """
            INSERT INTO runs (
                started_at, agent_id, label, ticket_count,
                policy_pass_rate, critical_violations, avg_similarity,
                escalation_recall, fact_pass_rate, avg_overall,
                gate_result, gate_reasons, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                agent_id,
                label,
                ticket_count,
                summary.get("policy_pass_rate"),
                summary.get("critical_violations"),
                summary.get("avg_similarity"),
                summary.get("escalation_recall"),
                summary.get("fact_pass_rate"),
                summary.get("avg_overall"),
                summary.get("gate_result"),
                json.dumps(summary.get("gate_reasons") or []),
                notes,
            ),
        )
        run_id = int(cur.lastrowid)
        conn.commit()
        return run_id
    finally:
        conn.close()


def insert_results(run_id: int, rows: list[dict[str, Any]], path: Path | None = None) -> None:
    conn = connect(path)
    try:
        conn.executemany(
            """
            INSERT INTO results (
                run_id, ticket_id, category, subcategory, store, story,
                should_escalate, ai_reply, policy_pass, critical,
                critical_reasons, fact_score, facts_missing, tone_pass,
                length_pass, similarity, escalation_ok, overall
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_id,
                    r["ticket_id"],
                    r.get("category"),
                    r.get("subcategory"),
                    r.get("store"),
                    r.get("story"),
                    1 if r.get("should_escalate") else 0,
                    r.get("ai_reply"),
                    1 if r.get("policy_pass") else 0,
                    1 if r.get("critical") else 0,
                    json.dumps(r.get("critical_reasons") or []),
                    r.get("fact_score"),
                    json.dumps(r.get("facts_missing") or []),
                    1 if r.get("tone_pass") else 0,
                    1 if r.get("length_pass") else 0,
                    r.get("similarity"),
                    1 if r.get("escalation_ok") else 0,
                    r.get("overall"),
                )
                for r in rows
            ],
        )
        conn.commit()
    finally:
        conn.close()


def list_runs(path: Path | None = None) -> list[dict[str, Any]]:
    conn = connect(path)
    try:
        rows = conn.execute("SELECT * FROM runs ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_run(run_id: int, path: Path | None = None) -> dict[str, Any] | None:
    conn = connect(path)
    try:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_results(run_id: int, path: Path | None = None) -> list[dict[str, Any]]:
    conn = connect(path)
    try:
        rows = conn.execute(
            "SELECT * FROM results WHERE run_id = ? ORDER BY ticket_id", (run_id,)
        ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            for key in ("critical_reasons", "facts_missing"):
                if isinstance(item.get(key), str):
                    try:
                        item[key] = json.loads(item[key])
                    except json.JSONDecodeError:
                        item[key] = []
            out.append(item)
        return out
    finally:
        conn.close()


def latest_run_for(agent_id: str, path: Path | None = None) -> dict[str, Any] | None:
    conn = connect(path)
    try:
        row = conn.execute(
            "SELECT * FROM runs WHERE agent_id = ? ORDER BY id DESC LIMIT 1",
            (agent_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
