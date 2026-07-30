---
slug: bump-can-mark-done-too
title: bump can mark done too
status: draft
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- dev/code
skills: []
workflow: code/with-review
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

## Evaluator review

I read the ticket cold, then verified every claim against the source. Findings below.

---

## Can an agent start cold?

Yes. The Description states the current behavior, the desired behavior, and the boundary (final step only, workflow-less bump unchanged) in three short paragraphs. The `## Context` gives a decided policy rather than options, and names concrete files. This is above average for startability — the problems are in accuracy and completeness, not clarity.

## Line-reference audit

Verified accurate: `bump.py:134-140` (final-step error; the `_bail` itself is 136-140), `bump.py:108-112`, `bump.py:142-158`, `bump.py:222-243`, `bump.py:84`, `mark.py:134` (`@app.command("done")`; `def done` at 135), `_DONE_FROM` at `mark.py:47`, `prompt.md:22-23`, `prompt.md:80-82`, `cli/SKILL.md:413-416`, `cli/SKILL.md:973`, `tests/test_smoke.py:6`. Two structural claims also check out: there is no repo-local `coga/workflows/code/` (live `coga/workflows/` holds only `autoclose-merged`, `blocker-reminders`, `branch-sweep`, `build`, `direct`, `skill-update` plus three loose files), and there is no live `coga/contexts/coga/cli/`.

Two references are off:

- **`tests/test_commands.py:389-394` is wrong in a way that hides work.** The test is `test_bump_past_final_step_errors_with_mark_done_hint`, lines 386-398. The range given stops at 394, which cuts off the two assertions that most need inverting: `assert f"coga mark done {slug}" in result.output` (395) and `assert t.status == "in_progress"` (398). Use `386-398`.
- **The "grep architecture and principles" hint points at the wrong files.** Neither `coga/contexts/coga/architecture/SKILL.md` nor `principles/SKILL.md` asserts the final-step rule. The live context that *does* is `coga/contexts/coga/current-direction/SKILL.md:247-248`: "`bump` does not finish tickets — bumping past the last step (or on a no-workflow ticket) errors and points at `coga mark done`." The ticket sends the agent to grep two clean files and never names the dirty one.

## What the ticket misses

The doc list is framed as exhaustive ("these need updating in the same PR, since they are the contract this change breaks"). It is not. Additional hits:

1. **`docs/reference.md:196-197`** — "Advance one workflow step. Bumping past the last step is an error — use `coga mark done` to finish." This is the user-facing CLI reference and it is verbatim the old rule. Unlisted.
2. **`src/coga/commands/mark.py:8-9`** — module docstring: "`coga bump` no longer marks final-step tickets done." Becomes flatly false, and it sits in a file the ticket already tells you to open.
3. **`coga/contexts/coga/current-direction/SKILL.md:247-248`** — see above. Live context, composed into any ticket that attaches it.
4. **The owner-gate paragraph exists in four workflows, not two.** The ticket says "both workflow files." The identical "must not merge the PR, delete the branch, run `coga mark done`" paragraph also appears in `src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md:56-60` (final step `review`, `assignee: owner` — identical exposure) and `src/coga/resources/templates/coga/bootstrap/workflows/docs/with-review.md:154-158` (same). Fixing only two of four leaves half the human PR gates undocumented against the new verb.
5. **`tests/test_launch_restart.py`** — the `_FakeAgent` docstring (~line 102, "`coga bump` for every step but the last, `coga mark done` on the last") and the `_FAKE_AGENT` script (~265-267): `if coga("bump", slug) != 0: coga("mark","done",slug)`. After the change, bump on the last step returns 0, so the `mark done` fallback becomes dead code and this end-to-end test silently stops exercising `mark done` at all. The assertions probably still pass — decide this deliberately rather than discovering it.
6. **`tests/test_smoke.py`** — the ticket cites the docstring at line 6 but not lines 99-100 and the actual `mark done` call in the smoke path. If the smoke test is meant to be representative of the loop, decide whether it now finishes via bump.
7. **`docs/getting-started.md:165-167`** — "You'll land at the final `review` step ... Close the ticket with `coga mark done <task>` once it's merged." Still technically true, but it's the narrative walkthrough of `code/with-review`, i.e. exactly the gate the change makes newly reachable by bump.
8. **`src/coga/autoclose.py:213-217`** — `_on_final_step` comment "No workflow → bump = done. Treat as 'final step'." Post-change this reads backwards (no-workflow is now the one case where bump is *not* done). Cosmetic, but it's the other automated done path.
9. **`tests/test_compose.py:342`** asserts `"coga mark done" in prompt`. Removing the `prompt.md:23` sentence leaves lines 66 and 80 to keep it green, so it won't break — but confirm rather than assume.
10. **`coga/contexts/coga/period-task/SKILL.md:46`** — "(or `coga bump` to the next non-final step)"; the qualifier becomes unnecessary. Minor.

## Behavior gaps the "reuse the `mark done` path" instruction papers over

These are the parts most likely to produce a wrong implementation:

- **`coga bump` has no `--force`.** `mark done` does (`mark.py:142-148`), because `coga.mark.mark_done` raises `StrandedProductCode` unless `force=True` (`coga/mark.py:131-132`). Route bump through `mark_done` and a final-step bump on a checkout with stranded product code fails with an error whose remedy — "re-run with --force" — names a flag `coga bump` doesn't have. Either add `--force` to bump or make the message point at `coga mark done --force`. The ticket asks for identical behavior and never resolves this.
- **The `--message` bullet describes the wrong mechanism.** "`--message` should ride the done broadcast the way it rides a normal bump broadcast" is misleading: a normal bump broadcasts *only because* `--message` was passed (`bump.py:209` → `advance_step(notify_slack=message is not None)`; `coga/bump.py:87,118` — step moves are otherwise silent in Slack). `mark_done` always notifies (`coga/mark.py:141-155`). An agent following the bullet literally could wire `notify_slack=message is not None` into the finish path and suppress the 🎉 done broadcast. Restate as: the finish always broadcasts like `mark done`; `--message` only appends the suffix.
- **`publish_current_branch` has nowhere to go.** The ticket explicitly requires the `requires:` gate still fire on a final step. That gate also computes `publish_current_branch` (`bump.py:158`), which `advance_step` forwards to `git.sync_task_state`. `mark_done` has no such parameter — it calls `_sync_done_state`. So a workflow whose *final* step declares `requires:` would silently lose the single-checkout PR-branch republish. Either declare that case out of scope or say how the flag reaches the sync.
- **"Reuse the `mark done` path" is ambiguous between the Typer command and the library function.** `mark.py:198` already calls `emit_done_marker`, and `bump.py:254` calls it unconditionally too — reusing the command double-emits. Also, `mark_done` pops `step:` (`coga/mark.py:135`) and runs `read_snapshot` / `_sync_done_state` / `_warn_if_state_not_advanced`, none of which `advance_step` does. The final-step branch must bypass `advance_step` entirely and call `coga.mark.mark_done`. Worth stating outright.
- On the supervised hint: it isn't merely imprecise on the finish path, it's structurally wrong — there is no next step and no `next_assignee`. Both branches at `bump.py:231-242` are inapplicable; a third branch is needed.

## Workflow fit

`code/with-review` is the right choice: real Python change, real test churn, a PR is wanted, and peer review is worth having on a change that loosens a gate. One thing to flag for whoever picks it up — this ticket's own final step is `review` on `code/with-review`, and the PR under review is the one that adds "don't `coga bump` on the review step." The reviewer will be enforcing a rule that isn't merged yet, and the implementing agent will be bumping into a review step whose semantics its own diff changes.

## Contexts

`dev/code` is correct and appropriately narrow — its closing section explicitly scopes itself to the ticket→branch→PR link, so there's no buried fact that should have been copied into `## Context`. No trim needed there.

Missing, in priority order:

- **`coga/architecture`** owns three things this change touches: the `step:` field contract, the `requires:` gate, and the supervisor terminal-signal contract. At 40 KB it's too big to attach casually — but then the specific constraints should be quoted into `## Context` rather than left to a grep.
- **`coga/codebase`** — CLAUDE.md makes it required reading for `src/coga/` changes (microkernel rule, test expectations). 20 KB.
- **`coga/current-direction`** at minimum needs naming, since it carries the sentence that directly contradicts the new behavior.

## Prompt budget

Nothing crosses 40%. `dev/code` at 7.3 KiB is 33% and earns it. `## Context` at 4.0 KiB / 18% is 4.4× the Description, which is unusual but defensible for a ticket that is mostly a touchpoint inventory. The one soft spot: the "grep `architecture` and `principles`" paragraph is filler that points at clean files — replace it with the concrete hits listed above and the layer gets both shorter and more useful.

## Scope

One ticket, but larger than it looks. The code change is ~15 lines in `bump.py`. Everything else is contract sync, which CLAUDE.md makes non-optional and which can't be usefully split. With the missed touchpoints folded in, the doc surface is roughly: 4 workflow files, 2 files under `docs/`, 2 live contexts, 1 packaged context, 1 module docstring, plus 4-5 test files. Still one ticket — but the `implement` step should not be surprised by the second half.

## Assumptions to question before launch

1. **The central tension is unresolved.** The ticket's stated motivation is deleting an "except" clause from agent prompts. But `prompt.md:17-23` tells every agent "run `bump` as the *last* thing in the current step" — so once bump closes tickets, an agent launched onto an owner `review` step has a working close verb and a top-level instruction pushing it toward exactly what the workflow file forbids. Keeping the gate then requires adding an "except an owner-gate step" sentence to `prompt.md` *and* to four workflow files. Net: one "except" removed from the CLI, several added to prose, and the enforcement drops from free (bump errored) to advisory. The alternative the ticket dismisses in a single line — finish only when the final step's assignee isn't `owner` — is one condition, not a complex carve-out. Worth a deliberate second look, because the failure mode is an agent silently closing a human PR gate.
2. **"The supervisor already treats `mark done` as terminal"** is true but not the risk. `bump.py:254` already emits the marker unconditionally; the hazard is a *double* emit if the finish path reuses the `mark done` Typer command, not a missing one.
3. **Autoclose overlap.** `autoclose.py` calls `mark_done` directly on final-step tickets whose PR merged. No change is required, but confirm a manual finishing bump and a concurrent sweep can't produce two `done` log lines — `_candidate` re-reads before marking, so it's probably fine, but the ticket never mentions autoclose at all despite it being the other automated done path.
