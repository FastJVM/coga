---
slug: review-slack-channels
title: review slack channels
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/important
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

`coga-important` has no automatic producers. The `important=True` route exists
end to end — `[notification.slack].important_webhook` in config,
`SlackChannel.webhook_for` in `src/coga/notification/slack.py:66`, the
`--important` flag on `coga slack` — but the flag is reachable only by a human
typing it, and **no shipped code, recipe, recurring template, or alias calls
it**. The only caller anywhere in the tree is `tests/test_commands.py:863`;
every other hit is documentation or the implementation itself. The result is a
second channel with a webhook, a config path, and a governing context, sitting
empty, while 100% of traffic lands in `coga-flow`.

This ticket gives `coga-important` its first automatic producers by routing
four **failure** events there. It does **not** widen the bar defined in
`coga/important`: each of the four is an unattended machine failure whose only
ticket is a *generated* recurring period task that nobody owns as a queue —
unlike a hand-owned blocked ticket, which `coga/important` correctly excludes
because "the ticket itself is already the queue." A generated period task is
nobody's queue; if its failure is not broadcast, nobody looks. Blockers,
blocker reminders, done/canceled outcomes, the daily digest, launch starts, and
`bump --message` all stay in `coga-flow`, and every currently silent lifecycle
event stays silent.

The audit behind this ticket also found that `coga/sync`'s live-surface
inventory is no longer exhaustive; correcting it is in scope.

## Context

### The four events to route

| # | Emitter | Current call | Why it qualifies |
|---|---|---|---|
| 1 | Recipe failed (non-zero exit) | `src/coga/recurring_runner.py:809` — `post(...)` | The task is left unfinished and needs diagnosis; no ticket queues it. |
| 2 | Recurring scan errors | `src/coga/recurring_runner.py:2228` — `notify(kind="recurring-error")` | Scheduled work was skipped and templates need repair. |
| 3 | Recurring watchdog timeout | `src/coga/mark.py:704` — `mark_paused` → `notify(kind="recurring-error")` | A wedged run was paused and needs intervention. |
| 4 | Declared period state did not advance | `src/coga/mark.py:321` — `post(...)` inside `_warn_if_state_not_advanced` | The next run silently duplicates work until a human repairs the high-water state. |

Events 2 and 3 are digest-spooled today. **Do not change their cadence.** They
keep spooling; the destination choice applies at delivery, so the installed
digest still aggregates them into one daily post. This means
`notification.notify` needs to carry an important destination through to its
*live fallback* path only (when no digest ticket is installed). A spool record
stays delivery-neutral — `commands/digest.py` owns the aggregate's destination
— so there is never both a live post and a spooled record for one event.

**Consequence, stated so it is not mistaken for a bug:** this repo has the
digest installed (`coga/recurring/digest/spool.md` exists) and the digest stays
in flow per Out of Scope. So in *this* repo events 2 and 3 never reach
`coga-important` — their important route is reachable only on the no-digest
fallback path, which this repo does not take. The honest local count is **two**
new important producers (events 1 and 4); events 2 and 3 are correctness work
for repos without a digest. Both still need the digest/no-digest test pair.

**Hazard for event 3:** `mark_paused` has three callers and only one of them
notifies. `src/coga/commands/mark.py:125` (manual `coga mark paused`) and
`src/coga/recurring_runner.py:1998` (non-timeout unfinished pause) pass no
`slack_text` and are silent; only `src/coga/recurring_runner.py:1974` (the
timeout path) passes it. Hardcoding the important destination at `mark.py:704`
inside the existing `if slack_text is not None:` guard is safe. Threading a
routing parameter through `mark_paused` instead risks giving the two silent
callers a notification — which would violate the "no currently silent event
becomes a notification" criterion. Prefer the hardcoded form.

### Decision: fail-loud is preserved everywhere (owner call)

`SlackChannel.webhook_for(important=True)` currently raises rather than falling
back to the flow webhook, and the shipped template leaves `important_webhook`
commented out (`src/coga/resources/templates/coga/coga.toml:87`). **Keep that
behavior unchanged for both automatic and manual routes.**

