---
name: code/claude-review
description: Claude-side peer review of the implemented branch. Runs the `/code-review` slash command against the branch diff, applies must-fix findings in place, and commits before bumping.
---

# Claude peer review

Independent Claude pass over what `code/implement` committed. Designed
to run in a Claude-attended session — the `/code-review` slash command
is Claude Code native. If the active agent is not Claude, `relay panic`
and let the human switch the ticket's `agent:` to claude before re-launching.

This step is not the human review gate. It catches the high-confidence
bugs Claude can see in a fresh session, applies them, and leaves a clean
diff for the next reviewer.

## Order of operations

1. **Confirm state.** Read `branch:` and `worktree:` under `## Dev` on
   the blackboard. Change into the feature worktree and confirm it is on
   the recorded branch with a clean working tree. If not, `relay panic`.
2. **Run `/code-review`.** Invoke the `/code-review` slash command
   against the branch diff vs `main` at default effort. Read the
   findings carefully — the rubric is correctness bugs and reuse /
   simplification / efficiency cleanups.
3. **Apply must-fix findings.** Edit the working tree to fix
   high-confidence correctness issues. Skip nit-level findings — leave
   those for the human reviewer to decide. If a finding implies a
   design rethink, write it to the blackboard and `relay panic` rather
   than patching over it.
4. **Re-run tests.** `python -m pytest`. Run `relay validate --json`
   against the example fixture if validation behavior may have changed.
   If anything regressed, fix it before bumping.
5. **Commit.** One commit summarizing the review pass — e.g.
   `claude-review: apply /code-review findings`. Skip the commit if the
   review came back clean (note "no findings" on the blackboard instead).
6. **Bump from the primary checkout.** Return to the primary checkout
   and run `relay bump <slug>` to advance to `codex-review`.

## Acceptance for this step

- `/code-review` has run against the branch.
- Must-fix findings are applied, committed, and tested.
- Working tree is clean; tests pass.
- A short `## Claude Review` section on the blackboard notes what was
  changed (or "no findings" if the pass came back clean).

## What this skill does NOT do

- Run the Codex review — that's `code/codex-review`.
- Open or mark the PR ready — that's `code/open-pr`.
- Rework the original change beyond what `/code-review` surfaces.

## Gotchas

- "No findings" is a valid outcome. Note it on the blackboard and bump.
- Don't suppress test failures. Fix the edit, not the test.
- Don't run `/code-review ultra` here — that's the cloud-billed deep
  pass, reserved for high-stakes PRs and triggered manually by the
  human, not by a normal workflow step.
