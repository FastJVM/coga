---
slug: recurring-should-start-by-checing-out-main
title: Service single-repo recurring runs from a control worktree too
status: draft
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: code/design-then-implement
secrets: null
---

## Description

`coga recurring` should be runnable from any working directory, on any branch.
Today it is not: bare `coga recurring` and `coga recurring launch <name>` both
hard-refuse when the checkout is not on the configured control branch, so
`coga dream` from a feature branch is a dead stop that only a manual
`git switch main` clears.

The sibling ticket `service-recurring-from-a-temp-control-worktree-ins`
addresses this for the `coga recurring --all` child only, by servicing the repo
from a temporary linked worktree holding the control branch. This ticket covers
the entry points that ticket leaves out of scope — bare `coga recurring`,
`coga recurring launch <name>`, and `--interactive` — where the templates that
matter are **agent-backed**, not deterministic.

Done looks like: from a repo parked on a feature branch with a dirty tree,
`coga dream` creates and launches its period task, the agent session runs
against the control branch rather than the operator's feature tree, the
serviced-period ledger line reaches `<remote>/<control-branch>`, and the
operator's checkout is byte-identical afterwards — same branch, same `HEAD`,
same `git status --porcelain --untracked-files=all --ignored`, no new stash
entry. (The agent's own *work* lands where it normally does — feature branches,
PRs, draft tickets — not on control. Only the ledger and period-task state go
to control.)

## Context

Cite symbols, not line numbers. `5243dfd5` (`delegate:` field, 2026-08-26)
moved ~306 lines in `recurring_runner.py` on the day this ticket was drafted
and invalidated every line citation in the first draft; see the evaluator
review on the blackboard.

### The refusal being removed

Both single-repo entry points `return 2` before scanning, via
`_refuse_non_control_branch` in `src/coga/recurring_runner.py`:

- `run_recurring_scan` — guarded by `not require_fresh_control`, so the gate is
  the *non*-`--all` path. `--all` children use the stricter
  `require_fresh_control` freshness gate instead. `--interactive` goes through
  this function too, so it refuses as well.
- `run_recurring_named` — unconditional. `coga dream` resolves through
  `src/coga/aliases.py` (`"dream": "recurring launch dream"`) straight into it.

`_refuse_non_control_branch` prints "Recurring launch refused: the current
checkout is on branch 'x', not the configured control branch 'main'" and tells
the human to `git switch main`. It exempts only `git_enabled = false` and
confirmed non-git workspaces.

Note for the design step: the sibling ticket's Out of Scope claims these entry
points "keep today's best-effort behavior off the control branch (they scan the
working tree they are in)". That is false — they refuse outright. The likely
source of the error is `_refuse_non_control_branch`'s own docstring, which says
"reachability and freshness remain best-effort for interactive runs"; that is
about *freshness*, not the branch.

### Prefer the worktree that already holds control

In the layout Coga recommends, a linked worktree already has the control branch
checked out — in which case `git worktree add <tmp> <control>` **fails**, since
git refuses to check one branch out twice. A create-a-throwaway-worktree design
is therefore absent in exactly the well-configured case. Reusing the existing
control worktree (`git._worktree_holding_branch` already locates it) should be
the primary path, not the fallback; creating one is the fallback.

### What makes the agent case different from the sibling's

The sibling settled the throwaway-`/tmp`-worktree shape for a deterministic,
short, unattended run. That inference does not carry to an attended agent
session, and the following are known breaks rather than open considerations:

- **The agent's own worktree lands inside the deleted directory.**
  `coga/skills/code/implement/SKILL.md` instructs `git worktree add
  ../coga-<branch-name> -b <branch-name> main`. From
  `/tmp/coga-recurring-X/checkout`, `../coga-<branch>` resolves inside the temp
  parent that cleanup `rmtree`s. A Dream run that branches and implements would
  have its feature checkout destroyed.
