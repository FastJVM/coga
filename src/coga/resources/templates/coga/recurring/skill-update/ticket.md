---
schedule: "0 9 * * 1"
schedule_comment: "Every Monday at 9am — update remotely managed GitHub/URL skills into one reviewable PR"
title: "Skill update"
# The reserved `ticket.py` sibling is this task's deterministic half: `coga
# launch` runs it directly, with no agent and no composed prompt. The one-step
# workflow keeps the period task's lifecycle and skill contract legible.
workflow: skill-update/run
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

1. walks every installed skill under `coga/skills/`: a skill whose
   `SKILL.md` frontmatter carries `gh skill`'s `metadata.github-repo` is
   GitHub-backed and gets its own `gh skill update --dir coga/skills --all
   <ref>` call; a skill carrying `.coga-source.json` with
   `source_type = "url"` goes through Coga's own URL updater; an installed
   twin of a package-bundled skill is reported `skipped-bundled`; local-backed
   and hand-vendored directories are outside every updater path,
2. for URL-backed skills, rewrites in place only when the upstream digest
   changed and the local copy is unmodified; the GitHub updater follows
   `gh skill`'s own stored-tree-SHA policy, and each of its skills reports
   what `gh` actually did — `updated`, `unchanged`, `fetch-failed`, or
   `skipped-pinned` — rather than one hardcoded hand-off row,
3. commits the clean updates onto the dedicated `coga/skill-update` branch
   and opens (or updates) one draft PR, and
4. appends a `## Skill Update` report to this period task's blackboard with
   one row per installed managed skill, bucketed by its emitted status.
   Bundled refs this repo never installed are not its skills and get no row.

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
digest recorded before the allowlist was honored is repaired only when the
downloaded, pruned upstream tree matches the installed files. That repair counts
as a change so `--pr` commits it; if retained upstream files changed first,
the updater reports a conflict requiring manual reconciliation. GitHub-backed directories
are upstream-owned by `gh skill update`; when its recorded tree SHA differs
from upstream, re-downloading can overwrite local modifications before the
draft PR is opened. That PR reviews the resulting upstream update; it does not
recover overwritten edits. Do not keep local adaptations in those directories.
Local-backed installs are pinned until an operator reviews their source and
reinstalls explicitly. They currently produce no per-skill update result, so
the weekly report neither lists nor verifies them; omission is not evidence
that their source or installed bytes are current. Hand-vendored directories
have the same unmanaged update posture.
Human-readable attribution for hand-vendored `anthropic/skill-creator` lives in
`coga/skills/anthropic/skill-creator/ATTRIBUTION.md`, pinning `anthropics/skills`
at `f458cee3`; the separate package-backed `browser/playwright` `local-override`
carries `coga/skills/browser/playwright/NOTICE.txt`, naming
`microsoft/playwright-cli` as the source of its adapted material.
Bundled (package-backed) skills are not touched here — they refresh when the
coga package is upgraded.

Another shape the allowlist protection does not cover is a URL skill whose
`.coga-source.json` carries **no** `include` key while its
`local_adaptation_notes` still describe a prune (a refresh that ran on code
predating the allowlist re-expands the tree and drops the key, as happened to
`clarity`). The updater then reads the full tree as the honest install and
never re-prunes, so the skill reports `unchanged` week after week. Treat
"notes describe a prune but no `include` is recorded" as a follow-up line,
not as clean: restore the reviewed `include` list and explicitly prune the
installed tree to that list, preserving its provenance and any local edits for
reconciliation. Then re-run `coga skill update <name>`. Restoring the key alone
can return `unchanged` before applying the allowlist. After pruning, the updater
repairs `installed_tree_digest` only if the freshly fetched, pruned upstream
matches the installed files; otherwise reconcile the reported conflict rather
than discarding local changes. **Do not simply accept a standing follow-up line as
the price of keeping the local edit** — see the cost below.

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
it reaches `coga bump`, so the period task is left unfinished and `in_progress`.
The recurring runner records that failure and keeps sweeping — the templates
ordered after `skill-update` still run for the period — but the sweep exits
non-zero and names this template in every sweep summary and run record until
the follow-up is resolved or the template is parked. Resolve it or park the
template rather than living with it.

<!-- coga:blackboard -->

This blackboard persists across every run of this recurring task. Each period
task gets its own blackboard; the `skill-update` run appends its
`## Skill Update` report there, not here. This template keeps no durable state
— every run's output is the skill-update PR and the period task's report.
