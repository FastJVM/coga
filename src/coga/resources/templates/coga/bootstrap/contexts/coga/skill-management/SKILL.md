---
name: coga/skill-management
description: The shapes skills take in a Coga repo (authored, GitHub-installed, URL-installed, hand-vendored, bundled), how `coga skill` installs and updates them, and the provenance rules that decide which updater owns a directory.
---

# Skill management

Coga resolves a skill ref from the directory path: project-local
`coga/skills/<ref>/` first, then the package's `bootstrap/skills/`. Agents see
the effective set through the generated `coga/.agent-skills/` view. Every
install is explicit: `coga init` installs no skills and makes no `gh` call.
`src/coga/skill_manager.py` implements everything below.

## Skill shapes

- **Repo-authored, namespaced**: `coga/skills/<ns>/<name>/`, copied from
  `_template/`. Frontmatter normally uses the Coga ref
  (`name: <ns>/<name>`); a skill meant to satisfy the portable Agent Skills
  grammar may keep a leaf `name:` (`browser/dochub` keeps `name: dochub`).
- **GitHub-backed, flat**: `coga skill install <owner/repo> <skill>` lands
  `coga/skills/<ref>/` under its upstream name. Membership is provenance, not
  a list: a skill is GitHub-backed exactly when its `SKILL.md` frontmatter
  carries `gh skill`'s `metadata.github-repo` (`gh_skill_repo`). There is no
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
  modifications, and no installer metadata. `anthropic/skill-creator/` is
  verbatim; `browser/playwright/` is adapted. Refresh by re-copying the
  reviewed upstream revision and deliberately reapplying recorded changes.
  Keep the upstream leaf `name:`.
- **Bundled**: package-backed under `bootstrap/skills/`; `coga skill` never
  writes into `coga/bootstrap/`. See [coga/packaging](../packaging/SKILL.md).

## `coga skill` commands

`install <owner/repo-or-url> [skill]`, `install-url <url> [--force]`,
`install-local <path> [skill]`, `update <skill>` or `update --all [--json] [--pr]
[--pr-title ...] [--verify <cmd>]...`, `remove <skill>` (exact name, a normal
Git delete), and `status [--check] [--json]`.

- `coga skill` wraps GitHub CLI `gh skill` (public preview, **gh 2.90.0+**);
  when it is unavailable Coga fails loud with an upgrade hint. `gh` is an
  external CLI, never a Python requirement.
- `update --all` emits one row per installed skill with a managed source.
  GitHub-backed skills are updated one `gh skill update --dir coga/skills
  <ref>` call at a time, so every outcome names that skill;
  `classify_gh_update_output` maps the output to `updated`, `unchanged`,
  `fetch-failed`, or `skipped-pinned`. `gh` is probed once before any write. A
  GitHub-backed skill nested below the root (`ns/<name>`) is `failed` without
  calling `gh`, which would move it to `coga/skills/<name>`.
- URL-backed skills go through Coga's digest checks. An installed twin of a
  bundled skill is `skipped-bundled` (the repo copy is maintained in the
  repo). Unmanaged directories and uninstalled bundled refs get no row.
- `--pr` requires `--all` and opens or updates one draft PR after running the
  `--verify` commands (default `coga validate --json`).
- `status` reports bundled skills as `package-backed` and a same-ref local
  skill as `local-override`. `status --check` uses the update vocabulary.

## URL-backed provenance rules

- **Local adaptation is detected by digest**: current tree versus
  `installed_tree_digest`. `install-url` refuses to overwrite an adapted skill
  without `--force`; `--force` rewrites the digest and clears
  `local_adaptation_notes` but keeps `include`. Force never overrides a
  namespace collision in either direction (flat ref over a namespace
  directory, or namespaced ref under a flat skill).
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
  pack's own bootstrap instructions (for example
  `google-agents-cli-workflow` telling the agent to run
  `uvx google-agents-cli setup`); following them installs an unmanaged second
  copy.
- **Keep Coga-managed skills flat** at `coga/skills/<ref>/`; `gh skill update
  --dir` has a known bug that relocates skills in nested directories.
- This repo keeps seven `google-agents-cli-*` packs on purpose as the live
  target of the GitHub-backed update path; no ticket does ADK work.

## Dependencies

Coga installs nothing for a skill. The convention is a `requirements.txt`
beside `SKILL.md` that the operator installs into whatever Python runs the
skill's script; a failing import should name it. No skill in this repo carries
one yet. Upstream `metadata.requires.bins` / `metadata.requires.install`
frontmatter (present in the Google packs) is read nowhere by Coga; it only
informs the reading agent.
