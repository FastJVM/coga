---
slug: build-an-order-for-megqlaunch
title: 'megalaunch: drain blocked tickets whose dependency landed in the same run'
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
---

## Description

`coga megalaunch` runs its queue oldest-first with no notion of ordering
between tickets. When ticket B needs ticket A to land first, B's agent
discovers the missing dependency mid-step and ends the session with
`coga block` — and that is terminal for the run. B stays parked even when A
completes minutes later in the *same* sweep, so the operator has to notice and
re-run megalaunch by hand. The same is true of a ticket that was already
`blocked` when the sweep started: it is skipped outright
(`skipped-unresolved-blocker`), even if this run lands the very thing it was
waiting for.

Add a **drain loop**. After the main sweep finishes, megalaunch re-examines
blocked tickets; for each one whose blocker is now satisfied it **resolves the
open blocker and then launches the ticket normally**; if any launched, it
restarts the walk from the top (an earlier drain may satisfy a later ticket).
A full pass that launches nothing is terminal — report and exit.

Deliberately *no* dependency model: no `depends_on:` frontmatter, no
topological sort, no new CLI flag. Satisfaction is decided by reading the open
blocker text off the blackboard, scanning it for a known task slug, and
checking whether that ticket has since finished.

## Context

### Decisions taken during ticket authoring (and why)

1. **Dependencies are discovered at run time, not declared.** A declared
   `depends_on:` / `after:` field plus a topological sort was considered and
   rejected — it is only as good as what someone remembers to declare, and the
   agent doing the work already discovers the real dependency for free.
2. **The agent blocks; megalaunch decides when to retry.** `coga block` keeps
   its current signature. No `--waiting-on` flag, no new ticket field.
3. **The satisfaction check must be pure Python — never spawn an agent to ask
   "are you still blocked?"** Before relaunching a blocked ticket, megalaunch
   reads its open blocker text, scans for known task slugs, and proceeds only
   if a named ticket has since finished.
4. **Satisfaction resolves the blocker, then launches — it is a one-way
   transition.** On a satisfied dependency megalaunch calls
   `resolve_open_blockers(...)` with an explanatory answer *before* launching,
   so the ticket enters the launch path as an ordinary reactivated task with no
   open asks. This is what makes the loop terminate: a drained ticket leaves the
   eligible set by construction, so it cannot be picked up again on the next
   pass regardless of how its session ends. A heuristic "did it make progress?"
   rule was considered and rejected — see the termination risk below for why it
   does not terminate.
5. **Fixed-point loop, not a single retry pass.** Walk all blocked tickets;
   drain any that are satisfied; if any launched, **restart the walk from the
   top** (an earlier drain may satisfy a later ticket). A full pass that
   launches nothing ends the run.
6. **Retry scope is every blocked ticket in scope**, not only the ones this run
   blocked. Chosen for simplicity and flexibility. Accepted cost: a
   human-parked blocker whose reason incidentally names a finished slug gets
   drained and relaunched once — and because draining resolves the blocker,
   that is not self-correcting. The answer text written by
   `resolve_open_blockers` must therefore say plainly that megalaunch resolved
   it automatically and name the dependency it matched.
7. **Convention, not schema.** Add one line to the queue directive telling
   agents to name the blocking ticket's slug in `--reason`. This is what makes
   the scan fire; without it a blocker phrased as "waiting on the schema
   migration" parses to nothing.
8. **Drain relaunches count against `--max-tasks`** like any other launch. The
   loop must not be able to exceed the operator's stated budget.

### Codebase pointers

*Line numbers were verified at authoring time; treat them as starting points,
not gospel.*

- `src/coga/megalaunch.py` — module docstring (`:38`) states today's order:
  oldest-first by first `coga/log.md` line, via `first_activity_map` (imported
  at `:70`, implemented in `src/coga/logfile.py`) and `_tasks_oldest_first`
  (`:538`). `run_megalaunch` is at `:140`.
- Blocked tickets are skipped today with outcome `skipped-unresolved-blocker`
  (`:581`, `:587`). The `MegalaunchOutcome` literal (`:97`) and the counts dict
  in `MegalaunchRun.counts` (`:126–134`) both need updating for whatever the
  drain loop reports.
- Reactivating a blocked ticket for launch exists today only on the *selection*
  path (`_activate_for_launch`); the sweep path has no such step. The drain loop
  needs one.
- `_launch_until_stop` (`:751–759`) calls `_reblock_unresolved`, which returns a
  ticket to `blocked` when the session exits `in_progress` with any ask still
  open. Decision 4 exists to keep the drain path out of that trap.
