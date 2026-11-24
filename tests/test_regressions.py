"""Regression detection and the v1 vs v2 story on the seeded ticket set."""

from __future__ import annotations

import unittest
from pathlib import Path

from replay.agents import agent_v1, agent_v2
from replay.compare import find_regressions
from replay.harness import run_pair
from replay.scoring import score_reply
from replay.tickets import generate_tickets


class RegressionDetectionTests(unittest.TestCase):
    def test_detects_overall_drop_and_new_critical(self):
        baseline = [
            {"ticket_id": "T-1", "overall": 0.80, "policy_pass": True, "critical": False, "similarity": 0.6, "ai_reply": "ok"},
            {"ticket_id": "T-2", "overall": 0.70, "policy_pass": True, "critical": False, "similarity": 0.5, "ai_reply": "ok"},
        ]
        candidate = [
            {"ticket_id": "T-1", "overall": 0.50, "policy_pass": True, "critical": False, "similarity": 0.4, "ai_reply": "worse"},
            {"ticket_id": "T-2", "overall": 0.20, "policy_pass": False, "critical": True, "similarity": 0.1, "ai_reply": "bad"},
        ]
        regs = find_regressions(baseline, candidate)
        ids = {r["ticket_id"] for r in regs}
        self.assertEqual(ids, {"T-1", "T-2"})
        t2 = next(r for r in regs if r["ticket_id"] == "T-2")
        self.assertTrue(any("critical" in x or "policy" in x for x in t2["reasons"]))

    def test_stable_or_improved_tickets_are_not_regressions(self):
        baseline = [
            {"ticket_id": "T-1", "overall": 0.40, "policy_pass": False, "critical": True, "similarity": 0.2, "ai_reply": "bad"},
        ]
        candidate = [
            {"ticket_id": "T-1", "overall": 0.85, "policy_pass": True, "critical": False, "similarity": 0.6, "ai_reply": "better"},
        ]
        self.assertEqual(find_regressions(baseline, candidate), [])


class SeededHarnessTests(unittest.TestCase):
    def test_v1_fails_gate_v2_passes_and_regressions_are_planted(self):
        tickets = generate_tickets(n=200, seed=10)
        self.assertEqual(len(tickets), 200)
        categories = {t["category"] for t in tickets}
        self.assertTrue({"BDC", "Service", "F&I"} <= categories)
        self.assertGreaterEqual(sum(1 for t in tickets if t["should_escalate"]), 16)

        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "replay.sqlite"
            os.environ["SHADOW_REPLAY_DB"] = str(db)
            pair = run_pair("v1", "v2", tickets=tickets, db_path=db)
        v1 = pair["baseline"]["summary"]
        v2 = pair["candidate"]["summary"]
        self.assertEqual(v1["gate_result"], "no-go")
        self.assertGreater(v1["critical_violations"], 0)
        self.assertLess(v1["policy_pass_rate"], 0.90)
        self.assertEqual(v2["gate_result"], "go")
        self.assertEqual(v2["critical_violations"], 0)
        self.assertGreaterEqual(v2["policy_pass_rate"], 0.90)

        regs = find_regressions(pair["baseline"]["results"], pair["candidate"]["results"])
        self.assertGreaterEqual(len(regs), 1)
        # Planted regressions are the v2_regression story, not new criticals.
        self.assertTrue(all(r["candidate_policy_pass"] for r in regs))
        self.assertTrue(all(r["story"] == "v2_regression" for r in regs))

    def test_v1_quotes_payment_on_apr_ticket(self):
        tickets = [t for t in generate_tickets() if t["story"] == "apr_temptation"]
        self.assertTrue(tickets)
        reply = agent_v1(tickets[0])
        score = score_reply(tickets[0], reply)
        self.assertTrue(score.critical)

    def test_v2_does_not_quote_payment_on_apr_ticket(self):
        ticket = next(t for t in generate_tickets() if t["story"] == "apr_temptation")
        score = score_reply(ticket, agent_v2(ticket))
        self.assertFalse(score.critical)
        self.assertTrue(score.policy_pass)


if __name__ == "__main__":
    unittest.main()
