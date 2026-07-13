---
slug: move-open-pr-gate-from-launch-into-bump-make-open
title: Move open-pr gate from launch into bump; make open-pr a mixed agent step
status: in_progress
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
contexts:
- coga/architecture
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
secrets: null
script: null
step: 2 (peer-review)
---

## Description

Rework PR #517. That PR closed a real hole — `coga bump` could march past the
`open-pr` step with nothing built (the cross-worktree divergence incident) —
but it did so by teaching `coga launch` to detect a per-step script
(`current_step_is_script`) and run it in place of the agent inside a
`mode: agent` workflow. That adds launcher machinery for something coga's
existing primitives already compose, and forces a step to be *either*
all-agent *or* all-script (it can no longer mix). It also pulled the `## Dev`
text-extraction into Python (`parse_worktree_path`) when an agent step already
has `## Dev` in its prompt.

**Move the gate from `launch` into `bump`, and let `open-pr` be a normal
(mixed text + script) agent step.**

### Base branch

Branch this work on `open-pr-script` (PR #517's branch), not fresh off `main`.
Reuse #517's `src/coga/open_pr.py` recipe, `autoclose.py`'s `parse_pr_url` /
`parse_worktree_path`, and `test_open_pr.py` intact. #517 is superseded by this
rework — close it (with a `superseded by #NNN` comment) when this PR opens.
Do not close #517 before then.

### Target shape

`open-pr` is an agent step again. The agent:
1. has `## Dev` (branch/worktree) in its composed prompt,
2. runs `coga open-pr <slug>` — a deterministic command that pushes the
   recorded branch, opens/readies the PR, and writes `pr: <url>` under
   `## Dev`, failing loud on no-branch / no-commits-ahead / `gh` error,
3. runs `coga bump`.

The gate becomes a **data check in `bump`**: `coga bump` refuses to advance
*off* a step that declares a completion gate until the required artifact is
recorded. A rogue agent that skips step 2 and bumps is rejected because there
is no `pr:`. Structural, not advisory — and the exit code stops being the gate,
the recorded artifact is.

### Gate mechanism (decided: declarative)

A workflow step may declare `requires: <token>` (frozen into frontmatter).
`bump` consults a tiny check registry `{"pr": parse_pr_url}` against the task
blackboard before advancing off that step; falsy → fail loud with a message
pointing at `coga open-pr <slug>`. `code/with-review`'s `open-pr` step declares
`requires: pr`. This keeps `bump` generic — no `code/*` skill name hardcoded
into the step engine — and lets any future step gate on a recorded artifact.

### Changes by file

- **Add `coga open-pr` command** — `src/coga/commands/open_pr.py`, registered
  in `cli.py`. Thin wrapper over the existing `src/coga/open_pr.py:open_pr()`
  recipe (from #517 — keep it). Operates on the `## Dev` branch **by name**, so
  it is worktree-agnostic; this is what actually retires the cross-worktree
  divergence trap, not a script-step worktree special-case.
- **Add the bump gate** — `src/coga/commands/bump.py`: before advancing, run
  the current step's `requires:` predicate against the blackboard; fail loud
  when unmet. Add `requires` to the frozen-step schema + `coga validate`.
- **Revert `src/coga/commands/launch.py`** — drop `run_current_as_script` and
  the supervisor-loop inline script branch (the whole #517 launch diff). Keep
  `is_script_launch` for whole `mode: script` tickets. `open-pr` is a normal
  agent step, so the existing agent-step supervisor path handles it.
- **Trim `src/coga/commands/launch_script.py`** — remove `current_step_is_script`
  (unused after the revert). Keep `run_script_mode` / `is_script_launch`.
- **Keep** `src/coga/open_pr.py` and `autoclose.py`'s `parse_pr_url` /
  `parse_worktree_path` (now consumed by both the command and the bump gate).

### Docs / contexts (live AND packaged copies, kept in sync)

- `code/open-pr/SKILL.md`: back to an agent skill — "read `## Dev`, run
  `coga open-pr <slug>`, then bump." Drop `script: run.py`.
- `coga/architecture` `SKILL.md`: replace the "Script steps inside an agent
  workflow" section with the completion-gate story (`requires:` on a step,
  enforced by `bump`).
- `dev/code` `SKILL.md` + `code/with-review`, `code/with-self-review`,
  `code/design-then-implement` workflow docs: `open-pr` is an agent step with
  `requires: pr`.

### Tests

- New `tests/test_open_pr_command.py` (command wiring); keep `test_open_pr.py`
  (recipe unchanged).
- New bump-gate cases in `tests/test_bump.py`: advance blocked with no `pr:`,
  allowed once recorded.
- Delete #517's `test_launch_chains_agent_into_scripted_step` and the
  `current_step_is_script` tests in `test_launch_script.py`.

### Verify explicitly

`coga open-pr` pushing the recorded branch by name is agnostic to
launch-worktree isolation — the exact seam the incident lived in gets its own
test.

## Context

This reworks the open PR #517
(https://github.com/FastJVM/coga/pull/517). Read that PR and its ticket
(`make-open-pr-a-script-step-so-bump-requires-a-real`) for the incident it
closed and the `open_pr()` recipe it introduced (which this rework keeps). The
design rationale — gate belongs in `bump` as a data check, not in `launch` as
per-step dispatch; steps should be able to mix text + script — is the outcome
of a design discussion; the `requires:` gate is the agreed mechanism.

<!-- coga:blackboard -->

## Dev
branch: open-pr-gate-in-bump
worktree: /home/n/Code/claude/coga-open-pr-gate
pr: (not yet created)

## Implement — done (committed, not pushed)

Commit `3f8820b5` on `open-pr-gate-in-bump`. Net `git diff main`: 25 files,
+1573/-150. Full suite green: **1096 passed, 1 skipped** (python3.12 venv; the
repo requires 3.11+). One pre-existing random-order flake in
`test_usage_probe.py` (passes in isolation and under `-p no:randomly`; untouched
by this change). `coga validate` clean for this change (the 20 live-repo errors
are pre-existing fenceless `install/*` task docs; example fixture validates 0).

What landed, mapped to the ticket:
- **`coga open-pr` command** (`src/coga/commands/open_pr.py`, registered in
  cli.py + `_BUILTIN_COMMANDS`): thin wrapper over the kept `coga.open_pr`
  recipe; pushes the `## Dev` branch by name.
- **Bump gate** (`src/coga/step_gate.py` registry `{"pr": parse_pr_url}`;
  `commands/bump.py` consults the current step's `requires:` before advancing,
  forward-only). `requires` added to WorkflowStep parse/freeze (`workflow.py`)
  and to `coga validate` (`validate.py`).
- **Reverted** #517's launch.py per-step-script dispatch (launch.py now == main)
  and dropped `current_step_is_script` from launch_script.py; kept
  `is_script_launch`.
- **`code/open-pr`** back to an agent skill (dropped `script: run.py`, deleted
  run.py both copies). Workflows declare `requires: pr` on the PR step.
- Docs/contexts synced live + packaged.

### Note for reviewer / open-pr step
- **Base:** branched off `open-pr-script` then **merged `main`** in (clean), so
  `git diff main` is exactly this rework — no revert of #516 etc. #517 is still
  open; close it as `superseded by #NNN` **when this PR opens** (open-pr step).
- **Packaged `architecture/SKILL.md` was already stale vs the live copy on
  main** (config-fail-loud section etc. missing). I applied ONLY my section
  replacement to it (not a full resync) to keep this PR scoped; that pre-existing
  drift is left as-is. The other three packaged files were in sync and got the
  matching edits.

### Adjacent (not fixed here — out of scope)
- Packaged/live `coga/contexts/coga/architecture/SKILL.md` drift on main
  predates this work; worth a follow-up sync ticket.

## Plan / decisions

**Base branch handling.** Task said "branch on `open-pr-script`". That branch
forked at `e89f2ee` and `main` has ~40 commits since (incl. #516's
already-satisfied close path). Branching straight off it and PRing against main
would spuriously revert merged work. Resolution: branched off `open-pr-script`
into `open-pr-gate-in-bump`, then **merged current `main` in** (clean merge).
Net `git diff main` is now exactly #517's changes — nothing merged is reverted.
Reuses #517's `open_pr.py` recipe, `autoclose.py` parse fns, and
`test_open_pr.py` intact per the ticket.

**Rework shape** (moving the gate from launch → bump):
- New `coga open-pr <slug>` command → thin wrapper over `open_pr()` recipe;
  operates on the `## Dev` branch by name (worktree-isolation-agnostic).
- `bump` gate: new `coga/step_gate.py` registry `{"pr": parse_pr_url}`. `bump`
  refuses to advance *off* a step that declares `requires:` until the artifact
  is recorded on the blackboard. Forward-only (rewind never gated).
- `requires:` added to WorkflowStep parse/freeze + `coga validate`.
- Revert #517's launch.py per-step-script dispatch; drop
  `current_step_is_script` from launch_script.py.
- `code/open-pr` back to an agent skill (drop `script: run.py`; delete run.py).
- Workflows: open-pr is an agent step with `requires: pr`.
- Docs/contexts synced (live + packaged copies).

## Usage

{"agent":"claude","cache_creation_input_tokens":583430,"cache_read_input_tokens":43802699,"cli":"claude","input_tokens":64727,"model":"claude-opus-4-8","output_tokens":224995,"provider":"anthropic","schema":1,"session_id":"ef77b458-be8c-42f0-a6dd-91bff5dfd497","slug":"move-open-pr-gate-from-launch-into-bump-make-open","step":"implement","title":"Move open-pr gate from launch into bump; make open-pr a mixed agent step","ts":"2026-07-06T06:07:21.451139Z","usage_status":"ok"}
