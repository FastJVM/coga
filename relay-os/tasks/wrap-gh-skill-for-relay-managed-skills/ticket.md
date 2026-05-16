---
title: Wrap gh skill for Relay-managed skills
status: done
mode: interactive
owner: nick
human: nick
agent: codex1
assignee: codex1
contexts:
- relay/architecture
- relay/principles
- relay/codebase
- relay/current-direction
- relay/project-stage
- dev/code
skills: []
workflow: null
---

## Description

Build Relay's skill-management surface as a thin wrapper around GitHub CLI's
`gh skill` command, with Relay-specific handling for non-GitHub URLs, removal,
and Dream PR creation.

The goal is not to build a new package manager. `gh skill` already handles the
common GitHub-backed case: install, preview, update, `--all`, `--dir`, pinning,
and source metadata. Relay should use that substrate where it fits and own the
parts that are specific to our workflow: installing into `relay-os/skills`,
supporting arbitrary URLs by downloading locally first, removing skills as
git-visible deletes, and opening reviewable PRs for updates so skill changes do
not silently change agent behavior.

## Context

What we learned:

- `gh skill` is public preview, and requires GitHub CLI `2.90.0+`.
- This checkout currently has an older `gh`, so implementation must fail loud
  with an actionable upgrade message when `gh skill` is unavailable.
- `gh skill install <repo> <skill> --dir relay-os/skills` covers the
  GitHub-backed install path.
- `gh skill install <local-dir> --from-local --dir relay-os/skills` covers a
  local directory once Relay has downloaded or unpacked it.
- `gh skill update --dir relay-os/skills --all` covers the GitHub-backed update
  path, but it must be tested against the exact Relay layout before Dream uses
  it automatically.
- `gh skill` injects source metadata into `SKILL.md` for GitHub/local installs.
  For arbitrary URLs, Relay must preserve the original URL/version/digest
  itself; otherwise `--from-local` would only remember the temporary download
  path.
- The official manual currently lists `install`, `preview`, `publish`,
  `search`, and `update`; Relay should provide its own exact-name
  `remove`/`uninstall` wrapper unless an official command lands.
- There is an open `gh skill update --dir` issue about custom nested
  directories being relocated/deleted on update. Relay should avoid nested
  layouts or add a guard test before using `--dir` updates in Dream.

Do not add `gh` to Python `requirements.txt`: it is an external CLI dependency,
not a pip package. The repo-level CLI tool list lives in `README.md` under
`External CLI Tools`; keep that section current and add any user-facing command
error/docs needed by the implementation.

## Proposed command surface

- `relay skill install <owner/repo-or-github-url> [skill]`
- `relay skill install-url <url> [skill-or-path]`
- `relay skill install-local <path> [skill]`
- `relay skill update <skill>`
- `relay skill update --all`
- `relay skill remove <skill>`
- `relay skill status`

Names can change during implementation if a simpler command shape emerges, but
the source types must be covered: GitHub repo/URL, arbitrary URL downloaded
locally, and local directory.

## Required behavior

- Default install/update target is `relay-os/skills`.
- GitHub-backed installs delegate to `gh skill install ... --dir
  relay-os/skills`.
- Arbitrary URL installs download to a temp directory, unpack if needed, verify
  a skill directory with `SKILL.md`, then install through `gh skill install
  <downloaded-dir> --from-local --dir relay-os/skills`.
- Arbitrary URL installs also record Relay-owned source metadata: original URL,
  resolved version or timestamp if known, content digest, and installed skill
  path.
- Updates for GitHub-backed skills delegate to `gh skill update --dir
  relay-os/skills`.
- Updates for arbitrary URL skills re-download the original URL, compare digest
  and installed contents, then update only if the installed skill has not been
  locally adapted.
- Removal is exact-name only, shows the target path before deletion, and leaves
  a normal git delete in the working tree. No prefix deletion.
- Dream runs the update-all path on a branch, runs `relay validate` and the
  relevant test command, then opens or updates one PR containing the skill
  changes and a summary of updated/unchanged/skipped/failed skills.
- If any update is skipped because of local adaptations, Dream lists it in the
  PR body or blackboard instead of forcing the overwrite.

## Acceptance criteria

- [x] `relay skill install` can install a GitHub-backed skill into
      `relay-os/skills` through `gh skill`.
- [x] `relay skill install-url` can install a skill from a non-GitHub URL by
      downloading locally, validating `SKILL.md`, and preserving original URL
      metadata.
- [x] `relay skill install-local` can install from an already-downloaded local
      directory.
- [x] `relay skill update --all` handles both GitHub-backed skills and
      URL-backed skills, while skipping locally adapted skills with clear
      evidence.
- [x] `relay skill remove <skill>` removes only an exact installed skill path
      and is reviewable through git diff.
- [x] `relay skill status` summarizes installed skills by source type, current
      ref/digest, update availability, and conflict/fetch failures.
- [x] Dream can run the update-all workflow and open/update one PR with command
      output, verification, and a human-readable skill-change summary.
- [x] The README external CLI tool list stays accurate for the `gh skill`
      dependency.
- [x] Tests cover GitHub delegation command construction, URL download/local
      install, local adaptation skip, exact remove, missing `gh skill`, and the
      Dream PR summary path.

## Out of scope

- Replacing `gh skill` for GitHub-backed installs/updates.
- Auto-merging skill updates. Human review stays required because skills affect
  agent behavior.
- Installing secrets or credentials. Private source access should rely on the
  user's existing `gh`/git authentication.
