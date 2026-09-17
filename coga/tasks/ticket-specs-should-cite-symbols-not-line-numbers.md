---
title: Ticket specs should cite symbols, not line numbers
status: in_progress
owner: nicktoper
agent: claude
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
    skills:
    - code/address-pr-comments
    assignee: owner
step: 3 (open-pr)
launch_generation: pending:c053a51a-a6de-4236-9421-7cdffdda1ffe
---

## Description

Source citations in a ticket body rot before the ticket is implemented, and three independent
tickets each hand-wrote their own warning about it because no skill carries the rule.
`launch-ignores-the-recorded-worktree-stranding-bla` opens its `## Context` with "Citations here
name **symbols, not line numbers**. An earlier draft pinned line numbers twice; both sets had
drifted within days."

Add the rule to `coga/skills/code/design/SKILL.md` and its packaged twin
`src/coga/resources/templates/coga/bootstrap/skills/code/design/SKILL.md` (edit both — they are a
synchronized pair).

## Context

Found by Dream 2026-08-24, Phase 2 knowledge scan — shard-03 and shard-05 reported this
independently from different evidence and were merged at reconciliation.

This run produced fresh evidence for it: Phase 3 shard ca-07 found `docs/cli-extension-audit.md`
citing a stale `cli.py:74-93` range for command registration, which had drifted exactly as
predicted.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: design-cite-symbols
worktree: /home/n/Code/claude/coga-design-cite-symbols

## Implement (2026-09-02)

**What changed.** `coga/skills/code/design/SKILL.md` and its packaged twin
`src/coga/resources/templates/coga/bootstrap/skills/code/design/SKILL.md` gain a new
`Order of operations` step 3, **"Cite symbols, not line numbers"** (old steps 3-6
renumbered to 4-7), plus an Acceptance bullet: "Every source citation in the spec names
a file and a symbol. No claim rests on a bare line number."

The rule carries the two refinements the evidence asked for, rather than a flat ban:
- a range is allowed when it aids navigation of a long module, but only after the symbol
  and only marked as expected to drift;
- best is to state the *relationship* that makes a fact load-bearing ("nothing between
  `spawn_agent_session` and the subprocess chooses the cwd"), because relationships
  survive refactors and coordinates do not.

**Decision — placement.** Its own numbered step, between "Investigate" and "Write the
spec", not a Gotcha. Gotchas are advisory; this is a form rule for the step's actual
output, and pairing it with an Acceptance bullet makes it checkable in `review-design`.

**Decision — verified example symbols.** `git.sync_task_state`, `spawn_agent_session`,
and the anti-example are grepped from live source, so the skill does not itself ship a
stale citation. (`git.py:597-640` appears only as the anti-example; its drifting is the
point.)

**Sync enforcement.** The design pair was *not* in `IDENTICAL_LIVE_PACKAGED_PAIRS` in
`tests/test_packaging.py`, so nothing guarded the "synchronized pair" the ticket depends
on. Registered it. New `tests/test_code_design_skill.py` asserts the rule's content,
mirroring `tests/test_code_implement_skill.py`.

**Tests.** `python -m pytest` in the feature worktree: 2203 passed, 1 failed.
The one failure is `tests/test_packaging.py::test_wheel_includes_bootstrap_batteries`,
which fails identically on unmodified `main`: the repo `.venv` has no `pip`, so the test's
`python -m pip wheel` subprocess cannot run. Environmental, not caused by this change.
No `example/` fixture carries a `code/design` copy, so no fixture update was needed.

## Related work

The sibling `coga/tasks/no-rule-says-ticket-context-must-cite-symbols-not.md`
landed as `e41d0262` (PR #793) while this branch was parked. Its
`bootstrap/ticket` skill owns the detailed citation rule and examples. This
branch keeps that pointer and extends the design skill's existing guidance
from `## Context` to all code claims in the spec.

## Peer review

Review (2026-09-17) on `design-cite-symbols` in the recorded
feature worktree. The branch was clean at `e787fd1b`. Fetched `origin/main`
at `9919d9c7` and started the required rebase; both design skill copies and
`tests/test_packaging.py` conflicted.

Rebase decisions: preserve current main's composed-section layout and frozen
workflow handoff. The sibling ticket has now landed as `e41d0262` (PR #793),
adding citation guidance for `## Context`; this change extends the rule to
the whole spec and its acceptance checklist. Consolidate the overlapping
guidance. Keep main's automatic twin discovery, which already covers
`code/design`, instead of restoring the obsolete manual pair registry.

The rebase completed at `a9c6d6f7` with a clean feature worktree and three
changed files: the identical skill pair and the existing content test.
`codex review --base origin/main` **returned**, exit 0: "No actionable
regressions found." It verified the skill pair and passed 20 targeted tests
with `PYTHONPATH="$PWD/src" /home/n/Code/claude/coga/.venv/bin/python -m pytest
tests/test_code_design_skill.py tests/test_bootstrap_ticket_skill_template.py
tests/test_packaging.py -q --tb=short`. Full review output is in
`/tmp/coga-design-cite-symbols-review-20260917.log`. No must-fix findings
remain and no additional review-fix commit was needed after the rebase.

Manual surface review: read both Markdown skill copies and checked the
all-spec scope, optional navigation ranges, module/symbol example, current
composed-section layout, and frozen-workflow handoff. No terminal, pager,
prompt widget, or Slack rendering behavior changed; no TTY exercise applies.

Full suite: `PYTHONPATH=/home/n/Code/claude/coga-design-cite-symbols/src
/home/n/Code/claude/coga/.venv/bin/python -m pytest` **passed: 2655 tests in
194.62 seconds**, exit 0. Confirmed Python 3.12.12 imports Coga from the
feature worktree. This environment has both `pip` and `hatchling`; the
implementation-stage wheel-test limitation is resolved. Output is in
`/tmp/coga-design-cite-symbols-pytest-20260917.log`.

`PYTHONPATH=/home/n/Code/codex/coga/src coga validate --task
ticket-specs-should-cite-symbols-not-line-numbers --json` passed: one valid
task, no issues. `git diff --check` and byte comparison of the skill pair
also passed.

Ready for handoff: `a9c6d6f7` is committed on `design-cite-symbols`, directly
on fetched `origin/main` (`9919d9c7`). No review findings or blockers remain.

## PR

Promote the citation guidance in `code/design` from the `## Context`
subsection to a standalone rule for code claims throughout the spec.
Require a file and symbol, allow line ranges only as navigation aids, and
add an acceptance check in both synchronized skill copies. Keep
`bootstrap/ticket` as the reference for detailed examples.

Test plan: `PYTHONPATH=/home/n/Code/claude/coga-design-cite-symbols/src /home/n/Code/claude/coga/.venv/bin/python -m pytest` — 2655 passed; `git diff --check` — passed.
