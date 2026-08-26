---
slug: reconcile-recurring-wrapper-tty-admission-guidance
title: Reconcile recurring wrapper TTY-admission guidance with resolve-conflicts template
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
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
step: 4 (review)
---

## Description

A recurring template whose work is "launch another agent" currently has to
fake a terminal to do it, and two shipped documents disagree about whether
that is sanctioned. Remove the need for the fake terminal.

`recurring/resolve-conflicts` owns only a schedule; its body tells the period
task's wrapper agent to run `coga resolve-conflicts --agent <type>`, which is
an alias for `coga launch bootstrap/resolve-conflicts` (`src/coga/aliases.py:67`).
That is a **double hop**: the recurring supervisor launches an agent, and that
agent shells out to launch a second agent. `coga launch` refuses an agent
launch unless stdin *and* stdout are terminals
(`_interactive_stdio_has_tty`, `src/coga/commands/launch.py:2361`), and an
agent's own Bash tool subprocess has neither — so the inner launch exits 2.

**Owner decision (2026-08-14): fix this structurally, not by wording.** The
wrapper agent must stop shelling out to a nested agent launch. Nothing needs
to manufacture a terminal: `recurring_runner` already runs in the operator's
own terminal and already calls `launch` in-process
(`src/coga/recurring_runner.py:684,709`), so it can launch the delegated
ticket directly instead of launching a wrapper that re-launches it. A
delegating template should *declare* its delegation rather than improvise it
in prose. Candidate mechanisms are in Context; pick one, record the reasoning
in the PR, and see the note there on when that choice has to be made.

Whichever lands, the `script -qec` pty recipe must stop being the sanctioned
pattern, and every document describing the shape must end up saying the same
thing.

**Blast radius: all delegating wrappers.** `resolve-conflicts` is the only
current instance — the inventory in Context was taken for this ticket and
re-verified, so re-confirming it is a few minutes, not a work item. The point
of the wider framing is that the context's gotcha is written as generic
guidance for *any* future wrapper: the deliverable is that the double-hop
shape becomes unnecessary or unavailable going forward, not merely that one
template changed.

## Context

### The two documents that disagree

- `coga/contexts/coga/recurring/SKILL.md:440-455` (under `## Gotchas`) —
  prescribes the workaround: run the delegation under a fake pty,
  `timeout 900 script -qec 'coga resolve-conflicts --agent claude' /dev/null`,
  and confirm success by reading the `bootstrap/resolve-conflicts` `slack:`
  line in `coga/log.md` rather than the captured stream (ANSI noise, plus the
  delegated session is torn down by the done sentinel seconds after its
  roll-up posts).
- `coga/recurring/resolve-conflicts/ticket.md:31` — "Recurring's outer agent
  supervisor remains responsible for TTY admission and the idle/max-session
  liveness bounds over the whole process tree." Also the frontmatter comment
  at line 5: "This template stays agent-backed so recurring's TTY admission
  … govern the whole delegated command."

**The template's sentence is true one level up and false one level down.**
The supervisor genuinely does own TTY admission for the *wrapper* session —
that is why `coga recurring` itself refuses to create an agent-backed period
task without a TTY (`src/coga/recurring.py:430,462`). It does not extend to a
nested launch the wrapper makes from inside its own tool shell. Preserve that
distinction in whatever replaces these passages; a reader who conflates the
two levels reproduces the original bug.

### Why this is a real defect, not a documentation nit

- 2026-08-13: the W33 run followed the template's framing, verified its tool
  shell has no TTY, judged the pty a design bypass, and terminally blocked
  (blocker `20260813T094004`, `coga/log.md:3287`). The sweep never ran.
- 2026-08-14: a rerun found the context section, ruled the pty sanctioned,
  and proceeded — then hit a *different* wall: the agent harness's own
  permission classifier refused to execute `script -qec` (`coga/log.md:3428`).
  W33 still has not swept.

So the wording fix alone would not make this job run unattended; only removing
the shell-out does. That second blocker is evidence for the structural
direction, not separate work — it should be moot once the supervisor performs
the launch.

### Candidate mechanisms, and the design question nobody has answered

These are not equally sound. Weigh them against the taxonomy facts below
before writing code.

**When to decide, and when to stop.** This choice is made before the first
line of code, but `code/with-review` only exposes it to a reviewer after the
implementation exists — so a wrong pick is discovered late and rewritten.
Owner's instruction (2026-08-14): the implement step picks and justifies the
choice in the PR, but if option 1's "who marks the period task done" question
has no clean answer, `coga block` with the specific ask rather than guessing.
All three options stay live; none is pre-rejected.

1. **Declarative delegation field** on the template frontmatter, sibling to
   `recipe:`, honoured by `recurring_runner`'s existing in-process
   `launch_cmd` call. The delegating template stays agent-backed, so the
   pre-create TTY refusals at `src/coga/recurring.py:430,462` keep guarding a
   headless sweep — correct behaviour preserved.
   **Its unanswered question:** every piece of period-task bookkeeping in the
   runner is written against the period `TaskRef` — `mark_in_progress`,
   `_stop_if_unfinished_after_launch`, `_advance_serviced_period`, the log and
   Slack lines. Launching `bootstrap/resolve-conflicts` instead means one
   session on a *bootstrap* ref, with the period task's transitions happening
   around it and no session inside to run `coga mark done`. Settle this before
   committing to the option; it is the actual design work in this ticket.
2. **A fixed `runner.RECIPES` entry** named by the template's `recipe:`.
   **Carries a specific defect — do not choose it without answering this.**
   The recipe/agent split *is* the mechanism of the TTY gate: both raises read
   `if not allow_agent and not template.recipe`. Giving this template a
   `recipe:` moves it into the class explicitly exempt from TTY admission, so
   a headless sweep would create the period task, run the recipe, and only
   then hit the agent-launch refusal at `src/coga/commands/launch.py:546` —
   relocating a clean pre-create refusal into a mid-run failure, which is
   strictly worse for an unattended job. It also contradicts two shipped
   documents (see files to touch). The tempting precedent — "`recurring-scan`
   is already a recipe that launches agents" — does not transfer:
   `recurring-scan` launches agents only because `coga recurring` invoked it
   from the operator's shell, and it re-checks `_interactive_stdio_has_tty()`
   and filters on the result. It is not evidence that recipes have terminals.
3. **No second session at all.** Templates may name a `workflow:`, and `dream`
   already does its work in-session. The delegated work is a stateless prose
   runbook at `coga/bootstrap/resolve-conflicts/ticket.md`; carrying it into
   the period task's own session by context or skill attachment removes the
   double hop with no code change and no new frontmatter field.
   **Its tension:** that runbook explicitly says "do not create a task per run
   … do not run `coga bump` / `coga mark`", which fights the period-task
   lifecycle, and the human-facing `coga resolve-conflicts` alias must keep
   working for on-demand use either way. Ruling this out is fine; ruling it
   out silently is not — record the reason.

### Recurring template taxonomy (what "audit all delegating wrappers" means)

