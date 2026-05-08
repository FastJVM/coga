---
name: bootstrap/dream/tasks/cleanup-orphan-markers
description: Open delete-only PRs for done tickets whose blackboard carries the processed Retro marker but whose task directory was not deleted by the Retro PR.
script: run.py
---

# Cleanup Orphan Markers

Recovery path for done tickets whose Retro PR recorded the processed marker
but did not delete the source task directory in the same PR. New Retro PRs
delete the source task directory in the same PR (see
`relay-os/skills/retro/done-ticket/SKILL.md`), so this worker should usually
find nothing.

The detection rules are deterministic — no LLM judgment, no fuzzy matching:

- exact `status: done` in ticket frontmatter;
- a `## Retro` block in the blackboard containing both
  `skill: retro/done-ticket` and `status: processed`;
- exact slug match (no prefix matching);
- no open PR already touching `relay-os/tasks/<slug>/`.

When all gates pass and `--open-prs` is set, the worker opens a delete-only PR
against `--base-branch` (default `main`). Without `--open-prs`, it reports
candidates only. The deletion happens in the PR (not the running working tree
directly) so the human can review or edit the PR before merge. Inside the PR
worktree, deletion uses `relay delete --exact <slug>`.

## Known Skill Contract

- Purpose: complete cleanup for done tickets with the processed Retro marker
  whose source task directory still exists.
- Runs: launcher-owned; `relay dream` creates a child `mode: script` task for
  this skill and launches it. The script entry point is
  `python relay-os/skills/bootstrap/dream/tasks/cleanup-orphan-markers/run.py`
  and script mode provides the task blackboard through `RELAY_TASK_BLACKBOARD`.
- Inputs: `relay-os/tasks/*/ticket.md`, `relay-os/tasks/*/blackboard.md`, and
  open PR file lists from `gh pr list`.
- May change: nothing in the running repo; cleanup PRs run
  `relay delete --exact <slug>` to delete only the matched
  `relay-os/tasks/<slug>/` directory on a fresh worktree off
  `origin/<base-branch>`.
- Action: `pr-required`
- Idempotency: skips any candidate whose task dir is already touched by an
  open PR; safe to re-run.
- Stop and ask: `gh` is unavailable or unauthenticated, the candidate's task
  dir is missing on the base branch, the worktree cannot be created, or any
  git/gh subcommand fails.
- Output: append `## Dream Worker: cleanup-orphan-markers` to the Dream run
  blackboard and optionally post a one-line Slack summary.

## How to Run

From the host repo root:

```
python relay-os/skills/bootstrap/dream/tasks/cleanup-orphan-markers/run.py --open-prs --blackboard relay-os/tasks/<dream-run-task>/blackboard.md --slack-task <dream-run-task>
```

Replace `<dream-run-task>` with the current Dream run task slug.

Without `--open-prs`, the worker reports candidates to the blackboard and
exits — useful for dry-runs or for a Dream pass that wants the human to
approve before opening cleanup PRs.

## Output

The skill appends a concise section to the Dream run blackboard:

```
## Dream Worker: cleanup-orphan-markers
```

The section includes the generation time, mode (`open-prs` or `report-only`),
counts by action (`pr-opened`, `skipped-open-pr`, `candidate-only`,
`human-needed`), and one line per candidate with the action and (when opened)
the PR URL.

## Safety

- Always opens cleanup PRs from a fresh worktree off `origin/<base-branch>`;
  the running repo's working tree is never touched.
- Refuses to delete anything outside the matched `relay-os/tasks/<slug>/`
  directory.
- Skips any slug whose dir is already touched by an open PR (no double-cleanup).
- Cleans up the worktree on success or failure.
