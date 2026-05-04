---
name: retro/done-ticket
description: Extract durable contextual knowledge from one done ticket into Relay contexts and open a reviewable PR.
---

# Retro Done Ticket

Retro is a prompt-only Codex skill. It is not Dream, not a Python worker, and
not a cleanup command. Its job is to read one completed ticket, compare it
against the repo's context corpus, and open a PR that moves new durable
contextual knowledge into `relay-os/contexts/`.

## Scope

Do:

- read one exact done ticket directory;
- read every context file under `relay-os/contexts/**/SKILL.md`;
- decide whether the ticket contains new, useful contextual knowledge;
- update, create, split, merge, or delete context blocks when warranted;
- open a PR containing the context changes;
- post a one-line Slack FYI with the PR link when Slack is available.

Do not:

- create or edit skills;
- delete the source ticket directory;
- delete local or remote git branches;
- mutate ticket frontmatter, `log.md`, or `task.lock`;
- preserve one-off execution noise as context.

If the ticket contains process knowledge, classify it as out of scope for
Retro. The original workflow or implementation process should have split that
into a skill/workflow ticket already. Mention the gap in the PR body if useful,
but do not create `relay-os/skills/**`.

## Inputs

The human should provide one done ticket slug. Work from the repo root.

Required files:

- `relay-os/tasks/<slug>/ticket.md`
- `relay-os/tasks/<slug>/blackboard.md`
- `relay-os/tasks/<slug>/log.md`
- `relay-os/contexts/**/SKILL.md`

Stop and ask if the task slug is ambiguous, the task is not `status: done`, or
any required task evidence file is missing.

## Workflow

1. **Inventory contexts.**
   Read all `relay-os/contexts/**/SKILL.md`. For each context, note its path,
   `name`, `description`, headings, and the knowledge it already covers. This
   inventory is the baseline for deciding whether ticket knowledge is new.

2. **Read the ticket evidence.**
   Read `ticket.md`, `blackboard.md`, and `log.md`. Extract candidate durable
   knowledge: domain facts, repo conventions, sharp gotchas, durable decisions,
   corrected assumptions, known failure modes, and boundaries future agents
   should inherit.

3. **Classify each candidate.**
   Use this table:

   | Classification | Action |
   | --- | --- |
   | Already covered | Drop; mention only in notes if important. |
   | New detail for an existing context | Patch the smallest fitting context block. |
   | New coherent topic | Create a focused context under `relay-os/contexts/<namespace>/<name>/SKILL.md`. |
   | Duplicate or stale existing context | Merge, rewrite, or delete the obsolete block/file. |
   | Process knowledge | Out of scope; do not create a skill. |
   | One-off execution detail | Drop. |

4. **Edit contexts.**
   Keep edits readable and reviewable. Prefer a small targeted patch to a broad
   rewrite. Create a new context only when no existing context can carry the
   knowledge cleanly. Delete a context block only when it is obsolete,
   duplicated, or replaced by the new edit.

5. **Self-review the diff.**
   Confirm the PR changes only context files unless the human explicitly asked
   for something else. Make sure the source ticket remains in place.

6. **Open the PR.**
   Commit the context edits on a branch such as
   `codex/retro-<ticket-slug>-context`, push it, and open a PR.

7. **Post Slack FYI.**
   If Slack is configured, post one short message:
   `Retro <ticket-slug>: extracted context PR <url>`.

## PR Body

Use this shape:

```markdown
## Summary
- Extracted durable context from done ticket `<slug>`.
- Updated/created/deleted: <short file list>.

## Source
- Ticket: `relay-os/tasks/<slug>/`

## Classification
- Moved into context: <bullets>
- Already covered: <bullets or "none">
- Dropped as one-off: <bullets or "none">
- Process knowledge out of scope: <bullets or "none">

## Test Plan
- Reviewed context diff against ticket evidence and existing context inventory.
```

## Quality Bar

The PR should make future task prompts better. If the ticket has no new durable
contextual knowledge, do not edit files just to prove Retro ran; report that no
context PR is warranted.
