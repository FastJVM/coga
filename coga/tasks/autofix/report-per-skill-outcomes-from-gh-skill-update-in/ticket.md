---
title: Report per-skill outcomes from gh skill update in skill-update
status: in_progress
owner: nicktoper
agent: claude
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 4 (review)
---

## Description

## What broke

The `recurring/skill-update` run exited 0 and wrote a report that describes
none of the skills this repo actually has installed. Its per-skill detail is
entirely about skills that are *not* installed, and the one line that stands in
for every installed skill is a hardcoded constant that is emitted identically
whether the update changed everything, nothing, or failed partway.

## Evidence from the run record

The blackboard report reads:

```
Result: 15 skill(s): 1 updated, 0 need follow-up, 14 skipped.
PR: https://github.com/FastJVM/coga/pull/736

### Updated
- `gh-managed`: `delegated` (github) - delegated GitHub-backed skill updates to gh skill

### Skipped
- `bootstrap/delete-task`: `skipped-bundled` (bundled) - ... run `pip install --upgrade coga`
  ... 13 more ...
```

This repo has 23 installed skills under `coga/skills/` (`find coga/skills -name SKILL.md`),
including the seven `google-agents-cli-*` skills that
`src/coga/resources/managed-skills.toml` explicitly declares as
`source_type = "github"` skills to be refreshed at update time. **Not one of
those 23 appears in the report.**

The 14 skills that *are* named are exactly `bundled_refs - local_refs` — the
packaged `bootstrap/*`, `browser/build-automation`, `coga/gmail`,
`coga/google-calendar`, `coga/calendar-reminder`, `retro/done-ticket` skills
that this repo has never installed. The report spends its whole detail section
telling the operator to `pip install --upgrade coga` for skills the repo does
not have, and says nothing about the ones it does.

That the report is wrong rather than merely terse is confirmed by the same
sweep's Dream run, which records that **PR #736 — the PR this very job opened —
edits `coga/skills/google-agents-cli-workflow/SKILL.md`**. A real installed
skill was updated, and the report attributes it to nothing.

## Where it lives

`src/coga/skill_manager.py`, the `--all` branch of `update_skills` (~L233-254):

- L236-237 calls `_update_gh_backed_skills` once and appends its single result.
- L250-254 iterates `sorted(bundled_refs - local_refs)` — i.e. reports only on
  *uninstalled* bundled skills.
- Installed skills whose metadata is not `source_type == "url"` produce **no
  result row at all**.

`_update_gh_backed_skills` (L870-884) shells out to
`gh skill update --dir <skills_root> --all` and then returns a literal:

```python
run_gh_skill(args, runner=runner)
return SkillResult(
    name="gh-managed", source_type="github", status="delegated",
    message="delegated GitHub-backed skill updates to gh skill",
    changed=True, ...
)
```

`run_gh_skill` (L542-561) returns the `CompletedProcess` but the caller drops
it, so `gh`'s stdout — the only place per-skill outcomes exist — is discarded.

Downstream in `src/coga/skill_update.py`, `delegated` is in `UPDATED_STATUSES`
(L35) and `changed=True`, so `render_result_line` (L152-168) prints
`1 updated, 0 need follow-up` on **every** run by construction.
`FOLLOWUP_STATUSES` (`conflict`, `fetch-failed`, `skipped-local-adaptation`) is
unreachable for gh-backed skills: a per-skill failure inside the bulk `gh` call
is invisible unless `gh` itself exits non-zero. The module docstring's promise —
"reports the skills that could not be updated cleanly … so they surface as
follow-up work on the task blackboard" — is not met for any gh-backed skill.

The weekly consequence is a PR titled "Update Coga-managed skills" whose diff is
unexplained by the report that accompanies it, and a `0 need follow-up` tally
that is asserted rather than measured.

## What a fix has to do

1. Parse `gh skill update --all`'s output (or, if it has no machine-readable
   mode, call `gh skill update <ref>` per installed gh-backed skill) and emit
   one `SkillResult` **per installed skill**, carrying its real status —
   `updated` / `unchanged` / `fetch-failed` / `conflict` — instead of a single
   synthetic `gh-managed` row with `changed=True` hardcoded.
2. Make the per-skill statuses map onto the existing buckets in
   `skill_update.py` so a failed or conflicted skill lands in **Needs
   follow-up** and the `Result:` tally reflects what happened. Keep the
   unknown-status-falls-through-to-followup rule at
   `skill_update.classify_status`.
