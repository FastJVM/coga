---
slug: bump-can-mark-done-too
title: bump can mark done too
status: done
owner: nick
human: nick
agent: claude
assignee: nick
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
---

## Description

`coga bump` on the final workflow step errors out today
(`src/coga/commands/bump.py:134-140`) and tells the caller to run
`coga mark done <slug>` instead. That split is a papercut: every agent
prompt has to teach "bump, except on the last step, where it's mark done",
and an agent that forgets stalls the workflow at exactly the moment the
work is finished.

Make `coga bump <slug>` on the final step finish the ticket instead of
bailing — same effect as `coga mark done <slug>`: status `done`, the
`mark done` log entry / Slack broadcast / digest detail, and the supervisor
done-marker. `bump` becomes the single "I finished this step" verb for the
whole workflow.

Scope is the final-step case only. `coga bump` on a **workflow-less**
ticket (`bump.py:108-112`) keeps its current error pointing at
`coga mark done` — bumping a ticket that has no steps is far more likely a
mistake than an intent.

## Context

**Decided behavior.** Bump-marks-done applies on *every* final step,
regardless of that step's assignee. The simplest rule wins: one verb, no
"except when" clause. See the tradeoff below — it has a real consequence
that needs handling in the same change.

**Tradeoff to handle, not ignore.** Four workflows end on a `review` step
with `assignee: owner` — a human PR gate — and each carries the same
paragraph telling an assisting agent it "must not merge the PR, delete the
branch, run `coga mark done`, or otherwise advance/close the task unless
the human explicitly says to." Once `bump` finishes on the final step,
`bump` is another way through that gate, so the guidance has to name it.
Update that paragraph in all four (see the doc list below). The gate stays
a prompt-level norm rather than a code guard — that is the deliberate
consequence of picking the simple rule, and it means the enforcement drops
from free (bump errored) to advisory.

The same tension reaches the base prompt: `src/coga/resources/prompt.md`
lines 17-23 tell every agent to "run `bump` as the *last* thing in the
current step." An agent launched onto an owner `review` step will then have
a working close verb and a top-level instruction pointing at it. `prompt.md`
needs its own "except an owner-gate step" sentence, not just the workflow
files.

**Implementation notes — the sharp edges:**

- **Bypass `advance_step` entirely and call `coga.mark.mark_done`** (the
  library function in `src/coga/mark.py`, not the Typer command in
  `src/coga/commands/mark.py`). `mark_done` pops `step:`
  (`coga/mark.py:135`) and runs `read_snapshot` / `_sync_done_state` /
  `_warn_if_state_not_advanced`, none of which `advance_step` does. Calling
  the Typer command instead double-emits the done marker, since
  `commands/mark.py:198` and `commands/bump.py:254` both call
  `emit_done_marker`.
- **Notification semantics differ.** A normal bump broadcasts to Slack
  *only* when `--message` was passed (`bump.py:209` →
  `advance_step(notify_slack=message is not None)`); step moves are
  otherwise silent. `mark_done` always notifies
  (`coga/mark.py:141-155`). The finish path must always broadcast like
  `mark done` — `--message` only appends the suffix. Do not carry
  `notify_slack=message is not None` into the finish branch.
- **`--force` has no equivalent on bump.** `mark_done` raises
  `StrandedProductCode` unless `force=True` (`coga/mark.py:131-132`), and
  `coga mark done` exposes `--force` (`commands/mark.py:142-148`). A
  final-step bump on a checkout with stranded product code will fail with a
  remedy naming a flag `coga bump` doesn't have. Either add `--force` to
  `bump` or make the message point at `coga mark done --force`. Pick one
  deliberately.
- **The `requires:` gate must still fire** before finishing
  (`bump.py:142-158`): a final step declaring `requires:` is not
  bump-completable until its artifact is on the blackboard. Note that the
  same gate computes `publish_current_branch` (`bump.py:158`), which
  `advance_step` forwards to `git.sync_task_state` but `mark_done` has no
  parameter for — it calls `_sync_done_state`. Decide how that flag reaches
  the sync, or declare the requires-on-final-step republish explicitly out
  of scope.
