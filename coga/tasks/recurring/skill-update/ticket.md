---
title: Skill update
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: 86a53d09-5601-40ce-8f8a-fedc3c29caae
workflow:
  name: skill-update/run
  steps:
  - name: update
    skills:
    - bootstrap/skill-update
    assignee: agent
---

## Description

Update every clean remotely managed GitHub/URL skill in one reviewable PR.

Imported skills live as plain directories under `coga/skills/`. GitHub-backed
installs are tracked by `gh skill`'s own metadata. URL-installed skills instead
carry Coga's `.coga-source.json` provenance with `source_type = "url"`.
`coga skill install-local` is a third supported installation path: `gh skill`
records `local-path`, but its updater skips that directory because it has no
GitHub source metadata, and Coga's URL updater does not consume it. Hand-vendored
packs likewise have no managed update source. A freshly initialized repo
attempts to install the optional GitHub refs declared in `managed-skills.toml`,
but installation may be skipped or fail and operators may add any source shape
later. Once a week this ticket fires on its schedule and its `ticket.py` runs
`coga skill update --all --pr`, which:

1. delegates the installed GitHub-backed skills to `gh skill update --dir
   coga/skills --all`, then walks in Coga's own code every skill carrying
   `.coga-source.json` with `source_type = "url"`; local-backed and
   hand-vendored directories are outside both updater paths,
2. for URL-backed skills, rewrites in place only when the upstream digest
   changed and the local copy is unmodified; the delegated GitHub updater
   follows its own stored-tree-SHA policy,
3. commits the clean updates onto the dedicated `coga/skill-update` branch
   and opens (or updates) one draft PR, and
4. appends a `## Skill Update` report to this period task's blackboard,
   bucketing every result emitted by the GitHub, URL, and bundled paths.

Local-edit protection applies to URL-backed skills: a diverged local copy,
provenance conflict, or fetch failure is left untouched and listed under the
report's follow-up heading for a human to resolve.

**A recorded `include` allowlist is not a divergence.** When a URL skill's
`.coga-source.json` carries an `include` list, that names the subset of upstream
this repo installs. The update re-applies it to each fetched archive before the
tree lands, so the pruning is reproduced rather than reported: `source_tree_digest`
stays the true unpruned upstream digest (so upstream-change detection still
works) while `installed_tree_digest` describes the pruned tree on disk. A pruned
skill therefore reads as `unchanged` or `updated`, not as a standing follow-up.
Edits *beyond* the allowlist are still real divergence and still conflict. A
digest recorded before the allowlist was honored is repaired in place on the
next run, and that repair counts as a change so `--pr` commits it. GitHub-backed directories
are upstream-owned by `gh skill update`; when its recorded tree SHA differs
from upstream, re-downloading can overwrite local modifications before the
draft PR is opened. That PR reviews the resulting upstream update; it does not
recover overwritten edits. Do not keep local adaptations in those directories.
Local-backed installs are pinned until an operator reviews their source and
reinstalls explicitly. They currently produce no per-skill update result, so
the weekly report neither lists nor verifies them; omission is not evidence
that their source or installed bytes are current. Hand-vendored directories
have the same unmanaged update posture.
Bundled (package-backed) skills are not touched here — they refresh when the
coga package is upgraded.

A URL install that was pruned after download is a distinct shape, and the
protection above does not cover it. `install_url_skill` copies the whole
materialized tree; nothing in `src/coga/` reads an `include` allowlist, and
`_url_metadata` writes a fixed key set with no such field, so a hand-added
`include` list in `.coga-source.json` is inert documentation — the first
successful update rebuilds the metadata without it, while
`_local_adaptation_notes` carries the prose describing it forward. Pruning is
always a hand adaptation, and what the weekly run does with it depends entirely
on which digests were recorded. `_update_url_skill_dir` compares exactly two
things: the freshly downloaded `materialized.source_tree_digest` against the
recorded `source_tree_digest`, and `hash_skill_tree(skill_dir)` against the
recorded `installed_tree_digest`. Record the pruned tree's digest as
`installed_tree_digest` and the run reads the skill as unmodified; record it as
`source_tree_digest` as well and the upstream comparison can never match, so the
run takes the `_replace_skill_tree` branch, restores every pruned path, drops
the `include` key, and reports `updated` — the un-pruning lands in the draft PR
as an ordinary upstream refresh, under the report's updated heading with no
follow-up line. Record the digests honestly instead — both taken from the
download — and the pruned copy reads as locally adapted forever:
`skipped-local-adaptation` while upstream is quiet, `conflict` when it moves,
parked under the follow-up heading on every run.