- **`worktree:` gets recorded pointing at a temp path.** `src/coga/open_pr.py`
  reads it back and requires that checkout to exist, be on the branch, be clean
  and ahead. After cleanup it does not exist. Relatedly, the `implement` step's
  `requires: branch` gate (`src/coga/step_gate.py`) is presence-based in *the
  checkout `coga bump` runs from*.
- **Lock duration.** Checking control out *is* the concurrency lock. For a
  seconds-long sweep that is fine; holding it for `COGA_REPL_IDLE_TIMEOUT`
  (15 min default) plus `max_session` blocks the operator's own
  `git switch main` in another terminal for potentially hours.

A **persistent** control worktree avoids the data-loss path, the recording
path, and the cleanup-on-signal problem in one move. Weigh it against the
throwaway shape rather than inheriting the sibling's choice.

### Dependency on the sibling — verify before relying on it

`_service_from_control_worktree` and `--control-worktree` **do not exist**
(`grep -rn control_worktree src/coga/` is empty). Worse, the sibling's
`## Proposed Shape` was written 2026-08-17 and is built on code since deleted:
`_run_recipe_task` is gone (the equivalent is `launch_script.py`, spawning with
`cwd=host_repo_root(cfg)`), and its recipe-backed/agent split predates #705,
which removed `recipe:` from recurring templates entirely. Re-derive against
HEAD; do not build a second worktree helper, but do not assume the sibling's
API shape either.

That ticket does record two rejected alternatives with full reasoning —
stash/switch/restore of the operator's checkout, and a detached worktree at the
remote tip (the latter because `git.sync_log` refuses on a detached HEAD and
`_sync_recurring_create_paths` skips the local commit there, so the
serviced-period ledger would never reach control and every sweep would re-fire
the period). Both rejections carry over here unchanged; they are not open
questions.

### The affected template set is small

Of the seven templates under `coga/recurring/`, five carry `ticket.py`
(`autoclose-merged`, `blocker-reminders`, `branch-sweep`, `digest`,
`skill-update`) and are already served by the sibling's work. Only `dream` and
`resolve-conflicts` are agent-backed — and `resolve-conflicts` is a `delegate:`
template as of `5243dfd5`, where the sweep performs the delegated launch in the
operator's own terminal with its own TTY-admission rules and a `coga/log.md`
slack-sentinel completion path. The design must say what happens to a
delegating template in this mode; that interaction is unanalyzed.

### Worktree hygiene facts

- `coga.local.toml`, `.coga/`, and `.agent-skills/` are all gitignored
  (`coga/.gitignore`), so a fresh worktree lacks them. `coga.local.toml` must be
  seeded at 0600 or `load_config` raises before anything runs. `.agent-skills/`
  is rebuilt by `src/coga/commands/launch.py` and self-heals. `.coga/` is
  unanalyzed — decide explicitly. (The sibling's note arguing `.agent-skills/`
  "is not needed" reasons from recipes not reading the merged skill view; that
  reasoning is void here, because this path runs agent sessions.)
- Any created worktree must live outside every plausible `--all` scan root, or
  `discover_coga_repos` (`src/coga/workspace_discovery.py`) picks it up as
  another Coga repo.

### Context to read and update

