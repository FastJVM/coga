---
title: Skill update
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: a0eda568-89ea-40d5-ba49-facfaed9c8ab
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
Attribution for such a skill is a human-readable file beside its `SKILL.md`,
not `.coga-source.json`. In Coga's own source checkout, the hand-vendored
`anthropic/skill-creator` carries `ATTRIBUTION.md` (pinning `anthropics/skills`
at `f458cee3`); that directory is not part of the package, so it exists only
where an operator vendored it. The package-backed `browser/playwright` skill
ships `NOTICE.txt` (naming `microsoft/playwright-cli` as the source of its
adapted material) in the installed package's `bootstrap/skills/browser/playwright/`;
a repo that copies it as a `local-override` carries the same file under
`coga/skills/browser/playwright/`.
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

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Skill Update

Generated: 2026-09-21T18:23:54+00:00
Command: `/home/n/.local/share/uv/tools/coga/bin/python3 -m coga.cli skill update --all --json --pr --pr-title 'Update Coga-managed skills'`
Task: `recurring/skill-update`

Result: 21 skill(s): 7 updated, 1 need follow-up, 13 skipped.
PR: https://github.com/FastJVM/coga/pull/858

### Updated

- `google-agents-cli-adk-code`: `updated` (github) - updated by gh skill (google/agents-cli) 00142fd8 > cc35b572 [v1.6.1]
- `google-agents-cli-deploy`: `updated` (github) - updated by gh skill (google/agents-cli) 6b6b0faf > 2696cf28 [v1.6.1]
- `google-agents-cli-eval`: `updated` (github) - updated by gh skill (google/agents-cli) 59e41b2c > 22bc3ed6 [v1.6.1]
- `google-agents-cli-observability`: `updated` (github) - updated by gh skill (google/agents-cli) e8493914 > 29f110ed [v1.6.1]
- `google-agents-cli-publish`: `updated` (github) - updated by gh skill (google/agents-cli) f7ba039f > cc618b10 [v1.6.1]
- `google-agents-cli-scaffold`: `updated` (github) - updated by gh skill (google/agents-cli) de88682a > 195988f1 [v1.6.1]
- `google-agents-cli-workflow`: `updated` (github) - updated by gh skill (google/agents-cli) 0251db1f > d3c52221 [v1.6.1]

### Needs follow-up

- `clarity`: `skipped-local-adaptation` (url) - local files differ from recorded installed digest; upstream digest unchanged; not overwriting

### Skipped

- `browser/dochub`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `browser/playwright`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `code/address-pr-comments`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `code/design`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `code/implement`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `code/open-pr`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `code/review-design`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `code/self-qa`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `coga/autoclose/sweep`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `coga/blockers/remind`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `coga/branch-sweep/sweep`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `coga/show`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
- `coga/ticket/finalize`: `skipped-bundled` (bundled) - repo copy of a package-bundled skill; it shadows the packaged copy and is maintained in this repo, so `coga skill update` leaves it alone
