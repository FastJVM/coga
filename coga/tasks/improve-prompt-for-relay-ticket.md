---
slug: improve-prompt-for-relay-ticket
title: improve prompt for relay ticket
status: in_progress
autonomy: interactive
owner: nick
human: nick
agent: codex
assignee: codex
contexts: []
skills: []
workflow:
  name: autonomy/assist-only
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: human
  - name: report-to-relay
    skills: []
    assignee: agent
step: 1 (agent-produces)
---

## Description

Investigate how Relay's ticket-creation interview (the `bootstrap/ticket`
skill that runs `relay ticket`) could be improved, and produce a concrete
**proposal** — not edits. The interview is suspected of asking too few or the
wrong questions, so tickets sometimes launch underspecified. Study the current
flow, let the investigation surface the real weak spots rather than assuming
them, and propose specific changes: better/different interview questions,
ordering or flow changes, and places the interview drops context it should
capture.

The deliverable is a written proposal (weak spots found, with examples from
real tickets; specific question/flow changes, ranked) on this ticket's
blackboard for the human to review. A separate follow-up ticket implements
whatever is accepted. **Do not edit the skill in this ticket.**

## Context

- The interview being studied:
  `relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md` — the live skill behind
  `relay ticket`. A packaged copy lives at
  `src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md`;
  note it for the future implementation ticket, but make no edits here.
- Prior art on ticket quality — read before proposing, so the work doesn't
  duplicate what already exists:
  `relay-os/bootstrap/skills/eval/ticket-diagnostic/SKILL.md` (a ticket
  diagnostic) and the step-6 evaluator review already baked into creation.
  Note the `ticket-diagnostic` skill is itself half-finished (it still
  contains a `<<YOU NEED TO BE MORE SPECIFIC HERE>>` placeholder) — treat it as
  a signal of intent, not polished prior art.
- Step 3 of the interview runs the autonomy triage in
  `relay-os/contexts/autonomy/triage/SKILL.md`. Any proposal touching the
  autonomy question must stay consistent with it.
- Keep it lean: the skill deliberately targets a short 4–6 question interview,
  and Relay is markdown-first and optimizes for human legibility and a tight
  correction loop (`docs/vision.md`,
  `relay-os/contexts/relay/principles/SKILL.md`). Heavier is not automatically
  better — adding questions has a real token/precision cost.
- Evidence: skim a handful of real filled tickets — they live in two layouts,
  flat `relay-os/tasks/<slug>.md` and nested
  `relay-os/tasks/<group>/<slug>/ticket.md` (so glob `relay-os/tasks/*.md` and
  `relay-os/tasks/**/ticket.md`, not `tasks/*/ticket.md`). Find where the
  current interview produced thin `## Description` / `## Context` sections and
  cite those as concrete motivation — but don't assume every thin ticket is the
  interview's fault; a thin answer or a skipped step can cause the same, and
  the proposal should distinguish them.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

(Independent cold read of the filled ticket, step 6 of bootstrap/ticket. Two
items below were fixed in the body after this review: the broken
`tasks/*/ticket.md` evidence glob, and a caveat that ticket-diagnostic is
half-finished. The assignee/human ambiguity is left for the human to resolve.)

**Description — clear enough to start cold? Yes.**
- Cleanly states the task (investigate the `relay ticket` interview, produce a proposal), the deliverable (ranked weak-spots write-up on the blackboard), and the hard boundary (no edits, repeated three times). The "let the investigation surface real weak spots rather than assuming them" framing is good — it guards against the agent just rubber-stamping the stated suspicion. A future agent could begin without further questions.

**Workflow fit — `autonomy/assist-only` is a reasonable fit, mild semantic stretch.**
- The shape (agent drafts → human owns/decides → no irreversible step) maps onto the workflow's three steps (`agent-produces` / `human-owns-and-finishes` / `report-to-relay`). Good match for "investigate → proposal doc → human decides."
- Minor mismatch: assist-only's own text frames it for "quality, taste, or differentiating judgment, not feasibility." This task is more analytical/investigative than taste-driven. `autonomy/human-verify` would also fit. Not worth blocking on — assist-only's "call out assumptions/weak spots rather than hiding them" guidance actually suits a proposal doc well — but worth a glance at launch.

**File pointers — one broken glob, the rest accurate.**
- BROKEN: the Evidence bullet says skim "real filled tickets under `relay-os/tasks/*/ticket.md`." That glob matches exactly one file — `_template/ticket.md`. Real tickets live in two layouts: flat `relay-os/tasks/<slug>.md` (47 of them, including this very ticket) and nested `relay-os/tasks/<group>/<slug>/ticket.md` (9, two levels deep). An agent following the pointer literally would find essentially no evidence. Should read `relay-os/tasks/*.md` and/or `relay-os/tasks/**/ticket.md`.
- All other pointers verified present and on-point: `bootstrap/ticket/SKILL.md` (live + packaged copy), `eval/ticket-diagnostic/SKILL.md`, `contexts/autonomy/triage/SKILL.md`, `docs/vision.md`, `principles/SKILL.md`. The claim that a "step-6 evaluator review [is] baked into creation" is accurate (it's step 6 of the ticket skill — the review you are reading is that step).
- Worth flagging to the investigator (not a ticket defect, but material to the actual work): the `bootstrap/ticket` skill itself uses the same wrong `tasks/<slug>/ticket.md` shape throughout, and the `eval/ticket-diagnostic` prior-art skill is half-finished — it contains a literal `<<YOU NEED TO BE MORE SPECIFIC HERE>>` placeholder. The agent should not treat ticket-diagnostic as polished prior art.

**`contexts: []` — correct call.** The material the agent needs is the two skill files and the triage context, all of which are *process/skill* knowledge pointed at by path — exactly what the skill's selection contract says to do (skills aren't attached as contexts; pointers go in the body). `vision`/`principles` are cited for one narrow fact ("keep it lean"), which the contract explicitly says to inline-by-reference rather than attach. No context's full body genuinely needs inlining here. Don't add any.

**Scope — well bounded, single ticket.** Investigate + write proposal, with implementation explicitly deferred to a named follow-up ticket. The three analysis angles (questions / ordering / dropped context) are one cohesive study, not three tickets. Good.

**Assumptions to question before launch:**
- Assignee inconsistency: `owner: nick`, `human: nick`, but `assignee: zach`, `agent: claude`. `zach` is not an agent — relay.toml defines only `claude` and `codex` as agents; `zach` appears solely as a Slack-user mapping (i.e. a person). So it's unclear who the reviewing human is (nick per `human:`, or zach per `assignee:`) and why they differ. Resolve before launch.
- The evidence strategy assumes thin `## Description`/`## Context` sections in past tickets are caused by the *interview*. They could equally come from the human giving thin answers or the agent skipping interview steps. The proposal should not attribute every thin ticket to the questions themselves.
- Assumes a markdown/blackboard proposal is the right deliverable home; that's consistent with Relay conventions, so fine.

Net: solid ticket. One must-fix (the `tasks/*/ticket.md` evidence glob is broken) and one should-resolve (assignee vs human ambiguity). Everything else is in good shape.
