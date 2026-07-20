---
name: retro/done-ticket
description: Extract durable knowledge from one done ticket or every eligible done ticket in a single run into Coga contexts or skills. A ticket that yields durable knowledge is deleted in its theme's reviewable knowledge PR; a ticket with no durable knowledge is direct-deleted via `coga delete`, with no PR and no marker.
---

# Retro Done Ticket

Retro is a prompt-only Codex skill and the knowledge-extraction gate for
done-ticket cleanup. Dream may call it for eligible completed tasks, but Retro
is not Dream, not a Python worker, and not a cleanup command. Its job is to
read one completed ticket — or every eligible done ticket Dream passes in a
single run — compare the evidence against the repo's context and skill corpus,
and decide whether each task contains durable knowledge worth adding to Coga.
A run loads the corpus once and processes every slug it was given. It then
partitions the tickets that hold new knowledge into coherent themes and opens
one reviewable PR per theme, each recording the source-task `## Retro` marker,
updating the knowledge base, and deleting those source task directories in the
same PR. A source task with no new durable knowledge is still deleted, but
**directly**: Retro removes its directory with
`coga delete <slug> --keep-control-checkout` — a working-tree `git rm` plus a
direct `Ticket: <slug> — deleted` commit — with no PR, no `## Retro` marker,
and no `## Pruned` bookkeeping. Recovery is via `git restore`. Retro never
leaves a processed done ticket on disk.

Retro runs only inside a subagent whose working directory is a dedicated linked
git worktree. The caller owns that boundary and delegates the complete pass
into it: use the agent's native worktree isolation when it has one, otherwise
create a temporary linked worktree with `git worktree add` and pass its absolute
path to the subagent. The caller fetches the configured remote control branch
first and bases the worktree's unique temporary branch on that fresh tip. The
caller also passes a read-only snapshot of the live Retro inputs, then
explicitly removes the worktree after every mutation is durable. Every
knowledge-PR branch switch and direct delete happens inside that boundary,
never in the caller's or operator's primary checkout.

## Known Skill Contract

- Purpose: extract durable knowledge from one done ticket or every eligible
  done ticket in a single run, and delete every processed source task — a
  knowledge-bearing ticket through its reviewable knowledge PR, a
  no-durable-knowledge ticket directly via `coga delete`.
- Runs: `retro/done-ticket <task-slug> [<task-slug> ...]` in one subagent whose
  cwd is a dedicated linked worktree, after a human chooses one exact done
  ticket or Dream passes every eligible done ticket in one run. Native
  `isolation: worktree` and a caller-created `git worktree add` checkout are
  equivalent ways to provide the boundary. The run partitions the tickets into
  coherent PR batches itself.
- Inputs: a caller-created read-only snapshot of each source task's complete
  resolved artifact (bare Markdown file or full directory, including sibling
  attachments), the repo-global `coga/log.md`, Dream's live `## Findings` when
  present, and every local context/skill file; plus the packaged
  `bootstrap/contexts/` and `bootstrap/skills/` corpus. Load the snapshot and
  packaged corpus once before ticket-by-ticket extraction.
- May change: warranted context files, warranted skill files, and the exact
  resolved source task directories under `coga/tasks/` for every processed
  source task — a knowledge-bearing ticket deleted in its theme's knowledge PR,
  a no-durable-knowledge ticket deleted directly via `coga delete`.
- Action: `pr-required` for knowledge edits and the source-task deletions
  bundled with them; `direct-delete` for no-durable-knowledge source tasks.
  Every knowledge edit lands in a reviewable PR; nothing in the knowledge base
  is changed on the working tree.
- Idempotency: for each source task, the task directory is gone, or an open PR
  is adding its `## Retro` marker and deleting the source task directory. A
  no-durable-knowledge ticket is direct-deleted during the run, so afterward its
  directory is simply gone. A processed `## Retro` marker on a still-present
  directory does not settle the task — Retro re-picks it for deletion.
- Stop and ask: the cwd is not a linked worktree distinct from the caller's
  checkout, the caller did not supply a complete evidence snapshot and caller
  repo root, any slug is ambiguous, any task is not `status: done`, any required
  evidence file is missing, a single coherent theme still exceeds the per-PR
  hard limits, or the diff would touch anything outside the allowed files or
  the exact source task directories.
