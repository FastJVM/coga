---
name: coga/skill-management
description: The shapes skills take in a Coga repo (authored, GitHub-installed, URL-installed, hand-vendored, bundled), how `coga skill` installs and updates them, and the provenance rules that decide which updater owns a directory.
---

# Skill management

Coga resolves a skill ref from the directory path: project-local
`coga/skills/<ref>/` first, then the package's `bootstrap/skills/`. Agents see
the effective set through the generated `coga/.agent-skills/` view. Every
install is explicit: `coga init` installs no skills and makes no `gh` call.

The generated view uses relative symlinks where possible. On Windows, links
to skills on another drive use absolute targets. This machine-local view
is rebuilt by init and launch and is not committed to the repository.

## Skill shapes

- **Repo-authored, namespaced**: `coga/skills/<ns>/<name>/`, copied from
  `_template/`. Frontmatter normally uses the Coga ref
  (`name: <ns>/<name>`); a skill meant to satisfy the portable Agent Skills
  grammar may keep a leaf `name:` (`ns/foo` may declare `name: foo`).
- **GitHub-backed, flat**: `coga skill install <owner/repo> <skill>` lands
  `coga/skills/<ref>/` under its upstream name. Membership is provenance, not
  a list: a skill is GitHub-backed exactly when its `SKILL.md` frontmatter
  carries `gh skill`'s `metadata.github-repo`. There is no
  manifest; a pack never installed, or removed, stays absent.
- **URL-backed, flat**: `coga skill install-url <url>` lands the same flat
  placement plus `.coga-source.json` (`schema: coga.skill-source.v1`,
  `source_type: "url"`, `source_url`, digests, optional `include`,
  `local_adaptation_notes`). That file is what puts a directory on Coga's own
  update path.
- **Local install**: `coga skill install-local <path>`. `gh skill` records it
  as `local-path` and skips it; Coga's URL updater ignores it; the update
  report has no row for it. Treat it as pinned and reinstall explicitly;
  absence from a weekly report does not mean it was checked.
- **Hand-vendored**: committed under a namespace with `ATTRIBUTION.md` or
  `NOTICE.txt` plus `LICENSE.txt` recording source, license, and
  modifications, and no installer metadata. Refresh by re-copying the
  reviewed upstream revision and deliberately reapplying recorded changes.
  Keep the upstream leaf `name:`.
- **Bundled**: package-backed under `bootstrap/skills/`; `coga skill` never
  writes into `coga/bootstrap/`. See [coga/context-layout](../context-layout/SKILL.md).
  A repo copy of a bundled skill shadows it and `coga skill status` reports it
  as `local-override`. Upgrading `coga` refreshes the package copy, not the repo twin.

## `coga skill` commands

The subcommands are `install`, `install-url`, `install-local`, `update`,
`remove` (exact name, a normal Git delete), and `status`; flags are in
`coga skill <subcommand> --help`.

- `coga skill` wraps GitHub CLI `gh skill` (public preview, **gh 2.90.0+**);
  when it is unavailable Coga fails loud with an upgrade hint. `gh` is an
  external CLI, never a Python requirement.
- `update --all` emits one row per installed skill with a managed source.
  GitHub-backed skills are updated one `gh skill update --dir coga/skills
  --all <ref>` call at a time, so every outcome names that skill. Here `--all`
  only suppresses gh's confirmation; the explicit ref still selects one skill.
  Each outcome is `updated`, `unchanged`, `fetch-failed`, or `skipped-pinned`. `gh` is probed once before any write. A
  GitHub-backed skill nested below the root (`ns/<name>`) is `failed` without
  calling `gh`, which would move it to `coga/skills/<name>`.
- URL-backed skills go through Coga's digest checks. Bundled refs without
  GitHub or URL provenance emit no row in `update --all`, whether or not a repo
  twin exists; those repo copies are maintained in the repo. Other unmanaged
  directories also get no row. Managed provenance still selects its updater
  when a skill shares a bundled ref.
- An explicit `update <bundled-ref>` without managed provenance still reports
  `skipped-bundled`: an installed twin is maintained in the repo, while an
  uninstalled ref is refreshed by upgrading the Coga package.
- `--pr` requires `--all` and opens or updates one draft PR after running the
  `--verify` commands (default `coga validate --json`).
  The updater reuses a shared branch protected by the
  [branch-sweep cleanup contract](../checkout-cleanup/branch-sweep/SKILL.md#branch-sweep-protection-and-archive).
- `status` reports bundled skills as `package-backed` and a same-ref local
  skill as `local-override`. `status --check` uses the update vocabulary.

## URL-backed provenance rules

- **Local adaptation is detected by digest**: current tree versus
  `installed_tree_digest`. `install-url` refuses to overwrite an adapted skill
  without `--force`; `--force` rewrites the digest and clears
  `local_adaptation_notes` but keeps `include`. Force never overrides a
  namespace collision in either direction (flat ref over a namespace
  directory, or namespaced ref under a flat skill).
- **Tree digests skip machine-local state.** Both digests exclude
  `.coga-source.json` and any path under a `.coga`, `.venv`, `.agent-skills`,
  `.claude`, `.codex`, or `__pycache__` directory — the same generated-state
  set the packaging twin comparison excludes. An agent tool's or
  interpreter's droppings inside an installed skill are therefore never local
  adaptation, and an upstream change confined to those paths is not detected.
  The set is fixed rather than read from `.gitignore`, so a digest depends
  only on the tree's bytes.
- **Older digests remain verifiable.** Provenance recorded by an older Coga
  still verifies; `update` migrates it to the current digests, and that
  metadata-only repair shows as a change in the `--pr` flow without touching
  skill files. A legacy mismatch is still an adaptation or upstream change.
- **`include` makes pruning reproducible.** Install and update prune the
  fetched tree to the listed repo-relative paths before landing it (no
  absolute paths or `..`; `SKILL.md` and `.coga-source.json` always kept).
  `source_tree_digest` stays the unpruned upstream digest;
  `installed_tree_digest` describes the pruned tree. A digest recorded before
  pruning was honored is repaired only when the pruned upstream still matches
  the installed files, and reports as a change. Notes and `include` are
  hand-edited; there are no flags.
- **`conflict`** means adapted locally and changed upstream;
  adapted with upstream unchanged is `skipped-local-adaptation`. Update and
  `status --check` classify identically, and the skill-update PR body lists
  conflicts separately.
- A URL skill's original `name` must be a valid Agent Skills name or
  slash-separated components that each are; Coga validates it before staging.
- Notes describing a prune without an `include` key leave the full tree as the
  install; the updater never re-prunes.

## Rules for managed packs

- **Treat GitHub-backed directories as read-only.** No Coga digest guards
  them: a local edit survives only until upstream moves, then the weekly job
  replaces it and its PR shows the upstream change, not the lost edit. Fix
  upstream, or convert to a hand-vendored namespaced copy.
- **Refresh only through `coga skill update`.** The weekly
  `recurring/skill-update` job runs `coga skill update --all --pr`. Ignore a
  pack's own bootstrap instructions (for example a skill telling the agent
  to run the pack's setup command); following them installs an unmanaged
  second copy.
- **Keep Coga-managed skills flat** at `coga/skills/<ref>/`; `gh skill update
  --dir` has a known bug that relocates skills in nested directories.

## Dependencies

Coga installs nothing for a skill. The convention is a `requirements.txt`
beside `SKILL.md` that the operator installs into whatever Python runs the
skill's script; a failing import should name it. Upstream
`metadata.requires.bins` / `metadata.requires.install` frontmatter is read
nowhere by Coga; it only informs the reading agent.
