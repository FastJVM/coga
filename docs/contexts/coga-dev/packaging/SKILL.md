---
name: coga-dev/packaging
description: Authoring Coga's packaged resources, enforcing user versus local-only Coga-dev contexts, canonical twins, and wheel contents, including the README as the PyPI long description.
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

## Canonical copies and twins

The audience criterion belongs to
[context layout](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/context-layout/SKILL.md#context-audiences): user
topics are required to operate shipped surfaces; Coga-dev topics explain
developing Coga itself. Only the user set ships. The entire `coga-dev/`
namespace is local-only, including its supporting files. A new development
topic needs no per-topic packaging exception.

This repo's canonical contexts live under its configured root, `docs/contexts/`
(`[layout] contexts` in `coga/coga.toml`). Packaged contexts map to canonical
files as follows; the starter `contexts/_template/SKILL.md` is package-only
scaffolding and has no docs twin:

```text
templates/coga/bootstrap/contexts/<ref>/SKILL.md -> docs/contexts/<ref>/SKILL.md
templates/coga/contexts/<path>                   -> docs/contexts/<path>
templates/coga/<path>                            -> coga/<path>
templates/coga/bootstrap/{skills,workflows}/<p>  -> coga/{skills,workflows}/<p>
```

**The package is the single committed owner of every shipped definition**
([v1/package-definitions](https://github.com/FastJVM/coga/blob/main/coga/tasks/v1/package-definitions/README.md)).
The live copies this repo still carries are transitional legacy counterparts
that stage B removes or converts. `tests/test_packaging.py` derives the pairs
above from the packaged tree and applies the stage A policy:

- **Pinned inventory.** `tests/legacy_removal_inventory.txt` lists every
  legacy live copy with its package owner. A derived counterpart missing from
  it (and not one of `SCAFFOLD_COUNTERPARTS`: `coga.toml`, `context.md`,
  `log.md`, `.gitattributes`, the two `.gitignore` files) fails, even when
  byte-identical, so the allowance cannot grow. Every inventory entry's
  package owner must exist, so deleting both copies is never a vacuous pass;
  there is no pair-count floor.
- **Optional, but compared while present.** A present legacy copy must equal
  its owner. A recurring parent ticket compares only the text above its
  blackboard fence; the blackboard is repo state. A reviewed difference goes in
  `LEGACY_DEFINITION_DIFFERENCES`, pinning the unchanged live definition's
  sha256 and the reason: stage A edits packaged recurring definitions only
  and never touches live ones (the sweep could publish them ahead of the
  code). Scaffold divergences stay in `INTENTIONALLY_DIVERGENT_TWINS`.
  A marked recurring state carrier is checked with `inspect_parent_dir`
  instead of compared with the definition: malformed headers and leftover
  definition siblings still fail. Phone-home's complete state remains
  parseable and the packaged seed stays unused.
- **Contexts.** A canonical copy under `docs/contexts/coga/` is optional;
  required bootstrap refs (`REQUIRED_BOOTSTRAP_CONTEXT_REFS`), the
  init-seeded files, the classification of every canonical topic and the
  local-only prohibition still apply.
- **Navigation.** Links resolve where each file actually lives (package files
  inside the package tree). A surviving source, anything not in the
  inventory, must link the package owner rather than a removable legacy copy.

Development files are rejected in either packaged context tree, including a
namespace accidentally added to the required bootstrap list or built wheel,
and shipped guidance may not require a local-only reference; optional absolute
GitHub links may expose implementation detail. Resolution and repo overrides are owned by
[context layout](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/context-layout/SKILL.md); edge shims and forks by
[edge code](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/SKILL.md).
Discovery skips `.coga/`, `.venv/`, `.agent-skills/`, `.claude/`, `.codex/`,
bytecode caches, and `coga.local.toml`. This repo overrides
`coga/bootstrap/resolve-conflicts/ticket.md` and
`coga/bootstrap/address-pr-comments/ticket.md` with identical copies; they are
inventoried legacy copies like the rest. Packaged batteries with no live
counterpart (`bootstrap/orient/`, `tasks/coga-build.md`) are not pairs;
`EXPECTED_BOOTSTRAP_RESOURCES` keeps them shipping. The Coga repo root keeps only `AGENTS.md`, which Claude Code reads
when no `CLAUDE.md` or `CLAUDE.local.md` exists (see `coga/init`); do not
add a root `CLAUDE.md` copy.

Shipped recurring definitions live together at
`templates/coga/recurring/<name>/` and resolve from the package through the
recurring catalog (`recurring.iter_template_sources`, selection in a repo's
`recurring/jobs.toml`); a repo keeps only its state carrier. Edit the package
copy. Downstream and promoted templates are local definitions. A
packaged template leaves `owner:` and `agent:` empty so each installing repo's
defaults apply: an explicit `agent: claude` blocked period creation in a
Codex-only repo even with a launch override (PR #857 review);
`tests/test_recurring.py::test_address_pr_comments_period_inherits_repository_routing`
pins the inherited routing. A job that force-pushes a reused branch must
lease against a remote tip it read live (`git ls-remote` on the push URL)
rather than a possibly stale tracking ref. `src/coga/skill_manager.py` reads it
in its pre-update branch guard and leases against that observed tip, so a hand
push after the check fails the lease; see
[coga/skill-management](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/skill-management/SKILL.md).

Hazards:

- **A rebase carries a fix through a rename, never into a twin created fresh
  in the same commit.** A fix once reached the live copy but not the new
  packaged one; rebase and suite both looked green. After any rebase touching
  a pair, re-diff every pair by hand.
- **Fan-out follow-ups that each rewrite one shared passage conflict
  pairwise, doubled by the twin.** Have the spawning ticket rewrite the
  passage once first, serialize the follow-ups, or give each its own
  sub-bullet.

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
