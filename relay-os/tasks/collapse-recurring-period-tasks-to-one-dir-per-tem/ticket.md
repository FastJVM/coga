---
title: Collapse recurring period tasks to one dir per template under tasks/recurring/,
  period in blackboard
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
---

## Description

Change recurring tasks from **one fresh directory per period** to **one
persistent directory per template**, living under a `tasks/recurring/` group,
with the current period tracked in the task's **blackboard** instead of the
slug.

- **Today:** `tasks/recurring-dream-2026-W21/`, `tasks/recurring-dream-2026-W22/`,
  … — a new directory each period; the `recurring-` prefix is the identity
  marker and the `<period>` is the dedup key, both baked into the slug.
- **Target:** `tasks/recurring/dream/` — one directory per template. The
  `recurring/` group dir carries the namespacing the prefix used to; the
  blackboard records which period the run is currently servicing; the
  append-only `log.md` accumulates period history (logs are never composed
  into prompts, so unbounded growth is fine).

### Why

The `recurring-` slug prefix is purely a namespace marker, and the `<period>`
suffix is purely a dedup/identity key — both encode in the slug what now has
better homes: the group directory (namespace) and the blackboard/log (period
state). Wins: recurring runs grouped in `relay status`, a cleaner layout, and
period state where state belongs. Uses the group-qualified-slug machinery from
\#350.

### Two-directory model (resolved in design)

There are two dirs, with a clean split of roles — the change is *which one
carries the period*, not a merge:

- **`relay-os/recurring/<name>/`** — the persistent template/control home.
  Unchanged location. Its `blackboard.md` gains a **last-serviced-period
  high-water mark** plus the existing cross-run state. It is the only place
  that survives a run, so it is the only place that can record "this period
  ran" after the instantiated task is deleted.
- **`relay-os/tasks/recurring/<name>/`** — the instantiated run. New stable,
  group-qualified slug `recurring/<name>` (no `recurring-` prefix, no period
  suffix). Created fresh each firing, used as that run's scratch blackboard,
  then **deleted at end of run** (Dream retro pass / `relay delete`) exactly
  as today. Because it is deleted on completion, there is no per-period
  blackboard reset to design — a leftover dir *is* the orphan signal.

## Acceptance Criteria

- [ ] A recurring firing creates the instantiated task at
      `tasks/recurring/<name>/` with bare group-qualified slug
      `recurring/<name>` — no `recurring-` prefix, no period suffix. The dir
      reports `group="recurring"`, `id_slug="recurring/<name>"`.
- [ ] The current period is written by the creator into
      `recurring/<name>/blackboard.md` as a single overwritten high-water
      value (not a growing list), and `relay/period-task` instructs the run
      to read its period from there rather than parsing its slug.
- [ ] Dedup ("this period already ran") is decided from the high-water mark:
      `last_serviced >= computed period_key` ⇒ skip. Works after the
      instantiated task is deleted. The unbounded human-readable period
      history continues to live in `recurring/<name>/log.md`.
- [ ] Orphan resume: a leftover `tasks/recurring/<name>/` whose recorded
      period ≠ the current `period_key` is resumed (not superseded by a fresh
      period), and the high-water mark is advanced when the new period is
      serviced. An `in_progress` leftover is still preferred over `active`.
- [ ] `relay status` still peels recurring runs into their own table —
      derived from **group membership** (`group == "recurring"`), not the
      `recurring-` prefix.
- [ ] Debug `--all` runs stay distinct: they create **top-level**
      (`tasks/<name>-dbg-<ts>`, outside the `recurring/` group) and remain
      excluded from resume/dedup. The real-vs-debug distinction no longer
      depends on the `recurring-` prefix.
- [ ] Clean-cut migration: existing `tasks/recurring-<name>-<period>/` dirs
      are removed; each template's high-water mark is seeded from its existing
      `log.md` ledger so no already-handled period re-fires. No dual-shape
      support is carried.
- [ ] `relay/architecture` and `relay/cli` contexts updated to the new slug
      shape and group-based identity, in **both** the live `relay-os/` copy
      and the packaged `src/relay/resources/templates/relay-os/` copy.
      `relay/period-task` updated likewise in both copies.
- [ ] `python -m pytest` and `relay validate --json` pass; recurring tests
      updated for the new slug/dir shape.

## Proposed Shape

**Runtime sequence** — what `relay recurring` does per firing for template
`recurring/<name>/`:

1. Compute `period_key` from the schedule (`_period_key`).
2. Read `last_serviced_period` from `recurring/<name>/blackboard.md`.
3. If `last_serviced >= period_key` and no leftover run dir → already handled,
   skip.
