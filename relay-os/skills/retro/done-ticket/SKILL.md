---
name: retro/done-ticket
description: Extract durable knowledge from one done ticket or every eligible done ticket in a single run into Relay contexts or skills, opening one reviewable PR per coherent theme only when new knowledge exists.
---

# Retro Done Ticket

Retro is a prompt-only Codex skill and the knowledge-extraction gate for
done-ticket cleanup. Dream may call it for eligible completed tasks, but Retro
is not Dream, not a Python worker, and not a cleanup command. Its job is to
read one completed ticket — or every eligible done ticket Dream passes in a
single run — compare the evidence against the repo's context and skill corpus,
and decide whether each task contains durable knowledge worth adding to Relay.
A run loads the corpus once and processes every slug it was given; it then
partitions the tickets that hold new knowledge into coherent themes and opens
one reviewable PR per theme, each recording the source-task `## Retro` markers,
updating the knowledge base, and deleting those source task directories in the
same PR. Source tasks with no new durable knowledge get a no-op marker on their
blackboard and no PR.

## Known Skill Contract

- Purpose: extract durable knowledge from one done ticket or every eligible
  done ticket in a single run, mark that Retro has processed each source task,
  and avoid marker-only cleanup PRs when no new knowledge exists.
- Runs: `retro/done-ticket <task-slug> [<task-slug> ...]` after a human
  chooses one exact done ticket, or Dream passes every eligible done ticket in
  one run. The run partitions them into coherent PR batches itself.
- Inputs: each source task's `ticket.md`, `blackboard.md`, and `log.md`, plus
  every context and skill file under `relay-os/contexts/` and
  `relay-os/skills/`, loaded once per run before ticket-by-ticket extraction.
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
  required evidence file is missing, a single coherent theme still exceeds the
  per-PR hard limits, or the diff would touch anything outside the allowed
  files or the exact source task directories.
- Output: one coherent PR per knowledge theme, each with knowledge edits and
  source task deletion for the tickets that contributed new knowledge, plus
  direct `no-new-durable-knowledge` markers (no PR, no source deletion) for
  tickets that contributed none.

## Scope

Do:

- read the done ticket directory for each slug passed to this skill;
- read every context file under `relay-os/contexts/**/SKILL.md`;
- read every skill file under `relay-os/skills/**/SKILL.md`;
- decide whether each ticket contains new, useful durable knowledge;
- maintain a running in-memory delta across the whole run — every ticket and
  every PR batch — so later tickets compare against the original corpus plus
  facts already accepted earlier in the run;
- update, create, split, merge, or delete context blocks when warranted;
- update or create a skill only when a ticket contains repeatable process
  knowledge that is not already covered;
- append or update exactly one `## Retro` marker in each source task's
  `blackboard.md`;
- when new durable knowledge exists, delete the source ticket directory in the
  same PR after recording the marker;
- when new durable knowledge exists, open one PR per coherent theme, containing
  that theme's knowledge-base changes and the deletion of its contributing
  source tasks;
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
state** of `relay-os/contexts/**` and `relay-os/skills/**`. Load that corpus
once at the start of the run. The final state of those files is the entire
learning record. Durable knowledge that was already captured by prior source
tasks lives in those files now — not in commit messages, not in PR descriptions,
not in diffs.

Do not:

- run `git log`, `git show`, `git diff`, or `git blame` to decide what is
  already covered;
- read prior PR descriptions or commit messages for the source task;
- inspect old revisions of context or skill files.

If a fact is present in the current file on disk, it is covered. If another
ticket already added the fact to this run's running delta, it is covered for
the rest of the run. Otherwise it is not covered. That is the only test.

## Inputs

This skill is invoked with one or more parameters: exact done ticket slugs. Work
from the repo root. `relay retire <slug>` passes one slug. Dream passes every
eligible done ticket in one run; the skill partitions them into coherent PR
batches itself.

Required files:

- `relay-os/tasks/<slug>/ticket.md` for each selected slug
- `relay-os/tasks/<slug>/blackboard.md` for each selected slug
- `relay-os/tasks/<slug>/log.md` for each selected slug
- `relay-os/contexts/**/SKILL.md`
- `relay-os/skills/**/SKILL.md`

Stop and ask if any task slug is ambiguous, any task is not `status: done`, any
required task evidence file is missing, a single coherent theme cannot be kept
within the per-PR hard limits below, or there is already an open PR adding a
`## Retro` marker for the same source task.

## Workflow

1. **Inventory contexts once.**
   Read all `relay-os/contexts/**/SKILL.md`. For each context, note its path,
   `name`, `description`, headings, and the knowledge it already covers. This
   inventory is the baseline for deciding whether ticket knowledge is new.

2. **Inventory skills once.**
   Read all `relay-os/skills/**/SKILL.md`. For each skill, note its path,
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
   As you accept new knowledge from a ticket, add it to an in-memory run delta
   before reading the next ticket. Compare later tickets against the original
   corpus plus that delta. The delta spans the whole run, across every PR
   batch: if two tickets teach the same fact, only the first contributes a
   knowledge edit, even when the two tickets land in different PRs.

5. **Partition the run into coherent PR batches.**
   Process every slug passed to the run — there is no per-run ticket cap. After
   reading the evidence, group the tickets that hold new knowledge into
   coherent PR batches and open one PR per batch. Each PR batch may include at
   most five source tickets, touch at most three knowledge files, and create at
   most one new context or skill file; all of a batch's extracted facts must
   fit one obvious theme or one existing context/skill area. Treat a batch as
   too broad when it would touch both `relay/*` and `dev/*`, touch both
   contexts and skills for unrelated reasons, create more than one new
   context/skill file, or need "and" in the PR title to describe the knowledge
   change. Split a too-broad batch into more PRs rather than dropping tickets —
   the run still covers every slug. If a single coherent theme cannot fit
   within one PR's limits, stop and ask.

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
   Confirm each PR changes only context files, warranted skill files, and the
   exact source task directories unless the human explicitly asked for something
   else. For no-new-durable-knowledge results, confirm the only source-task edit
   is the `blackboard.md` marker and that no PR will be opened solely for those
   markers.

11. **Open one PR per coherent batch when knowledge changed.**
   Work in the current checkout — do not create a `git worktree`. For each
   coherent batch, branch directly off `origin/main` with `git checkout -b
   codex/retro-<ticket-slug>-knowledge origin/main` for a single source task or
   `codex/retro-<theme>-knowledge origin/main` for a multi-ticket batch, make
   that batch's edits and source-task deletions there, commit, push, and open
   the PR, then return to `origin/main` for the next batch. Title each PR for
   its knowledge change, not the act of running Retro. Prefer
   `New context: <finding>` or `New skill: <finding>`. If a batch's only change
   would be the blackboard marker, do not open a PR for it.

12. **Post Slack FYI for PRs.**
   If Slack is configured, post one short message per PR that is useful without
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
  inventory, and the per-PR coherence limits.
```

## Quality Bar

Each PR should make future task prompts better when there is durable knowledge
to extract, and must stay small enough to review and describe with one clear
title — that is what the per-PR limits protect. Splitting a run into several
focused PRs is correct; a single sprawling PR is not. If a ticket has no new
durable knowledge, do not open an empty PR; record the
`no-new-durable-knowledge` marker directly and leave the source task directory
in place so Dream does not rerun Retro.
