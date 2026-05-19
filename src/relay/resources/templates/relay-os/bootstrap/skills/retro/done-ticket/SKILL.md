---
name: retro/done-ticket
description: Extract durable knowledge from one done ticket or a coherent batch into Relay contexts or skills and open a reviewable PR only when new knowledge exists.
---

# Retro Done Ticket

Retro is a prompt-only Codex skill and the knowledge-extraction gate for
done-ticket cleanup. Dream may call it for eligible completed tasks, but Retro
is not Dream, not a Python worker, and not a cleanup command. Its job is to
read one completed ticket or a small coherent batch, compare the evidence
against the repo's context and skill corpus, and decide whether the task(s)
contain durable knowledge worth adding to Relay. When they do, Retro opens a
reviewable PR that records the source-task `## Retro` markers, updates the
knowledge base, and deletes the source task directories in that same PR. When
they do not, Retro records no-op markers on the source blackboards and stops
without opening a marker-only PR.

## Known Skill Contract

- Purpose: extract durable knowledge from one done ticket or a coherent batch,
  mark that Retro has processed each source task, and avoid marker-only cleanup
  PRs when no new knowledge exists.
- Runs: `retro/done-ticket <task-slug> [<task-slug> ...]` after Dream or a
  human chooses one exact done ticket, or Dream chooses a coherent batch of at
  most five exact done tickets.
- Inputs: each source task's `ticket.md`, `blackboard.md`, and `log.md`, plus
  every local and bundled context/skill file under `relay-os/contexts/`,
  `relay-os/bootstrap/contexts/`, `relay-os/skills/`, and
  `relay-os/bootstrap/skills/`, loaded once per run before ticket-by-ticket
  extraction.
- May change: warranted context files, warranted skill files, the exact source
  task directories `relay-os/tasks/<slug>/` when a knowledge PR is opened, or
  only `relay-os/tasks/<slug>/blackboard.md` for source tasks where no new
  durable knowledge is found.
- Action: `pr-required` for knowledge edits; `direct-fix` for a
  no-new-durable-knowledge marker only.
- Idempotency: for each source task, the task is gone, the source task
  blackboard contains a `## Retro` section with `skill: retro/done-ticket` and
  `status: processed`, or an open PR is adding that marker or deleting the
  source task directory.
- Stop and ask: any slug is ambiguous, any task is not `status: done`, any
  required evidence file is missing, a batch exceeds the hard limits or cannot
  be made coherent, or the diff would touch anything outside the allowed files
  or the exact source task directories.
- Output: one coherent PR with knowledge edits and source task deletion for the
  source tasks that contributed new knowledge, or direct
  `no-new-durable-knowledge` markers with no PR and no source deletion.

## Scope

Do:

- read the done ticket directory for each slug passed to this skill;
- read every context file under `relay-os/contexts/**/SKILL.md` and
  `relay-os/bootstrap/contexts/**/SKILL.md`;
- read every skill file under `relay-os/skills/**/SKILL.md` and
  `relay-os/bootstrap/skills/**/SKILL.md`;
- decide whether each ticket contains new, useful durable knowledge;
- maintain a running in-memory delta while processing the selected tickets, so
  later tickets compare against the original corpus plus facts already accepted
  during this batch;
- update, create, split, merge, or delete context blocks when warranted;
- update or create a skill only when a ticket contains repeatable process
  knowledge that is not already covered;
- append or update exactly one `## Retro` marker in each source task's
  `blackboard.md`;
- when new durable knowledge exists, delete the source ticket directory in the
  same PR after recording the marker;
- when new durable knowledge exists, open one PR containing the knowledge-base
  changes and source task deletion for the coherent batch;
- when no new durable knowledge exists, record the marker directly and leave
  the source task directory in place;
- post a one-line Slack FYI with the PR title and link when Slack is
  available. The title should carry the new finding.

Do not:

- delete any task directory except the exact source ticket directories passed
  to this skill;
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
state** of the local roots (`relay-os/contexts/**`, `relay-os/skills/**`) plus
the bundled roots (`relay-os/bootstrap/contexts/**`,
`relay-os/bootstrap/skills/**`). Load that corpus once at the start of the run.
The final state of the local files is the editable learning record; bundled
files are package-backed baseline knowledge. Durable knowledge that was already
captured by prior source tasks lives in those files now — not in commit
messages, not in PR descriptions, not in diffs.

Do not:

- run `git log`, `git show`, `git diff`, or `git blame` to decide what is
  already covered;
- read prior PR descriptions or commit messages for the source task;
- inspect old revisions of context or skill files.

If a fact is present in the current file on disk, it is covered. If another
selected ticket already added the fact to this batch's running delta, it is
covered for the rest of the batch. Otherwise it is not covered. That is the only
test.

## Inputs

This skill is invoked with one or more parameters: exact done ticket slugs. Work
from the repo root. `relay retire <slug>` passes one slug. Dream may pass a
coherent batch of up to five slugs.

Required files:

- `relay-os/tasks/<slug>/ticket.md` for each selected slug
- `relay-os/tasks/<slug>/blackboard.md` for each selected slug
- `relay-os/tasks/<slug>/log.md` for each selected slug
- `relay-os/contexts/**/SKILL.md`
- `relay-os/bootstrap/contexts/**/SKILL.md`
- `relay-os/skills/**/SKILL.md`
- `relay-os/bootstrap/skills/**/SKILL.md`