- `open_blockers(ticket_path) -> list[Blocker]` lives in
  `src/coga/blackboard.py:285` and is **already imported** by megalaunch
  (`:52`) — the read side exists. Its sibling `resolve_open_blockers`
  (`blackboard.py:290`) is the write side decision 4 needs.
- `coga block` (`src/coga/commands/block.py`) appends the free-text reason via
  `append_blocker` (`:48`) and sets `status: blocked` (`:54`). `--reason` is
  required and non-empty (`:26–28`), so there is always text to scan. Note
  megalaunch itself writes **no** blocker record today — `_reblock_unresolved`
  calls `mark_blocked`, which flips `status:` and does not touch `## Blockers`.
- `--max-tasks` already exists (`src/coga/commands/megalaunch.py:73`) and is the
  natural budget for decision 8.
- Queue directive to amend: `src/coga/resources/prompt-megalaunch.md`.
- Tests: `tests/test_megalaunch.py`.
- Per `CLAUDE.md`, behavior changes update the matching context in the same PR.
  Megalaunch behavior is described in `coga/contexts/coga/architecture/SKILL.md`
  (megalaunch at `:302`, `:347`, `:387`). Keep the live copy under `coga/` and
  the packaged copy under `src/coga/resources/templates/coga/` in sync.

### Risks the implementer must handle

- **Termination is the whole design.** A "did it make progress?" rule was
  considered and does **not** work: a drained ticket that does real work and
  bumps, but never runs `coga unblock`, is returned to `blocked` by
  `_reblock_unresolved` with the same blocker still naming the same finished
  slug. It is then eligible again *and* it made progress, so the loop restarts
  and relaunches it forever. Decision 4 (resolve the blocker before launching)
  is the structural fix — do not replace it with a progress heuristic.
- **A drained relaunch must not inherit the blocker-resolution preamble.**
  `compose.py:156–176` injects it whenever open asks exist, and
  `prompt-blocker-resolution.md` tells the agent to *discuss the asks with the
  human* — wrong in an unattended queue. Decision 4 avoids this by construction
  (no open asks at launch time). Any alternative design must handle it another
  way. The `prompt-megalaunch.md` amendment in decision 7 is for a different
  purpose and does not cover this.
- **"Finished" has three states, not two.** A dependency may be `done`, or it
  may be *gone*: a session earlier in the same sweep can legitimately retire a
  finished task and delete its directory (`megalaunch.py:261–266`,
  `bootstrap/delete-task`). A naive `status == "done"` check raises
  `TicketNotFoundError` on the most completely finished case and treats it as
  unsatisfied. Handle both.
- **Slug scanning is lossier than it looks.** `append_blocker` writes the
  blocker as a **single line** and the parse regex captures the reason as the
  rest of that line — so a multi-line `--reason` silently loses everything after
  the first line, including a slug on line 2. Slugs are also truncated to ~50
  chars and nested tickets carry a `dir/slug` id, so an agent paraphrasing from
  memory will often not produce an exact match. False negative = ticket stays
  blocked (status quo, acceptable). False positive = an unwanted drain that
  decision 6 says must be legible in the resolution text.
- **Result accounting.** Each drain appends a second `MegalaunchResult` for a
  slug already in `run.results`, so `counts` double-counts and
  `render_run_summary` lists the slug twice. Decide whether a drain supersedes
  the earlier result or is reported as its own line.
- **Sweep scope is narrower than "every blocked ticket" implies.** `_run_sweep`
  (`:279`) skips tickets whose `owner != cfg.current_user`, and the queue is a
  snapshot taken before the first launch — so a ticket blocked *and created*
  mid-run is invisible to the drain loop unless it re-lists.
- **Every drain relaunch is a real interactive REPL** under the same TTY and
  the same idle-timeout / max-session backstops as the main sweep. The loop
  must not defeat those backstops.

### Open questions for the implement step

- Does the drain loop run for the default sweep only, or also for explicit
  `--pick` / `--relaunch` selections?
- Should the terminal pass report still-blocked tickets distinctly from ones
  that were never eligible?

### Out of scope

Declared dependency fields; topological reordering of the main sweep;
persisting dependency information across runs; changing `coga block`'s CLI
signature.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
pr: https://github.com/FastJVM/coga/pull/630
branch: megalaunch-blocker-drain
worktree: /tmp/coga-megalaunch-blocker-drain

## Implementation plan (confirmed 2026-07-22)

- Run the fixed-point dependency drain only after the default sweep. An explicit
  `--pick` / `--relaunch` selection must not expand into unpicked work.
