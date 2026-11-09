---
name: coga-dev/packaging
description: Authoring Coga's packaged resources, enforcing user versus local-only Coga-dev contexts, single-source ownership, and wheel contents, including the README as the PyPI long description.
---

# Packaging Coga's resources

## Where bundled resources live

Bundled skills, contexts, reusable workflows, and command tickets are authored
under `src/coga/resources/templates/coga/bootstrap/`. Runtime resolvers
(`paths.resolve_context_path`, `resolve_skill_path`, `resolve_workflow_path`,
`tasks.resolve_bootstrap`) check the repo first and then read the package; no
`coga/bootstrap/` mirror is materialized. Optional domain skills are not
packaged; operators install them with `coga skill install`
([coga/skill-management](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/skill-management/SKILL.md)).

**Local-first also applies to this repo.** A live `coga/<kind>/<name>`
shadows the packaged copy; where none exists, the packaged file is what this
repo resolves and freezes. This repo has no live `coga/workflows/code/`, so
editing `bootstrap/workflows/code/*.md` changes what `mark_active` freezes into
Coga's own tickets. Check which side is live before assuming an edit is
downstream-only.

## Distribution states for a context

- **Bootstrap fallback**: `templates/coga/bootstrap/contexts/<ref>/SKILL.md`
  (every `coga/*` topic). `coga init` skips `bootstrap/`;
  `paths.resolve_context_path` reads the package copy
  (`bootstrap_context_path`) when the repo has no local `<ref>/SKILL.md`.
- **Init-seeded**: `templates/coga/contexts/**`, today only the scaffolds
  `.gitignore` and `_template/SKILL.md`. `commands/update.py`
  `copy_fresh_templates` copies only the reviewed `FRESH_SCAFFOLDS`
  allowlist once; nothing reads the packaged original at runtime.
- **Local-only**: no packaged copy, resolved first and unknown to other repos
  (a repo's `product/` topics, or this repo's `coga-dev/` set).

Resolution is local, then `bootstrap/contexts/`, then `None`, which `compose`
turns into a `ComposeError`. Skills and workflows have the same split:
fallback only from `bootstrap/{skills,workflows}/`. Every reusable workflow
and skill, including `direct/body`, `build/onboarding` and the recurring
workflows, is now a bootstrap battery; `templates/coga/{skills,workflows}/`
hold only the ignored `_template` starters. A present but unusable local
override (`paths.local_definition_entry`) raises `LocalOverrideError` rather
than selecting the packaged copy.

**Bundled launchers may only name fallback contexts.** A bundled
`bootstrap/<verb>/ticket.md`, or a bundled skill that tells the agent to apply
a context, must name contexts that resolve from `bootstrap/contexts/`, because
an init-seeded copy may be pruned or predate the repo.
`tests/test_packaging.py::test_bundled_bootstrap_tickets_attach_only_bootstrap_contexts`
enforces this.

## Package ownership and repo state

The audience criterion belongs to
[context layout](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/context-layout/SKILL.md#context-audiences):
user topics operate shipped surfaces; Coga-dev topics explain developing Coga.
The complete `coga-dev/` namespace, including attachments, stays local. A
shipped surface may not require it; optional development navigation uses an
absolute GitHub link.

Every shipped definition has one committed owner under `src/coga/resources/`.
This repo has completed its cutover: user topics live only in package
`bootstrap/contexts/`, reusable skills/workflows in `bootstrap/{skills,workflows}/`,
and recurring definitions with their scripts/runbooks in `recurring/<name>/`.
Indexes link directly to those owners. The configured `docs/contexts/` root
holds local Coga-dev knowledge. There are no forwarding files or symlink mirrors.

`tests/test_packaging.py` owns the executable inventory:

- `_discover_live_packaged_twins()` derives every possible counterpart from
  the actual package tree, including top-level prompt overrides and both
  ordinary and obsolete bootstrap locations. `_ownership_problems()` rejects
  every unapproved counterpart, even byte-identical files.
- `tests/required_package_resources.txt` independently pins required package
  files. Removing both an owner and a local copy cannot make the test pass;
  new/retired resources need a deliberate manifest update. Bootstrap context
  refs remain pinned separately by `REQUIRED_BOOTSTRAP_CONTEXT_REFS`.
- `SCAFFOLD_COUNTERPARTS` explains required physical configuration, context,
  audit log, attribute and ignore files. `INTENTIONALLY_DIVERGENT_TWINS`
  explains actual differences from their seeds. This repo has not adopted
  trim-log, so its physical log attribute remains unchanged until that
  separate explicit adoption; removing definitions does not select the job.
- `STATE_CARRIER_COUNTERPARTS` explains saved recurring parent blackboards.
  `inspect_parent_dir` requires the exact carrier shape and rejects leftover
  definition siblings. Arbitrary blackboard notes remain state even without
  declared `state_keys`; phone-home's complete cursor is independently parsed.
- `LOCAL_DEFINITION_OVERRIDES` requires a reason for every retained definition
  counterpart. It is currently empty. An ambiguous customization is retained
  for owner review, never silently deleted. All exception entries must name
  real current files; stale reasons fail. Repo-only jobs and attachments have
  no packaged counterpart and stay local.
- Authoring starters may exist only as ignored, untracked materializations.
  `.coga/`, `.venv/`, generated agent views, bytecode caches and local config
  are machine-local artifacts outside the definition inventory.
- Navigation reads actual package-relative links and inbound links from local
  development topics, repo-authored skills/workflows/jobs, indexes and release
  notes. Frozen task histories and archives are excluded; archives are never
  read by the check.

The generic migration and rollback contract belongs to
[the recurring runbook](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/package-definitions-migration.md).
Its source-repo rehearsal retained every parent blackboard, worklist, frozen
period, custom job and clone ledger. Publication continues to use the ordinary
state roots and guards. Package edits are outside those roots; deliberately
reviewed local knowledge edits must still be committed before a sweeping CLI
command. See [state publication](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md).

A packaged recurring template leaves `owner:` and `agent:` empty so each
adopting repo's defaults apply; `test_recurring` pins that routing. A local
full fork owns all its siblings, while a carrier reads the package's definition.
The Coga repo keeps only root `AGENTS.md`; Claude Code reads it when no
`CLAUDE.md` or `CLAUDE.local.md` exists. Do not recreate a second root guide.

## Wheel packaging

`[tool.hatch.build.targets.wheel]` in `pyproject.toml` walks
`packages = ["src/coga", "src/coga_edge"]` and force-includes pure-data trees. Hatchling's walk
silently drops no-`.py` skill directories, so `bootstrap/` and
`skills/_template` are excluded from the walk and force-included as their
single shipper. A walk and a force-include of the same file abort the build
("A second file is being added to the wheel archive at the same path").

This fails only on a pristine tree: in a dev tree, gitignored agent symlink
views under the templates tree dedup the collision away. The wheel tests
therefore build from a pristine copy of the tracked files
(`test_packaging._pristine_source`), assert no archive path ships twice, and
smoke-test the installed, read-only artifact outside the source tree.
Build artifacts (`.coga/`, `.venv/`, `__pycache__/`) are excluded so a dirty
tree cannot ship a stale venv into every `coga init`.

`README.md` is also the package's PyPI long description
(`readme = "README.md"` in `pyproject.toml`). PyPI does not resolve relative
links, so every README link must be an absolute GitHub URL: `blob/main/...`
for files and `tree/main/...` for directories. Done tickets are retired, so
link evidence such as a ticket file or a `coga/log.md` excerpt at a commit
(`blob/<sha>/...`), not at `main`.