The first case is the one to check for: a skill whose recorded
`source_tree_digest` is the digest of the pruned tree on disk rather than of any
upstream tree. Compare each URL-installed skill's recorded `source_tree_digest`
against a fresh download to tell them apart.

Neither shape is a steady state — the follow-up heading is for exceptions a
human resolves, and the updated heading is for changes a human reviewed. The
resolution has to actually clear the follow-up. Implement the `include`
allowlist in the URL install and update path so the pruning is re-applied from
each fetched archive, keeping `source_tree_digest` the true upstream digest and
re-recording `installed_tree_digest` from the pruned result; that is a code
change and needs its own ticket. **Do not simply accept a standing follow-up
line as the price of keeping the local edit** — see the cost below. If the
allowlist is not implemented, drop it and the claim in
`local_adaptation_notes`, and resolve the pruning some way that leaves no
recurring follow-up: re-record the digests to match the tree actually on disk,
or reinstall the skill unpruned.

A week with no upstream changes is a quiet no-op: nothing is committed and no
PR is opened. Two non-zero exit codes keep a run visible. Each writes the
`## Skill Update` report before exiting, but that write is best-effort — an
unwritable blackboard leaves the exit code as the only signal:

- **Exit 1 — follow-ups to resolve.** Every skill was classified, but some
  need human follow-up and no PR was opened to carry them, so the period task
  stays visible until a human resolves or parks it. `--pr` mode only: under
  `--no-pr`, a run full of follow-ups still exits 0.
- **Exit 2 — the update failed.** `coga skill update` exited non-zero, or
  emitted output that was not valid JSON, so nothing was classified. The report
  carries the attempted command and the failing output under a `### Failed`
  heading in place of the per-skill buckets.

Exit 2 has a second source: `ticket.py` passes through `coga bump`'s exit code
once the update succeeds, and `coga bump` exits 2 on most of its own refusals.
An exit 2 whose report has the per-skill buckets and no `### Failed` block is a
failed bump, not a failed update.

**Do not treat a standing exit 1 as a steady state.** `ticket.py` exits before
it reaches `coga bump`, so the period task is left unfinished — and until the
tracked fix lands, the recurring runner treats a non-zero `ticket.py` as a
sweep-ending failure, returning that code instead of continuing. Every template
ordered after `skill-update` is then skipped for that period, so a permanently
unresolved follow-up silently disables the rest of the recurring schedule week
after week. Resolve it or park the template rather than living with it, even
once the sweep stops being starved.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Skill Update

Generated: 2026-09-14T18:55:32+00:00
Command: `/home/n/.local/share/uv/tools/coga/bin/python -m coga.cli skill update --all --json --pr --pr-title 'Update Coga-managed skills'`
Task: `recurring/skill-update`

Result: 16 skill(s): 1 updated, 0 need follow-up, 15 skipped.
PR: none opened — no clean skill updates to commit.

### Updated

- `gh-managed`: `delegated` (github) - delegated GitHub-backed skill updates to gh skill

### Skipped

- `bootstrap/delete-task`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/dream/scan/contract-audit`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/dream/scan/knowledge-scan`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/dream/scan/scan-protocol`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/dream/tasks/cleanup-orphan-markers`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/dream/tasks/validate-drift`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/import`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/skill-update`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/ticket`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `browser/build-automation`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `coga/calendar-reminder`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `coga/gmail`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `coga/google-calendar`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `retro/done-ticket`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `clarity`: `unchanged` (url) - upstream digest unchanged
