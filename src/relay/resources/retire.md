Retire the done ticket `{slug}`.

Retire is the wrap-up gesture for a finished task: extract durable knowledge,
delete the source task directory, and prune the dead branch. This task is the
ad-hoc shell that drives that combo. Do not invent additional steps.

### Console Progress

Write short progress updates to the console before and after each phase:
retro PR open/merge check, branch pruning, final bump. Include the slug,
branch name, or PR link being acted on. The blackboard remains the durable
record; console progress is for the human watching the run.

### Ordered Pass

Run these in order. Stop and ask if any precondition fails — do not
improvise.

1. **Run `retro/done-ticket` against `{slug}`.** Read the skill at
   `relay-os/skills/retro/done-ticket/SKILL.md` and follow it. The skill
   stops and asks if the slug is ambiguous, the task is not `status: done`,
   or any required evidence file is missing. It opens a PR that records the
   `## Retro` marker, edits the knowledge base if warranted, and deletes
   `relay-os/tasks/{slug}/` in the same PR. Do not delete the directory
   outside the PR.

2. **Prune the source-task feature branch.** Read the source task's
   `## Dev` section in `blackboard.md` for the `pr:` link. If the linked
   PR is `MERGED` (check with `gh pr view <url> --json state,headRefName`),
   delete the local branch with `git branch -d <branch>`. Skip remote
   deletion: GitHub's auto-delete-on-merge setting is the right surface
   for that. If the PR is open, unmerged, or absent, skip pruning and note
   why on the blackboard — do not force-delete.

3. **Optional: prune other dead branches.** Walk `git branch --merged main`,
   exclude `main` and any branch matching the active worktree's
   `git worktree list` output, and delete each safely with `git branch -d`.
   Report the list on the blackboard. Skip if the user only wanted the one.

4. **Bump this retire task to done.** Run `relay bump <this-task-slug>`
   with a `--message` summarizing what happened: the retro PR link, the
   pruned branches, or "no-op" if everything was already cleaned up.

### Stop conditions

- Source task is not `status: done` → escalate via `relay panic` with the
  reason. Retire only operates on done tickets.
- Source task is missing → escalate; the slug is wrong.
- Retro skill stops and asks → surface the reason, do not proceed to
  branch pruning.
- Anything outside the allowed scope above → escalate, do not improvise.
