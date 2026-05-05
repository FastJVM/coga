---
name: retro/done-ticket
description: Extract durable knowledge from one done ticket into Relay contexts or skills and open a reviewable PR.
---

# Retro Done Ticket

Retro is a prompt-only Codex skill. It is not Dream, not a Python worker, and
not a cleanup command. Its job is to read one completed ticket, compare it
against the repo's context and skill corpus, and open a PR that moves new
durable knowledge into the right markdown block.

## Known Skill Contract

- Purpose: extract durable knowledge from one done ticket and mark that Retro
  has processed it.
- Runs: `retro/done-ticket <task-slug>` after Dream or a human chooses one
  exact done ticket.
- Inputs: the source task's `ticket.md`, `blackboard.md`, and `log.md`, plus
  every context and skill file under `relay-os/contexts/` and
  `relay-os/skills/`.
- May change: warranted context files, warranted skill files, and the source
  task's `blackboard.md` only.
- Action: `pr-required`
- Idempotency: the source task blackboard contains a `## Retro` section with
  `status: processed`. An open PR adding that same marker counts as in flight.
- Stop and ask: the slug is ambiguous, the task is not `status: done`, any
  required evidence file is missing, or the diff would touch anything outside
  the allowed files.
- Output: a PR with knowledge edits or a marker-only "no new durable
  knowledge" result, plus a Slack FYI when Slack is available.

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
- open a PR containing the knowledge-base changes;
- post a one-line Slack FYI with the PR title and link when Slack is
  available. The title should carry the new finding.

Do not:

- delete the source ticket directory;
- delete local or remote git branches;
- mutate ticket frontmatter, `log.md`, or `task.lock`;
- preserve one-off execution noise as context.

Knowledge type decides the target: domain facts, repo conventions, constraints,
and known failure modes belong in contexts; repeatable instructions for how an
agent should do work belong in skills. If the process knowledge is already
covered by an existing skill, do not duplicate it.

## Inputs

This skill is invoked with one parameter: the done ticket slug. Work from the
repo root.

Required files:

- `relay-os/tasks/<slug>/ticket.md`
- `relay-os/tasks/<slug>/blackboard.md`
- `relay-os/tasks/<slug>/log.md`
- `relay-os/contexts/**/SKILL.md`
- `relay-os/skills/**/SKILL.md`

Stop and ask if the task slug is ambiguous, the task is not `status: done`, or
any required task evidence file is missing.

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
   should inherit.

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

6. **Mark the source blackboard.**
   Append or update exactly one `## Retro` section in
   `relay-os/tasks/<slug>/blackboard.md`:

   ```markdown
   ## Retro

   status: processed
   skill: retro/done-ticket
   result: <knowledge-pr | no-new-durable-knowledge>
   title: <PR title>
   ```

   This is the idempotency marker Dream reads on later runs. If no durable
   knowledge is found, still write the marker with
   `result: no-new-durable-knowledge`.

7. **Self-review the diff.**
   Confirm the PR changes only context files, warranted skill files, and the
   source task blackboard unless the human explicitly asked for something else.
   Make sure the source task directory remains in place.

8. **Open the PR.**
   Commit the knowledge edits on a branch such as
   `codex/retro-<ticket-slug>-knowledge`, push it, and open a PR. Title the
   PR for the knowledge change, not the act of running Retro. Prefer
   `New context: <finding>` or `New skill: <finding>`. If the only change is
   the blackboard marker, use `Retro processed: no new durable knowledge for
   <ticket-slug>`.

9. **Post Slack FYI.**
   If Slack is configured, post one short message that is useful without
   opening GitHub:
   `<PR title>. PR: <url>`.

## PR Body

Use this shape:

```markdown
## Summary
- Extracted durable knowledge from done ticket `<slug>`.
- Updated/created/deleted: <short file list>.

## Source
- Ticket: `relay-os/tasks/<slug>/`
- Marker: `relay-os/tasks/<slug>/blackboard.md` contains `## Retro` with
  `status: processed`.

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
to extract. If the ticket has no new durable knowledge, open a marker-only PR
so Dream can delete the task without rerunning Retro forever.