- Output: one coherent PR per knowledge theme, each with knowledge edits and
  the source-task deletion for the tickets that contributed new knowledge;
  no-durable-knowledge tickets removed by direct `coga delete` with no PR.

## Scope

Do:

- read the done ticket directory for each slug passed to this skill;
- read every context file under local `coga/contexts/**/SKILL.md` and package
  `bootstrap/contexts/**/SKILL.md`;
- read every skill file under local `coga/skills/**/SKILL.md` and package
  `bootstrap/skills/**/SKILL.md`;
- decide whether each ticket contains new, useful durable knowledge;
- maintain a running in-memory delta across the whole run — every ticket and
  every PR batch — so later tickets compare against the original corpus plus
  facts already accepted earlier in the run;
- update, create, split, merge, or delete context blocks when warranted;
- update or create a skill only when a ticket contains repeatable process
  knowledge that is not already covered;
- for a knowledge-bearing source task, append or update exactly one `## Retro`
  marker in its `ticket.md` blackboard region and delete its directory in the same knowledge
  PR;
- for a no-durable-knowledge source task, delete its directory directly with
  `coga delete <slug> --keep-control-checkout` — no marker, no PR and no
  fast-forward of another checkout holding the control branch;
- open one PR per coherent knowledge theme, containing that theme's
  knowledge-base changes and the deletion of its contributing source tasks;
- post a one-line Slack FYI with the PR title and link when Slack is
  available. The title should carry the new finding.

Do not:

- delete any task directory except the exact source ticket directories passed
  to this skill;
- delete local or remote git branches;
- open a delete-only PR, fold a deletion into a `## Pruned` section, or open any
  PR at all for a no-durable-knowledge ticket — those are direct-deleted via
  `coga delete`;
- open a marker-only PR — a PR whose only change is a blackboard `## Retro`
  marker with the source task directory left in place;
- mutate ticket frontmatter, `log.md`, or `task.lock` before deleting the
  source task directory;
- preserve one-off execution noise as context.

Knowledge type decides the target: domain facts, repo conventions, constraints,
and known failure modes belong in contexts; repeatable instructions for how an
agent should do work belong in skills. If the process knowledge is already
covered by an existing skill, do not duplicate it.

## Isolation boundary

Run only inside a subagent whose cwd is a dedicated linked git worktree. Claude
callers may supply native `isolation: worktree`; a caller whose agent tool has
no isolation argument (including Codex) creates the worktree first with
`git worktree add`, then tells the subagent to run every command from that exact
absolute path. In both cases, the caller fetches the configured remote control
branch first and creates a unique temporary branch from that fresh tip. The
subagent never creates a second worktree.

Before reading the corpus or changing anything, require the caller's absolute
repo root and prove both parts of the boundary:

```bash
test "$(git rev-parse --show-toplevel)" != "<caller-repo-root>"
test "$(git rev-parse --path-format=absolute --git-dir)" != \
  "$(git rev-parse --path-format=absolute --git-common-dir)"
```

Stop immediately if either check fails. A separate cwd without linked-worktree
git metadata is not enough. Every `git checkout` and `coga delete` command must
run inside the verified worktree; never switch, stage, merge, or dirty the
operator's primary checkout's branch, index, and files.

The caller owns teardown because a mutating Claude subagent may retain its
worktree and Codex has no native worktree lifecycle. Leave the worktree clean
and report its path, temporary branch, PR URLs, and direct-delete verification.
After checking every result is durable, the caller explicitly runs
`git worktree remove <path>` from outside it, then deletes the caller-created
temporary branch with `git branch -D <temporary-branch>`. If durability or
cleanup cannot be verified, preserve the path and branch for recovery and stop
instead of force-removing them.

## Comparison baseline

The baseline is the caller's **current working-tree state**, captured before
delegation in a read-only evidence snapshot, plus the packaged roots
(`bootstrap/contexts/`, `bootstrap/skills/`) available in the isolated
checkout. The snapshot must include local `contexts/`, local `skills/`, the
complete resolved artifact for every selected task (bare Markdown or the whole
directory including sibling attachments), the repo-global `log.md`, and the
caller task's live `## Findings` when present. Copies must be ordinary files,
not symlinks back to the mutable caller checkout. Load the snapshot and
packaged corpus once at the start of the run.

