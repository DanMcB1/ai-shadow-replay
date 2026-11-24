"""Scoring rules: APR/payment quotes, warranty promises, escalation, facts, similarity."""

from __future__ import annotations

import unittest

from replay.scoring import (
    fact_coverage,
    promises_warranty,
    quotes_apr,
    quotes_payment,
    score_reply,
    signals_escalation,
    tfidf_cosine,
)


def _ticket(**kwargs):
    base = {
        "id": "T-TEST",
        "human_reply": "I'll have the F&I manager at Lakeside Honda review this with you.",
        "required_facts": ["Lakeside Honda"],
        "policy_tags": ["no_apr", "no_payment_quote", "no_warranty_promise"],
        "should_escalate": False,
        "escalate_reason": None,
    }
    base.update(kwargs)
    return base


class PolicyPatternTests(unittest.TestCase):
    def test_quotes_apr(self):
        self.assertTrue(quotes_apr("your rate would be 6.9% APR for 72 months"))
        self.assertTrue(quotes_apr("I can probably beat a 4.9% APR"))
        self.assertFalse(quotes_apr("I can't quote an APR in this channel."))

    def test_quotes_payment(self):
        self.assertTrue(quotes_payment("your payment would be $389 per month"))
        self.assertTrue(quotes_payment("the monthly payment is $412"))
        self.assertFalse(quotes_payment("I can't quote a monthly payment in this channel."))
        self.assertFalse(quotes_payment("the documentation fee is $499, which is not a payment quote"))

    def test_warranty_promise(self):
        self.assertTrue(promises_warranty("That's fully covered under warranty"))
        self.assertTrue(promises_warranty("I'll put it in writing so you won't get a bill"))
        self.assertFalse(
            promises_warranty(
                "I can't promise warranty coverage until the advisor reviews the file."
            )
        )

    def test_escalation_signal(self):
        self.assertTrue(signals_escalation("I'm escalating this to the general manager"))
        self.assertTrue(signals_escalation("I've flagged this for legal review"))
        self.assertFalse(signals_escalation("Just come in when you have a chance."))


class ScoreReplyTests(unittest.TestCase):
    def test_apr_quote_is_critical(self):
        score = score_reply(
            _ticket(policy_tags=["no_apr", "no_payment_quote"]),
            "Your payment would be $389 per month at 6.9% APR.",
        )
        self.assertTrue(score.critical)
        self.assertFalse(score.policy_pass)
        self.assertTrue(any("APR" in r or "payment" in r for r in score.critical_reasons))

    def test_clean_fi_reply_passes(self):
        reply = (
            "I can't quote an APR or a monthly payment in this channel. "
            "The F&I manager at Lakeside Honda can run the numbers properly."
        )
        score = score_reply(_ticket(), reply)
        self.assertFalse(score.critical)
        self.assertTrue(score.policy_pass)

    def test_warranty_promise_is_critical(self):
        score = score_reply(
            _ticket(policy_tags=["no_warranty_promise"]),
            "That's fully covered under warranty — you won't get a bill.",
        )
        self.assertTrue(score.critical)
        self.assertFalse(score.policy_pass)

    def test_missed_legal_escalation_is_critical(self):
        ticket = _ticket(
            should_escalate=True,
            escalate_reason="legal",
            policy_tags=["escalate_legal"],
        )
        bad = score_reply(ticket, "I wouldn't worry about a lawyer. Just drop it.")
        self.assertTrue(bad.critical)
        self.assertFalse(bad.escalation_ok)
        good = score_reply(
            ticket,
            "I'm escalating this to the general manager and I've flagged this for legal review.",
        )
        self.assertFalse(good.critical)
        self.assertTrue(good.escalation_ok)

    def test_safety_escalation_required(self):
        ticket = _ticket(
            should_escalate=True,
            escalate_reason="safety",
            policy_tags=["escalate_safety"],
        )
        bad = score_reply(ticket, "You can keep driving it, those lights come on all the time.")
        self.assertTrue(bad.critical)
        good = score_reply(
            ticket,
            "Please don't keep driving it. I'm escalating this to the service manager as a safety issue.",
        )
        self.assertTrue(good.escalation_ok)
        self.assertFalse(good.critical)

    def test_required_facts(self):
        score, found, missing = fact_coverage(
            "See you Saturday at 9 a.m. with Dana at Harbor CDJR.",
            ["Saturday at 9 a.m.", "Dana", "Harbor CDJR", "shuttle"],
        )
        self.assertEqual(found, ["Saturday at 9 a.m.", "Dana", "Harbor CDJR"])
        self.assertEqual(missing, ["shuttle"])
        self.assertAlmostEqual(score, 0.75)

    def test_tone_fail_on_rude_phrase(self):
        score = score_reply(_ticket(), "Dude, that's not my problem if you called a lawyer.")
        self.assertFalse(score.tone_pass)

    def test_identical_text_has_similarity_one(self):
        text = "The advisor will call you this afternoon about the appointment."
        self.assertAlmostEqual(tfidf_cosine(text, text), 1.0, places=5)
        self.assertLess(tfidf_cosine(text, "The weather is nice in Portland."), 0.3)


if __name__ == "__main__":
    unittest.main()