`coga/contexts/coga/recurring/SKILL.md` is not attached — at ~9.2k tokens it
was 70% of the composed prompt for a handful of facts. Read it directly. Two
sections matter: `## Recurring runs start on the control branch` (the contract
this ticket invalidates — "Every launching entry point requires the configured
control branch… There is deliberately no override") and the `delegate:` gotcha
near the end, which is the only place TTY admission for delegated launches is
explained.

Per the repo's context-in-the-same-PR rule, the `## Recurring runs start on the
control branch` section must be rewritten in the same PR as the behavior
change. There is no packaged duplicate to sync — it is one file.

### Not this ticket

- The `--all` path and its parent summary — the sibling ticket owns those.
- The diverged-control case (control branch checked out but its local commits
  cannot rebase onto the fetched tip). That keeps failing loud.
- Running recurring from a **separate clone or install** pointed at another
  repo. Discussed and deliberately deferred; if wanted, it is its own ticket.
- A general-purpose temp-worktree helper for commands other than `recurring`.

<!-- coga:blackboard -->

## Evaluator review

Independent cold review, 2026-08-26. Written verbatim; the reviewer had not
seen the authoring interview.

### Verdict up front

The problem statement is real and correctly diagnosed. The proposed solution —
run attended agent sessions inside a throwaway `/tmp` worktree — is not sound in
its current form, and the ticket bundles two tickets' worth of work behind a
dependency that is itself stale. I'd send this back before launching design.

### 1. Every line citation in the ticket is wrong

All four references were correct as of `5243dfd5^` and are wrong at HEAD.
`5243dfd5` ("Declare recurring delegation with a `delegate:` field",
2026-08-26) landed the same day the ticket was written and moved ~306 lines.

| Ticket says | Actually at HEAD |
|---|---|
| `_refuse_non_control_branch` at `recurring_runner.py:122` | `src/coga/recurring_runner.py:129` |
| scan gate at `recurring_runner.py:693` | `src/coga/recurring_runner.py:700` |
| `run_recurring_named` refusal at `recurring_runner.py:967` | `src/coga/recurring_runner.py:1273` — line 967 is now unrelated `TaskOutcome` classification code |
| (`_sync_control_checkout_ahead` at `:1054`) | `src/coga/recurring_runner.py:1360` |

`src/coga/workspace_discovery.py:18` is the one citation that still holds.

Two are off by 7 and findable. `:967` will actively mislead. Fix them, or drop
line numbers in favour of symbol names.

### 2. The substantive claims are TRUE

**(a) Both entry points hard-refuse with 2.** Confirmed.
`recurring_runner.py:700` — `if not require_fresh_control and
_refuse_non_control_branch(cfg): return 2`; `recurring_runner.py:1273` —
unconditional, same return. `--interactive` goes through `run_recurring_scan`
too, so it refuses as well. `coga dream` resolves via `src/coga/aliases.py:59`
(`"dream": "recurring launch dream"`) straight into the second one. The "dead
stop" framing is accurate.

**(b) The sibling's Out of Scope really does mischaracterize this.** Its line
"Bare `coga recurring`, `coga recurring launch <name>`, and `--interactive`
keep today's best-effort behavior off the control branch (they scan the working
tree they are in)" is false. They refuse. The likely source of the error is
`_refuse_non_control_branch`'s own docstring (`recurring_runner.py:132-135`),
which says "reachability and freshness remain best-effort for interactive
runs" — that's about *freshness*, not the branch. Good catch by this ticket;
the correction is worth keeping.

**(c) The `requires: branch` claim is TRUE and is the sharpest thing in the
ticket.** `src/coga/step_gate.py:63` plus the `## implement` section of the
workflow both confirm the gate is presence-based in the ticket copy of the
checkout `coga bump` runs from. Keep this.

**One stale phrase:** "The `--all` path is recipe-only" — `recipe:` was deleted
from recurring templates on 2026-08-24 (`df1d0602`, #705). No template carries
it; the split is now `ticket.py` vs agent, which the ticket uses correctly
everywhere else.

### 3. The dependency on the sibling is a trap, and worse than it looks

`grep -rn control_worktree src/coga/` returns nothing.
`_service_from_control_worktree` and `--control-worktree` do not exist. That
alone would be manageable — but the sibling's `## Proposed Shape`, written
2026-08-17 and still parked at `review-design`, is built on code that has since
been deleted:

- `_run_recipe_task:748` — gone. The equivalent is
  `src/coga/launch_script.py:285` (`cwd=host_repo_root(cfg)`).
- "Agent templates (no `recipe:`)" and "recipe-backed templates" — `recipe:` no
  longer exists on recurring templates (#705). That acceptance criterion is
  unimplementable as written.
- `create_template` "raises at `:428` and `:460`" — the current raises are at
  `src/coga/recurring.py:558`, `:585`, `:626`.
- `run_recurring_scan_recipe:728` → now `:994`. `_sync_control_checkout_ahead:920`
  → now `:1360`.
- Its design note says `.agent-skills/` "is not needed: the child is spawned as
  `sys.executable -m coga.cli` and no registered recipe reads the merged skill
  view." That reasoning is void for *this* ticket, which runs agent sessions.

So the sibling needs its own re-design pass before it can be implemented, and
this ticket depends on an API whose shape will change. Its instruction to
"re-read its `## Proposed Shape` before writing this spec" is the right
instinct but understates the problem: that section is not merely at risk of
changing, it is already wrong.

**Recommendation:** don't launch this until the sibling clears `review-design`
and its shape is re-derived against HEAD. Or restructure so this ticket doesn't
depend on it at all (see §5).

### 4. The temp-worktree-for-agent-sessions plan has a concrete data-loss path

This is the part I'd push back on hardest. The ticket correctly identifies
worktree lifetime as "the central design problem" but then treats the
temp-and-delete shape as settled because the sibling settled it. The sibling
settled it for a *deterministic, short, unattended* run. The inference does not
carry to an attended agent session.

Specifically:

1. **The agent's own worktree lands inside the directory that gets deleted.**
   `coga/skills/code/implement/SKILL.md:27-30` instructs `git worktree add
   ../coga-<branch-name> -b <branch-name> main`. From
   `/tmp/coga-recurring-X/checkout`, `../coga-<branch>` resolves to
   `/tmp/coga-recurring-X/coga-<branch>` — inside the `parent` the sibling's
   `finally` does `shutil.rmtree(parent, ignore_errors=True)` on. A Dream run
   that opens a ticket, branches, and implements would have its feature checkout
   destroyed by cleanup. Not a hypothetical: it's the default instruction in the
   shipped skill.

2. **`worktree:` gets recorded pointing at a temp path.**
   `src/coga/open_pr.py:321-335` reads it back and requires that checkout to
   exist, be on the branch, be clean and ahead. After cleanup it doesn't exist.
   The ticket flags the `requires: branch` interaction but stops at "needs the
   interaction checked" — it's not a check, it's a break.

3. **The lock duration is wrong by an order of magnitude.** Checking the control
   branch out *is* the concurrency lock — that's the sibling's load-bearing
   design choice, and it's correct for a sweep measured in seconds. Here it
   means no other checkout of `main` anywhere on the machine — including the
   operator's own `git switch main` in another terminal — for
   `COGA_REPL_IDLE_TIMEOUT` (15 min default) plus `max_session`, potentially
   hours for a Dream run. The ticket names this but files it as a design
   consideration rather than as a reason to doubt the shape.

4. **It's unavailable in exactly the layout Coga recommends.** If a linked
   worktree already holds `main`, `git worktree add` fails and the sibling's
   fallback is "keep today's loud refusal." For a scheduled sweep that's a rare
   fallback. For `coga dream` typed by a human it's the *common* case, which
   means the feature would be absent for well-configured repos. The primary
   answer here should be "reuse the worktree that already holds control"
   (`git._worktree_holding_branch:4451` already finds it), not "create a
   throwaway one and give up if you can't."

5. **The payoff is two templates.** Of the seven under `coga/recurring/`, five
   carry `ticket.py` (`autoclose-merged`, `blocker-reminders`, `branch-sweep`,
   `digest`, `skill-update`). Only `dream` and `resolve-conflicts` are
   agent-backed — and `resolve-conflicts` is a `delegate:` template as of
   `5243dfd5` (today), where the sweep performs the delegated launch in the
   operator's own terminal with its own TTY-admission rules and a `coga/log.md`
   slack-sentinel completion path. That interaction is entirely unanalyzed, and
   it landed after this ticket was written.

### 5. Scope: this is two tickets, and the cheap half should ship alone

Split it:

- **A (cheap, independent of the sibling):** make the single-repo refusal
  actionable instead of a dead stop. Name the worktree already holding control
  and tell the operator to run from there; or reuse it directly. This needs no
  temp worktree, no lifetime problem, no cleanup semantics, and it fixes the
  reported symptom — `coga dream` from a feature branch being a dead stop — for
  the recommended layout. It also does not depend on the sibling.
- **B (the real ticket):** running agent sessions off-control in a created
  checkout, with the worktree-lifetime, `requires: branch`, `worktree:`
  recording, and lock-duration questions treated as the subject rather than as
  prerequisites. And if B is still wanted, a *persistent* control worktree is a
  much better candidate than a throwaway one: it removes the data-loss path, the
  recording path, and the cleanup-on-signal problem in one move.

`code/design` step 5 explicitly licenses the design step to recommend a split.
If this launches as-is, that is what I'd expect it to come back with — so it's
cheaper to split now.

### 6. Workflow fit

`code/design-then-implement` is right. This genuinely needs a written spec and
an owner gate before code. No mismatch. Note that `review-design` is where the
split decision has to be made, so whoever reviews should expect that
conversation.

### 7. The `coga/recurring` attachment: drop it

9,188 tokens (the file is 40,539 bytes / 671 lines) for four facts. Of its
fourteen sections, exactly one is the thing being changed — `## Recurring runs
start on the control branch` (lines 176-205, ~30 lines). Two more are adjacent:
the `owner` gate (206-260) and the `delegate:` gotcha at the end (~640-655),
which matters because it is the only place that explains TTY admission for
delegated launches. The rest — the creation contract, REM, Dream, the autofix
loop, dropping a new template, extending with a workflow — is not needed to
design this.

The design step can `cat` the file in one tool call if it wants the rest.
Front-loading 70% of the prompt with it buys nothing.

**Concrete recommendation:** drop `contexts: [coga/recurring]`, and put into
`## Context`:

- The exact sentence being invalidated, quoted from
  `coga/contexts/coga/recurring/SKILL.md:177-185` ("Every launching entry point
  requires the configured control branch… There is deliberately no override").
- An explicit instruction that `coga/contexts/coga/recurring/SKILL.md`, section
  `## Recurring runs start on the control branch`, must be rewritten in the same
  PR (per the repo's context-in-the-same-PR rule). There is no packaged
  duplicate of this file to sync — `src/coga/resources/templates/coga/contexts/`
  does not exist — so it's one file.
- A pointer to the `delegate:` gotcha near the end of that file, because
  `resolve-conflicts` is a delegating template and this design has to say what
  happens to it.

If you'd rather keep an attachment, `coga/cli` or `coga/sync` would earn its
place better than `coga/recurring` — the sync layer (`sync_log`,
`_push_control_branch`, detached-HEAD refusals) is where the real constraints
live.

### 8. Other things the design step will wish it had

- **What the agent actually sees.** A Dream run inside a control worktree scans
  the control tip, not the operator's dirty feature-branch tree. For Dream
  that's arguably correct; for other agent templates it may not be. The ticket
  never says which is intended, and it changes what the feature *means*.
- **`.agent-skills/` and `.coga/`.** Both gitignored (`coga/.gitignore`), so a
  fresh worktree lacks them. `.agent-skills/` is rebuilt by
  `src/coga/commands/launch.py:610` and `:1036`, so it self-heals — but the
  ticket inherits the sibling's note arguing it isn't needed *for the wrong
  reason*, and `.coga/` is not addressed at all. Say this explicitly rather than
  importing a note that argues the opposite case.
- **The `delegate:` field**, which landed in `5243dfd5` after this ticket's
  citations were taken and which changes what "agent template" means.
- **Acceptance Criteria.** Absent, which is fine for a draft that design will
  fill in — but the `Done looks like` paragraph asserts "its work and the
  serviced-period ledger reach `<remote>/<control-branch>`". The ledger does. A
  Dream run's *work* lands as PRs on feature branches and draft tickets, not on
  control. Tighten that sentence or design will encode the conflation.
- **Slug hygiene.** `recurring-should-start-by-checing-out-main` carries a typo
  ("checing") and no longer matches the title. The slug is the durable handle in
  `coga/log.md` and every task ref; worth fixing before launch rather than
  after.
