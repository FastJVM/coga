---
title: Install init skills via skill downloader
status: in_progress
mode: interactive
owner: nick
human: nick
agent: codex
assignee: codex
contexts:
- relay/architecture
- relay/principles
- relay/codebase
- relay/current-direction
- relay/project-stage
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 3 (open-pr)
---

## Description

Change `relay init` / `relay init --update` so Relay-owned skills are installed
through the skill downloader/installer path instead of being copied wholesale
from bundled template directories.

The problem: today the upstream Relay template tree contains skill directories,
and `relay init` / `init --update` copy or mirror those files into each repo.
That makes the resulting skills look like local template content rather than
installed, provenance-tracked skills. Once Relay has a real skill
install/update surface, init should use it.

## Context

Related ticket: `wrap-gh-skill-for-relay-managed-skills`.

This ticket is the init integration slice. It should not build the full skill
installer itself; it should consume that public installer/downloader API once it
exists.

Core Relay scaffolding can still be copied from templates:

- `relay.toml`, `rules.md`, `context.md`
- bootstrap launch shims such as `bootstrap/orient`
- workflows, recurring templates, scripts, hook templates
- non-skill context templates and skeleton directories

Actual `SKILL.md` directories should move to an install manifest instead of
being copy-pasted from the template tree. Fresh init and update should install
them into the correct Relay skill locations with provenance metadata, so later
`relay skill status` and `relay skill update --all` can reason about them.

## Proposed shape

- Add a Relay-managed skill manifest, for example
  `src/relay/resources/skills.toml` or similar.
- Each manifest entry names the destination path, source URL/repo/ref, expected
  digest when available, and whether the skill is required for bootstrap.
- `relay init` creates the base `relay-os/` scaffold, then installs required
  skills through the same code path as `relay skill install`.
- `relay init --update` refreshes the vendored CLI/templates, then runs the
  same skill update/install reconciliation used by `relay skill update --all`.
- Init output should clearly separate copied scaffolding from downloaded or
  updated skills.
- Existing compatibility symlinks, such as `skills/bootstrap` or `skills/retro`
  if still needed, should point at installed skill directories rather than
  copied template payloads.

## Required behavior

- No fresh init should silently produce untracked copy-pasted Relay skills when
  those skills have a declared upstream source.
- Skill installation failures for required bootstrap skills fail loud with the
  source URL/path and the remediation command.
- Optional/non-critical skill failures may be reported as warnings only if the
  ticket explicitly marks them optional in the manifest.
- Existing local custom skills under `relay-os/skills/<custom-ns>/` are never
  overwritten by init/update.
- `relay init --update` does not force-overwrite locally adapted installed
  skills. It reports conflicts and leaves them for the skill update PR flow.
- Tests should not require live network access; use fixtures or fake installer
  calls for init behavior.

## Acceptance criteria

- [ ] Relay-owned skill directories are no longer copied directly from
      `src/relay/resources/templates/relay-os/**/skills/**` during fresh init.
- [ ] Fresh init installs required Relay skills through the skill installer API
      and records provenance/update metadata.
- [ ] `init --update` reconciles Relay-managed skills through the updater path
      instead of wholesale mirroring skill directories.
- [ ] Init output reports installed/updated/skipped skill counts separately from
      copied scaffolding.
- [ ] Missing downloader support, missing external CLI tools, or source fetch
      failures fail loud for required bootstrap skills.
- [ ] Local custom skills and locally adapted installed skills are preserved.
- [ ] Tests cover fresh init, init update, required-skill failure, local custom
      skill preservation, and locally adapted installed-skill skip.

## Out of scope

- Building the skill installer/downloader itself. That belongs to
  `wrap-gh-skill-for-relay-managed-skills`.
- Removing all templates. Non-skill scaffolding remains template-based.
- Auto-opening a PR from init. Dream owns reviewable skill-update PRs.
