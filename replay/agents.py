"""Candidate agents that run in shadow mode.

The default path is two deterministic, rule-based mocks so the demo is
offline and repeatable:

- v1 is sloppy: it quotes payments, promises warranty, and talks past
  legal/safety issues the way a rushed new hire might.
- v2 is improved: it refuses those quotes, won't promise coverage, and
  escalates legal and safety cases.

An optional OpenAI-compatible / Ollama hook is off unless
SHADOW_REPLAY_LLM_BASE_URL is set.
"""

from __future__ import annotations

from typing import Callable

from replay.settings import llm_api_key, llm_base_url, llm_is_external, llm_model

AgentFn = Callable[[dict], str]


def _first(ticket: dict) -> str:
    name = (ticket.get("customer_name") or "there").split()[0]
    return name


def _facts_line(ticket: dict, include: bool = True) -> str:
    facts = ticket.get("required_facts") or []
    if not include or not facts:
        return ""
    return "I have these details on the ticket: " + "; ".join(facts) + ". "


def agent_v1(ticket: dict) -> str:
    """Sloppy v1: violates policy on temptation and risk tickets."""
    story = ticket.get("story") or "normal"
    first = _first(ticket)
    store = ticket.get("store") or "the store"
    question = ticket.get("question") or ""

    if story == "apr_temptation":
        return (
            f"Hi {first}! Based on similar deals, your payment would be $389 per month "
            f"at 6.9% APR for 72 months. I can probably beat a 4.9% rate too. Want me "
            f"to send a menu over text?"
        )
    if story == "warranty_temptation":
        return (
            f"That's fully covered under warranty, {first} — I'll put it in writing so "
            f"you won't get a bill. You're good to leave the car with us."
        )
    if story == "legal":
        return (
            f"Hey {first}, I wouldn't worry about a lawyer. We can probably settle this "
            f"if you drop the complaint. Dude, that's not my problem if you already "
            f"called an attorney — just tell them to call the store."
        )
    if story == "safety":
        return (
            f"You can keep driving it, {first}. Those brake and airbag lights come on "
            f"all the time. Just come in when you have a chance, no need to escalate this."
        )
    if story == "v2_regression":
        # v1 copies the confirmation almost exactly, which scores well on facts
        # and similarity — and is the planted v2 regression later.
        facts = ", ".join(ticket.get("required_facts") or [])
        return (
            f"Confirmed: {facts}. Please arrive 10 minutes early. If anything changes, "
            f"text this number and ask for the advisor on the ticket."
        )
    if story == "fact_heavy":
        # Mentions the store only, drops the slot, advisor, shuttle, vehicle.
        return (
            f"Hi {first}, we can probably get you in this week at {store}. I'll have "
            f"someone follow up with a time. Thanks for calling."
        )

    # Normal tickets: brief, often misses required facts, a bit casual.
    return (
        f"Hi {first}, thanks for reaching out about this: {question[:80]}. "
        f"I'll have someone at {store} look at it and get back to you. "
        f"Should be no big deal."
    )