Templates come in two shapes (`coga/contexts/coga/recurring/SKILL.md:121-126`):
a known `recipe:` selects deterministic headless execution; without one the
task is agent-backed and runs under the REPL supervisor.

- `recipe:` — `digest`, `branch-sweep`, `autoclose-merged` (its recipe name is
  `autoclose`, not the template name — grepping `runner.RECIPES` for
  `autoclose-merged` finds nothing), `blocker-reminders`, `skill-update`. No
  agent, no TTY, unaffected.
- agent-backed — `dream` (does its work in-session; fine) and
  `resolve-conflicts` (the only double-hop).

Confirm that inventory still holds at implementation time rather than trusting
it; the deliverable is that the double-hop shape is unavailable or unnecessary
going forward, not just that one template changed.

### Files to touch, and the packaged twin rule

- `coga/recurring/resolve-conflicts/ticket.md` — **has an identical packaged
  twin** at `src/coga/resources/templates/coga/recurring/resolve-conflicts/ticket.md`
  (verified byte-identical). Both must change together, per CLAUDE.md.
- `coga/contexts/coga/recurring/SKILL.md` — repo-local only; there is **no**
  packaged twin (packaged `coga/` contexts live under
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/` and that set
  does not include `recurring`). Do not create one as a side effect.
- `coga/contexts/coga/architecture/SKILL.md:525-527` — states the taxonomy
  this change alters, verbatim: "A recurring template selects this path with
  `recipe:`; without one, its period task is an agent launch and therefore
  needs a TTY." Any mechanism makes that incomplete. **Has a byte-identical
  packaged twin** at
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md`;
  both move together.
- `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md:307`
  — enumerates the recipe registry by name; option 2 makes it stale. **This
  one is packaged-only: there is no `coga/contexts/coga/cli/`.** The usual
  "check the live copy and the packaged copy" habit misses it precisely
  because there is no live copy to start from.
- Code: `src/coga/recurring.py`, `src/coga/recurring_runner.py`, and
  `src/coga/runner.py` / `src/coga/aliases.py` depending on which mechanism is
  chosen. The human-facing `coga resolve-conflicts` alias
  (`src/coga/aliases.py:67`) must keep working unchanged for on-demand use —
  do not repurpose it as part of the fix.
- The microkernel rule in CLAUDE.md constrains option 2: a recipe is a fixed
  name in `runner.RECIPES`, not a plugin, and skills describe how to invoke
  commands rather than supplying launch plugins.

### Acceptance

- **The test that distinguishes a correct fix from a relocated bug:** a
  headless (no-TTY) sweep must still refuse the delegating template at
  *admission* — before the period task is created — and not fail mid-run.
  Name it explicitly in `tests/`.
- An attended sweep runs the delegated conflict work end to end with no
  `script`/pty invocation anywhere in the path.
- `coga validate --json` clean — it statically resolves recurring templates,
  including `recipe:` names against the fixed registry.
- Add tests under `tests/` named for the module changed, per CLAUDE.md.

### Out of scope

- Adding a harness permission rule for `script -qec` to work around the
  2026-08-14 blocker. The structural fix should remove the need; do not ship
  both.
- Running the W33 sweep itself. That is `recurring/resolve-conflicts`'s work,
  currently paused, and it should be re-run by the owner after this lands.
- The conflict-resolution *operation* itself. What the sweep does — which PRs
  it selects, how it rebases, verifies, force-pushes, and rolls up — is not
  changing; only how it gets launched. The runbook at
  `coga/bootstrap/resolve-conflicts/ticket.md` (packaged twin under
  `src/coga/resources/templates/coga/bootstrap/resolve-conflicts/`) is
  therefore edited only if the chosen mechanism forces it — option 3 would,
  and its sentence describing the `coga resolve-conflicts` alias sits in the
  blast radius if the alias path moves.
- `coga/period-task` guidance.

### Provenance

Dream 2026-W33 stale finding F5 (`coga/tasks/recurring/dream/ticket.md:307,374`).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Superseded parallel run (collapsed 2026-08-19)

A second, parallel implementation of this ticket was recorded here from
another checkout: branch `reconcile-recurring-delegation` (commits `a02c3731`
+ `6a07a50a`, worktree `/tmp/coga-reconcile-recurring-delegation`). Its record
claimed implement + codex peer review complete, but those commits exist
neither in this clone nor on origin and the /tmp worktree is gone, so the
record was collapsed in favor of the reachable run below
(`delegate-recurring`). The full text is in this file's git history.

Its peer review found two must-fix failure-path defects in the same design
family — check the surviving implementation for both during peer review:

- a named delegated launch reported success after a watchdog timeout;
- a pre-spawn bootstrap refusal paused the period task even though no
  delegated session ran (an originally-active task should be restored to
  `active`, not parked).

## Plan (implement step, 2026-08-18)

Chosen mechanism: **option 1 — declarative `delegate:` frontmatter field** on
recurring templates, mutually exclusive with `recipe:`.

**The "who marks the period task done" question has a clean answer:** the same
actor that already does it for recipe-backed period tasks — `recurring_runner`
itself. `_run_recipe_task` already owns the full lifecycle around a recipe
subprocess (`mark_in_progress` → run → `mark_done` on exit 0, failure Slack
otherwise). A new `_run_delegated_task` mirrors that exactly, with the
subprocess replaced by an in-process `launch_cmd(<bootstrap ref>)` call:

- period task `active` → `mark_in_progress` (actor `system`) before delegating;
- the delegated `bootstrap/<name>` launch runs in the operator's own terminal
  (the sweep is a foreground command) under the sweep's idle/max-session
  liveness bounds and queue guidance — no nested shell-out, no pty;
- clean return → runner `mark_done`s the period task; liveness timeout →
  `_stop_if_unfinished_after_launch(timed_out=True)` pauses it as a watchdog
  timeout and the sweep continues — both identical to existing recurring
  bookkeeping paths. No session ever runs *on* the period task, so no session
  inside it needs to run `coga mark done`.
- a crashed delegated launch leaves the period task `in_progress`; the next
  sweep resumes it as a dead sweep's orphan and re-delegates — the existing
  orphan-resume rule, unchanged.

**TTY admission preserved at admission:** the gates at
`src/coga/recurring.py` read `if not allow_agent and not template.recipe`; a
delegating template has no `recipe:`, so a headless sweep still refuses it
*before the period task is created*. Option 2 was rejected for exactly this
(recipe class is exempt from TTY admission → mid-run failure); option 3
rejected because the bootstrap runbook is deliberately stateless ("no task per
run, no `coga bump`/`coga mark`") and folding it into the period task's own
session would either violate that contract or fork the runbook into two
copies; the on-demand `coga resolve-conflicts` alias must keep working
unchanged either way.

Changes:
- `src/coga/recurring.py`: `Template.delegate` property + load-time validation
  (non-empty string, `bootstrap/<name>` shape, exclusive with `recipe:`);
  `DueTask.delegate` field; `scan_due` carries it.
- `src/coga/recurring_runner.py`: `_run_delegated_task`; sweep loop and
  `_launch_created`/`run_recurring_named` branch on `delegate` like `recipe`.
- `src/coga/validate.py`: resolve `delegate:` targets via `resolve_bootstrap`
  so `coga validate` rejects unknown targets statically.
- `coga/recurring/resolve-conflicts/ticket.md` + packaged twin: add
  `delegate:`, delete the wrapper instructions and the two-level-conflating
  frontmatter comment.
- `coga/contexts/coga/recurring/SKILL.md` (repo-local only): field docs +
  replace the pty Gotcha with the `delegate:` shape.
- `coga/contexts/coga/architecture/SKILL.md` + packaged twin: taxonomy
  sentence gains the delegate shape.
- packaged-only `.../contexts/coga/cli/SKILL.md`: recurring section notes
  delegate templates are TTY-gated like agent templates.
- Tests in `tests/test_recurring.py`, incl. the acceptance-named
  headless-admission-refusal test.

## Dev

pr: https://github.com/FastJVM/coga/pull/723
branch: delegate-recurring
worktree: /home/n/Code/claude/coga-delegate-recurring

## Implementation result (implement step, 2026-08-18)

Committed as `353e6395` on `delegate-recurring`, rebased onto latest
`origin/main` (`773cb7ad`). Not pushed; no PR (later steps own that).

What landed, per the plan above (no deviations):

- `src/coga/recurring.py`: `delegate:` validated in `Template.load`
  (non-empty string, `bootstrap/<name>` shape, no nested path, mutually
  exclusive with `recipe:`), `Template.delegate` property, `DueTask.delegate`
  field carried by `scan_due`. The TTY admission gates are untouched — a
  delegating template has no `recipe:`, so a headless sweep still refuses it
  pre-create.
- `src/coga/recurring_runner.py`: `_run_delegated_task` mirrors
  `_run_recipe_task`'s lifecycle bookkeeping around an in-process
  `launch_cmd(<bootstrap ref>)` (in_progress → delegated launch → done; a
  liveness timeout routes through `_stop_if_unfinished_after_launch(timed_out=True)`
  → paused, sweep continues). Sweep loop and `_launch_created` /
  `run_recurring_named` branch on `delegate` beside `recipe`.
- `src/coga/validate.py`: `unknown-delegate-target` issue — delegate refs are
  resolved statically via `resolve_bootstrap`.
- Templates/contexts: resolve-conflicts template rewritten (live + packaged
  twin byte-identical; old wrapper steps and the two-level-conflating
  frontmatter comment deleted); recurring SKILL.md gained the `delegate:`
  field doc and its pty Gotcha replaced by the two-level TTY-admission
  explanation + delegate rule; architecture SKILL.md taxonomy sentence
  updated (live + packaged twin byte-identical); packaged-only cli SKILL.md
  TTY-skip paragraph covers delegating templates. Verified there is no
  packaged `recurring` context to create. `coga/bootstrap/resolve-conflicts`
  runbook and the `coga resolve-conflicts` alias untouched.
- Tests: `tests/test_recurring.py` —
  `test_headless_scan_refuses_delegating_template_at_admission` (the
  acceptance-named admission test), delegate declaration rejections,
  `test_delegated_task_launches_target_and_owns_lifecycle` (done/resume/
  timeout parametrization), `test_bare_recurring_launches_delegate_target_directly`
  (sweep launches `bootstrap/resolve-conflicts`, never the period task, and
  the period task ends `done`); `tests/test_validate.py` unknown/valid
  delegate-target cases; `tests/test_packaging.py` wrapper pin updated to pin
  the new shape (delegate field present, no `coga mark done` / `script -qec`
  instructions in the body).

Verification: `python3.12 -m pytest` → 1806 passed, 1 skipped, 3 failed —
the 3 failures (`test_autoclose.py::test_recipe_preflights_live_summary_before_closing`,
`test_recurring.py::test_named_launch_keeps_control_only_malformed_ledger_blocked_on_retry`,
`test_recurring.py::test_sweep_retry_revalidates_control_only_malformed_ledger`)
fail identically on unmodified `main` in this environment (verified by
running them from the primary checkout before any change), so they are
pre-existing and untouched, not masked. Possible follow-up ticket material.
`coga validate --json` from the worktree matches main's issue list except
`missing-user (config)`, which is only the untracked machine-local
`coga.local.toml` not existing in a linked worktree.

Template inventory re-confirmed at implementation time: recipes = digest,
branch-sweep, autoclose-merged (recipe `autoclose`), blocker-reminders,
skill-update; agent-backed = dream (in-session); resolve-conflicts is now the
only `delegate:` template and no template instructs a nested `coga launch` —
the context Gotcha now prohibits the shape generically and names the field
instead.

## Peer review (2026-08-18)

`codex review --base 773cb7ad` found three must-fix failure-path defects:

- `_run_delegated_task` treats both the bootstrap done sentinel and a natural
  zero REPL exit as a clean return, so it can mark the period task `done`
  without the delegated command's required final `coga slack` signal.
- the helper always converts a watchdog timeout to a paused task plus return
  code 0; that is correct for a multi-task sweep that must continue, but makes
  `coga recurring launch <name>` falsely report success and makes retry skip
  the now-paused task.
- the period task is persisted as `in_progress` before bootstrap resolution,
  TTY/CLI/composition/secret preflights. A pre-spawn `SystemExit` therefore
  leaves an originally active task falsely started and orphan-resumable.

Fix direction: expose the bootstrap supervisor's termination kind to the
in-process caller and accept only the done sentinel; give scheduled sweep and
named launch distinct timeout policies; and restore an originally active
period task after a pre-spawn refusal while preserving `in_progress` for a
genuinely spawned crash or a resumed orphan. Add focused regression coverage
before rebasing.

## Peer-review continuation (2026-08-25)

`codex review --base origin/main` on the surviving `delegate-recurring`
branch found three further must-fix integration gaps:

- delegation was read from the current recurring template instead of frozen
  into each materialized period task, so editing or removing a template could
  silently reroute an already-live run; direct `coga launch recurring/<name>`
  also bypassed delegation entirely;
- a `delegate:` target with `ticket.py` could return through launch's script
  path before the delegated lifecycle callback ran, leaving the period task
  eligible for repeated deterministic execution;
- scheduled-sweep watchdog timeouts paused the task but were recorded as
  `unfinished`, losing the timeout classification used by run history.

Confirmed fix direction: make `delegate` an optional canonical, recurring-only
task field copied at creation; make sweep retries, named runs, and direct task
launches route exclusively from that frozen value; reject script-backed
bootstrap delegates before task creation and again when validating a frozen
task (deterministic recurring work belongs in the recurring template's own
`ticket.py`); and return a structured delegated result so callers preserve the
watchdog termination kind. The tradeoff is a small recurring-aware branch in
the ordinary launch path, in exchange for one immutable source of dispatch
truth and no wrapper session.

## Peer-review fixes applied (2026-08-25)

- `delegate` is now an optional canonical field reserved for materialized
  `tasks/recurring/*` tickets. Creation freezes the normalized target there;
  `scan_due`, named launches, and direct `coga launch recurring/<name>` all
  dispatch from the ticket snapshot rather than current template frontmatter.
- Agent delegation now rejects a bootstrap target carrying `ticket.py` before
  a fresh or replacement period task is created. Task/template validation
  reports the same invalid shape, and runtime rechecks a frozen target before
  spawn in case the bootstrap definition changed later.
- Delegated runs now return `DelegatedRunResult(exit_code, kind)`. A scheduled
  timeout still pauses and continues with exit zero, but its run record retains
  `timed-out`; a named/direct timeout remains nonzero and retryable.
- Durable recurring, architecture, CLI, and extension-model guidance now
  documents the frozen field and agent-only target boundary. All three packaged
  twins remain byte-identical to their live copies; the recurring context stays
  intentionally repo-local.

Focused verification: 19 exact delegate/lifecycle/validation regressions pass;
the broader affected-module run reached 709 passes. Its seven launch failures
were caused solely by a relative `PYTHONPATH=src` becoming invalid inside test
subprocess checkouts and all seven pass with the feature worktree's absolute
source path. The packaging wheel check separately lacks `hatchling` in this
interpreter; neither result reflects changed product behavior. Full verification
still follows the required rebase.

## Final peer-review findings addressed (2026-08-25)

A second `codex review --base origin/main` after the frozen-dispatch fixes
found four remaining must-fix boundaries, all addressed without changing the
chosen mechanism:

- direct `coga launch recurring/<name>` now applies the same control-branch
  and committed recurring-owner gates before it can mutate the period or spawn
  the bootstrap agent;
- the runner reloads `coga.toml` after the delegated child/refresh boundary,
  before timeout parking or completion validation, publication, and
  notification;
- a materialized period carrying both frozen `delegate:` and `ticket.py` is
  rejected at runtime and by `coga validate`, rather than silently choosing a
  dispatch signal;
- delegate validation rejects `.` / `..` and either platform path separator,
  keeping the target to one real bootstrap child component.

Durable recurring, architecture, extension-model, and packaged CLI guidance
now states the direct-launch gates and frozen-task mutual exclusion. Regression
coverage exercises both gates, post-session config reload, runtime/static
dispatch conflict refusal, and unsafe component rejection. Focused delegation
tests pass (38 passed), and the full changed-module set passes (551 passed).

## Final verification review (2026-08-25)

A third `codex review --base origin/main` reproduced three remaining launch
boundary defects that must be fixed before handoff:

- direct launch authorizes only after seeing optional `delegate:` state, so an
  accidentally stripped frozen field can fall through to an ungated ordinary
  recurring-task launch;
- the period-start callback publishes `in_progress` and syncs the log after
  bootstrap composition, and that sync can move the control checkout, leaving
  the already-composed prompt/config/secrets stale at spawn;
- a no-TTY sweep resumes an existing delegated `active`/`in_progress` period
  before applying agent admission, reaches the bootstrap TTY refusal, and
  aborts before later headless `ticket.py` jobs run.

Fix direction: gate every direct `TaskRef(directory="recurring")` before
reading optional dispatch state; make the launch boundary re-derive all
spawn inputs after the start publication; and apply headless admission to
frozen resumed delegates while leaving the existing period task untouched.

## Final verification fixes applied (2026-08-26)

All three findings from the final verification review are addressed in
`9b1ebeb1` (`peer-review: recompose delegated launches after publication`):

- direct launch applies control-branch and committed-owner authorization from
  any `TaskRef(directory="recurring")` before reading its ticket, so deleting
  optional `delegate:` state cannot fall through to an ungated ordinary launch;
- the delegated bootstrap launch is now two-pass. The first pass completes all
  target/TTY/CLI/push/secret/composition/argv preflights, makes its single
  launch audit durable, and publishes the period start. The second pass reloads
  config and target state and repeats every preflight/composition step without
  duplicating the audit, leaving no moving sync between final composition and
  spawn;
- a no-TTY scan applies admission to an existing period whose own frozen task
  carries `delegate:`. It leaves `active` / `in_progress` state untouched and
  continues returning later `ticket.py` work. The check is deliberately narrow
  so existing forced-resume behavior for ordinary agent periods is unchanged.

Regression tests remove `delegate:` before a direct launch gate, mutate both
bootstrap instructions and agent CLI during the start publication and verify
the spawned command sees the refreshed values with one launch audit, and cover
both active and orphaned headless delegate resumes. Verification so far:
`tests/test_launch.py tests/test_recurring.py` (430 passed) and
`tests/test_validate.py tests/test_dream_validate_drift.py
tests/test_packaging.py` (133 passed).

An existing PR, #723, was opened earlier against the old three-commit remote
history while this ticket still remained in `peer-review`. Its one inline
timeout-record finding is already fixed locally. The required fresh rebase,
full test, PR-body update, and workflow bump still follow; `open-pr` should
reconcile that PR rather than create a duplicate.

## Peer-review final verification (2026-08-26)

- Unconditionally fetched `origin/main` and rebased all six feature commits
  cleanly onto `38128432`; no conflict decisions were needed. Reviewed head is
  `b0f34e27` (`peer-review: recompose delegated launches after publication`).
- Post-rebase `python -m pytest`: **2037 passed** in 153.92s, with no failures,
  skips, or deselections.
- `coga validate --json`: 133 checks clean and no delegate-related issue. The
  aggregate exit remains 1 for the dogfood checkout's 23 unrelated existing
  findings (`missing-user`, unfrozen workflows, stale/large task warnings,
  unknown assignees, and four unsynthesized v2 draft blackboards).
- Architecture, extension-model, and resolve-conflicts live/packaged twins are
  byte-identical. `git diff --check origin/main...HEAD` is clean; the worktree
  is clean and six commits ahead of `origin/main`.
- PR #723 already exists against the stale remote feature history. Its body
  predates the frozen-dispatch and three rounds of failure-path hardening, so
  this final `## PR` text is also applied directly before handoff; the next
  mechanical `open-pr` step can force-with-lease the rebased branch and reuse
  the same PR.

## PR

### Summary

- Add declarative `delegate: bootstrap/<name>` for agent-backed recurring
  templates and launch the bootstrap command in-process, eliminating wrapper
  sessions and fake PTYs while preserving no-TTY refusal before fresh period
  creation.
- Freeze delegation into each materialized period ticket so sweeps, named
  retries, and direct task launches use immutable dispatch. Direct recurring
  launches retain the control-branch/owner gates, catch up control, and
  re-resolve the exact period before dispatch; sweeps reread the durable field
  after reconciliation. Resumed delegated periods remain TTY-gated without
  starving later deterministic jobs.
- Make delegated start and spawn a two-pass boundary: preflight and publish the
  single launch audit/period start, then reload config, target, secrets, prompt,
  and argv before the real spawn, where the exact post-publication period
  snapshot is leased again. Only the bootstrap done sentinel completes the
  period; natural exits, crashes, races, named timeouts, and sweep timeouts
  retain their distinct refusal, retry, and run-record semantics.
- Reject script-backed, ambiguous, unknown, or unsafe delegate targets at
  creation, validation, and runtime, and reconcile the live/packaged recurring,
  architecture, CLI, extension-model, and resolve-conflicts guidance.

### Design choice

Option 1 was chosen because `recurring_runner` already owns recipe-style period
lifecycle bookkeeping and can launch the stateless bootstrap target from the
operator's real terminal. A deterministic recipe was rejected because it would
move this template out of pre-create TTY admission; folding the bootstrap
runbook into the period session was rejected because it conflicts with the
runbook's stateless lifecycle and would duplicate the unchanged on-demand
`coga resolve-conflicts` alias path.

### Test plan

`PYTHONPATH=/tmp/coga-test-deps:/home/n/Code/claude/coga-delegate-recurring/src python -m pytest` — 2044 passed; `coga validate --json` — no delegation issues (unrelated pre-existing repository findings remain).

## Control-race review (2026-08-25)

The required `codex review --base origin/main` completed after the preceding
launch-boundary fixes and reproduced three further P1 races:

- direct `coga launch recurring/<name>` can read a stale local period after its
  branch/owner gates; a later non-fatal lifecycle sync refusal does not prevent
  the obsolete bootstrap session from spawning;
- `_broadcast_scan` and forced reconciliation can replace the period ticket,
  but `_launch_due_tasks` still branches on the pre-reconciliation
  `DueTask.delegate` cache;
- the period-start publication can integrate a changed/terminal period ticket,
  while the recomposed bootstrap launch still uses the delegate captured before
  publication and can start obsolete work.

Fix direction: perform recurring's best-effort control catch-up before direct
dispatch and re-resolve config/ref; reload the frozen dispatch from the durable
ticket after every scan/force reconciliation; and revalidate the period status
and exact frozen target at the post-publication recompose boundary before the
bootstrap may spawn. Focused race regressions will pin all three boundaries.

## Control-race fixes applied (2026-08-26)

All three final P1 races are fixed in `2859ed51` after an unconditional fresh
rebase onto `origin/main` at `fa3c84fd`:

- actual direct recurring launches apply branch and committed-owner gates,
  perform the same best-effort control catch-up as the other interactive entry
  points, reload config, and re-resolve the exact period ref before reading
  frozen dispatch;
- `_launch_due_tasks` rereads `status` and `delegate` from the durable period
  ticket after broadcast/force reconciliation rather than branching on the
  stale `DueTask` cache;
- the delegated start callback captures the exact in-progress period bytes
  after publication, and the recomposed launch revalidates status, frozen
  target, and that complete snapshot at the final pre-PTY boundary. A
  concurrent completion, replacement, dispatch change, or other ticket edit
  refuses before any bootstrap agent starts.

Regression coverage includes a rival control checkout completing a stale
direct-launch period, both cached/durable dispatch inversions, and terminal,
retargeted, stripped, and same-dispatch ticket mutations after publication.
Post-rebase `python -m pytest`: **2044 passed** in 157.57s. Packaging is included
and clean using isolated `/tmp` Hatchling dependencies. `coga validate --json`
reports 134 clean checks and no delegate issue; its 23 findings are unrelated
dogfood state already present in the checkout. All three live/packaged twins
are byte-identical, `git diff --check origin/main...HEAD` is clean, and the
recorded worktree is clean with eight commits ahead of `origin/main`.

## open-pr step (2026-08-26)

- Ran `coga open-pr` from the primary control checkout (`/home/n/Code/codex/coga`,
  on `main`). The recorded feature branch lives in an independent fallback clone
  (`/home/n/Code/claude/coga-delegate-recurring`, worktree of
  `/home/n/Code/claude/coga`), which is the layout the control-checkout gate is
  built for.
- The command reported `origin/main advanced only through non-overlapping Coga
  task/log state; branch is safe to publish` — the two commits `origin/main`
  gained since the rebase base (`434e3cbd`, `e3d7b7fb`) are this ticket's own
  generated ticket/log state, so no rebase or re-test was required.
- It reused the already-open PR #723 rather than creating a duplicate, and
  recorded `pr: https://github.com/FastJVM/coga/pull/723` under `## Dev`.
  Published branch tip is `2859ed51`.
- PR #723's body still carried the pre-control-race revision (it predated the
  `## PR` rewrite and had no `Closes ticket:` line, since the PR was hand-opened
  during peer review). Replaced it with this ticket's current `## PR` section
  plus the `Closes ticket:` line, so the PR describes the eight commits actually
  on the branch.

## Post-merge peer-review findings (2026-08-26)

While a required independent `codex review --base origin/main` was still
running, PR #723 was opened, advanced through the mechanical workflow step,
and merged as `5243dfd5`. The task is now at the owner-controlled `review`
gate, so the original peer-review step cannot be bumped or silently replayed.

The completed review found six actionable regressions in the merged code:

- **P1:** the period start is not an observable compare-and-set. A start-audit
  sync can integrate a replacement or changed delegate, which can then be
  marked `in_progress` and announced under the stale target before the later
  snapshot check refuses it; a swallowed state-sync regression can likewise
  admit stale local bytes.
- **P1:** completion and timeout do not re-lease the period generation after
  the child exits. A later period materialized at the stable path can therefore
  be marked `done` or `paused` by the previous period's delegate result.
- **P2:** delegating through a stateless bootstrap target skips the period
  TaskRef's push-auth preflight, so work can start after authentication is
  already known to be unable to publish the period state (or the shipped
  conflict-resolution pushes).
- **P2:** direct `coga launch recurring/<name>` routes delegated periods before
  ordinary inline activation, so a paused delegated period cannot use the
  documented launch-as-readiness transition.
- **P2:** the direct-launch catch-up runs only after initial task resolution,
  so a remotely materialized recurring ref that is absent locally is reported
  missing before control can be refreshed and re-resolved.
- **P2:** public recurring-task launch gates also run inside already-authorized
  sweep/named-launch paths, repeating owner/control network fetches per task and
  turning a later transient fetch miss into a mid-sweep abort.

Required owner decision: authorize a follow-up fix PR from current `main`, or
rewind/reopen this ticket's implementation flow. Do not close the review gate
with these two stale-period P1s unresolved.

## Owner decision (2026-08-26)

The owner authorized a separate follow-up fix PR from current `main` for all
six post-merge peer-review findings. Keep the existing owner-controlled review
gate open; this authorization covers the corrective branch and PR, not a
workflow bump or task closure.

## Follow-up fix implementation (2026-08-26)

Branch `delegate-recurring-postmerge-fixes`, worktree
`/tmp/coga-delegate-postmerge-fixes`, based on current `main` at `f3965ce3`.

The two P1 races are fixed with one explicit period lease: exact materialized
ticket bytes plus the sorted multiset of all audit lines tagged with that
stable period ref. The audit half distinguishes a later period/forced run even
when its ticket is byte-identical. Start publication uses that lease as an
observable control-branch compare-and-set and publishes before announcing;
final spawn rechecks it on control; completion and watchdog pause consume it
again after the child exits. A strict state-guard mode in `coga.git`/shared mark
finalizers re-raises guard refusal so the runner can roll back only its generated
ticket/log bytes and suppress the stale notification or child spawn.

The four P2 fixes are paired with that lifecycle:

- delegated work explicitly preflights push auth for the materialized period
  TaskRef before entering the stateless bootstrap launch;
- direct `coga launch recurring/<name>` may activate a paused/draft delegated
  period as one guarded compound transition;
- an explicit direct recurring ref gates/catches up before local resolution,
  so a remotely materialized missing-local period becomes discoverable;
- outer sweep/named-launch admission now calls a typed internal period-launch
  seam, avoiding repeated public owner/control/catch-up gates per task while
  keeping every task-local launch preflight.

Focused regression coverage includes local and real-control same-ticket/new-
audit generation races at start and completion, timeout non-mutation, push-auth
ordering, paused direct launch, missing-local catch-up, the internal seam, and
strict guard/notification ordering. The recurring/launch/mark/git module suite
is green (684 passed before the final real-control completion test was added);
packaging + validation tests are green (99 passed). Full verification remains
before publication.

## Follow-up independent review (2026-08-26)

`codex review --base origin/main` found two additional P1 admission failures:

- the typed internal seam trusted the sweep's outer catch-up for every
  ordinary period, so another checkout could pause, finish, or replace a later
  task while an earlier child ran; the later stale local task could still
  start because ordinary lifecycle guard failures are intentionally non-fatal;
- delegated exact-lease checks propagated `StateRegressionError` but the Git
  layer still swallowed transport/publication `GitError`, allowing a child to
  spawn or a completion to be announced without verified control state.

Both are fixed on the follow-up branch. The ordinary seam now refreshes and
re-admits each exact period immediately before launch, skips a newly parked or
closed control task, and refuses when that per-child refresh cannot be
verified. Delegated start, orphan resume, final spawn, completion, and timeout
now request strict Git publication after the period push-auth preflight; all
attempted control transport/publication failures propagate through the shared
mark/git layers, restore the runner-owned local mutation, and suppress spawn or
notification. Focused regression tests cover a remotely paused later ordinary
period plus transport loss at delegated fresh-start, orphan-resume, and
completion boundaries.

## Follow-up second independent review (2026-08-26)

A second `codex review --base origin/main` found three remaining fail-open
edges:

- strict period publication propagated transport failures but still swallowed
  setup-time `FeaturePublicationError` such as a vanished control branch;
- the ordinary per-child refresh treated missing control/remote configuration
  as a successful no-op, so a Git checkout could start without any control
  verification;
- a delegated timeout returned sweep success when its guarded pause either
  lost the generation lease or failed to publish.

The follow-up branch now propagates setup failures whenever strict Git
publication is requested, gives recurring refresh an explicit
`require_control_verification` mode (while preserving intentional Git-disabled
and genuine non-Git operation), and reports a nonzero refusal unless the
watchdog pause is verified on control. Regression tests cover missing control,
missing remote, timeout transport loss, and a later-generation timeout race.

## Follow-up third independent review (2026-08-26)

The final pre-publication `codex review --base origin/main` found two more P2
transaction gaps in strict lifecycle publication:

- a failed feature-checkout control landing could leave its generated
  `in_progress`/`done`/`paused` commit in local PR history even though the
  runner restored the working files;
- a transport error reported after control had actually accepted the push
  could make the runner restore local files to the prior state, splitting the
  checkout from durable control state.

Strict recurring publication now captures exact generated bytes and uses a
local ref lease on both control and feature checkouts. An unaccepted candidate
CAS-unwinds its generated commit before the runner restores files. Every
control push exposes its exact candidate OID; an ambiguous failure probes all
configured push destinations. Confirmed acceptance completes normally, a
confirmed miss unwinds and fails, and an unprovable outcome raises an explicit
uncertain-publication refusal while retaining generated local evidence for
reconciliation. Detached checkouts use the same exact-byte control candidate
without creating an orphan commit. Focused real-Git tests cover feature-branch
unwind, lost acknowledgements from feature and control checkouts, an unavailable
probe, and runner-side no-rollback/no-notification behavior. The expanded
Git/mark/launch/recurring suite passes: **698 tests**.

## Follow-up fourth independent review (2026-08-26)

The final review rerun found two remaining fail-closed gaps before publication:

- direct `coga launch recurring/<name>` ignored a failed control catch-up and
  could therefore resolve and execute stale ordinary work;
- a delegated child returning `done` treated malformed replacement ticket
  bytes like an absent/reaped period and falsely reported success.

Both are must-fix. The direct public path will refuse an unverified catch-up,
and replacement classification will distinguish an absent ticket from present
but unparsable bytes. Focused regressions, the full suite, and another clean
independent review are required before the follow-up PR opens.

Both findings are fixed in commit `15f75e67`. Direct public period launch now
distinguishes intentional Git-disabled/non-Git operation from an actual control
checkout whose catch-up was not verified; the latter exits with the stale-
control retry code before task resolution. Delegated completion now accepts
only a truly absent/reaped ticket or a parseable terminal replacement as an
already-completed result; present malformed bytes are retained and refused.
Focused launch/recurring verification passes (**456 tests**) and the final
full suite after an unconditional fetch/rebase passes: **2086 tests**.

## Follow-up fifth independent review (2026-08-26)

The next review found one P2 sweep-liveness edge: after a successful per-child
refresh, a period reaped by another checkout was treated as a fatal missing
target instead of the same skipped outcome as a remotely terminal/paused
period. The internal seam now reports the exact missing period as no longer on
control and returns `skipped`, allowing later due tasks to continue. A real-Git
regression deletes the period from a competing checkout and proves no launch
occurs. The review also exposed stale durable wording that still called direct
launch catch-up “best-effort”; recurring, architecture (live + packaged), CLI
(packaged-only), and resolve-conflicts template (live + packaged) guidance now
all state that a Git-backed direct launch requires verified catch-up before
resolution. Focused verification passes (**4 tests**); full verification and a
fresh independent review remain before publication.

## Follow-up sixth independent review (2026-08-26)

The next review found two dispatch-generation gaps in the ordinary recurring
path: the per-child refresh could launch a new active/in-progress generation
that replaced the one admitted for the sweep, and an exact period deleted from
control could prefix-resolve to a sole sibling before the mismatch failed the
whole sweep. Inspection also found the same pre-classification liveness edge
when an earlier child's teardown had already refreshed a later deletion into
the local checkout.

The follow-up branch now shares one `PeriodLease` primitive (exact ticket bytes
plus task-tagged audit generation) between recurring orchestration and launch.
The sweep freezes all generations before its first child, carries the admitted
lease through ordinary and delegated dispatch, and skips any later deletion or
replacement. The ordinary typed seam refreshes control, resolves only an exact
task ref (never a prefix sibling), and compares the refreshed lease before
entering launch. Named recurring launch carries the same lease from its own
admission. Regression coverage includes an audit-only byte-identical
replacement, exact deletion with a surviving prefix sibling, and a later task
reaped locally during an earlier child. The affected launch/recurring modules
pass **459 tests**; full-suite verification and another independent review
remain before publication.

Full verification after the sixth-review fixes: `python3.12 -m pytest` with
the worktree source/dependency paths passed **2089 tests** in 123.15 seconds.
`coga validate --json` reports 136 clean checks and only the existing dogfood
repository findings (no recurring/delegate issue). Live/packaged architecture
and resolve-conflicts twins remain byte-identical.

## Follow-up seventh independent review (2026-08-26)

The post-rebase review found one P2 strict-completion omission: the delegated
period snapshot covered the period ticket, audit log, and digest spool, but not
the parent `coga/recurring/<name>/ticket.md` named by `.state-snapshot.json`.
Because strict publication builds from captured bytes, `done` could reach
control while a child-updated cross-run cursor remained only in the launch
checkout.

Completion snapshots now include that parent recurring ticket. The cursor and
period `done` state therefore publish in one exact transaction, while start and
timeout snapshots retain their narrower file scope. A real-Git regression
advances a parent cursor during the delegated child and verifies the new parent
bytes at remote `main` after completion. Recurring/mark/git verification passes
**506 tests**. The review tool's separate 19 failures were environment-only
(`coga` and Hatchling unavailable without this worktree's explicit source/build
paths), while both configured full-suite runs passed **2089 tests**.

## Follow-up eighth independent review (2026-08-26)

The next `codex review --base origin/main` found two must-fix teardown and
publication races:

- an ordinary agent-backed period carried its admission lease into spawn but
  not into the unfinished-session pause, so a replacement generation could be
  paused at the stable path after the old child exited;
- a strict control landing cleaned up immediately when a retry raised
  `StateRegressionError`, even if an earlier candidate push could have reached
  only some of a multi-push remote's effective destinations.

The follow-up now returns a typed ordinary-launch result containing the last
pre-spawn period lease and the launch-time publication class. Teardown compares
the append-only canonical task-creation witness, which remains stable across
the same child's ticket plus launch/usage audit writes but gains a counted line
for every replacement; a matching generation gets a fresh exact lease for its
strict pause, while a replacement is left untouched and the sweep refuses.
Strict landing now treats every armed candidate as a possibly attempted push:
even a later state regression probes every effective destination, and
destination disagreement retains local evidence as an uncertain publication
instead of running cleanup. Focused regressions cover both races plus
same-generation child edits. The expanded launch/recurring/Git/mark suite
passed **707 tests** before the generation-witness refinement, and the full
recurring/create/autofix slice passes **355 tests** afterward. Full-suite and
another independent review remain pending before publication.

## Follow-up ninth independent review (2026-08-26)

The next `codex review --base origin/main` found one P1 generation gap in the
deterministic recurring path. A pure `ticket.py` period never reaches an agent
spawn callback, so the typed launch result carried no period lease and its
post-script unfinished pause fell back to the unguarded historical path. An
old deterministic child could therefore pause a replacement period at the
same stable path. The fix will retain the refreshed admitted lease for a
script-only launch and consume it in the same guarded teardown used after an
agent child. A focused replacement regression, affected/full verification,
and another independent review remain pending before publication.

Fixed on the follow-up branch: `launch_recurring_period` now initializes its
typed result with the exact generation proven by the per-child refresh, then
tightens that lease again before every agent spawn. A pure `ticket.py` child
therefore retains the admitted generation even though it has no spawn callback,
and the runner refuses every non-skipped result that lacks a child-generation
lease. Recurring, architecture (live + packaged), and packaged CLI guidance
now state the deterministic/agent distinction. The end-to-end regression
replaces a deterministic period while its simulated script owns the launch and
proves teardown refuses without pausing or editing the replacement. The
expanded launch/recurring/Git/mark/create/autofix suite passes **801 tests**.

## Follow-up tenth independent review (2026-08-26)

The next independent review found a P2 scalability defect in the generation
lease itself: every `local_period_lease` call reads and filters the complete
repo-global `coga/log.md`, so a sweep and its repeated lifecycle boundaries are
O(periods × unbounded audit history). That violates the recurring contract that
routine scans must not repeatedly pay for the whole log. The replacement-safe
generation proof needs either one batched audit pass or a bounded durable
witness; implementation and regression coverage are pending before
publication.

The scalability finding is addressed on the follow-up branch with a bounded,
creator-owned `period_generation` token in every newly materialized recurring
period ticket. The token changes on each supported rematerialization and stays
fixed across the child's lifecycle edits, so exact ticket bytes plus that token
retain the replacement guard without reading or filtering the repo-global log.
Legacy period tickets without a token remain launchable; any replacement
created by the updated runner receives one. Recurring templates are forbidden
from declaring the runner-owned field, and task creation, canonical rendering,
validation, live/packaged architecture guidance, recurring guidance, and the
packaged CLI context all recognize the new state explicitly.

Regression coverage proves `local_period_lease` never reads `coga/log.md`,
exercises token creation/rendering/validation, and updates local and real-control
start, completion, ordinary-agent teardown, and deterministic-script teardown
races to use distinct stable-path generations. The expanded affected suite
passes: **916 tests** across launch, recurring, Git, mark, create, recurring
autofix, ticket, and validation modules. An independent review still follows
before final rebase and publication.

## Follow-up eleventh independent review (2026-08-26)

The next review found two remaining lifecycle gaps:

- an ordinary agent spawn recaptured the ticket at its final boundary but
  adopted a replacement `period_generation` instead of rejecting it, allowing
  stale composed work to start and later park the replacement;
- delegated strict completion published `done` before calling the digest
  notifier, so an installed digest spool event remained local rather than
  joining the terminal-state transaction.

Both are fixed on the follow-up branch. The final ordinary-agent callback now
requires the admitted bounded token before refreshing the exact ticket bytes;
a replacement exits before spawn. Strict delegated completion appends a
configured digest event before publication and includes the union-safe spool in
the same exact control commit as the terminal period (and any parent cursor),
while a live notification still waits until publication succeeds. Focused tests
cover the pre-spawn replacement and assert the remote ticket and digest event
share one commit. The expanded affected suite passes: **918 tests**.

## Follow-up twelfth independent review (2026-08-26)

The next review found one ordinary-completion compatibility regression in the
strict digest-publication change: `_sync_done_state` passed the new
`extra_paths=[]` and `land_union_files_to_control=False` keyword arguments even
when no digest spool participated. Besides changing an established internal
call contract, that broke focused command and period-state test doubles for
ordinary (non-delegated) completion.

The helper now supplies those keyword arguments only when a digest spool is
actually part of the strict terminal-state transaction, preserving the old
ordinary call shape. The two reported regressions and the delegated atomic
digest-publication regression pass together: **3 tests**. Another independent
review follows before the mandatory final rebase and full verification.

## Follow-up thirteenth independent review (2026-08-26)

The next review found two P1 regressions in Coga's supported remote-less Git
mode: the new public direct-launch freshness gate rejected every Git checkout
without a configured remote, and the strict per-child refresh did the same for
ordinary scheduled and named periods. Treating every missing remote as local
would have reopened the converse race already covered by this branch — a remote
that disappears after sweep admission must still fail closed.

The fix freezes whether a configured control remote exists at the public
sweep/named admission boundary and carries that fact through the internal
ordinary-period launch seam. A checkout proven remote-less at admission uses
its exact local period lease and local `HEAD`; a configured remote that is
offline or disappears still requires verification and refuses. Direct
`coga launch recurring/<name>` makes the same distinction at its own admission
boundary before resolving the period. Live recurring guidance and the
live/packaged architecture plus packaged CLI contexts now state the distinction.

Focused regressions cover direct and internal remote-less launches, the
existing disappeared-remote refusal, and sweep/named propagation of the frozen
admission class. The full launch, recurring, and recurring-autofix slice passes:
**515 tests**. Another independent review follows before final rebase and full
verification.

## Follow-up fourteenth independent review (2026-08-26)

The next review found two remaining same-generation races in ordinary recurring
work. The final agent callback checked only `period_generation`, so a period
parked, completed, advanced, or edited after prompt composition could still
spawn stale work. Unfinished teardown recaptured newer same-generation ticket
bytes for its guard but continued rendering the older `Ticket` object read
before that capture, allowing it to overwrite an intervening blackboard,
workflow, or metadata edit.

The final ordinary-agent boundary now receives the exact ticket used to compose
that spawn, reparses the current leased bytes, requires `in_progress`, and
requires the complete semantic ticket snapshot to match before spawning. The
teardown path now parses its mutation input from the newly captured lease before
checking terminal state or rendering `paused`, so guarded publication and the
state it derives share one byte source. Live recurring guidance and the
live/packaged architecture plus packaged CLI contexts describe both guarantees.

Focused regressions cover a same-generation close between composition and
spawn and a same-generation edit between teardown lookup and lease capture.
The full launch, recurring, and recurring-autofix slice passes: **517 tests**.
Another independent review follows before final rebase and full verification.

## Follow-up fifteenth independent review (2026-08-26)

The next independent review found two must-fix state-integrity gaps:

- delegated completion includes the parent recurring ticket in its strict
  publication, but its CAS guard currently leases only the period ticket. A
  concurrent control-side parent/cursor edit could therefore be overwritten by
  the child's stale local parent bytes;
- `period_generation` is globally schema-valid even though the context defines
  it as runner-owned state reserved for materialized recurring tasks, so an
  ordinary hand-authored task can currently carry a misleading lease identity.

The follow-up branch will bind the exact parent input into completion's control
guard and add an ownership validation analogous to `delegate:`. Focused race
and schema regressions are required before another independent review.

Both findings are fixed on the follow-up branch. Final delegated spawn
admission now captures the parent ticket selected by the period's state
snapshot, proves those exact bytes on control, and carries that parent lease
into the strict completion CAS. A real competing-control regression proves a
newer parent cursor is preserved, the child's local cursor evidence remains for
reconciliation, no completion notification is emitted, and the period returns
to `in_progress`. Validation now rejects a non-empty `period_generation` on
anything except a directory-form task directly under `tasks/recurring/`, while
the schema continues to own malformed-value diagnostics. Recurring,
architecture (live + packaged), and packaged CLI guidance describe both
contracts; the CLI text also now names the bounded creator-owned token rather
than the superseded audit-derived witness. The complete recurring + validation
modules pass: **363 tests**. Another independent review follows.

That review found one downstream integration miss: Dream's deterministic
validator-drift classifier did not recognize the new
`invalid-period-generation-owner` issue, so it fell through to human-needed
unknown-kind remediation. The kind now joins the file-backed recurring/schema
PR-proposal bucket and its explicit classifier matrix. The combined Dream
validator-drift, validation, and recurring modules pass: **398 tests**.

## Follow-up sixteenth independent review (2026-08-26)

`codex review --base origin/main` found no actionable correctness defects in
the completed follow-up branch. Its focused Git, recurring, lifecycle, and
validation suite passed: **609 tests**. The reviewer's unconfigured full-suite
attempt had 19 subprocess-only failures because the isolated environment could
not import the checkout's `coga` package and lacked Hatchling; the branch's
configured full-suite run remains the final verification gate below.

## Follow-up final verification (2026-08-26)

- Unconditionally fetched `origin/main` and rebased; the branch was already
  current at `e14cfc16`, so no conflict or material-drift decision was needed.
- Configured full suite: **2108 passed** in 127.54s.
- `coga validate --json`: 136 checks clean and no recurring, delegation, or
  period-generation issue. Its exit remains 1 only for the dogfood checkout's
  24 unrelated existing warnings/errors.
- Architecture and resolve-conflicts live/packaged twins are byte-identical;
  `git diff --check origin/main...HEAD` is clean; the feature worktree is clean
  with 18 commits ahead of `origin/main`.

## Follow-up PR body

### Summary

- Give every materialized recurring period a bounded, creator-owned dispatch
  generation and verify that generation, status, and exact ticket state at the
  final spawn, completion, and teardown boundaries. Validation reserves the
  field for directory-form tasks directly under `tasks/recurring/`.
- Make delegated lifecycle, digest, and parent cursor publication one guarded
  control-plane transaction. Concurrent replacement, same-generation edits,
  stale control, transport ambiguity, and disappeared remotes now fail closed
  without announcing success or overwriting newer state; checkouts admitted as
  intentionally remote-less keep their local behavior.
- Prevent later entries in a sequential sweep and direct recurring launches
  from dispatching or parking a generation reaped or replaced by earlier work,
  while preserving ordinary non-delegated sync call contracts. Update the live
  and packaged behavioral guidance and Dream's validator-drift classification.

This is a lifecycle-hardening follow-up to #723; it does not change the
conflict-resolution operation or restore the removed nested PTY wrapper.

### Test plan

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/coga-peer-review-build-deps:/tmp/coga-delegate-postmerge-fixes/src PYTEST_ADDOPTS='-p no:cacheprovider' python3.12 -m pytest` — 2108 passed; `coga validate --json` — no recurring/delegation/generation findings (unrelated existing dogfood findings remain).

## Follow-up PR (2026-08-26)

Opened **#725 — Harden delegated recurring lifecycle leases**:
https://github.com/FastJVM/coga/pull/725

Branch `delegate-recurring-postmerge-fixes` was pushed at reviewed head
`3dd50c8f`. The task remains at its owner-controlled review gate; this follow-up
does not bump or close it.