Use snapshot files for classification and the isolated worktree for edits. Do
not copy unrelated uncommitted caller changes into a knowledge PR. If a
warranted Retro edit overlaps a snapshot-only change and you cannot isolate the
Retro delta cleanly, stop and preserve the worktree for recovery.

Do not:

- run `git log`, `git show`, `git diff`, or `git blame` to decide what is
  already covered;
- read prior PR descriptions or commit messages for the source task;
- inspect old revisions of context or skill files.

If a fact is present in the current file on disk, it is covered. If another
ticket already added the fact to this run's running delta, it is covered for
the rest of the run. Otherwise it is not covered. That is the only test.

## Inputs

This skill is invoked with one or more parameters: exact done ticket slugs. The
delegation prompt must also carry the caller's absolute repo root and the
absolute read-only evidence-snapshot path. Work from the isolated repo root.
Resolve each slug to its actual task path; tasks may be single files or
directories at any depth under `coga/tasks/`. `coga retire <slug>` passes one
slug. Dream passes every eligible done ticket in one run; the skill partitions
them into coherent PR batches itself.

Required files:

- snapshot copy of each selected task's complete resolved artifact, including
  its ticket body, blackboard region, and any sibling files
- snapshot copy of the repo-global `coga/log.md`
- snapshot copy of the caller task's live `## Findings`, when present
- snapshot copy of local `coga/contexts/**/SKILL.md`
- package `bootstrap/contexts/**/SKILL.md`
- snapshot copy of local `coga/skills/**/SKILL.md`
- package `bootstrap/skills/**/SKILL.md`

If you need the filesystem path for the installed package bootstrap root, run:

```bash
python -c "from importlib.resources import files; print(files('coga.resources').joinpath('templates', 'coga', 'bootstrap'))"
```

Stop and ask if the linked-worktree preflight fails, the caller root or snapshot
path is missing, any task slug is ambiguous, any snapshot task is not
`status: done`, any required evidence file is missing, a selected source task
does not exist in the isolated base (an uncommitted-only task cannot be deleted
durably), a single coherent theme cannot be kept within the per-PR hard limits,
or there is already an open PR adding a `## Retro` marker for the same source
task.

## Workflow

1. **Inventory contexts once.**
   Read all snapshot-local `coga/contexts/**/SKILL.md` and package
   `bootstrap/contexts/**/SKILL.md`. For each context, note its path, `name`,
   `description`, headings, and the knowledge it already covers. This inventory
   is the baseline for deciding whether ticket knowledge is new.

2. **Inventory skills once.**
   Read all snapshot-local `coga/skills/**/SKILL.md` and package
   `bootstrap/skills/**/SKILL.md`. For each skill, note its path, `name`,
   `description`, headings, and the process it already covers. This inventory is
   the baseline for deciding whether ticket knowledge belongs in a skill and
   whether the process is already covered.

3. **Read ticket evidence one ticket at a time.**
   For each selected slug, read its snapshot ticket (body + blackboard region),
   relevant sibling files from its resolved artifact, its lines in the snapshot
   repo-global `coga/log.md`, and the snapshot `## Findings` supplied by Dream
   when present.
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
   too broad when it would touch both `coga/*` and `dev/*`, touch both
   contexts and skills for unrelated reasons, create more than one new
   context/skill file, or need "and" in the PR title to describe the knowledge
   change. Split a too-broad batch into more PRs rather than dropping tickets —
   the run still covers every slug. If a single coherent theme cannot fit
   within one PR's limits, stop and ask.

   Tickets with no new durable knowledge are not a batch theme — they are not
   extracted and not bundled into any PR. After settling the knowledge batches,
   delete every no-durable-knowledge source task directly with
   `coga delete <slug> --keep-control-checkout` (see step 9). They get no
   `## Retro` marker and never appear in a knowledge PR.

