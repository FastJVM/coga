---
name: retro/done-ticket
description: Extract durable knowledge from one done ticket into Relay contexts or skills and open a reviewable PR only when new knowledge exists.
---

# Retro Done Ticket

Retro is a prompt-only Codex skill and the knowledge-extraction gate for
done-ticket cleanup. Dream may call it for eligible completed tasks, but Retro
is not Dream, not a Python worker, and not a cleanup command. Its job is to
read one completed ticket, compare it against the repo's context and skill
corpus, and decide whether the task contains durable knowledge worth adding to
Relay. When it does, Retro opens a reviewable PR that records the source-task
`## Retro` marker, updates the knowledge base, and deletes the source task
directory in that same PR. When it does not, Retro records a no-op marker on
the source blackboard and stops without opening a marker-only PR.

## Known Skill Contract

- Purpose: extract durable knowledge from one done ticket, mark that Retro has
  processed it, and avoid marker-only cleanup PRs when no new knowledge exists.
- Runs: `retro/done-ticket <task-slug>` after Dream or a human chooses one
  exact done ticket.
- Inputs: the source task's `ticket.md`, `blackboard.md`, and `log.md`, plus
  every context and skill file under `relay-os/contexts/` and
  `relay-os/skills/`.
- May change: warranted context files, warranted skill files, the exact source
  task directory `relay-os/tasks/<slug>/` when a knowledge PR is opened, or
  only `relay-os/tasks/<slug>/blackboard.md` when no new durable knowledge is
  found.
- Action: `pr-required` for knowledge edits; `direct-fix` for a
  no-new-durable-knowledge marker only.
- Idempotency: the source task is gone, the source task blackboard contains a
  `## Retro` section with `skill: retro/done-ticket` and `status: processed`,
  or an open PR is adding that marker or deleting the source task directory.
- Stop and ask: the slug is ambiguous, the task is not `status: done`, any
  required evidence file is missing, or the diff would touch anything outside
  the allowed files or the exact source task directory.
- Output: a PR with knowledge edits and source task deletion, or a direct
  `no-new-durable-knowledge` marker with no PR and no source deletion.

## Scope

Do:

- read the done ticket directory named by the slug passed to this skill;
- read every context file under `relay-os/contexts/**/SKILL.md`;
- read every skill file under `relay-os/skills/**/SKILL.md`;
- decide whether the ticket contains new, useful durable knowledge;
- update, create, split, merge, or delete context blocks when warranted;
- update or create a skill only when the ticket contains repeatable process
  knowledge that is not already covered;
- append or update exactly one `## Retro` marker in the source task's
  `blackboard.md`;
- when new durable knowledge exists, delete the source ticket directory in the
  same PR after recording the marker;
- when new durable knowledge exists, open a PR containing the knowledge-base
  changes and source task deletion;
- when no new durable knowledge exists, record the marker directly and leave
  the source task directory in place;
- post a one-line Slack FYI with the PR title and link when Slack is
  available. The title should carry the new finding.

Do not:

- delete any task directory except the exact source ticket directory;
- delete local or remote git branches;
- open a marker-only or delete-only PR when no new durable knowledge exists;
- delete the source task directory when no new durable knowledge exists;
- mutate ticket frontmatter, `log.md`, or `task.lock` before deleting the
  source task directory;
- preserve one-off execution noise as context.

Knowledge type decides the target: domain facts, repo conventions, constraints,
and known failure modes belong in contexts; repeatable instructions for how an
agent should do work belong in skills. If the process knowledge is already
covered by an existing skill, do not duplicate it.

## Comparison baseline

The baseline you compare ticket evidence against is the **current working-tree
state** of `relay-os/contexts/**` and `relay-os/skills/**`. The final state of
those files is the entire learning record. Durable knowledge that was already
captured by the source task's PR lives in those files now — not in commit
messages, not in PR descriptions, not in diffs.

Do not:

- run `git log`, `git show`, `git diff`, or `git blame` to decide what is
  already covered;
- read prior PR descriptions or commit messages for the source task;
- inspect old revisions of context or skill files.

If a fact is present in the current file on disk, it is covered. If it is not,
it is not. That is the only test.

## Inputs

This skill is invoked with one parameter: the done ticket slug. Work from the
repo root.

Required files:

- `relay-os/tasks/<slug>/ticket.md`
- `relay-os/tasks/<slug>/blackboard.md`
- `relay-os/tasks/<slug>/log.md`
- `relay-os/contexts/**/SKILL.md`
- `relay-os/skills/**/SKILL.md`

Stop and ask if the task slug is ambiguous, the task is not `status: done`, any
required task evidence file is missing, or there is already an open PR adding a
`## Retro` marker for the same source task.

## Workflow

