---
slug: check-we-can-extend-coga-recurring
title: check we can extend coga recurring
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/recurring
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

Answer, then fix, one question: **can Coga's recurring system drive one of
our own task-specific tickets/workflows, or is it effectively locked to the
built-in template shape?**

First investigate the recurring engine and confirm — **against the code, not
against this ticket's framing** — what a recurring template can and cannot
carry: in particular whether a template can point at an arbitrary `workflow:`
and set of `contexts:` so a normal, task-specific ticket (not just Dream / the
bundled janitors) fires on a schedule. Then **document the answer** by folding
the durable "here's how you extend recurring with your own ticket" write-up
into the `coga/recurring` context.

The expected outcome is doc-only. The passthrough appears to already work, so
if the investigation confirms task-specific tickets are already supported, the
correct disposition is: document the yes/answer and its constraints in
`coga/recurring` and close — do **not** manufacture a code change to justify
the workflow. Only ship a code change if the investigation surfaces a *genuine*
gap that blocks a task-specific recurring ticket from working, and even then,
if the fix is large or separable, spin it into a follow-up ticket named in the
PR rather than expanding this one.

Done looks like: a clear yes/no (with the real constraints named) is
documented in `coga/recurring`; the claims in that write-up are verified
against `recurring.py` / `recurring_runner.py`, not just asserted; and either
no code change was needed (the common case) or a small blocking gap was fixed
in the same PR.

## Context

The recurring subsystem already exists and is well-developed — this is an
"extend/verify", not a "build from scratch". Start here:

- **Context to read first:** `coga/recurring` (attached) — defines a recurring
  task as a ticket-format directory `coga/recurring/<name>/ticket.md` with a
  cron `schedule`, whose frontmatter *already* passes `workflow`, `contexts`,
  `owner`, `assignee`, `watchers` through to the created period task. That
  passthrough is the crux of the question: on paper a template can name any
  workflow, so the answer is likely "substantially yes, with constraints" —
  the job is to prove it and pin the constraints.
- **Code:** `src/coga/recurring.py`, `src/coga/recurring_runner.py`,
  `src/coga/commands/recurring.py`, `src/coga/period_state.py`. The scan +
  get-or-create + launch path is where any real limit will live (fixed period
  task path `coga/tasks/recurring/<name>/`, blackboard not carrying across
  runs except in the template, script-vs-agent deduction, one-step-workflow
  rules for script-backed templates).
- **Related patterns:** the spool/consumer pattern in
  `coga/contexts/coga/patterns/SKILL.md` and the per-firing rules in
  `coga/contexts/coga/period-task/SKILL.md` — read these if the extension
  touches cross-run state or period-task behavior. (Referenced here rather than
  attached to keep the launch prompt lean; read them from disk if needed.)

Already spot-checked against the code during ticket authoring (verify, then
build the write-up on these anchors — don't just re-assert them): the
`workflow` + `contexts` passthrough works (`recurring.py:634-651`,
`_create_at_slug`); there is one instantiated task per template with a stable
slug (`_live_task_for_template`, `_recurring_slug`); the run blackboard is
recreated fresh each firing; a ticket-level `script:` forces every step to run
as a script (`is_script_launch` true whenever `ticket.script` is set,
`launch_script.py:41`, re-checked per step at `launch.py:438`), so it only fits
a one-step workflow; agent templates need a TTY while script templates run
headless (TTY gate at `recurring.py:394,423`). The likely conclusion is
therefore "yes, task-specific tickets are already supported" — your job is to
confirm that holds and document it precisely, not to assume it.

Constraints to name explicitly in the write-up (they are the "or not really"
half of the answer): the instantiated task path is fixed to one per template;
the run blackboard is recreated fresh each firing so cross-run state must live
in the template's own blackboard; a ticket-level `script:` runs on every step
so it only fits a one-step, ungated workflow; agent templates need a TTY /
REPL supervisor while script templates run headless.

Testing note: the primary deliverable, the `coga/recurring` context, is **not
a packaged context** — only four context SKILLs ship under
`src/coga/resources/templates/coga/contexts/` and `coga/recurring` is not one
of them, so there is no packaged copy to keep in sync. Do not go looking for
or create one. The repo↔packaged sync rule only bites if this ticket ends up
touching recurring *code* or the shipped recurring *templates* under
`src/coga/resources/templates/coga/recurring/`; if it does, run
`python -m pytest` and `coga validate --json` and mind the recurring
clean-checkout-only failure modes noted in `coga/contexts/coga/codebase`.

Scope boundary: this ticket is scoped to making task-specific recurring
tickets *possible and documented*. Do not build out a specific production
recurring job here — if the investigation surfaces a large, separable code
change, spin it into a follow-up ticket rather than expanding this one.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