3. Stop presenting `bundled_refs - local_refs` as this repo's "skipped" skills.
   Either drop uninstalled bundled refs from the update report entirely, or
   report `bundled_refs & local_refs` (installed skills skipped *because* they
   are package-backed), which is what "skipped" means to a reader.
4. While touching the `--all` path, confirm `gh skill update --dir coga/skills
   --all` does not rewrite Coga's own first-party skills under `code/*`,
   `coga/*`, `direct/body`, and `_template` — those are repo source with no
   external provenance, and the bulk `--dir` invocation currently points at them.
5. Cover it in `tests/` with a fake runner: a gh update where one skill updates
   and one fails must yield a report naming both, a non-zero follow-up count,
   and no `gh-managed` row.

Related but distinct: Dream's finding 5 this run deferred a separate issue in
`coga/skills/google-agents-cli-workflow/SKILL.md` (it tells agents to refresh
the pack with `uvx google-agents-cli setup`, bypassing `coga skill update`
entirely) to PR #736's review. That is about the skill's own text; this ticket
is about the update command's reporting. They should not be merged into one
change.

---

Written by the `coga recurring` autofix loop from the sweep this
ticket's `run-log.md` records. The finding is an agent's
reading of that run, not a verified diagnosis: confirm it against
`run-log.md` before changing anything, and close the ticket
through the workflow's already-satisfied path if the problem was
transient or already fixed.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/796
branch: skill-update-per-skill
worktree: /home/n/Code/claude/coga-skill-update-per-skill

## Diagnosis (confirmed against run-log.md and gh v2.92.0 source)

- The run-log report is exactly what the ticket describes: one synthetic
  `gh-managed`/`delegated` row plus 14 `skipped-bundled` rows for refs that are
  `bundled_refs - local_refs` (never installed here). None of the 7 installed
  `google-agents-cli-*` skills is named. (`clarity`, the URL-backed skill,
  was installed 2026-09-08, after the 09-02 run, so its absence is expected.)
- `gh skill update` (v2.92.0, `pkg/cmd/skills/update/update.go`) has no
  `--json`. Per-skill outcomes exist only as lines: stdout `Updated <name>`;
  stderr `X Failed to update <name>: <err>`, `! Skipping <name>: <reason>`,
  `⊘ <name> is pinned to <v> (skipped)`, `! <name> has no GitHub metadata.
  Reinstall to enable updates`, `All skills are up to date.`. Up-to-date skills
  are never named individually. Exit is 1 (silent) when any update failed.