1. **Inventory contexts.**
   Read all `relay-os/contexts/**/SKILL.md`. For each context, note its path,
   `name`, `description`, headings, and the knowledge it already covers. This
   inventory is the baseline for deciding whether ticket knowledge is new.

2. **Inventory skills.**
   Read all `relay-os/skills/**/SKILL.md`. For each skill, note its path,
   `name`, `description`, headings, and the process it already covers. This
   inventory is the baseline for deciding whether ticket knowledge belongs in a
   skill and whether the process is already covered.

3. **Read the ticket evidence.**
   Read `ticket.md`, `blackboard.md`, and `log.md`. Extract candidate durable
   knowledge: domain facts, repo conventions, sharp gotchas, durable decisions,
   corrected assumptions, known failure modes, and boundaries future agents
   should inherit. Read the ticket files themselves — do not consult git
   history, prior PRs, or old revisions for any of this.

4. **Classify each candidate.**
   Use this table:

   | Classification | Action |
   | --- | --- |
   | Already covered | Drop; mention only in notes if important. |
   | New detail for an existing context | Patch the smallest fitting context block. |
   | New coherent topic | Create a focused context under `relay-os/contexts/<namespace>/<name>/SKILL.md`. |
   | Duplicate or stale existing context | Merge, rewrite, or delete the obsolete block/file. |
   | Repeatable process knowledge | Update an existing skill, or create a focused skill if none fits. |
   | One-off execution detail | Drop. |

   "New and useful" means a future launched agent would make a better decision
   because this knowledge is present. Do not preserve facts that are already
   obvious from the code, only mattered during the finished task, or are merely
   lifecycle bookkeeping.

5. **Edit knowledge blocks.**
   Keep edits readable and reviewable. Prefer a small targeted patch to a broad
   rewrite. Create a new context only when no existing context can carry the
   knowledge cleanly. Create a new skill only when the ticket contains
   repeatable process instructions and no existing skill can carry them cleanly.
   Delete a context or skill block only when it is obsolete, duplicated, or
   replaced by the new edit.

6. **Record the Retro marker.**
   Append or update exactly one `## Retro` section in
   `relay-os/tasks/<slug>/blackboard.md`:

   ```markdown
   ## Retro

   status: processed
   skill: retro/done-ticket
   result: <knowledge-pr | no-new-durable-knowledge>
   title: <PR title or no-op title>
   ```

   If no durable knowledge is found, write the marker with
   `result: no-new-durable-knowledge`, use a title such as
   `No new durable knowledge for <slug>`, leave `relay-os/tasks/<slug>/` in
   place, and do not open a PR. Return a one-line no-op result to the caller.

7. **Delete the source task only for knowledge PRs.**
   If new durable knowledge was added to a context or skill, delete
   `relay-os/tasks/<slug>/` in the same PR after recording the marker. The
   marker is preserved in PR history, and after merge git history is the audit
   trail for the deleted task.

8. **Self-review the diff.**
   Confirm the PR changes only context files, warranted skill files, and the
   exact source task directory unless the human explicitly asked for something
   else. For no-new-durable-knowledge results, confirm the only source-task
   edit is the `blackboard.md` marker and that no PR will be opened.

9. **Open the PR only when knowledge changed.**
   Work in the current checkout — do not create a `git worktree`. Branch
   directly off `origin/main` with `git checkout -b
   codex/retro-<ticket-slug>-knowledge origin/main`, make the edits and the
   source-task deletion there, commit, push, and open a PR. Title the
   PR for the knowledge change, not the act of running Retro. Prefer
   `New context: <finding>` or `New skill: <finding>`. If the only change
   would be the blackboard marker, do not open a PR.

10. **Post Slack FYI for PRs.**
   If Slack is configured, post one short message that is useful without
   opening GitHub:
   `<PR title>. PR: <url>`.

## PR Body

Use this shape:

```markdown
## Summary
- Extracted durable knowledge from done ticket `<slug>`.
- Updated/created/deleted: <short file list, including deleted source task>.

## Source
- Ticket: deleted `relay-os/tasks/<slug>/`
- Marker: PR history for `relay-os/tasks/<slug>/blackboard.md` records `## Retro`
  with `status: processed`.

## Classification
- Moved into context: <bullets>
- Moved into skill: <bullets or "none">
- Already covered: <bullets or "none">
- Dropped as one-off: <bullets or "none">

## Test Plan
- Reviewed context/skill diff against ticket evidence and existing knowledge inventory.
```

## Quality Bar

The PR should make future task prompts better when there is durable knowledge
to extract. If the ticket has no new durable knowledge, do not open an empty
PR; record the `no-new-durable-knowledge` marker directly and leave the source
task directory in place so Dream does not rerun Retro.