- Re-list owner- and directory-scoped blocked tickets on each pass; match blocker
  text against known task refs, treating `done` and a ref deleted during the run
  as finished.
- Resolve the open asks with a legible megalaunch answer naming the matched
  dependency before activation/launch, and never drain the same ticket twice in
  one run.
- Keep one result row per task: a drain replaces its earlier blocker-skip row,
  carries a `drained` marker/count, and retains the final launch outcome. A
  terminal unsatisfied blocker keeps `skipped-unresolved-blocker`.
- Share `--max-tasks` across the main sweep and drain attempts; restart the scan
  after every actual drain launch.

Accepted tradeoffs: explicit selections will not chain into
unselected blocked tickets, and terminal reporting will not distinguish a
recognized-but-unfinished dependency from a blocker with no recognized task ref.

Primary checkout note: `coga/log.md` was already modified before implementation;
preserve it as unrelated control-plane state.

## Implementation progress

- Added the default-sweep fixed-point drain. It re-lists current-owner blocked
  work in scope, remembers refs deleted during the run, resolves exact-slug
  blockers before activation, and drains each ticket at most once.
- Drain attempts share the main `--max-tasks` budget. Results remain one row
  per task and carry an orthogonal `drained` marker/count; explicit selections
  do not drain unpicked work.
- Important write invariant: re-read the ticket after
  `resolve_open_blockers(...)` and before `mark_active(...)`; otherwise the
  stale `Ticket.body` would reopen the blocker while writing frontmatter.
- Updated `prompt-megalaunch.md` with the exact path-qualified slug convention
  and documented the behavior in both architecture-context copies.
- Verification so far: `tests/test_megalaunch.py` (62 passed); full suite
  (1402 passed, 1 skipped); task-scoped validation passed with only the
  worktree's expected missing-local-user warning.

## Implement handoff

- commit: `454b028d` (`Drain megalaunch blockers after dependencies finish`)
- rebased onto: `origin/main` at `44c73a5c`
- post-rebase verification: `tests/test_megalaunch.py` (62 passed), full suite
  (1402 passed, 1 skipped), `git diff --check` clean.
- The live and packaged architecture files carry the same new megalaunch
  section. Their unrelated pre-existing deprecated-config paragraph difference
  was preserved.

## Follow-up

- The full pytest run inherited this launch's `COGA_TASK_BLACKBOARD`; two
  Dream-script tests appended fixture output to the live ticket. The artifacts
  were removed. The peer-review tool reproduced the same leak before later
  verification runs explicitly scrubbed the metadata. A separate test-harness
  fix should scrub inherited `COGA_TASK_*` metadata before subprocess tests.

## Peer review

`codex review --base main` found three must-fix edge cases; all were confirmed:

- dotted directory refs can let a shorter completed slug false-match inside an
  unfinished dependency ref;
- a caller-accepted trailing slash in the directory scope is normalized for the
  main sweep but not for the blocker drain;
- replacing a main-sweep result with a pre-spawn drain failure can erase that
  the task launched earlier in the same run.

Applied the three focused fixes: task-ref boundaries now include dotted path
segments, the drain normalizes the accepted directory spelling, and result
replacement preserves whether any attempt launched. Verification before the
freshness rebase: `tests/test_megalaunch.py` (65 passed), full suite (1405
passed, 1 skipped), and `git diff --check` clean.

## Peer-review handoff

- implementation commit: `95824c9b` (`Drain megalaunch blockers after dependencies finish`)
- peer-review commit: `60b1ac39` (`peer-review: fix megalaunch drain edge cases`)
- rebased onto: `origin/main` at `326bb553`
- post-rebase verification: full suite (1420 passed, 1 skipped), and
  `git diff --check` clean; task-scoped validation passed with only the
  installed-version-skew warning; feature worktree clean.

## PR

Summary:

- Add a fixed-point post-sweep drain that recognizes finished task refs in open
  blockers, resolves those asks before composition, and relaunches the blocked
  task through the normal megalaunch path.
- Re-list current-owner blocked work on every pass, handle dependencies deleted
  after finishing, share `--max-tasks`, keep one summary row per task, and leave
  explicit selections scoped to exactly what the operator picked.
- Make exact-ref matching safe for nested and dotted task paths, normalize the
  directory scope across both phases, and preserve earlier launch accounting on
  a failed retry.
- Document the behavior in both architecture-context copies and teach queued
  agents to include the exact path-qualified dependency slug in blocker text.

Test plan: `python -m pytest` (1420 passed, 1 skipped).