Stop and ask if any task slug is ambiguous, any task is not `status: done`, any
required task evidence file is missing, the batch cannot be kept within the
hard limits below, or there is already an open PR adding a `## Retro` marker for
the same source task.

## Workflow

1. **Inventory contexts once.**
   Read all `relay-os/contexts/**/SKILL.md` and
   `relay-os/bootstrap/contexts/**/SKILL.md`. For each context, note its path,
   `name`, `description`, headings, and the knowledge it already covers. This
   inventory is the baseline for deciding whether ticket knowledge is new.

2. **Inventory skills once.**
   Read all `relay-os/skills/**/SKILL.md` and
   `relay-os/bootstrap/skills/**/SKILL.md`. For each skill, note its path,
   `name`, `description`, headings, and the process it already covers. This
   inventory is the baseline for deciding whether ticket knowledge belongs in a
   skill and whether the process is already covered.

3. **Read ticket evidence one ticket at a time.**
   For each selected slug, read `ticket.md`, `blackboard.md`, and `log.md`.
   Extract candidate durable knowledge: domain facts, repo conventions, sharp
   gotchas, durable decisions, corrected assumptions, known failure modes, and
   boundaries future agents should inherit. Read the ticket files themselves —
   do not consult git history, prior PRs, or old revisions for any of this.

4. **Maintain the running delta.**
   As you accept new knowledge from a ticket, add it to an in-memory batch delta
   before reading the next ticket. Compare later tickets against the original
   corpus plus that delta. If two tickets teach the same fact, only the first
   one contributes a knowledge edit; the later one is already covered by this
   batch.

5. **Keep the batch bounded and coherent.**
   A batch PR may include at most five source tickets, touch at most three
   knowledge files, and create at most one new context or skill file. All
   extracted facts must fit one obvious theme or one existing context/skill
   area. Treat the batch as too broad when it would touch both `relay/*` and
   `dev/*`, touch both contexts and skills for unrelated reasons, create more
   than one new context/skill file, or need "and" in the PR title to describe
   the knowledge change. If the selected slugs exceed this, shrink the batch or
   stop and ask; do not open a broad PR.

6. **Classify each candidate.**
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

7. **Edit knowledge blocks once.**
   Keep edits readable and reviewable. Prefer a small targeted patch to a broad
   rewrite. Create a new context only when no existing context can carry the
   knowledge cleanly. Create a new skill only when the ticket contains
   repeatable process instructions and no existing skill can carry them cleanly.
   Delete a context or skill block only when it is obsolete, duplicated, or
   replaced by the new edit.

8. **Record the Retro markers.**
   Append or update exactly one `## Retro` section in each selected source
   task's `blackboard.md`:

   ```markdown
   ## Retro

   status: processed
   skill: retro/done-ticket
   result: <knowledge-pr | no-new-durable-knowledge>
   title: <PR title or no-op title>
   ```

   If no durable knowledge is found for a source task, write the marker with
   `result: no-new-durable-knowledge`, use a title such as
   `No new durable knowledge for <slug>`, leave that `relay-os/tasks/<slug>/` in
   place, and do not open a PR solely for that marker. Return a one-line no-op
   result when no source task in the run contributed new durable knowledge.

9. **Delete source tasks only for knowledge PRs.**
   If a source task contributed new durable knowledge that was added to a
   context or skill, delete `relay-os/tasks/<slug>/` in the same PR after
   recording the marker. The marker is preserved in PR history, and after merge
   git history is the audit trail for the deleted task. Do not delete source
   tasks whose only result is `no-new-durable-knowledge`.

10. **Self-review the diff.**
   Confirm the PR changes only context files, warranted skill files, and the
   exact source task directories unless the human explicitly asked for something
   else. For no-new-durable-knowledge results, confirm the only source-task edit
   is the `blackboard.md` marker and that no PR will be opened solely for those
   markers.

11. **Open the PR only when knowledge changed.**
   Work in the current checkout — do not create a `git worktree`. Branch
   directly off `origin/main` with `git checkout -b
   codex/retro-<ticket-slug>-knowledge origin/main` for a single source task or
   `codex/retro-batch-knowledge origin/main` for a batch, make the edits and the
   source-task deletions there, commit, push, and open a PR. Title the
   PR for the knowledge change, not the act of running Retro. Prefer
   `New context: <finding>` or `New skill: <finding>`. If the only change
   would be the blackboard marker, do not open a PR.

12. **Post Slack FYI for PRs.**
   If Slack is configured, post one short message that is useful without
   opening GitHub:
   `<PR title>. PR: <url>`.

## PR Body

Use this shape:

```markdown
## Summary
- Extracted durable knowledge from done ticket(s): `<slug>`, ...
- Updated/created/deleted: <short file list, including deleted source tasks>.

## Source
- Tickets: deleted `relay-os/tasks/<slug>/`, ...
- Markers: PR history for each deleted `blackboard.md` records `## Retro`
  with `status: processed`.

## Classification
- Moved into context: <bullets>
- Moved into skill: <bullets or "none">
- Already covered: <bullets or "none">
- Dropped as one-off: <bullets or "none">

## Test Plan
- Reviewed context/skill diff against ticket evidence, the existing knowledge
  inventory, and the batch coherence limits.
```

## Quality Bar

The PR should make future task prompts better when there is durable knowledge
to extract. A batch PR must stay small enough to review and describe with one
clear title. If a ticket has no new durable knowledge, do not open an empty PR;
record the `no-new-durable-knowledge` marker directly and leave the source task
directory in place so Dream does not rerun Retro.
