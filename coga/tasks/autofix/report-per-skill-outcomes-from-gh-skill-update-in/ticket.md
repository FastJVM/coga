---
slug: autofix/report-per-skill-outcomes-from-gh-skill-update-in
title: Report per-skill outcomes from gh skill update in skill-update
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
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
secrets: null
step: 1 (implement)
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
