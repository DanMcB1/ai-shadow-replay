# Historical Shadow Replay Harness

**Portfolio project #10 of 12** from [@suraj_sharma14's FDE project list](https://x.com/suraj_sharma14/status/2125197762752806998).

A small, local demo that **replays historical support tickets through a candidate AI agent in shadow mode**, scores the replies against what a human actually said, and produces a go / no-go readiness call before anything is shown to a customer.

This is a **portfolio demo**, not production software. The tickets are fictional. The default agents are local rule-based mocks, not a live model. No customer ever sees the AI output. The rubric is a deterministic checklist, not a certified QA process.

Built for **Daniel McBrearty** as part of a Forward Deployed Engineer / solutions engineer portfolio. The sample company is **Lakeside Auto Group**, the same fictional mid-size dealer group used in the other portfolio demos.

## Why this matters for FDE work

A dealer group will not let a new BDC or service assistant take live calls just because the prompt looks good. They review call recordings first. The same instinct applies to an AI agent: **prove it is safe on real history before go-live**.

A Forward Deployed Engineer is often the person who has to set that up, in language a desk manager and a compliance lead will both accept:

- run the candidate against last quarter's tickets, not a handful of happy-path examples
- score policy (don't quote an APR or a payment, don't promise warranty coverage, escalate legal and safety)
- check that the required facts are in the reply, and that it still sounds like the store
- compare two prompt or policy versions side by side
- show the regressions — the tickets that got *worse*
- write down a clear go / no-go bar, and keep the runs so you can compare next week

This harness is a practice version of that pre-go-live artifact.

## Quick start

You need Python 3.10+ (3.13 is fine). No account, no cloud key, no internet after the packages are installed.

```bash
git clone https://github.com/DanMcB1/ai-shadow-replay.git
cd ai-shadow-replay
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Or: `./run.sh`

The app opens in your browser (usually [http://127.0.0.1:8510](http://127.0.0.1:8510) if you use `./run.sh`). On first load it shadow-replays the 200-ticket set through **v1** and **v2** and stores the runs in a local SQLite file.

Useful command-line entry points:

```bash
python -m replay generate
python -m replay run --agent v2
python -m replay run --agent v2 --compare
python -m replay export --out examples/v1-vs-v2-report.md
python -m unittest discover -s tests
```

An optional OpenAI-compatible or Ollama backend is supported with `SHADOW_REPLAY_LLM_BASE_URL` (and optional `SHADOW_REPLAY_LLM_API_KEY`, `SHADOW_REPLAY_LLM_MODEL`) and `--agent external`. It is **off by default**.

## What’s on the screen

- An honest banner that this is a demo, not a live customer system
- Side-by-side **go / no-go** cards for v1 and v2, with policy pass rate, critical violations, similarity to the human reply, and escalation recall
- **Pass rate by category** (BDC, Service, F&I, Customer Care) against the 90% policy bar
- A **regressions** table — tickets v2 got worse on — with the human, v1, and v2 replies
- **Worst failures** with a word-level diff against the historical human reply
- A ticket inspector, Markdown / CSV export, and a history of stored runs

A saved example of the Markdown report is in [`examples/v1-vs-v2-report.md`](examples/v1-vs-v2-report.md).

## How it works

1. **Tickets.** `python -m replay generate` writes 200 fictional Lakeside tickets with a fixed seed (`10`). They cover BDC (hours, test drives, inventory), Service (appointments, status, warranty, safety), F&I (stipulations, funding, APR/payment questions), and Customer Care (legal). Each row has the customer question, the human agent's reply, resolution, CSAT, handle time, required facts, and whether the case should have been escalated.
2. **Shadow run.** A candidate agent writes a reply for every ticket. That reply is scored and stored. It is never sent to a customer.
3. **Default agents.** **v1** is a sloppy mock: it invents a $389 / 6.9% APR quote, promises warranty coverage, and talks past legal and safety issues. **v2** is an improved mock: it refuses those quotes, will not promise coverage, and escalates legal and safety cases to a manager. Both are rule/template based so the demo is offline and repeatable.
4. **Rubric.** Policy rules are regular expressions (APR, monthly payment, warranty promises, escalation language). Required facts are a simple “is this phrase in the reply” checklist. Tone and length are band checks. Semantic similarity is local TF-IDF cosine against the human reply. A missed legal or safety escalation is a **critical** fail, same as an APR quote.
5. **Gate.** The demo bar is **≥ 90% policy pass** and **0 critical violations**. On the seeded set, v1 is a no-go and v2 is a go, with a handful of planted regressions on exact appointment confirmations (v1 copies the slot; v2 is more generic).
6. **Store.** Each run is appended to `data/replay.sqlite` (gitignored) so you can compare versions over time.

## Honest limitations

- This is a **demo**. Lakeside Auto Group is fictional. No real customer, contract, or warranty file was used.
- The default “agents” are **templates**, not a production model. They are written so v1 fails the policy rules and v2 passes them, with a few intentional regressions.
- The rubric will **miss** some bad answers and can **false-flag** others. A payment-like dollar amount with the right wording is flagged; a number written in words may not be. That is the point of showing the rule, not hiding it.
- Similarity is bag-of-words TF-IDF, not a neural embedding. It is good enough to rank “sounds like the human” and honest about what it is.
- The go/no-go bar is a **demo threshold**, not a customer's risk appetite, and not legal advice.
- Identity and authorization are not modeled. There is no SSO, and no live ticketing system.

## What a production version would add

- A real historical extract from the customer's BDC / service / F&I ticketing or call-transcript store, with PII handled under their policy
- Human review on a sample of disagreements, not only automatic scores
- A maintained policy pack (fair lending, advertising, warranty language) signed off by compliance, not just a few regexes
- The customer's actual candidate model or prompt, behind the same shadow path, with no send-to-customer side effect
- Stronger semantic scoring (approved embeddings) plus outcome metrics — did the customer still come in, was the ticket reopened
- Per-store and per-role views, and a change log when the prompt or the rubric moves
- Retention, access control, and an export path for the compliance team

## Project layout

```
ai-shadow-replay/
  app.py                 Streamlit UI (v1 vs v2, gate, regressions)
  run.sh                 One-command launcher
  requirements.txt
  README.md
  LICENSE                MIT, Copyright (c) 2026 Daniel McBrearty
  DEMO_SCRIPT.md         ~1-minute talk track for interviews
  replay/                Tickets, agents, rubric, store, CLI
  data/tickets.json      Seeded fictional ticket set (committed)
  examples/
  tests/
  screenshots/
```

## For interviewers

Start `./run.sh`, point at the two gate cards (v1 no-go, v2 go), then open **Regressions** or **Worst failures** and read one ticket out loud — a payment question where v1 quotes $389 at 6.9% APR, or a brake-failure ticket v1 tells the customer to keep driving. The talk track is in [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md).

Daniel’s background is car sales, F&I, and auto software sales (Dealr.cloud), not professional ML-evaluation engineering. This project is meant to show he understands **why you rehearse an agent on history the way you’d review a new BDC rep’s call recordings, and why a go-live decision needs a bar you can defend**.

## License

This project is released under the [MIT License](LICENSE). Copyright (c) 2026 Daniel McBrearty.
