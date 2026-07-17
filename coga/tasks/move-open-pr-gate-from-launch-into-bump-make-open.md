---
slug: move-open-pr-gate-from-launch-into-bump-make-open
title: Move open-pr gate from launch into bump; make open-pr a mixed agent step
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
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
worktree: /tmp/coga-open-pr-gate-review
pr: https://github.com/FastJVM/coga/pull/585

## Peer review — done

Rebuilt the change on current `origin/main` (`4edcb1d5`) because PR #517 is
already merged and current main has since generalized per-step script dispatch.
The rework therefore preserves that general capability while making `open-pr`
an agent step whose recorded artifact is enforced by `bump`.

Commits (not pushed):
- `861d82fc` — adapted implementation and native review fixes.
- `d0d445c2` — lifecycle smoke coverage for the completion gate.

Native `codex review --base main` findings addressed:
- Require `coga open-pr` to run from the configured control checkout, while it
  pushes the branch in the recorded feature worktree.
- Make post-rebase retries safe with an observed-OID `--force-with-lease`.
- Validate malformed non-string `requires:` values instead of raising
  `TypeError` during validation or bump.
- Preserve current main's point-of-use `gh` executable/auth preflight.

Verification:
- `PYTHONPATH=/tmp/coga-open-pr-gate-review/src python3.12 -m pytest` —
  **1263 passed, 1 skipped**.
- Task-scoped `coga validate --json` — 1 task OK, no issues.
- Branch is clean, rebased, and 2 commits ahead of current main.

The original linked recovery worktree became unwritable mid-rebase, so the
review branch was recovered into the standalone worktree recorded above. Its
`origin` points at `https://github.com/FastJVM/coga.git`. PR #517 was verified
live as merged, so there is no still-open predecessor PR to close.

## Open-pr step — done

Opened https://github.com/FastJVM/coga/pull/585 by dogfooding the branch's own
command from the control checkout:
`PYTHONPATH=/tmp/coga-open-pr-gate-review/src python3.12 -m coga.cli open-pr <slug>`.
It detected origin/main's only drift as non-overlapping `coga/log.md` state,
continued visibly, pushed `open-pr-gate-in-bump`, and wrote `pr:` under `## Dev`
itself. The peer-review commits above are now pushed. #517 is merged (not open),
so per the ticket there was nothing to close; left a `superseded by #585`
traceability comment there instead.

## PR

Summary:
- Move open-PR completion enforcement into a declarative `requires: pr` gate
  checked by `coga bump`.
- Make `code/open-pr` an agent step that calls deterministic `coga open-pr`,
  while retaining mixed script-step support for other workflows.
- Add control-checkout enforcement, lease-safe rebase retries, malformed-gate
  validation, command/recipe/gate coverage, and synchronized docs/fixtures.

Test plan: `PYTHONPATH=/tmp/coga-open-pr-gate-review/src python3.12 -m pytest`
(`1263 passed, 1 skipped`).
