---
name: coga/context-layout
description: The `coga/` directory layout, local-first then bundled resolution, and relocating contexts with `[layout] contexts` (checkout-root anchor, rejection cases, trackability, publication, uninstall ownership).
---

# The `coga/` layout and the contexts root

```
coga/
  coga.toml          shared config (committed)
  coga.local.toml    machine-local config (gitignored; user, overrides)
  context.md         repo-context layer of every composed prompt
  log.md             repo-global audit log (CLI-managed)
  tasks/             tickets: <slug>.md, or <slug>/ticket.md plus attachments,
                     at any sub-directory depth
  recurring/<name>/  recurring task templates
  skills/<ref>/      project-local skills and overrides
  contexts/<ref>/    project-local contexts (default contexts root)
  workflows/<ref>.md project-local workflows
  .agent-skills/     generated local-plus-bundled skill view (gitignored)
```

Every context is `<contexts-root>/<ref>/SKILL.md`, and the ref is the
directory path. Owners of the other pieces: tickets and attachments in
[coga/tickets](../tickets/SKILL.md) and
[coga/script-tickets](../script-tickets/SKILL.md), recurring templates in
[coga/recurring](../recurring/SKILL.md), skill shapes in
[coga/skill-management](../skill-management/SKILL.md), and workflows in
[coga/workflows](../workflows/SKILL.md).

## Local first, then bundled

Resolution is per ref. `src/coga/paths.py` `resolve_context_path` checks
`context_path` (`cfg.contexts_root/<ref>/SKILL.md`) and, only when that local
file is genuinely absent, falls back to `bootstrap_context_path`, the
installed package's `bootstrap/contexts/<ref>/SKILL.md`. Skills, workflows
and bootstrap tickets follow the same local-then-package order. The package
`bootstrap/` tree is never materialized into a repo, so a local file at the
same ref is an override and an upgrade changes the fallback without touching
the repo.

Before testing existence or falling back, `require_context_artifact` checks
the local path at either root. Symlinked artifacts or ancestors (internal
links, chains, dangling links, cycles), entries inside Git metadata or a
nested checkout, and non-regular files are rejected. In a Git checkout the
file must also be tracked or untracked-but-unignored, so a fresh clone
composes the same bytes. An uncommitted, unignored file is fine. Invalid
artifacts raise actionable errors, surface as `broken-context` in
`coga validate`, and stop composition before their bytes reach a prompt.
This policy covers context refs only, not skills or ordinary attachments.

## Relocating: `[layout] contexts`

```toml
[layout]
contexts = "docs/contexts"
```

Contexts are the one primitive humans hand-edit as prose, so a repo may keep
them beside its docs. Unset (the default) means `coga/contexts/`.
`Config.contexts_root` is the single accessor. Ref resolution, composition,
`coga validate`, `coga create` / `coga ticket` checks and authoring sync, the
`mark done` product-stranding guard (which excludes the Coga root and the
current contexts root from its diff), and `coga init` / `coga uninstall` all
follow it.

**Anchor.** The value is relative to the **Git checkout root**
(`find_checkout_root`), not the Coga root. `Config.repo_root` is
`<checkout>/coga/` in the nested layout but the checkout itself in the root
layout. The checkout root is above both, so `docs/contexts` always means
`<checkout>/docs/contexts`. A Coga root deeper in a monorepo spells the full
path (`tools/ops/docs/contexts`).

**Rejected at config load** (`resolve_layout_contexts_path`, `_parse_layout`),
because a quiet miss is catastrophic: bundled fallback would keep
`coga/architecture` resolving while every local context vanished from
prompts. Rejected values are a non-string or empty value; an absolute path;
Git pathspec magic (leading `:`, `*`, `?`, `[`); no enclosing checkout; the
checkout root itself; symlinked path components; anything outside the
checkout (`..` escapes); the Coga root or one of its ancestors; Git's
`.git` directory or a nested checkout; and a target that does not exist or
is not a directory.

**Trackability** (`_require_trackable_context_entry`): the root must not be
gitignored, must contain at least one tracked or unignored file (use a
`.gitkeep` for an intentionally empty root), and every real `SKILL.md` under
it passes the artifact check above. The ignored `_template/` scaffold is
exempt. `[layout]` is rejected in `coga.local.toml`: where a repo keeps its
prose is a repo fact.

## Publication and ownership

Context edits are review work. The end-of-command state sweep
(`src/coga/git.py` `sync_coga_state`) publishes only tasks, `log.md` and
`recurring/`, so edits under either root stay dirty until committed through
normal Git or a PR. The sweep reloads config at that boundary
(`src/coga/cli.py` `_sweep_coga_state`), because an agent may have edited
`coga.toml` mid-command. The `coga ticket` authoring interview is the
exception: it hashes the configured root before the session and publishes
the context files it created or changed (`src/coga/authoring.py`
`authoring_sync_roots`, `support_paths`). Moving an existing tree is an
ordinary commit: move the files and set the key together.

`coga init` relocates its scaffold only when the template's `coga.toml` sets
the key ([coga/init](../init/SKILL.md)). The whole configured root is
Coga-owned: `coga uninstall` deletes it, other files included
([coga/uninstall](../uninstall/SKILL.md)). Keep indexes and non-context
material outside it.