4. Else get-or-create the instantiated run at `tasks/recurring/<name>/`
   (slug `recurring/<name>`, template body copied in). A leftover dir with a
   stale period is resumed, not superseded.
5. Write the current `period_key` into `recurring/<name>/blackboard.md`
   (overwrite the high-water line) and append history to `log.md`.
6. Launch the run.
7. On completion the instantiated dir is deleted (Dream retro / `relay
   delete`), freeing the path for the next period.

All slug/identity logic is in `src/relay/recurring.py` unless noted.

1. **Slug (`_recurring_slug` ~:689, `_RECURRING_PREFIX` :686).** Replace the
   `recurring-<name>-<period>` builder with a constant group-qualified slug
   `recurring/<name>`. Drop `_RECURRING_PREFIX`. `create_task`
   (`create.py:121`) already does `tasks_dir(cfg) / slug` + `mkdir(parents=
   True)`, so a slashed `slug_override` lands the dir under the group; verify
   the uniqueness/collision check (`create.py:115`, top-level leaves only)
   does the right thing for a grouped slug and that `list_tasks` reports
   `group="recurring"`.
2. **Period high-water mark.** Add helpers to read/write a single
   `last_serviced_period` value in `recurring/<name>/blackboard.md`
   (a labeled line the creator overwrites each period). The creator
   writes the current `period_key` here when it creates/advances a run.
3. **Dedup (`_period_already_created` ~:727 → rewrite).** Replace the
   `created <slug>` log-scan with `last_serviced >= period_key` against the
   high-water mark. Keep appending human history to `log.md` via `_record_run`
   (`:623`) — it stops being load-bearing for dedup but stays as the audit
   ledger. Drop the legacy `blackboard.md` `created …` back-compat scan.
4. **Live-task / orphan lookup (`_live_task_for_template` ~:700,
   `_task_with_slug` :693).** Match on the fixed `id_slug == "recurring/
   <name>"` instead of `slug.startswith(prefix)`. Orphan-resume = the dir
   exists with recorded period ≠ current `period_key`; prefer `in_progress`
   over `active` as today. Update `scan_due` (:237–:251) and `list_templates`
   (:513–:515) to the new lookup.
5. **Status identity (`is_recurring_slug` :360 → group-based).** Replace the
   prefix test with a group check; update the two callers
   (`commands/status.py:118-119`, `commands/recurring.py:395`) to filter on
   `ref.group == "recurring"`. (Note: the ticket's `is_recurring_period_task`
   / `_reap_debug_orphans` names do not exist in the tree — the real symbols
   are `is_recurring_slug` and the `_DEBUG_SLUG_RE` reaper logic; see
   blackboard Open Questions.)
6. **Debug runs (`create_debug_run` :370, `is_debug_slug` :353).** Already
   top-level and prefix-free; confirm they stay outside the `recurring/` group
   and that group-based identity (step 5) keeps excluding them.
7. **`relay/period-task` context.** Rewrite the "your slug names your parent"
   section: the run is at `tasks/recurring/<name>/`, its parent is
   `recurring/<name>/`, and its current period comes from the parent
   blackboard's high-water line, not the slug. Cross-run state still lives in
   the parent blackboard (unchanged intent).
8. **Migration (one-shot).** Delete existing `tasks/recurring-<name>-<period>/`
   dirs; for each template seed `last_serviced_period` from the newest
   `created …` line in its `log.md`. Decide whether this is a throwaway
   script or a guarded step in `scan_due` — record in blackboard.
9. **Context sync.** Update `relay/architecture` and `relay/cli` for the new
   slug/group shape in both the live and packaged trees; sync the
   `relay/period-task` rewrite to both trees too.

## Out of Scope

- Merging the template dir and the instantiated task dir into a single
  directory — explicitly two dirs (template = control/state, task = run).
- Changing the `_period_key` bucketing heuristic or the cron schedule model.
- Streaming / the `mode: auto` ban (`_effective_mode`) — untouched.
- Any change to non-recurring task creating or the `#350` group machinery
  itself (consumed as-is).
- Reworking how `relay delete` / Dream's retro pass deletes done runs — relied
  on as-is.

## Context

`#350` shipped the group-qualified-slug machinery this builds on:
`TaskRef.group` / `TaskRef.id_slug` (`tasks.py:46-57`) and `list_tasks`
one-level-deep group discovery (`tasks.py:80-`). Deletion of completed
recurring runs is `relay delete` → `bootstrap/delete-task` (rmtree); this
change relies on that "deleted when done" behavior for orphan detection.