6. **Classify each candidate.**
   Use this table:

   | Classification | Action |
   | --- | --- |
   | Already covered | Drop; mention only in notes if important. |
   | New detail for an existing context | Patch the smallest fitting context block. |
   | New coherent topic | Create a focused context under `coga/contexts/<namespace>/<name>/SKILL.md`. |
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

8. **Record the Retro markers for knowledge-bearing tickets.**
   For each source task that contributed new durable knowledge, append or update
   exactly one `## Retro` section in its `ticket.md` blackboard region:

   ```markdown
   ## Retro

   status: processed
   skill: retro/done-ticket
   result: knowledge-pr
   title: <PR title>
   ```

   A source task with no new durable knowledge gets **no** marker — it is
   direct-deleted in step 9. Never open a marker-only PR that writes the marker
   and leaves the directory in place. Return a one-line result naming the
   direct-deleted tickets when no source task in the run contributed new durable
   knowledge.

9. **Delete every processed source task.**
   A source task that contributed new durable knowledge is deleted inside the PR
   that records its `## Retro` marker, after recording that marker — in its
   theme's knowledge PR. A source task with no new durable knowledge is deleted
   **directly** with `coga delete <slug> --keep-control-checkout`, from a clean,
   unique temporary local branch based on freshly fetched `origin/main`. That
   removes its directory in the isolated worktree and commits
   `Ticket: <slug> — deleted` straight to the remote control branch without
   fast-forwarding the operator's control checkout — no PR, no marker, no
   `## Pruned` section. Do not run direct deletes from detached HEAD: leave the
   isolated worktree clean so the caller can verify and remove it. After
   deletion git history is the audit trail, and recovery is via `git restore`.

10. **Self-review the diff.**
   Confirm each knowledge PR changes only context files, warranted skill files,
   and the exact source task directories that contributed knowledge unless the
   human explicitly asked for something else. Confirm every knowledge-bearing
   source task directory is deleted in exactly one PR, that no-durable-knowledge
   tickets are direct-deleted (not bundled into any PR), and that no marker-only
   PR (marker written, directory left in place) is opened.

11. **Open the PRs.**
   Work only in the caller-provided linked worktree; do not create a second
   worktree. For each coherent knowledge batch, branch off `origin/main` inside
   that isolated checkout with
   `git checkout -b codex/retro-<ticket-slug>-knowledge origin/main` for a
   single source task or `codex/retro-<theme>-knowledge origin/main` for a
   multi-ticket batch, make that batch's edits and source-task deletions there,
   commit, push, and open the PR, then return the isolated checkout to
   `origin/main` for the next batch. Title each knowledge PR for its knowledge
   change, not the act of running Retro. Prefer
   `New context: <finding>` or `New skill: <finding>`. No-durable-knowledge
   tickets are not part of any knowledge branch — after the knowledge branches
   are committed and pushed, remove each with
   `coga delete <slug> --keep-control-checkout` from the isolated checkout's
   clean temporary branch. Never branch-switch or refresh the caller's checkout.

12. **Post Slack FYI for PRs.**
   If Slack is configured, post one short message per PR that is useful without
   opening GitHub:
   `<PR title>. PR: <url>`.

## PR Body

Knowledge PR — use this shape:

```markdown
## Summary
- Extracted durable knowledge from done ticket(s): `<slug>`, ...
- Updated/created/deleted: <short file list, including deleted source tasks>.

## Source
- Tickets: deleted `<task-dir>`, ...
- Markers: PR history for each deleted ticket records its `## Retro`
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

No-durable-knowledge tickets do not get a PR — they are removed directly with
`coga delete <slug> --keep-control-checkout`, which commits
`Ticket: <slug> — deleted` to the remote control branch without refreshing a
different checkout. After the run, git history is the audit trail for each
direct-deleted task.

## Quality Bar

Each knowledge PR should make future task prompts better, and must stay small
enough to review and describe with one clear title — that is what the per-PR
limits protect. Splitting a run into several focused PRs is correct; a single
sprawling PR is not. A ticket with no new durable knowledge contributes no
knowledge edit and is direct-deleted via `coga delete` — it never rides in a
knowledge PR. Never open a marker-only PR that writes a `## Retro` marker and
leaves the source task directory on disk; a processed done ticket should not
survive the run.
