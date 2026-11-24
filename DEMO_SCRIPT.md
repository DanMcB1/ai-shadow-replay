# Demo script (~1 minute)

A talk track you can say out loud in an interview. Plain language. Practice it once with the app open on the default v1 vs v2 view. You do not need to memorize it word for word.

**Setup:** `./run.sh` is already running and the comparison has loaded. You will point at the two go / no-go cards, then at one failure or one regression.

---

## The talk track

“In a dealership you don’t put a new BDC rep on live calls just because they had a good interview. You sit with them and review call recordings first. That’s the same idea here, for an AI agent.

This is a shadow replay of about two hundred fictional Lakeside Auto Group tickets — BDC, service, F&I. The customer never sees the AI reply. We already have the human’s answer, the CSAT, the handle time, and whether the case should have been escalated.

The scoring is a simple rulebook, not a mystery model. Don’t quote an APR or a monthly payment. Don’t promise warranty coverage. If someone mentions a lawyer, or the brakes failed on the highway, escalate it. Then we check whether the required facts are in the reply, and how close it is to what the human actually said.

v1 is a no-go. It invents a three-hundred-and-eighty-nine-dollar payment at 6.9 percent APR, it promises warranty coverage, and it tells a safety caller they can keep driving. That’s sixty critical violations. v2 clears the bar: 100 percent policy pass, zero criticals, and it escalates the legal and safety cases. There are still a few regressions — confirmation tickets where v1 copied the exact time and v2 got vaguer — so I wouldn’t ship it blind. I’d walk those with the desk manager, then I’d be willing to talk about a supervised pilot.”

---

## Timing notes

Spoken at a normal pace, that is about 50–60 seconds. If you have a few extra seconds, open **Worst failures**, read the payment quote or the “keep driving” line out loud, and stop. Let them ask questions.

If you have two minutes, switch to **Regressions** and show that a go on the gate does not mean every ticket got better.

## If they ask a follow-up

- **“Is this a real model?”**  
  “No. The default agents are local templates, so the demo runs on a laptop with no account and no bill. There’s an optional OpenAI-compatible hook, off by default. The point of the project is the harness and the rubric, not the model.”

- **“Why not just use an LLM-as-judge?”**  
  “I would, as a second opinion, once the customer agreed to it. I started with rules you can point at — this line quoted an APR, this line didn’t escalate a lawyer — because that’s what a compliance lead is going to ask me to show.”

- **“Are these real tickets?”**  
  “No, and I label that. They’re generated with a fixed seed so the story is repeatable: payment questions, warranty questions, legal, safety, and ordinary appointment work. In a real engagement I’d pull a historical extract under their privacy rules.”

- **“Why is v2 not a perfect 100 on facts?”**  
  “I planted a few confirmation tickets where v1 copies the exact slot and v2 is more generic. That’s the regression tab. I wanted a go on policy that still leaves something to talk about with the desk manager.”

- **“What’s the bar?”**  
  “In this demo, 90 percent policy pass and zero criticals. That’s a starting point, not their policy. A group might also require a human review sample, or a higher bar on F&I than on hours questions.”

- **“What would you do on a real dealer group?”**  
  “Agree the policy list with F&I and compliance — especially payment quotes and warranty language. Pull 90 days of BDC, service, and F&I tickets. Run the candidate in shadow only. Sit with a desk manager on the worst failures and the regressions. Keep the runs in a store so the next prompt change is comparable. And don’t turn it on for customers until that gate is green.”
