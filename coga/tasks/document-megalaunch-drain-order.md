---
slug: document-megalaunch-drain-order
title: Surface megalaunch drain order and the numbered-task convention in `--help`
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

`coga megalaunch` orders the tasks it drains, and the ordering is expressive:
oldest-first by first `coga/log.md` line, except that a sub-directory whose
tasks carry `1-`/`2-`/`3-` prefixes runs as one contiguous block in number
order. That is how you sequence a pipeline — and because it is a naming
convention rather than a flag, there is nothing to stumble onto.

`coga megalaunch --help` never mentions it. Someone reading the help text sees
`DIR`, `--pick`, `--relaunch`, `--max-tasks`, `--agent` and concludes the
command has no ordering story. That is the whole bug: the behavior is correct
and the long-form docs are fine, but the surface people actually read is
silent.

Fix the help text and add a regression test so it can't go quiet again.

## Context

### Where the facts live — read, don't re-derive

The behavior is well documented already. Read these rather than reconstructing
the rules from source:

- `docs/reference.md:122-128` — complete and accurate: age ordering, the
  `1-schema`/`2-migrate`/`3-cutover` convention, block anchoring, unnumbered
  siblings, top-level exemption, `--pick` parity, `status --order-by created`
  parity, the `coga validate` duplicate warning.
- Packaged `bootstrap/contexts/coga/cli/SKILL.md:662-688` — the fullest
  writeup, "**Drain order.**" section. Deliberately not attached to this ticket
  (~58 KiB / ~15k tokens composed); open the file directly.
- `src/coga/service_order.py:1-27` — module docstring, the implementation's own
  statement of the rules.

Two details worth knowing because they are easy to get wrong in help text:

- The prefix match is strict — `^(\d+)-` (`service_order.py:37-40`). `02-` ==
  `2-`, `10-` sorts after `9-`, and `2fa-login` is **not** numbered.
- **`--pick` does not order anything.** The selection is a set filter applied
  over the already-service-ordered queue (`megalaunch.py:211-214`), so pick
  order is discarded. Worth a clause in the help text; it is a real trap.

### The gap

**`src/coga/commands/megalaunch.py:48-93`** — the Typer help strings, silent on
ordering. This is the fix, and it is the whole fix.

`coga pick` is an argv alias (`pick = "megalaunch --pick"`), **not** a separate
command — there is no second docstring to edit, and inventing a `pick` command
would violate the microkernel rule in `CLAUDE.md`.

Deliberately out of scope, each with a reason — do not "fix" these:

- **`src/coga/resources/prompt-megalaunch.md`.** Owner decided to leave it out:
  a queued agent has already been selected and ordered, so drain order is not
  actionable for it, and that file's word budget is spent on every queued
  session.
- **A megalaunch `SKILL.md`.** Its absence is not an oversight. Commit
  `2741d36f` (#550) removed it — megalaunch is on-demand only, unlike the
  recipe-backed `autoclose/sweep`, `blockers/remind`, `branch-sweep/sweep`.
  `paths.py:11-16` still carries the migration message. Re-adding it reverses a
  merged decision.
- **A repo-side `coga/contexts/coga/cli/` copy.** Context refs fall back to the
  packaged copy (`resolve_context_path`, `paths.py:133-142`), so `coga/cli`
  already resolves in this repo — `nightly-auto-drain-run-for-ready-tickets.md:11`
  attaches it today. A repo copy would create a 1,058-line sync burden that
  currently does not exist.
- **`docs/reference.md`.** Already correct. Leave it.
- **`README.md`, `AGENTS.md`, `CLAUDE.md`, the `usage`/`architecture`
  contexts.** Ordering is off-topic for their framing.

### Tests — cover discoverability, not the ordering logic

**The ordering logic is already well covered — do not add tests there.**
`tests/test_service_order.py` has 9 focused tests spanning every edge case
(`2fa-login` not numbered, top-level ignored, no-log-line sorts last, block
anchoring, per-directory numbering, nested groups), plus
`tests/test_megalaunch.py:1709,1757` end-to-end and
`tests/test_validate.py:1619-1662` for duplicate positions. Duplicating that is
waste.

What is untested is the thing that actually failed — **nothing asserts any
user-facing surface states the convention**, which is why it could go missing
with every test green. Add a regression test that `coga megalaunch --help`
mentions the drain order and the numbered-task convention. Assert on substance
(oldest-first, `1-`/`2-`/`3-` sequencing), not exact prose, so wording stays
editable. Extend an existing test module rather than adding one.

Run `python -m pytest` and put the exact command in the PR.

### Scope boundary

Permitted: the megalaunch help strings and the test above. Nothing else.

**Do not change ordering logic, `coga.service_order`, or any runtime
behavior.** The convention is correct as built; this ticket only makes it
discoverable. If you conclude the convention itself is wrong, stop and raise it
— that is a different ticket.

### Done looks like

Someone who runs `coga megalaunch --help` and reads nothing else learns that
tasks drain oldest-first, that naming a sub-directory's tasks `1-`/`2-`/`3-`
sequences them, and that it is a naming convention rather than a flag. A test
fails if that stops being true.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Implementation notes

- Scope confirmed: change only `src/coga/commands/megalaunch.py` help text and
  extend an existing test module with a help-discoverability regression.
- Help must state oldest-first draining, the sub-directory `1-` / `2-` / `3-`
  naming convention, and that `--pick` filters the already ordered queue rather
  than honoring selection argument order.
- Runtime ordering and long-form documentation are already correct and remain
  untouched.

## Dev

branch: codex/megalaunch-drain-help
worktree: /tmp/coga-feature.Q4qFDr/repo

The linked-worktree attempt hit the launch sandbox's read-only `.git` metadata,
so this is the documented independent clone fallback, refreshed from
`origin/main`.

## Verification

- Added the discoverability regression first; it failed against the existing
  help because `oldest-first` was absent:
  `python -m pytest tests/test_megalaunch.py::test_megalaunch_help_describes_drain_order`
- After the help change, the focused regression passed.
- Full suite passed: `python -m pytest` — 1569 passed, 1 skipped in 57.17s.
- Committed as `b3b0d975` (`Document megalaunch drain order in help`).
- Final `git fetch origin main && git rebase FETCH_HEAD` reported the feature
  branch up to date; the feature checkout is clean and contains `FETCH_HEAD`.

## Peer review

- Initial inspection confirms the feature diff is limited to the megalaunch
  help strings and an existing megalaunch test module, as required.
- The help states oldest-first draining, the sub-directory `1-` / `2-` / `3-`
  naming convention, and that `--pick` filters the service-ordered queue
  instead of using selection argument order.
- `codex review --base main` found no actionable regressions after tracing the
  wording against `service_order`, the rendered Typer help, and the existing
  reference/context documentation.
- Refreshed unconditionally with `git fetch origin main && git rebase
  FETCH_HEAD`; the feature commit rebased cleanly onto `74aa7f7f`.
- Full post-rebase suite passed: `python -m pytest` — 1569 passed, 1 skipped in
  59.69s.
- No peer-review code changes were necessary; the feature checkout is clean at
  `18b2d6d1`.

## PR

Surface the existing megalaunch service order in `coga megalaunch --help`:
tasks drain oldest-first, `1-` / `2-` / `3-` task names sequence a
sub-directory as a contiguous numbered pipeline, and `--pick` filters that
already ordered queue. Add a regression test that keeps those conventions
discoverable without pinning the exact prose.

Test plan: `python -m pytest`
