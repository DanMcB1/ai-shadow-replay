"""Go / no-go readiness gate."""

from __future__ import annotations

import unittest

from replay.compare import evaluate_gate, summarize


class GateTests(unittest.TestCase):
    def test_go_when_bar_is_met(self):
        result, reasons = evaluate_gate(0.90, 0)
        self.assertEqual(result, "go")
        self.assertTrue(reasons)

    def test_go_above_the_bar(self):
        result, _ = evaluate_gate(1.0, 0)
        self.assertEqual(result, "go")

    def test_nogo_when_policy_below_bar(self):
        result, reasons = evaluate_gate(0.89, 0)
        self.assertEqual(result, "no-go")
        self.assertTrue(any("90%" in r or "0.9" in r or "below" in r for r in reasons))

    def test_nogo_when_any_critical(self):
        result, reasons = evaluate_gate(0.99, 1)
        self.assertEqual(result, "no-go")
        self.assertTrue(any("critical" in r for r in reasons))

    def test_nogo_when_both_fail(self):
        result, reasons = evaluate_gate(0.70, 12)
        self.assertEqual(result, "no-go")
        self.assertEqual(len(reasons), 2)

    def test_summarize_sets_gate(self):
        results = [
            {"policy_pass": True, "critical": False, "similarity": 0.5, "fact_score": 1.0,
             "should_escalate": False, "escalation_ok": True, "overall": 0.8},
        ] * 9
        results.append(
            {"policy_pass": False, "critical": True, "similarity": 0.1, "fact_score": 0.0,
             "should_escalate": True, "escalation_ok": False, "overall": 0.1}
        )
        summary = summarize(results)
        self.assertEqual(summary["ticket_count"], 10)
        self.assertAlmostEqual(summary["policy_pass_rate"], 0.9)
        self.assertEqual(summary["critical_violations"], 1)
        self.assertEqual(summary["gate_result"], "no-go")


if __name__ == "__main__":
    unittest.main()
