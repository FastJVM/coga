---
name: code/codex-review
description: Codex-side peer review of the implemented branch. Runs `codex review --base main` non-interactively, applies must-fix findings in place, and commits before bumping.
---

# Codex peer review

Independent pass with the other agent's eyes. Codex CLI ships a
first-class `codex review` subcommand that produces a non-interactive
review report against the branch diff. Designed to run in a Codex-attended
session so the agent reading and applying the findings is the same one
that produced them — for the cleanest cross-check, the human switches
the ticket's `agent:` to `codex` (or uses `relay launch <slug> --agent
codex`) before this step.

If `codex` is not on the PATH, `relay panic` with a hint to install it.

## Order of operations

1. **Confirm state.** Read `branch:` and `worktree:` under `## Dev` on
   the blackboard. Change into the feature worktree and confirm it is on
   the recorded branch with a clean working tree. If not, `relay panic`.
2. **Run the review.** From the feature worktree, run
   `codex review --base main`. For a focused pass, append a short prompt
   (e.g. `codex review --base main "focus on the retry path"`). The
   command is non-interactive and prints the findings to stdout.
3. **Apply must-fix findings.** Edit the working tree to fix
   high-confidence correctness issues. Skip nit-level findings — leave
   those for the human reviewer to decide. If a finding implies a
   design rethink, write it to the blackboard and `relay panic` rather
   than patching over it.
4. **Re-run tests.** `python -m pytest`. Run `relay validate --json`
   against the example fixture if validation behavior may have changed.
   If anything regressed, fix it before bumping.
5. **Commit.** One commit summarizing the review pass — e.g.
   `codex-review: apply codex review findings`. Skip the commit if the
   review came back clean (note "no findings" on the blackboard instead).
6. **Bump from the primary checkout.** Return to the primary checkout
   and run `relay bump <slug>` to advance to `open-pr`.

## Acceptance for this step

- `codex review --base main` has run against the branch.
- Must-fix findings are applied, committed, and tested.
- Working tree is clean; tests pass.
- A short `## Codex Review` section on the blackboard notes what was
  changed (or "no findings" if the pass came back clean).

## What this skill does NOT do

- Run the Claude review — that's `code/claude-review`.
- Open or mark the PR ready — that's `code/open-pr`.
- Rework the original change beyond what `codex review` surfaces.

## Gotchas

- "No findings" is a valid outcome. Note it on the blackboard and bump.
- If `/code-review` (the previous step) and `codex review` disagree on
  a specific edit, leave the code in the safer state and note the
  disagreement on the blackboard — the human reviewer is one step away.
- Don't suppress test failures. Fix the edit, not the test.
