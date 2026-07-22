---
slug: build-an-order-for-megqlaunch
title: "megalaunch: drain blocked tickets whose dependency landed in the same run"
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- dev/code
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

`coga megalaunch` runs its queue oldest-first with no notion of ordering
between tickets. When ticket B needs ticket A to land first, B's agent
discovers the missing dependency mid-step and ends the session with
`coga block` — and that is terminal for the run. B stays parked even when A
completes minutes later in the *same* sweep, so the operator has to notice and
re-run megalaunch by hand.

Add a **drain loop**. After the main sweep finishes, megalaunch re-examines
blocked tickets, relaunches any whose blocker is now satisfied, and repeats
from the top until a full pass launches nothing; that pass is terminal and the
run reports and exits.

Deliberately *no* dependency model: no `depends_on:` frontmatter, no
topological sort, no new CLI flag. Satisfaction is decided by reading the open
blocker text off the blackboard, scanning it for a known task slug, and
checking whether that ticket is now `done`.

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
   reads its open blocker text, scans for known task slugs, and relaunches only
   if a named ticket is now `done`.
4. **Fixed-point loop, not a single retry pass.** Walk all blocked tickets;
   launch any that look satisfied; if any launched, **restart the walk from the
   top** (an earlier ticket may have unblocked a later one). A full pass that
   launches nothing ends the run.
5. **Retry scope is every blocked ticket in scope**, not only the ones this run
   blocked. Chosen for simplicity and flexibility. Accepted cost: a
   human-parked blocker whose reason incidentally names a now-`done` slug will
   get relaunched once.
6. **Megalaunch normalizes the blocker record it writes** when a supervised
   session ends in `coga block`, so later passes parse a stable shape instead
   of re-scanning free prose. Exact shape is a design-step decision.
7. **Convention, not schema.** Add one line to the queue directive telling
   agents to name the blocking ticket's slug in `--reason`. This is what makes
   the scan fire; without it a blocker phrased as "waiting on the schema
   migration" parses to nothing.

### Codebase pointers

- `src/coga/megalaunch.py` — module docstring (`:39`) states today's order:
  oldest-first by first `coga/log.md` line, via `first_activity_map`
  (`:70`) and the ordering helper around `:543`. `run_megalaunch` is at `:140`.
- Blocked tickets are skipped today with outcome `skipped-unresolved-blocker`
  (`:581`, `:587`). The `MegalaunchOutcome` literal (`:96`) and the counts dict
  in `MegalaunchRun.counts` (`:131`) both need updating for whatever the drain
  loop reports.
- `open_blockers(ticket_path) -> list[Blocker]` lives in
  `src/coga/blackboard.py:285` and is **already imported** by megalaunch
  (`:52`) — the read side exists.
- `coga block` (`src/coga/commands/block.py`) appends the free-text reason via
  `append_blocker` and sets `status: blocked`. `--reason` is required and
  non-empty, so there is always text to scan.
- Queue directive to amend: `src/coga/resources/prompt-megalaunch.md`.
- Tests: `tests/test_megalaunch.py`.
- Per `CLAUDE.md`, behavior changes update the matching context in the same PR.
  Megalaunch behavior is described in `coga/contexts/coga/architecture/SKILL.md`
  (megalaunch at `:302`, `:347`, `:387`). Keep the live copy under `coga/` and
  the packaged copy under `src/coga/resources/templates/coga/` in sync.

### Risks the implementer must handle

- **Termination is the whole design.** Define "progress" precisely: a ticket
  that relaunches, does no work and blocks again on the same ask must **not**
  count as progress, or the loop spins and burns agent sessions. Progress
  should mean the step actually advanced (bump / done), not merely "launched".
- **False positives are cheap, false negatives are silent.** A reason that
  mentions a `done` slug incidentally causes one wasted relaunch (the agent
  re-blocks) — tolerable, provided the progress rule above treats it as no
  progress. A blocker with no slug in it never drains at all; accepted,
  mitigated by decision 7.
- **Every drain relaunch is a real interactive REPL** under the same TTY and
  the same idle-timeout / max-session backstops as the main sweep. The loop
  must not defeat those backstops.

### Open questions for the design/implement step

- Does "satisfied" mean the named ticket is strictly `done`, or any state past
  the blocking point?
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