- **The supervised hint needs a third branch.** Both branches at
  `bump.py:231-242` assume a next step and a `next_assignee`; on the finish
  path neither exists.
- `--to` / `--backward` rewind is unaffected. The not-`in_progress` guard
  (`bump.py:84`) stays.

**Docs and prompts that assert the old rule** — all of these need updating
in the same PR, since they are the contract this change breaks:

- `src/coga/commands/bump.py` — the `bump()` docstring ("Bumping past the
  last step is an error") and the `--help` text.
- `src/coga/commands/mark.py:8-9` — module docstring, "`coga bump` no
  longer marks final-step tickets done." Becomes flatly false.
- `src/coga/resources/prompt.md:22-23` and `:80-82` — "On the *final* step,
  run `coga mark done <id>` instead" and "**Final step, or no workflow:**
  run `coga mark done <id>`". The no-workflow half stays true; the
  final-step half does not.
- `docs/reference.md:196-197` — user-facing CLI reference, carries the old
  rule verbatim.
- `docs/getting-started.md:165-167` — the `code/with-review` walkthrough,
  "Close the ticket with `coga mark done <task>` once it's merged."
- `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md`
  — `:413-416` (the final-step error and the no-workflow rule) and `:973`
  ("Finishing a task (final step, or no workflow) → `coga mark done`").
  No live `coga/contexts/coga/cli/` copy exists; the packaged file is the
  only one.
- `coga/contexts/coga/current-direction/SKILL.md:247-248` — "`bump` does
  not finish tickets — bumping past the last step (or on a no-workflow
  ticket) errors and points at `coga mark done`." This is the live context
  that directly contradicts the new behavior. (`coga/architecture` and
  `coga/principles` were checked and are clean on this rule.)
- `coga/contexts/coga/period-task/SKILL.md:46` — "(or `coga bump` to the
  next non-final step)"; the qualifier becomes unnecessary. Minor.
- The owner-gate paragraph in **four** packaged workflows, all under
  `src/coga/resources/templates/coga/bootstrap/workflows/`:
  `code/with-review.md`, `code/with-self-review.md`,
  `code/design-then-implement.md:56-60`, and `docs/with-review.md:154-158`.
  There is no repo-local `coga/workflows/code/` copy.
- `src/coga/autoclose.py:213-217` — the `_on_final_step` comment "No
  workflow → bump = done. Treat as 'final step'." reads backwards
  post-change. Cosmetic.

Per `CLAUDE.md`, check both the live copy under `coga/` and the packaged
copy under `src/coga/resources/templates/coga/` for anything you touch.

**Tests.**

- `tests/test_commands.py:386-398`
  (`test_bump_past_final_step_errors_with_mark_done_hint`) asserts the
  error string, the `coga mark done` hint, and `status == "in_progress"`.
  Invert it to assert the ticket lands `done`.
- `tests/test_launch_restart.py` — the `_FakeAgent` docstring (~line 102)
  and the `_FAKE_AGENT` script (~265-267,
  `if coga("bump", slug) != 0: coga("mark","done",slug)`). Post-change the
  `mark done` fallback is dead code and this end-to-end test silently stops
  exercising `mark done`. Decide this deliberately.
- `tests/test_smoke.py` — docstring line 6 plus the actual `mark done` call
  (~99-100). Decide whether the smoke path now finishes via bump.
- `tests/test_compose.py:342` asserts `"coga mark done" in prompt`. Should
  stay green via `prompt.md` lines 66/80 — confirm rather than assume.
- New coverage: bump-on-final-step sets `status: done` and writes the same
  log/notification shape as `mark done`; a final step with `requires:`
  still refuses until the artifact is recorded; the workflow-less bump
  still errors. `tests/test_mark.py` and
  `tests/test_done_marker_emission.py` are the neighbouring suites.