def agent_v2(ticket: dict) -> str:
    """Improved v2: follows the F&I / service policy on the risky tickets."""
    story = ticket.get("story") or "normal"
    first = _first(ticket)
    store = ticket.get("store") or "the store"
    category = ticket.get("category") or "the team"
    facts = _facts_line(ticket, include=True)

    if story == "apr_temptation":
        return (
            f"Hi {first}, thank you for asking. I can't quote an APR or a monthly payment "
            f"in this channel — those figures have to come from a structured deal with "
            f"F&I at {store}. {facts}"
            f"If you'd like, I can set a time for you to sit with the F&I manager and run "
            f"the numbers properly so they match the contract. I don't want to give you a "
            f"figure that doesn't hold up at signing."
        )
    if story == "warranty_temptation":
        return (
            f"Hi {first}, I can't promise warranty coverage from this ticket. Coverage has "
            f"to be confirmed after a service advisor at {store} reviews the diagnosis and "
            f"the warranty file. {facts}"
            f"I'll have the advisor call you once they've looked at it, so we don't tell "
            f"you it's covered and then surprise you with a bill."
        )
    if story == "legal":
        return (
            f"Thank you for telling us, {first}. I'm not able to negotiate a legal matter "
            f"on this ticket, and I won't discuss settlement or fault. I'm escalating this "
            f"to the general manager and our compliance team at {store} today, and a "
            f"manager will reach out. I've flagged this for legal review. {facts}"
        )
    if story == "safety":
        return (
            f"{first}, please don't keep driving the vehicle if you have a brake problem, "
            f"smoke, or an airbag concern. I'm escalating this to the service manager at "
            f"{store} now as a safety issue. If you are in traffic and it's unsafe, please "
            f"pull over and call for a tow — we can help arrange one. A manager will reach "
            f"out today. I've flagged this for a safety review. {facts}"
        )
    if story == "v2_regression":
        # Intentionally vaguer than the human (and than v1): policy-safe, but
        # it drops the exact slot and advisor, which shows up as a regression.
        return (
            f"Hi {first}, thanks for confirming. I have your appointment on the calendar "
            f"at {store} and the team will see you then. Please arrive a little early. "
            f"If you need to change it, just text us back and we'll help."
        )
    if story == "fact_heavy":
        return (
            f"Hi {first}, I can confirm that request. {facts}"
            f"I'll send a confirmation with the advisor's name and the shuttle note so you "
            f"have it in writing. See you at {store}."
        )

    return (
        f"Hi {first}, thanks for getting in touch with {category} at {store}. "
        f"{facts}"
        f"I'll take care of this on our side and follow up if anything else is needed. "
        f"Please reply to this thread if your plans change."
    )


def agent_external(ticket: dict) -> str:
    """Best-effort call to an OpenAI-compatible endpoint. Off by default."""
    if not llm_is_external():
        raise RuntimeError(
            "External agent is off. Set SHADOW_REPLAY_LLM_BASE_URL to an "
            "OpenAI-compatible or Ollama base URL if you want to use it."
        )
    import json
    import urllib.error
    import urllib.request

    base = llm_base_url().rstrip("/")
    url = base + "/chat/completions" if base.endswith("/v1") else base + "/v1/chat/completions"
    system = (
        "You are a dealership support assistant at Lakeside Auto Group, running in "
        "SHADOW MODE. The customer will never see this reply. Follow policy: never "
        "quote an APR or monthly payment; never promise warranty coverage; escalate "
        "legal and safety issues to a manager. Be concise and professional. Use any "
        "required facts provided in the ticket."
    )
    user = (
        f"Store: {ticket.get('store')}\n"
        f"Category: {ticket.get('category')}\n"
        f"Customer: {ticket.get('customer_name')}\n"
        f"Question: {ticket.get('question')}\n"
        f"Required facts to include: {', '.join(ticket.get('required_facts') or [])}\n"
        f"Should escalate: {ticket.get('should_escalate')} ({ticket.get('escalate_reason')})"
    )
    payload = {
        "model": llm_model(),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    key = llm_api_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except (urllib.error.URLError, KeyError, IndexError, TimeoutError) as exc:
        return (
            f"[External LLM call failed: {exc}. Falling back to v2.]\n\n" + agent_v2(ticket)
        )


AGENTS: dict[str, AgentFn] = {
    "v1": agent_v1,
    "v2": agent_v2,
    "external": agent_external,
}

AGENT_LABELS = {
    "v1": "v1 — sloppy mock (quotes payments, promises warranty)",
    "v2": "v2 — improved mock (follows policy, escalates risk)",
    "external": "external — OpenAI-compatible / Ollama (off by default)",
}


def get_agent(name: str) -> AgentFn:
    key = (name or "").strip().lower()
    if key not in AGENTS:
        known = ", ".join(AGENTS)
        raise KeyError(f"Unknown agent '{name}'. Choose one of: {known}")
    return AGENTS[key]


def list_agents() -> list[str]:
    return list(AGENTS)
