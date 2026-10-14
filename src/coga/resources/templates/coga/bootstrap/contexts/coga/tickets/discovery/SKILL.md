---
name: coga/tickets/discovery
description: Where tickets live and how they are named — task discovery, file versus directory form, parked and group directories, task refs, finding a retired task in Git, and the reserved `ticket.py` sibling.
---

# Where tasks live and how they are named

Part of [coga/tickets](../SKILL.md).

`src/coga/tasks.py` `list_tasks` walks `coga/tasks/` at any depth:

- **Directory form**: a directory holding `ticket.md`, plus any attachments.
  A task directory is never recursed into (no task inside a task).
- **File form**: a bare `tasks/<slug>.md`, for a self-contained task with no
  siblings. Promote with `mkdir <slug>/ && mv <slug>.md <slug>/ticket.md`.
- `<slug>.md` and `<slug>/` must not both exist (`DuplicateTaskSlugError`).
- `README.md` is never a task; it documents its directory. Names starting
  with `_` are skipped at every level: `_template/` holds the canonical
  ticket shape, and any other `_`-prefixed directory is **parked**.
- A **parked** directory (such as `_v2/`) keeps files Coga never lists,
  launches, validates, or scans for Dream, while state sync still publishes
  them. It holds captures and wishes that need not be current or consistent.
  `coga create "_v2/<title>"` writes there, title-only is fine, and `coga
  ticket` refuses a parked target. `_template` is reserved at every level:
  `coga/.gitignore` ignores it, so `coga create` refuses it as a component. Pull an item forward with `git mv` out of
  the parked tree; it is then an ordinary ticket and must pass validation.
- Other directories are plain folders managed with `mkdir`/`mv`/`rm`; Coga
  has no command for them.
- **The directory is the group.** Related tickets sit side by side in a plain
  folder whose `README.md` holds shared material; the folder has no workflow,
  status, owner, or completion. There is no parent or umbrella ticket: when
  splitting work, give every deliverable to a real sibling ticket, then remove
  the original with `coga delete` rather than keeping it as a parent
  (`coga retire` accepts only a `done` ticket). Pick a group path other than
  the original's own path: `coga create` refuses to nest a ticket inside a
  directory-form task. Do not put `ticket.md` at a group root; that makes it a
  task, and discovery stops there.
  Owner decision (2026-09-25): there is deliberately no split contract (no
  split skill, `## Split` roster, or `Split from` cross-link convention; #889
  closed) and no oversized-ticket instruction in the `code/*` step skills
  (#899, then removed in `2ffcd4f8b`): agents almost never split or escalated,
  so the text was prompt noise. Splitting stays the ad-hoc sibling practice
  above; reopen only on evidence of repeated oversized-ticket failures.

A task's identity is its **path under `tasks/`**: the bare leaf at top level,
otherwise the relative path (`marketing/social/relaunch`). `resolve_task`
accepts an exact ref or a unique prefix; a nested task's bare leaf does not
resolve, and ambiguous prefixes fail listing the matches. Agents use the exact
task directory printed in the composed prompt header rather than rebuilding it
from the ref. Log lines are tagged with the ref and never rewritten, so moving
a task orphans its history under the old tag: record the prior ref in the body
and grep for it.

A retired or deleted task (`coga retire`, `delete-task`, Retro) leaves its
body and blackboard only as a Git blob; `coga show` no longer finds it. Find
the deleting commit on the control ref, then read the file from its parent.
`<control>` is `<remote>/<control_branch>` from `coga.toml` `[git]`
([coga/configuration](../../configuration/SKILL.md) owns the keys and defaults),
or the local `<control_branch>` in a repo with no remote:

```bash
git log <control> --diff-filter=D --name-only -- \
  ':(glob)coga/tasks/**/<slug>.md' ':(glob)coga/tasks/**/<slug>/**' \
  ':(glob)relay-os/tasks/**/<slug>.md' ':(glob)relay-os/tasks/**/<slug>/**'
git show <commit>^:<path>
```

The pathspecs name the slug exactly, in both the `<slug>.md` and `<slug>/`
forms at any group depth, so a task whose slug merely starts with `<slug>` is
not matched. Search both trees: the tree was `relay-os/tasks/` before the
relay → coga rename (`d0645a197`, #454), so a `coga/tasks/`-only search misses
earlier deletions. The newest hit that deletes `<slug>.md` or
`<slug>/ticket.md` is the retirement; older hits are a `.md` ↔ `<slug>/`
format conversion or an attachment removed earlier. Older directory-form
tasks kept the blackboard in a sibling `blackboard.md`; read it the same way.

A directory-form task may reserve the exact sibling `ticket.py` as its
deterministic phase ([coga/script-tickets](../../script-tickets/SKILL.md)); no
other attachment changes dispatch. Attachments are never composed.
