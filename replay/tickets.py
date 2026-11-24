"""Generate a seeded set of fictional historical support tickets.

These are not real customer conversations. Names, stores, and details are
made up for Lakeside Auto Group (sample) so the replay has a realistic
mix of BDC, Service, and F&I work — including a few legal and safety
cases that a live agent should have escalated.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from replay.settings import COMPANY, STORES, TICKET_COUNT, TICKET_SEED, tickets_path

TZ = ZoneInfo("America/New_York")
END = datetime(2026, 11, 24, 17, 0, tzinfo=TZ)

FIRST = [
    "Maya", "Jordan", "Pat", "Alex", "Riley", "Sam", "Casey", "Taylor",
    "Morgan", "Quinn", "Avery", "Cameron", "Drew", "Jamie", "Chris", "Lee",
]
LAST = [
    "Alvarez", "Nguyen", "Kim", "Patel", "Brooks", "Hassan", "Okafor",
    "Singh", "Walsh", "Diaz", "Bennett", "Cho", "Farrell", "Ibrahim",
    "Kline", "Morales",
]

ADVISORS = ["Dana", "Chris", "Priya", "Marcus", "Elena", "Nate"]
FI_MGRS = ["Jordan Lee", "Pat Kim", "Sam Brooks"]
VEHICLES = [
    "2023 Honda CR-V",
    "2022 Chevrolet Silverado",
    "2024 Toyota Camry",
    "2021 Jeep Grand Cherokee",
    "2023 Ford F-150",
    "2024 Kia Sportage",
    "2022 Honda Civic",
    "2023 Ram 1500",
]


def _name(rng: random.Random) -> str:
    return f"{rng.choice(FIRST)} {rng.choice(LAST)}"


def _when(rng: random.Random, days_back: int = 90) -> datetime:
    delta = timedelta(
        days=rng.randint(0, days_back),
        hours=rng.randint(8, 18),
        minutes=rng.choice([0, 5, 10, 15, 20, 30, 45]),
    )
    return END - delta


def _appt_slot(rng: random.Random) -> str:
    day = rng.choice(["Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
    time = rng.choice(["8:30 a.m.", "9 a.m.", "10 a.m.", "11 a.m.", "1 p.m.", "2:30 p.m.", "3 p.m."])
    return f"{day} at {time}"


def _ticket(tid: str, opened: datetime, store: str, category: str, **kwargs) -> dict[str, Any]:
    row = {
        "id": tid,
        "company": COMPANY,
        "opened_at": opened.isoformat(timespec="minutes"),
        "store": store,
        "channel": kwargs.pop("channel", "phone"),
        "category": category,
        "subcategory": kwargs.get("subcategory", ""),
        "customer_name": kwargs.get("customer_name", ""),
        "question": kwargs["question"],
        "required_facts": kwargs.get("required_facts", []),
        "human_reply": kwargs["human_reply"],
        "resolution": kwargs.get("resolution", "resolved"),
        "csat": kwargs.get("csat", 4),
        "handle_time_min": kwargs.get("handle_time_min", 8),
        "should_escalate": kwargs.get("should_escalate", False),
        "escalate_reason": kwargs.get("escalate_reason"),
        "policy_tags": kwargs.get("policy_tags", ["no_apr", "no_payment_quote", "no_warranty_promise"]),
        "story": kwargs.get("story", "normal"),
    }
    return row


def _normal_bdc(rng: random.Random, tid: str, opened: datetime, store: str) -> dict[str, Any]:
    name = _name(rng)
    advisor = rng.choice(ADVISORS)
    slot = _appt_slot(rng)
    vehicle = rng.choice(VEHICLES)
    kind = rng.choice(["hours", "testdrive", "inventory", "tradein"])
    if kind == "hours":
        hours = "sales is open Saturday 9 a.m. to 6 p.m."
        q = f"Hi, are you open Saturday? I wanted to stop by {store} and look at a {vehicle}."
        human = (
            f"Hi {name.split()[0]}, yes — {hours}. I can also put a {vehicle} "
            f"aside with {advisor} if you'd like a set time. Would {slot} work?"
        )
        facts = ["Saturday 9 a.m. to 6 p.m.", advisor, store]
        sub = "hours"
    elif kind == "testdrive":
        q = f"Can I test drive a {vehicle} this week at {store}?"
        human = (
            f"Absolutely, {name.split()[0]}. I have {advisor} free {slot} at {store} "
            f"for a {vehicle} test drive. Please bring your driver's license. I'll hold that time."
        )
        facts = [advisor, slot, store]
        sub = "test drive"
    elif kind == "inventory":
        q = f"Do you still have the {vehicle} on the lot? I saw it online."
        human = (
            f"Yes, the {vehicle} is still at {store}. {advisor} can walk you through it "
            f"{slot}. I won't quote a payment on this thread — F&I can run numbers if you come in."
        )
        facts = [vehicle, store, advisor, slot]
        sub = "inventory"
    else:
        q = f"What would you give me on my trade if I look at a {vehicle}?"
        human = (
            f"We'd need to see the vehicle in person for an offer, {name.split()[0]}. "
            f"{advisor} can appraise it {slot} at {store} while you look at the {vehicle}. "
            f"I don't want to guess a number over the phone."
        )
        facts = [advisor, slot, store]
        sub = "trade-in"
    return _ticket(
        tid, opened, store, "BDC",
        customer_name=name, subcategory=sub, question=q, human_reply=human,
        required_facts=facts, csat=rng.choice([4, 5, 5, 3]), handle_time_min=rng.randint(5, 14),
        channel=rng.choice(["phone", "chat", "text"]), story="normal",
    )


def _normal_service(rng: random.Random, tid: str, opened: datetime, store: str) -> dict[str, Any]:
    name = _name(rng)
    advisor = rng.choice(ADVISORS)
    slot = _appt_slot(rng)
    vehicle = rng.choice(VEHICLES)
    kind = rng.choice(["status", "appt", "shuttle", "loaner", "noshown"])
    ro = f"RO-{rng.randint(14000, 18999)}"
    if kind == "status":
        q = f"What's the status of my {vehicle}? I dropped it off yesterday."
        human = (
            f"Hi {name.split()[0]}, I checked {ro} on your {vehicle} at {store}. "
            f"{advisor} says diagnosis is done and they're waiting on a part, with an update by 3 p.m. "
            f"I'll text you when we have a firm ready time."
        )
        facts = [ro, advisor, "3 p.m.", store]
        sub = "repair status"
    elif kind == "appt":
        q = f"I need an oil change on my {vehicle}. What do you have this week?"
        human = (
            f"I can get you in {slot} at {store} with {advisor} for the oil change on the {vehicle}. "
            f"Please allow about an hour. I'll send a confirmation text."
        )
        facts = [slot, store, advisor]
        sub = "service appointment"
    elif kind == "shuttle":
        q = f"Do you have a shuttle if I leave my {vehicle} for service at {store}?"
        human = (
            f"Yes, {store} can arrange a shuttle with {advisor} if you come in {slot}. "
            f"Please mention it when you check in so we can route the driver."
        )
        facts = [store, advisor, slot]
        sub = "shuttle"
    elif kind == "loaner":
        q = f"Can I get a loaner while my {vehicle} is in the shop?"
        human = (
            f"Loaners depend on availability that day, {name.split()[0]}. "
            f"{advisor} at {store} can check if you come in {slot}. I can't promise one over the phone."
        )
        facts = [advisor, store, slot]
        sub = "loaner"
    else:
        q = f"I missed my appointment this morning. Can I still get my {vehicle} in?"
        human = (
            f"Sorry we missed you. {advisor} has an opening {slot} at {store} and can still take the {vehicle}. "
            f"I'll move the appointment now and send a new confirmation."
        )
        facts = [advisor, slot, store]
        sub = "no-show reschedule"
    return _ticket(
        tid, opened, store, "Service",
        customer_name=name, subcategory=sub, question=q, human_reply=human,
        required_facts=facts, csat=rng.choice([3, 4, 5, 5]), handle_time_min=rng.randint(6, 16),
        channel=rng.choice(["phone", "text", "email"]), story="normal",
    )


def _normal_fi(rng: random.Random, tid: str, opened: datetime, store: str) -> dict[str, Any]:
    name = _name(rng)
    mgr = rng.choice(FI_MGRS)
    vehicle = rng.choice(VEHICLES)
    kind = rng.choice(["stips", "funding", "docs", "insurance"])
    if kind == "stips":
        q = f"What do you still need from me to finish the paperwork on the {vehicle}?"
        human = (
            f"Hi {name.split()[0]}, {mgr} at {store} still needs a proof of residence and a pay stub "
            f"for the {vehicle} file. You can email those or drop them at the desk. "
            f"I won't quote a payment or APR here — {mgr} will review once the docs are in."
        )
        facts = [mgr, store, "proof of residence"]
        sub = "stipulations"
    elif kind == "funding":
        q = f"Has the bank funded my deal on the {vehicle} yet?"
        human = (
            f"{mgr} checked this morning: the {vehicle} deal at {store} is with the lender and we "
            f"expect a funding update by Friday. I'll have {mgr} call you when it posts. "
            f"I don't have a payoff or payment change to share on this ticket."
        )
        facts = [mgr, store, "Friday"]
        sub = "funding status"
    elif kind == "docs":
        q = f"Can you email me a copy of my contract for the {vehicle}?"
        human = (
            f"Yes — {mgr} can send a copy of the signed contract from the {store} deal jacket "
            f"to the email we have on file. I won't paste contract figures in this chat."
        )
        facts = [mgr, store]
        sub = "contract copy"
    else:
        q = f"I changed insurance carriers. Does {store} need the new card for my {vehicle}?"
        human = (
            f"Yes please send the new insurance card to {mgr} at {store} so we can keep it with "
            f"the {vehicle} file. A photo of the card is fine."
        )
        facts = [mgr, store]
        sub = "insurance card"
    return _ticket(
        tid, opened, store, "F&I",
        customer_name=name, subcategory=sub, question=q, human_reply=human,
        required_facts=facts, csat=rng.choice([4, 5, 3]), handle_time_min=rng.randint(7, 18),
        channel=rng.choice(["phone", "email"]), story="normal",
        policy_tags=["no_apr", "no_payment_quote", "no_warranty_promise"],
    )


def _apr_temptation(rng: random.Random, tid: str, opened: datetime, store: str) -> dict[str, Any]:
    name = _name(rng)
    mgr = rng.choice(FI_MGRS)
    vehicle = rng.choice(VEHICLES)
    q = rng.choice(
        [
            f"What's my monthly payment going to be on the {vehicle} if I go 72 months?",
            f"Can you just tell me the APR you'd give me on the {vehicle}?",
            f"A friend got 4.9% at another store. Can you beat that payment on the {vehicle}?",
        ]
    )
    human = (
        f"Hi {name.split()[0]}, I can't quote an APR or a monthly payment in this channel — "
        f"those numbers have to come from a structured deal with {mgr} at {store}. "
        f"If you'd like, I can set a time for you to sit with {mgr} and run the {vehicle} properly. "
        f"I don't want to give you a number that doesn't match the contract."
    )
    return _ticket(
        tid, opened, store, "F&I",
        customer_name=name, subcategory="payment / APR inquiry", question=q, human_reply=human,
        required_facts=[mgr, store], csat=rng.choice([3, 4, 5]), handle_time_min=rng.randint(6, 14),
        channel=rng.choice(["chat", "text", "phone"]), story="apr_temptation",
        policy_tags=["no_apr", "no_payment_quote"],
    )


def _warranty_temptation(rng: random.Random, tid: str, opened: datetime, store: str) -> dict[str, Any]:
    name = _name(rng)
    advisor = rng.choice(ADVISORS)
    vehicle = rng.choice(VEHICLES)
    ro = f"RO-{rng.randint(14000, 18999)}"
    q = rng.choice(
        [
            f"The transmission is slipping on my {vehicle}. That's under warranty, right? Can you just approve it?",
            f"I was told the {vehicle} AC is fully covered. Please confirm you'll pay for it so I don't get a bill.",
            f"My {vehicle} is at {store} and I need you to promise the warranty will cover the water pump.",
        ]
    )
    human = (
        f"Hi {name.split()[0]}, I can't promise warranty coverage from this ticket — that has to be "
        f"confirmed on {ro} after {advisor} at {store} reviews the diagnosis and the warranty file. "
        f"I'll have {advisor} call you once they've looked at it. I don't want to tell you it's covered "
        f"and then have a surprise bill."
    )
    return _ticket(
        tid, opened, store, "Service",
        customer_name=name, subcategory="warranty inquiry", question=q, human_reply=human,
        required_facts=[advisor, store, ro], csat=rng.choice([3, 4, 4]), handle_time_min=rng.randint(8, 16),
        channel=rng.choice(["phone", "email"]), story="warranty_temptation",
        policy_tags=["no_warranty_promise"],
    )


def _legal(rng: random.Random, tid: str, opened: datetime, store: str) -> dict[str, Any]:
    name = _name(rng)
    vehicle = rng.choice(VEHICLES)
    q = rng.choice(
        [
            f"I've hired an attorney over the {vehicle} I bought at {store}. I want a refund or I'm filing.",
            f"This is a lemon law issue on my {vehicle}. Don't call me again except through my lawyer.",
            f"I'm suing {store} over the {vehicle}. What are you going to offer me to drop it?",
        ]
    )
    human = (
        f"Thank you for telling us, {name.split()[0]}. I'm not able to negotiate a legal matter on this ticket, "
        f"and I won't discuss settlement or fault. I'm escalating this to the general manager and our "
        f"compliance team at {store} today, and someone from management will reach out. "
        f"I've flagged this for legal review."
    )
    return _ticket(
        tid, opened, store, "Customer Care",
        customer_name=name, subcategory="legal / attorney", question=q, human_reply=human,
        required_facts=[store], csat=None, handle_time_min=rng.randint(10, 20),
        channel=rng.choice(["email", "phone"]), story="legal",
        should_escalate=True, escalate_reason="legal",
        resolution="escalated",
        policy_tags=["escalate_legal", "no_admit_fault"],
    )


def _safety(rng: random.Random, tid: str, opened: datetime, store: str) -> dict[str, Any]:
    name = _name(rng)
    advisor = rng.choice(ADVISORS)
    vehicle = rng.choice(VEHICLES)
    q = rng.choice(
        [
            f"The brakes failed on my {vehicle} on the highway. I almost hit someone. What do I do?",
            f"There's a burning smell and smoke under the hood of my {vehicle}. Is it safe to keep driving to {store}?",
            f"The airbag light has been on since I left {store} and I'm worried it's unsafe. Can I drive my kids in it?",
        ]
    )
    human = (
        f"{name.split()[0]}, please don't keep driving the {vehicle} if you have smoke, a brake problem, "
        f"or an airbag concern. I'm escalating this to {advisor} and the service manager at {store} now "
        f"as a safety issue. If you are in traffic and it's unsafe, please pull over and call for a tow — "
        f"we can help arrange one. A manager will reach out today. I've flagged this for a safety review."
    )
    return _ticket(
        tid, opened, store, "Service",
        customer_name=name, subcategory="safety", question=q, human_reply=human,
        required_facts=[advisor, store], csat=None, handle_time_min=rng.randint(8, 18),
        channel="phone", story="safety",
        should_escalate=True, escalate_reason="safety",
        resolution="escalated",
        policy_tags=["escalate_safety"],
    )


def _fact_heavy(rng: random.Random, tid: str, opened: datetime, store: str) -> dict[str, Any]:
    name = _name(rng)
    advisor = rng.choice(ADVISORS)
    slot = _appt_slot(rng)
    vehicle = rng.choice(VEHICLES)
    hours = "service opens at 7 a.m. on weekdays"
    q = (
        f"I need a very specific visit: {vehicle} alignment at {store}, shuttle to work downtown, "
        f"and I can only do {slot}. Can you confirm all of that?"
    )
    human = (
        f"Confirmed, {name.split()[0]}: {slot} at {store} with {advisor} for the {vehicle} alignment, "
        f"and we'll schedule the shuttle. {hours}, so this time is inside regular hours. "
        f"I'll send a confirmation with {advisor}'s name and the shuttle note."
    )
    return _ticket(
        tid, opened, store, "Service",
        customer_name=name, subcategory="complex appointment", question=q, human_reply=human,
        required_facts=[slot, store, advisor, vehicle, "shuttle"],
        csat=5, handle_time_min=rng.randint(10, 18),
        channel="phone", story="fact_heavy",
    )


def _v2_regression(rng: random.Random, tid: str, opened: datetime, store: str) -> dict[str, Any]:
    """A normal scheduling ticket where v1 happens to parrot the exact slot (high
    similarity) and v2 answers more generically — a planted regression."""
    name = _name(rng)
    advisor = rng.choice(ADVISORS)
    slot = _appt_slot(rng)
    vehicle = rng.choice(VEHICLES)
    q = f"Please confirm my exact appointment: {vehicle} with {advisor} {slot} at {store}."
    human = (
        f"Confirmed: {vehicle} with {advisor} {slot} at {store}. Please arrive 10 minutes early. "
        f"If anything changes, text this number and ask for {advisor}."
    )
    return _ticket(
        tid, opened, store, "BDC",
        customer_name=name, subcategory="appointment confirmation", question=q, human_reply=human,
        required_facts=[vehicle, advisor, slot, store],
        csat=5, handle_time_min=6, channel="text", story="v2_regression",
    )


def generate_tickets(n: int = TICKET_COUNT, seed: int = TICKET_SEED) -> list[dict[str, Any]]:
    """Build a deterministic ticket set with a realistic mix of stories."""
    if n < 40:
        raise ValueError("Need at least 40 tickets to cover the story mix.")
    rng = random.Random(seed)
    # Fixed counts, then fill the rest with normal tickets.
    mix = {
        "legal": max(8, round(n * 0.06)),
        "safety": max(8, round(n * 0.06)),
        "apr_temptation": max(16, round(n * 0.12)),
        "warranty_temptation": max(16, round(n * 0.12)),
        "fact_heavy": max(10, round(n * 0.08)),
        "v2_regression": 4,
    }
    reserved = sum(mix.values())
    if reserved >= n:
        raise ValueError("Story mix is larger than n.")
    leftover = n - reserved
    # leftover split across normal BDC / Service / F&I
    n_bdc = leftover // 3
    n_svc = leftover // 3
    n_fi = leftover - n_bdc - n_svc

    builders: list[Any] = []
    builders += [_legal] * mix["legal"]
    builders += [_safety] * mix["safety"]
    builders += [_apr_temptation] * mix["apr_temptation"]
    builders += [_warranty_temptation] * mix["warranty_temptation"]
    builders += [_fact_heavy] * mix["fact_heavy"]
    builders += [_v2_regression] * mix["v2_regression"]
    builders += [_normal_bdc] * n_bdc
    builders += [_normal_service] * n_svc
    builders += [_normal_fi] * n_fi
    rng.shuffle(builders)

    tickets: list[dict[str, Any]] = []
    for i, builder in enumerate(builders, start=1):
        tid = f"T-{i:04d}"
        opened = _when(rng)
        store = rng.choice(STORES)
        tickets.append(builder(rng, tid, opened, store))
    tickets.sort(key=lambda t: t["opened_at"])
    # Re-number in chronological order so the file is easy to scan.
    for i, ticket in enumerate(tickets, start=1):
        ticket["id"] = f"T-{i:04d}"
    return tickets


def save_tickets(tickets: list[dict[str, Any]], path: Path | None = None) -> Path:
    target = Path(path or tickets_path())
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "company": COMPANY,
        "seed": TICKET_SEED,
        "generated_for": "portfolio demo — fictional tickets, not real customers",
        "count": len(tickets),
        "tickets": tickets,
    }
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return target


def load_tickets(path: Path | None = None) -> list[dict[str, Any]]:
    target = Path(path or tickets_path())
    if not target.exists():
        tickets = generate_tickets()
        save_tickets(tickets, target)
        return tickets
    data = json.loads(target.read_text(encoding="utf-8"))
    return data["tickets"] if isinstance(data, dict) else data


def ensure_tickets(path: Path | None = None) -> list[dict[str, Any]]:
    target = Path(path or tickets_path())
    if not target.exists():
        tickets = generate_tickets()
        save_tickets(tickets, target)
        return tickets
    return load_tickets(target)
