---
title: Measure Relay prompt scope (precision comparison scoped, not measured)
status: draft
mode: interactive
owner: nick
human: nick
agent: codex
assignee: codex
contexts:
- relay/principles
- relay/codebase
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

This ticket originally bundled two things under one title: (1) measure Relay's
**prompt scope** by layer, and (2) measure Relay's **agent precision** against an
ordinary agent session. Those are not the same kind of problem, and conflating
them oversold what the work could honestly deliver. This rewrite separates them.

**Part 1 — prompt-scope accounting — is done and useful.** `relay launch
--prompt-report` prints a read-only, per-layer breakdown of the composed prompt
(bytes + approximate tokens for base prompt, mode prompt, rules, repo context,
each ticket context, the workflow skill, the blackboard, and the ticket body),
plus a total. Token counting is dependency-free (characters / 4). It does not
activate drafts, lock, post to Slack, or spawn an agent — it stays read-only per
the `relay/principles` contract. This is the part that earns its keep: it makes
prompt bloat visible, and it already paid for itself by exposing that this
ticket's own contexts could drop 6→3 refs (~9.1k→~6.4k tokens).

**Part 2 — agent precision vs. a normal agent — is well-described but not
built, and is largely not cheaply buildable.** "Is Relay more precise / cheaper
than a normal agent?" is a controlled-experiment question: it needs matched runs
and enough of them to beat noise. The original task description itself said *do
not build a benchmark* — which is correct, but it means the honest answer is "we
can't settle this with cheap tooling," not "we measured it." Nothing in the
shipped work measures precision, and the title should stop implying otherwise.

So the real remaining scope is narrow: instrument the precision-adjacent signals
that **already exist on disk**, and explicitly decline the normal-agent
comparison as a measured claim.

## Context

Origin: the question "does Relay reduce token/cost and increase precision versus
a normal agent?" Working answer: precision *should* improve from explicit
task/workflow/context state and blackboard continuity, but token cost is only
justified when those tokens prevent rediscovery, wrong turns, human correction,
or failed handoffs — and proving that requires comparison we cannot do cheaply.

Design nuance to preserve: Relay's intended model is **not** "dump every context
into every launch." A ticket selects the relevant contexts; the workflow step
selects the relevant skill. Today the repo may still attach broad context as a
temporary product-stage baseline — that is something to *measure and control*
with `--prompt-report`, not the target design. (The companion change tightened
`bootstrap/ticket` so `contexts:` are treated as prompt payload, not labels.)

Why the split matters: `--prompt-report` is deterministic, filesystem-only, and
fits the principles. A precision A/B is a research project with no clean answer
and a high risk of producing a noisy number that reads as proof. Keeping them in
one ticket made the deliverable look bigger and more certain than it is.

## Outcome (shipped)

- `src/relay/compose.py` builds a `PromptComposition` of per-layer `PromptLayer`
  metadata; `compose_prompt()` stays compatible.
- `relay launch --prompt-report` prints the read-only layer report and exits.
- README, `docs/spec.md`, and the `relay/cli` context document the report and the
  scoped-context direction.
- `bootstrap/ticket` (live skill + packaged template) now states the
  context-selection contract; a template test covers it.
- Verified: `pytest` green (249), `relay validate --json` clean.

## Acceptance criteria

Done (part 1):

- [x] Lightweight per-layer prompt-scope report for composed launches (base
      prompt, mode, rules, repo context, each ticket context, workflow skill,
      blackboard, ticket body) with a total.
- [x] Report names the exact context and skill refs included for a task.
- [x] Token counting is dependency-light (characters / 4); exact tokenizer
      parity not required.
- [x] Current broad/all-context behavior is visible as a baseline; scoped-context
      direction documented.
- [x] Focused tests for `compose.py` / launch output.

Remaining (part 2 — narrow, on-disk only):

- [ ] Surface the precision-adjacent signals Relay *already records*: e.g.
      turn/tool-call counts and human-correction counts recoverable from
      `log.md` / blackboard diffs, and a cold-relaunch continuity check (can a
      fresh session continue from ticket + blackboard + selected contexts
      alone?). Report what's cheaply available; do not invent telemetry.

Cut (do not attempt under this ticket):

- [ ] ~~A real-task comparison of Relay vs. a normal agent session as a measured
      claim.~~ Not cheaply answerable; would require matched, repeated runs.
      Treat as an explicit non-goal, not a TODO.

## Out of scope

- Paper-grade benchmarking, or any measured "Relay vs. normal agent" claim.
- Claims about all repos or all agent models. Output must distinguish precision,
  up-front prompt size, total task cost, and avoided rework — and must not assert
  Relay is always cheaper.
- A server, database, telemetry daemon, or opaque usage tracker.
- Replacing ticket-selected contexts with a global context dump as the desired
  long-term behavior.
