---
name: coga/packaging
description: How Coga's packaged resources are authored, reach a repo (bootstrap fallback versus init-seeded), stay byte-identical to this repo's canonical copies, and ship in the wheel.
---

# Packaging Coga's resources

## Where bundled resources live

Bundled skills, contexts, reusable workflows, and command tickets are authored
under `src/coga/resources/templates/coga/bootstrap/`. Runtime resolvers
(`paths.resolve_context_path`, `resolve_skill_path`, `resolve_workflow_path`,
`tasks.resolve_bootstrap`) check the repo first and then read the package; no
`coga/bootstrap/` mirror is materialized. Optional domain skills are not
packaged; operators install them with `coga skill install`
([coga/skill-management](../skill-management/SKILL.md)).

**Local-first also applies to this repo.** A live `coga/<kind>/<name>`
shadows the packaged copy; where none exists, the packaged file is what this
repo resolves and freezes. This repo has no live `coga/workflows/code/`, so
editing `bootstrap/workflows/code/*.md` changes what `mark_active` freezes into
Coga's own tickets. Check which side is live before assuming an edit is
downstream-only.

## Three distribution states for a context

- **Bootstrap fallback**: `templates/coga/bootstrap/contexts/<ref>/SKILL.md`
  (`coga/*` bootstrap topics, `dev/*`, `browser/*`). `coga init` skips
  `bootstrap/`; `resolve_context_path` reads the package copy when the repo has
  no local `<ref>/SKILL.md`. A repo overrides by creating the local file.
- **Init-seeded**: `templates/coga/contexts/**`, today only the scaffolds
  `.gitignore` and `_template/SKILL.md`. `commands/update.py`
  `copy_fresh_templates` copies them once; the repo then owns them and nothing
  reads the packaged original at runtime.
- **Local-only**: a topic with no packaged copy, resolved first and unknown to
  other repos (for example `product/`, `marketing/`, `coga/current-direction`).

Resolution is local, then `bootstrap/contexts/`, then `None`, which `compose`
turns into a `ComposeError`; `validate` and `create` reject the ref
statically. Skills and workflows have the same split: fallback only from
`bootstrap/{skills,workflows}/`, while seeded `templates/coga/{skills,workflows}/`
files are one-time copies.

**Bundled launchers may only name fallback contexts.** A bundled
`bootstrap/<verb>/ticket.md`, or a bundled skill that tells the agent to apply
a context, must name contexts that resolve from `bootstrap/contexts/`, because
an init-seeded copy may be pruned or predate the repo.
`tests/test_packaging.py::test_bundled_bootstrap_tickets_attach_only_bootstrap_contexts`
enforces this.

**Do not repair a missing bundled resource by copying it into
`coga/bootstrap/`.** Fix package data or the resolver; a mirror hides the bug
and drifts. Deliberate authoring there is fine: a repo mints its own command
ticket or intentionally overrides a shipped one. This repo overrides
`coga/bootstrap/resolve-conflicts/ticket.md` and
`coga/bootstrap/address-pr-comments/ticket.md`; those are twins like any other.

## Canonical copies and twins

This repo's canonical contexts live under its configured root, `docs/contexts/`
(`[layout] contexts` in `coga/coga.toml`). Each packaged context pairs with
exactly one canonical file:

```text
templates/coga/bootstrap/contexts/<ref>/SKILL.md -> docs/contexts/<ref>/SKILL.md
templates/coga/contexts/<path>                   -> docs/contexts/<path>
templates/coga/<path>                            -> coga/<path>
templates/coga/bootstrap/{skills,workflows}/<p>  -> coga/{skills,workflows}/<p>
```

`tests/test_packaging.py` derives the pairs from the packaged tree (nothing to
register) and requires byte-identity. For contexts it is stricter than for
other areas: every packaged context file must have its canonical counterpart,
every canonical topic must be classified as bootstrap, init-seeded, or in an
explicit local-only exception set, and `REQUIRED_BOOTSTRAP_CONTEXT_REFS`
fails the suite if a required bootstrap topic disappears from both trees.
Discovery skips `.coga/`, `.venv/`, `.agent-skills/`, `.claude/`, `.codex/`,
bytecode caches, and `coga.local.toml`. A deliberate difference goes in
`INTENTIONALLY_DIVERGENT_TWINS` with its reason, and the suite fails once the
entry stops describing a real divergence. Packaged batteries with no live
counterpart (`bootstrap/orient/`, `bootstrap/workflows/` fallbacks,
`tasks/coga-build.md`) are not pairs; `EXPECTED_BOOTSTRAP_RESOURCES` keeps them
shipping. Root `CLAUDE.md` and `AGENTS.md` are a hand-kept twin outside the
test: edit both and `cmp` them.

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
views under the templates tree dedup the collision away. Verify packaging
changes against a fresh `git clone` or `git worktree` as well as a dev tree.
Build artifacts (`.coga/`, `.venv/`, `__pycache__/`) are excluded so a dirty
tree cannot ship a stale venv into every `coga init`.

## Wheel-owned edge implementations

`src/coga_edge/` ships beside `src/coga/` in the **same distribution**, with
one version and install transaction, no extra dependency, registry or CLI.
The one-way import boundary is owned by
[coga/extension-model](../extension-model/SKILL.md). `coga_edge/__init__.py`
has no eager job imports or side effects.

A repo-owned `ticket.py` may import a stable module `main` and return its exit
code. Init seeds that shim; recurring creation copies its bytes. On the next
process invocation it uses the installed implementation, even if the template
script later changes or disappears. The shim contains no job logic or duplicate
completion. A missing module is an ordinary script failure, never a fallback.
Installing a wheel does not discover or rewrite repositories. Legacy full
copies adopt the shim once through the
[reviewed migration procedure](edge-code-upgrades.md); until then they retain
their old code. Markdown, schedules, workflows and shim-contract changes still
need reviewed repo edits.

Ordinary Python attachments have the same shipping option: a worker has a
direct module entry point invoked explicitly by instructions, or a plain named
attachment shim. Only the reserved `ticket.py` participates in automatic
execution and recurring copying. There is no general dispatcher or additional
attachment discovery/copying.

Default period tasks freeze the shim, not its imported implementation. Retain
the exact wheel artifact/hash and repo revision for reproducibility; a version
string alone cannot distinguish unreleased main-branch builds. Running
processes are not promised hot upgrades.

### Explicit local forks

A full implementation replacing either template or period `ticket.py` is
repo-owned. New periods copy the template fork; existing periods retain their
own script. Neither installation nor launch overwrites, merges or bypasses it.
Editing a wrapper that still imports the default is not an implementation fork.
A fork stops receiving upstream fixes and must remain compatible with the
shared core it imports; restoring the stock shim rejoins wheel updates.

Phone-home's complete module is deliberately forkable: it imports only stdlib
and shared `coga.*`, never relative or sibling edge modules, and carries both
normal and private `--worker` dispatch behind `__main__`. Its worker executes
that same file, including when copied to a local fork. Preserve these constraints
when refactoring it. The migration procedure includes source inspection and
copy commands; do not run production telemetry to find its source.
