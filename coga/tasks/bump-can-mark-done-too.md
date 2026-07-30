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

**Tradeoff to handle, not ignore.** In `code/with-review` and
`code/with-self-review` the final step is `review`, `assignee: owner` — a
human PR gate. Both workflow docs currently tell an assisting agent it
"must not merge the PR, delete the branch, run `coga mark done`, or
otherwise advance/close the task unless the human explicitly says to."
Once `bump` finishes on the final step, `bump` is another way through that
gate, so the guidance has to name it. Update that paragraph in both
workflow files to forbid `coga bump` alongside `coga mark done` on the
`review` step. The gate stays a prompt-level norm rather than a code
guard — that's the deliberate consequence of picking the simple rule.

**Behavior details to get right:**

- The `requires:` completion gate (`bump.py:142-158`) must still run before
  finishing. A final step that declares `requires:` should not be
  bump-completable until its artifact is on the blackboard.
- Reuse the `mark done` path rather than reimplementing it, so the log
  line, Slack text, digest detail, GIF (`cfg.gif_for("done")`), and
  assignee/status writes stay identical to `coga mark done`. See
  `src/coga/commands/mark.py:134` and `_DONE_FROM`.
- `--message` should ride the done broadcast the way it rides a normal
  bump broadcast.
- `--to` / `--backward` rewind is unaffected.
- `emit_done_marker` still fires so a supervised `coga launch` tears the
  session down. The supervisor already treats `mark done` as terminal;
  confirm the "will chain / will stop" hint printed under `COGA_SUPERVISED`
  (`bump.py:222-243`) reads correctly for the finish case rather than
  claiming a next step.
- Bumping a ticket that is not `in_progress` keeps its existing guard
  (`bump.py:84`).

**Docs and prompts that assert the old rule** — these need updating in the
same PR, since they are the contract this change breaks:

- `src/coga/commands/bump.py` — the `bump()` docstring ("Bumping past the
  last step is an error") and the `--help` text.
- `src/coga/resources/prompt.md` — the composed base prompt, lines ~23 and
  ~80 ("On the *final* step, run `coga mark done <id>` instead" and
  "**Final step, or no workflow:** run `coga mark done <id>`"). The
  no-workflow half of that sentence stays true; the final-step half does
  not.
- `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md`
  — lines ~414-416 describe the final-step error and the "no workflow, no
  steps" rule; ~973 lists "Finishing a task (final step, or no workflow) →
  `coga mark done <slug>`".
- `src/coga/resources/templates/coga/bootstrap/workflows/code/with-review.md`
  and `.../code/with-self-review.md` — the `## review` owner-gate paragraph
  described above. There is no repo-local `coga/workflows/code/` copy, so
  the packaged file is the only one.
- `tests/test_smoke.py:6` — "`coga bump` advances; `coga mark done`
  finishes the final step."

Per `CLAUDE.md`, check both the live copy under `coga/` and the packaged
copy under `src/coga/resources/templates/coga/` for anything you touch.
The `coga/cli` context has no live copy; `coga/architecture` and
`coga/principles` do — grep them for the final-step rule before assuming
they're clean.

**Tests.** `tests/test_commands.py:389-394` currently asserts the
final-step error string and must be inverted to assert the ticket lands
`done`. Add coverage for: bump-on-final-step sets `status: done` and
writes the same log/notification shape as `mark done`; a final step with
`requires:` still refuses until the artifact is recorded; and the
workflow-less bump still errors. `tests/test_mark.py` and
`tests/test_done_marker_emission.py` are the neighbouring suites.

**Out of scope:** changing what `coga mark done` does, the workflow-less
bump error, and any code-level restriction on agents finishing an
owner-assigned final step.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