- In bulk mode, a repo whose ref fails to resolve prints one `Skipping <first>`
  line and silently skips every sibling skill from that repo — so parsing the
  bulk output cannot give a measured status per skill. Decision: invoke
  `gh skill update --dir <root> --all <ref>` once per installed gh-backed skill
  (the ticket's second option). Cost: N calls instead of one; the weekly job
  is not latency-sensitive and the per-skill status is measured, not asserted.
- gh identifies a gh-backed skill by `metadata.github-repo` in SKILL.md
  frontmatter (`internal/skills/source/source.go` `ParseMetadataRepo`). Coga
  will use the same marker to decide which installed skills to update via gh,
  instead of `_infer_non_coga_source_type`'s "github.com in the text" guess.
- Item 4 (first-party skills safe): `gh skill update --dir coga/skills --dry-run`
  run locally lists `_template`, `code/*`, `direct/body`, `coga/show`,
  `browser/*`, `clarity`, `marketing/write-post`, `anthropic/skill-creator` as
  "has no GitHub metadata. Reinstall to enable updates" and never touches them;
  gh only rewrites skills carrying `github-repo`. With per-skill invocation
  Coga never even names those to gh. Note gh scans only two directory levels,
  so `coga/<a>/<b>` skills are invisible to it either way.

## Implemented (commit 04b31874 on `skill-update-per-skill`)

- `src/coga/skill_manager.py`
  - `gh_skill_metadata(skill_dir)`: a skill is gh-backed iff its SKILL.md
    frontmatter `metadata` carries `github-repo` (gh's own marker). Replaces
    the "github.com appears in the text" guess for the update path.
  - `_update_gh_backed_skill(cfg, ref)`: runs `gh skill update --dir <root>
    --all <ref>` for one skill. `_update_gh_backed_skills` (bulk + synthetic
    `gh-managed` row) is gone.
  - `classify_gh_update_output(...)`: maps gh's per-skill lines to `updated`
    (changed=True) / `unchanged` / `fetch-failed` (Failed to update, Skipping:
    could not resolve / discover / invalid metadata) / `skipped-pinned`;
    anything unrecognised → `failed` with gh's raw output (falls into
    follow-up). Strips ANSI + gh's `! X ✓ ⊘ •` icons first. `details` carries
    command, returncode, stdout, stderr.
  - `update_skills --all`: one row per installed skill with a managed source —
    URL-backed (existing path), gh-backed (new per-skill path), or installed
    twin of a bundled ref (`skipped-bundled`). Uninstalled bundled refs get no
    row (ticket item 3, second option: report `bundled_refs & local_refs`).
  - Single-skill path uses the same helper (and now passes `--all`, which the
    old argv lacked — without it gh exits 1 "updates available; re-run with
    --all" non-interactively when an update exists). A skill with no managed
    source returns an `unmanaged` row instead of being sent to gh.
- `src/coga/skill_update.py`: `delegated` removed from `UPDATED_STATUSES`
  (now falls through to follow-up); `skipped-pinned` added to
  `SKIPPED_STATUSES`; docstring updated.
- Tests (`tests/test_skill_manager.py`, `tests/test_skill_update.py`):
  per-skill argv + row per skill; the ticket's item-5 regression (one updates,
  one fails → both named, `1 updated, 1 need follow-up`, no `gh-managed`,
  rendered through `skill_update.render_blackboard_report`); parametrized
  classifier over every gh line shape incl. forced colour; single-skill and
  `unmanaged` paths; installed-bundled-twin vs uninstalled-bundled-ref;
  `delegated` classifies as follow-up.
- Docs updated in the same commit: `recurring/skill-update/ticket.md`
  (packaged + live twin), `bootstrap/skill-update/SKILL.md`, `coga/cli`
  context, `coga/codebase` context (packaged + live twin). Twins verified
  byte-identical.
- Verification: `python -m pytest` → 2449 passed. Live smoke in the worktree:
  `coga skill update --all --json` → 21 rows: 7 `google-agents-cli-*`
  `unchanged` (gh queried each, ~10s total), 13 installed bundled twins
  `skipped-bundled`, `clarity` `skipped-local-adaptation`; working tree
  untouched. Branch rebased on `origin/main` (already current).

## Decisions

- Per-skill `gh skill update <ref>` over parsing one bulk call: gh has no
  `--json`; bulk output never names up-to-date skills and silently skips a
  repository's sibling skills after one resolve error, so only the per-skill
  call yields a *measured* status for every row. Cost is N gh calls (7 here,
  ~10s); the weekly job is not latency-sensitive.
- `delegated` dropped from the updated bucket rather than kept for
  compatibility: nothing emits it any more, and if something did, an asserted
  hand-off should read as follow-up, not as an update.
- Installed bundled twins (`code/*`, `coga/*`, `browser/*` in this repo) are
  reported `skipped-bundled` — the report is now an inventory of installed
  managed skills, which is what "skipped" means to a reader.

## Adjacent findings (not fixed here)

- `clarity` (URL-backed) reports `skipped-local-adaptation` on a clean
  checkout: on-disk tree differs from its recorded `installed_tree_digest`.
  That is a standing follow-up row for every weekly run until someone
  re-records the digest or reinstalls — exactly the steady-state the
  `recurring/skill-update` ticket template warns against. Pre-existing.
- ~~`status_skills` still uses `_infer_non_coga_source_type`~~ — fixed in
  self-QA (`b8bfb8bf`): `status_skills` now shares `gh_skill_repo`, so
  `coga skill status` labels only skills carrying `metadata.github-repo` as
  gh-managed. See `## Self-QA`.
- `gh skill update --dir` scans only two directory levels
  (`scanInstalledSkills`), so a gh-backed skill at `coga/<a>/<b>` would be
  invisible to it. None exist today; the per-skill call would report it as
  `failed` ("none of the specified skills are installed") rather than hide it.

## Self-QA

- Reviews **returned** before the bump. `/code-review` (default effort,
  forked slash command) ran against `skill-update-per-skill` vs `main` and
  returned five findings (1 medium, 4 low), all applied. `/simplify` ran as
  four parallel review agents (reuse / simplification / efficiency /
  altitude) and returned; findings deduped and applied except two noted
  below. No review is in flight.
- `/code-review` fixes, in `b8bfb8bf`:
  1. (medium) `ensure_gh_skill` ran only when the loop reached the first
     gh-backed dir, after URL-backed skills (`clarity/` sorts before
     `google-*/`) were already rewritten — a host without `gh skill` would
     have died mid-run with uncommitted skill edits. The probe now runs once,
     before any updater writes.
  2. Single-skill `coga skill update code/x` on an installed bundled twin
     reported `unmanaged` + "reinstall"; now `skipped-bundled` like `--all`.
  3. `failed` fallback embedded gh's multi-line output in `message`, which
     the PR body and blackboard render as one bullet; now first line only,
     full output stays in `details`.
  4. Installed-twin `skipped-bundled` said `pip install --upgrade coga`,
     which cannot change a repo copy that shadows the package; reworded.
  5. Nested gh-backed refs: **verified on gh 2.92.0** in the scratchpad that
     `gh skill update --dir d --force --all ns/x` deletes `d/ns/x` and
     reinstalls `d/x`, printing `Updated ns/x`, exit 0. Coga now refuses
     `ns/x` as `failed` before calling gh (no probe either). Test fixtures
     that modelled nested gh-backed skills were flattened — `coga skill
     install` always lands them flat.
- `/simplify` applied: one classifier `_managed_update_source` (url / github
  / bundled / None) + one dispatch `_run_planned_updates` for both paths
  (`checked=` gone); `run_gh_skill(check=False)` instead of a copied
  prelude; `gh_skill_metadata` → `gh_skill_repo` (returns the repo string);
  `status_skills` now uses the same predicate, retiring
  `_infer_non_coga_source_type` (three of four agents flagged the two
  disagreeing "is gh-backed" definitions; `coga skill status` no longer
  labels first-party `code/open-pr` as gh-managed); `coga/text.py`
  `strip_ansi` shared by `skill_manager` and `recurring_autofix` (2
  consumers, microkernel rule); classifier `Updated` branch simplified;
  test helpers deduped. Docs: `coga/cli` + `coga/codebase` contexts follow.
- `/simplify` skipped (noted, not argued): report installed twins as
  `local-override` instead of `skipped-bundled` — the ticket already chose
  the `skipped-bundled` vocabulary and docs say so; and carrying the parsed
  `.coga-source.json` through the plan tuple to avoid a second tiny read.
- Verification: `python -m pytest` → 2452 passed (worktree, via
  `PYTHONPATH=src` and the primary `.venv`, the shell's default python is
  3.9). Smoke in the worktree: `coga skill update --all --json` still 7
  `google-agents-cli-*` gh-queried rows + 13 `skipped-bundled` + `clarity`;
  `coga skill status --json` now 7 `delegated` (exactly the gh-backed
  ones), first-party skills `unmanaged`/`local-override`. Working tree
  clean; twins byte-identical (`tests/test_packaging.py` green on branch).

### Needs the human's eye: `main` is red on `test_packaging` until this PR merges

The smoke run above was made with the live `coga/contexts/coga/codebase/
SKILL.md` edit still uncommitted in the worktree. Coga's state sync treats
every uncommitted `coga/` file as task state and committed it as
`Sync coga state` — on the branch (`d7a7edac`, fine) **and on `main`
(`74692b23`), pushed to `origin/main`**, then merged main into the branch
(`c121aac5`). `main` now carries the new live context ahead of its packaged
twin, so `tests/test_packaging.py::test_live_and_packaged_copies_stay_identical`
fails there. Doc-only; the code on `main` is unchanged.

- I tried `git revert 74692b23` on `main`; the auto-mode permission
  classifier denied it (shared-resource change), so `main` is left as is.
- **Merging this PR fixes it** (the packaged twin arrives). Branch and
  `main` hold identical content for that file, so the merge loses nothing.
- If you'd rather fix `main` first: revert `74692b23` on `main`, then merge
  `main` into the branch **and re-apply the branch's version of the file**
  — a bare revert + merge would make the PR side match the merge base and
  the doc change would silently drop out at PR merge.
- Recorded as a gotcha in `code/self-qa` (both twins, in `b8bfb8bf`).

## PR step

- `coga open-pr` run from the primary control checkout (on `main`); the
  worktree was clean on `skill-update-per-skill`, 4 commits ahead of
  `origin/main`. Opened https://github.com/FastJVM/coga/pull/796 and recorded
  `pr:` under `## Dev`.
- The command's `[git] sync refused` line named
  `coga/tasks/dream-findings-have-three-routing-holes-that-lose.md` — another
  ticket's uncommitted drift in the shared checkout, left untouched per the
  step's "never commit another ticket's drift" rule. Nothing about this PR
  was affected.
- Reminder for the merge step: `main` is red on `test_packaging` until #796
  merges (see `## Self-QA`); the branch carries the packaged twin that fixes it.
