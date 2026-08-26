---
slug: reconcile-recurring-wrapper-tty-admission-guidance
title: Reconcile recurring wrapper TTY-admission guidance with resolve-conflicts template
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
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
step: 3 (open-pr)
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