Accepted cost, stated explicitly so it is not rediscovered as a bug: once these
routes are automatic, a repo that has not exported
`COGA_IMPORTANT_WEBHOOK_URL` will crash the first time a recipe fails — and
because all four events are themselves failures, the crash destroys the failure
notification that triggered it. This repo is not exposed:
`coga/coga.toml:69` sets `important_webhook` and the variable is exported, so
the risk is a downstream-repo concern.

**Blast radius (larger than a lost notification).**
`src/coga/recurring_runner.py:699-701` calls `_run_recipe_task` with no
`try/except` — it only inspects the returned code. A `typer.Exit(1)` raised
from the important post at line 809 propagates out of the *scan loop*, so a
misconfigured repo skips every remaining due task and the end-of-run
`_broadcast_scan` summary. One unconfigured webhook silently halts the whole
recurring run.

**The owner was shown this blast radius and confirmed fail-loud anyway, with no
call-site guard.** Do not wrap `recurring_runner.py:809` to contain it and do
not reopen the decision — the `coga validate` warning is the chosen mitigation,
which is why that criterion is not optional.

**Event 4 is fail-quiet, not fail-loud.** `webhook_for` raises `typer.Exit`,
whose MRO is `(click.exceptions.Exit, RuntimeError, Exception, BaseException,
object)`, and the guard at `src/coga/mark.py:331` is a bare `except Exception`.
So a missing `important_webhook` on the period-state warning is swallowed and
degraded to a stderr line. Preserve that guard as-is (see the criterion about
not undoing a successful `mark done`) and accept that event 4 does not fail
loud. Do **not** narrow the guard as part of this ticket.

Treat configuring the second webhook as an operational prerequisite, make that
prerequisite explicit in `coga/sync` and the shipped template comment, and add
a `coga validate` warning when `[notification].channels` includes slack and
`important_webhook` is unresolved — a warning at validate time is consistent
with a crash at post time and converts a 3am blackout into a setup-time nudge.
`src/coga/notification/__init__.py:52` already exposes
`preflight_post(cfg, *, important=False)` (used by `commands/block.py:74` and
`commands/launch.py:600`); consider it alongside the validate warning.

### `coga/sync` inventory is stale

`coga/contexts/coga/sync/SKILL.md` is 50 KB — **read it, do not attach it**; the
facts needed here are copied above. The two anchors you need are its live
surface at `:35-48` and its "Live callers (`post`)" list at `:280-289`; both
enumerate the same five — `block`, blocker reminders, `coga slack`,
`bump --message`, `launch`. The audit found four live posters absent from both:

- `src/coga/mark.py:321` — stale declared period state (moving to important, #4)
- `src/coga/recurring_runner.py:809` — recipe failure (moving to important, #1)
- `src/coga/dream_validate_drift.py:426` — Dream drift summary (**stays flow**)
- `src/coga/commands/megalaunch.py:147` — megalaunch drain summary (**stays flow**)

Update the inventory so it is exhaustive again, including the two that stay in
flow.

### Prior art — read but do not trust

`coga/tasks/v2/move-some-alerts-to-coga-important-instead-of-coga.md` is paused
at `review-design` with a 19-row source-derived routing matrix. **The owner has
declined its premise** — it widens the bar to "human action or high-signal
outcome" and routes `mark done`, the digest, megalaunch and Dream summaries to
important. This ticket deliberately does not. Its matrix is still useful as a
call-site inventory, but it is stale in at least two places:

- It cites `commands/launch_script.py` **four** times (lines 125, 128, 134,
  135) and that module no longer exists in the tree (only a stale `.pyc`).
- Its last row attributes the Dream drift summary to packaged
  `bootstrap/dream/tasks/validate-drift/run.py::post_slack_summary`; the live
  emitter is `src/coga/dream_validate_drift.py:426`.

Verify every call site against source. That ticket should be canceled once this
one is approved.

### Repo conventions

Per `CLAUDE.md`: behavior changes update the matching context in the same PR,
and the packaged copies under
`src/coga/resources/templates/coga/bootstrap/contexts/coga/` must stay in sync
with the live copies under `coga/contexts/coga/`.

## Acceptance Criteria

- [ ] The four events above deliver to the important webhook; every other
  emitter's destination and cadence is unchanged, and no currently silent
  event becomes a notification.
- [ ] Events 2 and 3 still append exactly one delivery-neutral spool record
  with the current schema when the digest is installed, and reach important
  only through the daily aggregate — never as a duplicate live post.
- [ ] `notification.notify` accepts an important destination and forwards it to
  `post` **only** on the no-digest live-fallback path.
- [ ] `coga slack --important` behavior is unchanged.
- [ ] `webhook_for(important=True)` is unchanged — no fallback added, for
  either automatic or manual routes. Event 4 is the known exception: its
  existing bare `except Exception` at `src/coga/mark.py:331` swallows the
  resulting `typer.Exit`, and that guard is preserved rather than narrowed.
- [ ] `coga validate` warns when slack is a selected channel and
  `important_webhook` is unresolved.
- [ ] `coga/contexts/coga/sync/SKILL.md` separates cadence from destination,
  lists all four new important routes, and its live-surface inventory also
  includes the Dream drift summary and megalaunch drain summary that remain in
  flow.
- [ ] `coga/contexts/coga/important/SKILL.md` keeps its existing bar — no
  rewrite of the tune-out or blocker arguments — and gains a short note that
  unattended failure events qualify under the same "no ticket holds it" test.
- [ ] The shipped template comment at
  `src/coga/resources/templates/coga/coga.toml` states that
  `important_webhook` becomes required once recurring jobs run.
- [ ] Packaged context copies match their live counterparts byte-for-byte,
  verified with `diff -q coga/contexts/coga/<name>/SKILL.md
  src/coga/resources/templates/coga/bootstrap/contexts/coga/<name>/SKILL.md`
  for both `important` and `sync`. They match today, so this starts clean.
- [ ] Tests assert the destination by **webhook URL**, not just an
  `important=True` keyword, with controls proving flow posts still use the
  primary URL and silent paths make no request. Cover: recipe failure, scan
  error (digest and no-digest), watchdog timeout, period-state warning, plus
  unchanged controls for block, blocker reminders, done, launch start,
  `bump --message`, and message-less bump.
- [ ] The period-state warning still cannot undo a successful `mark done` when
  its important post fails (its existing exception guard is preserved).
- [ ] `python -m pytest` and `coga validate --task review-slack-channels` pass.

## Out of Scope

- Widening the bar to outcomes — `mark done`, `mark canceled`, the daily
  digest, megalaunch drain summaries, and Dream summaries stay in `coga-flow`.
- Routing blockers or blocker reminders to important. The owner explicitly
  agreed with `coga/important`'s existing argument that the ticket is already
  the queue.
- Any change to live-vs-digest cadence.
- A flow fallback for a missing `important_webhook` (decided against above).
- `slack_important_recipient` / mention-envelope work, and reviving the closed
  unmerged PR #578.
- Message text, emoji, GIF selection, digest rendering, or the JSONL spool
  schema.
- New route flags such as `bump --important`, or inferring importance from
  message contents.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

*Independent cold read. Verbatim. Findings B1 and B4 plus the factual
corrections have been folded into the ticket body above; B2 and B3 are with the
owner.*

### Verdict

Launchable, but not as-is. The factual base is unusually solid — all four emitter cites are exact — yet two claims are wrong, one acceptance criterion is self-contradictory against real code, and the ticket's headline promise ("gives `coga-important` its first automatic producers … routing exactly four failure events there") is only half true in this repo. Fix the four items in **Blocking** before launch; the rest are notes for the implementer.

### 7. Factual verification

**(a) The four emitter cites — all four are exactly right.** Verified file, line, call kind, and enclosing function: `src/coga/recurring_runner.py:809` `post(` in `_run_recipe_task` inside `if code:`; `src/coga/recurring_runner.py:2228` `notify(kind="recurring-error")` in `_broadcast_scan` inside `if scan.errors:`; `src/coga/mark.py:704` `notify(kind="recurring-error")` in `mark_paused` inside `if slack_text is not None:`; `src/coga/mark.py:321` `post(` in `_warn_if_state_not_advanced` inside `try:`.

Also verified: `SlackChannel.webhook_for` is at `src/coga/notification/slack.py:66`; the commented-out `important_webhook` is at `src/coga/resources/templates/coga/coga.toml:87`; `notify` has no `important` parameter today (`src/coga/notification/__init__.py:233-245`).

Worth adding to the ticket, because it is load-bearing and non-obvious: **#3's cite is safe only because of the `slack_text is not None` guard.** `mark_paused` has three callers — `src/coga/commands/mark.py:125` (manual `coga mark paused`) and `src/coga/recurring_runner.py:1998` (non-timeout unfinished pause) both pass **no** `slack_text` and stay silent; only `src/coga/recurring_runner.py:1974` (the timeout path) passes it. Hardcoding `important=True` at mark.py:704 is therefore correct, but an implementer who instead threads a parameter through `mark_paused` risks violating the "no currently silent event becomes a notification" criterion. Say so.

**(b) "nothing in the repo calls it" — substantially true, one imprecision.** No shipped code, recipe, recurring template, or `coga.toml` alias invokes `coga slack --important`. But `tests/test_commands.py:863` does — that is a test, not "documentation or the implementation itself," and the sentence in the Description overstates. It matters because that test is the natural control for the "`coga slack --important` behavior is unchanged" criterion; the ticket should point at it rather than imply it doesn't exist.

Related-but-clear: `coga/tasks/ship-a-shared-recurring-reminder-engine-battery.md:60` proposes an engine defaulting to `coga slack --important`. That ticket is **canceled**, and `coga/tasks/important-alerts-the-task-owner-drop-important-rec.md` (the `important_recipient` work in Out of Scope) is **done**. No live producer conflicts.

**(c) `commands/launch_script.py` does not exist — confirmed.** Only `src/coga/commands/__pycache__/launch_script.cpython-312.pyc` remains.

**WRONG:** the ticket says the prior-art matrix "cites `commands/launch_script.py` three times." It cites it **four** times — `coga/tasks/v2/move-some-alerts-to-coga-important-instead-of-coga.md` lines 125, 128, 134, 135. Trivial, but this ticket's whole posture toward the prior art is "verify every call site against source," and it fumbles the count in the same sentence.

The "19-row source-derived routing matrix" claim is correct (21 pipe-lines = header + separator + 19 data rows).

**Second stale cite the ticket missed:** that matrix's last row attributes the Dream drift summary to `packaged bootstrap/dream/tasks/validate-drift/run.py::post_slack_summary`. The live emitter is `src/coga/dream_validate_drift.py:426`. The ticket gets the new location right in its own inventory but doesn't flag that the prior art is stale on this row too — relevant since the ticket instructs the implementer to mine that matrix as a call-site inventory.

**(d) Digest-spooled vs live — correct.** Events 2 and 3 go through `notify`, which spools when `recurring/digest/spool.md` exists and otherwise falls back to a live `post` (`src/coga/notification/__init__.py:272-281`). Events 1 and 4 call `post` directly and are live. All accurate.

**The stale-inventory claim checks out.** `coga/contexts/coga/sync/SKILL.md:35-48` lists exactly `block`, blocker reminders, `coga slack`, `bump --message`, `launch`; the parallel "Live callers (`post`)" list at line 280 repeats the same five. A full sweep of `src/coga/` finds live posters at `mark.py:321`, `mark.py:584` (launch start, listed), `mark.py:657` (block, listed), `bump.py:122` (listed), `blocker_reminders.py:135` (listed), `commands/slack.py:59` (listed), `recurring_runner.py:809`, `dream_validate_drift.py:426`, `commands/megalaunch.py:147`, and `commands/digest.py:140` (covered by the digest section). So the four named absentees are right and the list is otherwise complete. `repl_supervisor.py`'s `_notify` is console-only, not a channel post — correctly excluded.

Also verified: the live and packaged context copies currently match byte-for-byte, so criterion 9 starts from a clean baseline; `src/coga/resources/templates/coga/bootstrap/contexts/coga/` is the only packaged location (there is no `templates/coga/contexts/coga/`), so the ticket's path is right; and `validate.py` already has a `severity="warn"` mechanism for criterion 6.

### BLOCKING — problems to resolve before launch

**B1. Two of the four "automatic producers" produce nothing for `coga-important` in this repo.**

This repo has the digest installed (`coga/recurring/digest/spool.md` exists). By the ticket's own design — spool records stay delivery-neutral, `commands/digest.py` owns the aggregate's destination, and the digest stays in flow per Out of Scope — events **2 and 3 will never reach `coga-important` here**. Their important routing is reachable only on the no-digest fallback path, which this repo does not take. The Description opens by promising "its first automatic producers by routing exactly four failure events there"; the honest count for this repo is two (recipe failure, period-state warning).

This may well be what the owner wants, but the ticket never states it, and an implementer will discover it while writing the "scan error (digest and no-digest)" test and reasonably wonder if they've misread the design. Add one sentence to `## Context` saying so explicitly.

**B2. Criteria 5 and 12 contradict each other for event 4.**

- Criterion 5: "`webhook_for(important=True)` still fails loud with no fallback, for both automatic and manual routes."
- Criterion 12: "The period-state warning still cannot undo a successful `mark done` … (its existing exception guard is preserved)."

`webhook_for` raises `typer.Exit(1)`, and `typer.Exit.__mro__` is `(click.exceptions.Exit, RuntimeError, Exception, BaseException, object)`. The guard at `src/coga/mark.py:331` is a bare `except Exception`. So once event 4 is routed to important, a missing `important_webhook` will be **swallowed** and degraded to `[period-state] FYI broadcast failed: 1` on stderr. Fail-loud does not hold for event 4, and the ticket's whole "Decision: fail-loud is preserved everywhere" section is wrong about one of its four events.

Pick one and write it down: (i) accept that event 4 is fail-quiet and say so in the Decision section, or (ii) narrow the guard to `except NotificationDeliveryError` (plus whatever else is intended) so config errors escape while delivery misses are still swallowed. Option (ii) changes existing behavior and needs the owner's sign-off; option (i) is free. Do not leave it for the implementer to arbitrate between two acceptance criteria.

**B3. A misconfigured repo doesn't just lose one notification on event 1 — it aborts the recurring scan.**

`src/coga/recurring_runner.py:699-701` calls `_run_recipe_task` with no `try/except`; the loop only inspects the returned code. A `typer.Exit(1)` raised from the important post at line 809 propagates out of the scan loop, skipping every remaining due task and the end-of-run `_broadcast_scan` summary. The ticket's stated accepted cost is "the crash destroys the failure notification that triggered it" — the actual blast radius is larger. State it, or the owner is accepting a cost they weren't shown.

**B4. The load-bearing justification is weaker than the Description claims.**

"none is already attached to a ticket the owner will see — which is precisely the distinction that context draws." All four events name a ticket (`ref.id_slug` in every message), and events 1 and 3 leave that ticket in a non-terminal state that `coga status` surfaces. `coga/contexts/coga/important/SKILL.md:59-64` argues a blocker is excluded because "the ticket itself is already the queue — the blocker is attached to it and cannot be lost." That argument applies with nearly equal force to a watchdog-paused ticket.

The real distinction — that a generated recurring period task is nobody's queue, unlike a hand-owned blocked ticket — is a good argument and it is **not in the ticket**. As written, criterion 8 asks the implementer to add a note to `coga/important` asserting a "no ticket holds it" test that the four events don't literally pass. Write the actual argument into `## Context` so the context edit has something true to say.

### 1. Is the description clear enough to start cold?

Yes, and unusually so. The four events are enumerated with exact call sites, the destination-vs-cadence split is explained, the rejected alternative (flow fallback) is named with its cost, and Out of Scope closes off the seven adjacent temptations. A cold agent knows what to touch and what not to.

Two gaps beyond the blocking items:

- **`preflight_post` is never mentioned.** `src/coga/notification/__init__.py:52` already exposes `preflight_post(cfg, *, important=False)` and is used by `commands/block.py:74` and `commands/launch.py:600` to catch a misconfigured webhook before committing state. It is the closest existing primitive to the problem criterion 6 solves, and an implementer should at least consider it alongside the validate warning. Point at it.
- **The verification commands are under-specified for the sync path.** Criterion 9 requires packaged copies to match live; the ticket names the paths but not the check. `diff -q coga/contexts/coga/<name>/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/coga/<name>/SKILL.md` is the whole gate and belongs in criterion 14.

### 2. Workflow fit — `code/with-review`

Correct choice, no design step needed. The design work already happened: the prior-art ticket `v2/move-some-alerts-…` is paused at `review-design` precisely because the owner rejected its design, and this ticket is the replacement design written out. Sending it back through `code/design-then-implement` would re-litigate a decision the owner has already made twice.

The peer-review step earns its place here specifically because the four routing changes have subtle blast radius (B2, B3, and the shared-`mark_paused` hazard) that a second reader is likely to catch. `code/with-review` resolves from `src/coga/resources/templates/coga/bootstrap/workflows/code/with-review.md` and matches what every other code ticket in `coga/tasks/` uses.

### 3–4. Attached contexts

`coga/important` (3.2 KiB, matching the layer report exactly) is the right and probably only attachment. It is entirely on-topic, it is the bar the ticket is committing not to widen, and criterion 8 requires the implementer to *preserve* its tune-out and blocker arguments verbatim — which they cannot do from a paraphrase. Attaching it is correct; no fact should have been copied out instead.

Deliberately **not** attaching `coga/sync` (50,851 bytes — the ticket's "50 KB" is accurate) and copying the needed facts into `## Context` is exactly right, and rare enough in this repo's tickets to be worth naming as good practice. It also gives the implementer the two exact anchors (`coga/contexts/coga/sync/SKILL.md:35-48` live surface, `:280-289` live callers) they need to edit without loading the file into the prompt.

Nothing critical is missing. `coga/codebase` would cover the test expectations behind criterion 11, but the criterion already spells out the test matrix in more detail than the context would; attaching it would be pure cost. One caveat: the ticket leans on "Per `CLAUDE.md`" for the sync convention, and `CLAUDE.md` is auto-loaded for Claude but not guaranteed for the Codex peer-reviewer at the `peer-review` step. The convention is restated in `## Context` anyway, so this is fine as written — just don't strip that paragraph.

### 5. Scope

Reasonable, at the upper end. The core (four routes + `notify` plumbing + tests) is one coherent PR. Two riders:

- **Criterion 6, the `coga validate` warning**, is a new user-facing check with its own test surface. It is justified as the mitigation for a cost this ticket introduces, so it belongs here — but it is the first thing to cut if the PR gets unwieldy.
- **The `coga/sync` inventory correction** is explicitly a rider ("The audit behind this ticket *also* found…"). The rows for the two events that move are required by the CLAUDE.md same-PR rule. The rows for Dream drift (`src/coga/dream_validate_drift.py:426`) and megalaunch drain (`src/coga/commands/megalaunch.py:147`), which do **not** change behavior, are scope creep. They are about four lines of markdown and leaving the inventory half-corrected would be worse, so keep them — but don't let them grow into a broader context rewrite.

Not a multi-ticket bundle. The Out of Scope section is doing real work holding it there.

### 6. Assumptions to question

Beyond B1–B4:

- **The digest destination is assumed to stay flow forever.** If the owner ever routes the daily digest to important, events 2 and 3 arrive there by a completely different path with different framing. Not this ticket's problem, but the `coga/sync` note should make the dependency visible.
- **"Treat configuring the second webhook as an operational prerequisite"** is asserted for downstream repos. Verified: this repo has `important_webhook = "env:COGA_IMPORTANT_WEBHOOK_URL"` at `coga/coga.toml:69` with the variable exported, so the fail-loud risk is genuinely a downstream-repo concern, not a self-inflicted one here. That is worth stating — it changes how urgent criterion 6 is.
- **Criterion 11's "silent paths make no request" control** is the one most likely to be skipped, and it is the criterion that actually protects against a sloppy `mark_paused` refactor (see the note under 7a). Keep it.

### 8. Prompt layer sizes

No layer breaches 40%. `base_prompt` (`prompt.md`, 7.3 KiB / 1,858 tokens) is **39.5%** — right at the line, and the only candidate. It is the shared harness prompt, not ticket-authored, so trimming it is out of scope here; flagging it only because it is one edit away from tripping the threshold on every ticket in the repo.

Ticket-authored layers are well-proportioned: `task_context` 22%, `ticket_context` 17%, `task_description` 7%. The 18.5 KiB total is modest for a ticket touching five modules and two contexts, and it is small *because* `coga/sync` was read-not-attached. That trade paid off — do not undo it.