**Autoclose overlap.** `src/coga/autoclose.py` calls `mark_done` directly on
final-step tickets whose PR merged — the other automated done path. No
change expected (`_candidate` re-reads before marking), but confirm a
manual finishing bump and a concurrent sweep can't produce two `done` log
lines.

**Note for the implementer:** this ticket's own workflow ends on a
`code/with-review` `review` step, and the PR under review is the one adding
"don't `coga bump` on the review step." Follow the rule as of the merged
tree, not the diff.

**Out of scope:** changing what `coga mark done` does, the workflow-less
bump error, and any code-level restriction on agents finishing an
owner-assigned final step.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
pr: https://github.com/FastJVM/coga/pull/675
branch: codex/final-bump-done
worktree: /tmp/coga-final-bump-done

## Implement

- Final-step forward bumps will bypass `advance_step` and call the shared
  `mark_done` library path, preserving the existing `requires:` gate and
  emitting the supervisor done marker once from the bump command.
- Add `--force` to `coga bump`; this keeps stranded-product-code remediation
  available without making the final-step caller switch back to a second verb.
- Owner-assigned final review gates remain advisory by design. The base prompt
  and all four packaged review workflows will explicitly prohibit both
  `coga bump` and `coga mark done` without human approval.
- Regression tests first reproduced the final-step error. The implementation
  now routes terminal forward bumps through `mark_done`, always uses the done
  notification/digest path, exposes `bump --force`, and threads a final
  `requires:` gate's branch-publication flag into the done-state sync.
- Added an autoclose race test where a manual final bump lands during the PR
  lookup; the sweep's existing second read observes `done`, so only one
  terminal log entry is written.

## Verification

- `python -m pytest`: 1573 passed, 1 skipped.
- `coga validate --json --task bump-can-mark-done-too`: 1 ok, no issues.
- Seeded `example/` `coga validate --json`: 2 ok, no issues.
- `python -m coga.cli bump --help`: terminal completion and `--force` are
  present in the rendered CLI help.
- `git diff --check`: clean; stale old-rule wording search returned no matches.

## Handoff

- Implementation commit: `bebcbe87ab658e22ffe39b8087b874e014a7df74` (`Let bump finish final
  workflow steps`).
- Peer-review commit: `58f08de65209fbdd826b6e4a124da45d70995c4a`
  (`peer-review: fix terminal bump workflow template`).
- `git fetch origin main && git rebase FETCH_HEAD`: branch is current (0
  behind, 2 ahead); both commits were rebased cleanly.
- Feature checkout is clean. No push or PR has been performed.

## Peer review

- `codex review --base main` completed against the recorded feature branch.
  Core terminal-state, notification, sync, supervisor, and race-regression
  paths passed review; the full suite reported 1573 passed, 1 skipped.
- One P2 contract miss was found: the live and packaged starter workflow
  templates still said `coga bump` stops at the final step. Both copies now
  teach the terminal bump behavior and are byte-identical.
- Post-fix template/packaging tests passed (117 passed, 1 skipped). After the
  required fresh rebase, the full suite passed again (1573 passed, 1 skipped),
  scoped and seeded-example validation were clean, CLI help was correct, and
  stale old-rule wording was absent.

## PR

Make `coga bump` the single workflow-step completion verb: a forward bump on
the final step now delegates to the shared `mark_done` finalizer, preserving
done-state audit, notification, digest, sync, and supervisor behavior. Preserve
the workflow-less error, completion gates, feature-branch publication, and the
stranded-product-code guard with a matching `bump --force` escape hatch.

Update the base prompt, CLI/user docs, live and packaged contexts, starter
templates, and all four owner-controlled review workflows to match the new
contract while keeping owner gates advisory. Add regression coverage for final
completion, notification shape, required artifacts, branch publication,
stranded code, supervisor chaining, and autoclose overlap.

Test plan: `python -m pytest` (1573 passed, 1 skipped); scoped task validation
and seeded `example/` validation both report no issues.
