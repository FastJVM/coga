---
slug: migrate-desktop-relay-repos-to-coga-tracking
title: Migrate Desktop relay repos to coga (tracking)
status: draft
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow: null
secrets: null
script: null
---

## Description

Single tracking ticket (deliberately not one ticket per repo — a ticket can't
cleanly rename the repo it lives in) to migrate the ~8–10 Desktop relay repos
to the coga layout. Follow [docs/migrating-to-coga.md](../../docs/migrating-to-coga.md)
for each repo; the CLI cutover (section 1) must already be done on the machine
first.

Fill in the actual repo list below (repos live on the owner's Desktop; not
enumerable from this checkout), then run the per-repo steps.

Per repo, from a clean working tree:

1. `git mv relay-os coga`, `git mv relay.toml coga.toml`,
   `mv relay.local.toml coga.local.toml` (if present).
2. Rename local override namespaces: `coga/contexts/relay/` → `coga/contexts/coga/`,
   `coga/skills/relay/` → `coga/skills/coga/`.
3. Replace blackboard fences `<!-- relay:blackboard -->` → `<!-- coga:blackboard -->`.
4. Frontmatter-only context/skill refs `relay/<name>` → `coga/<name>`;
   config/.gitignore tokens `RELAY_REPO_URL`, `relay.local.toml`, `relay-os` → coga
   spellings. Leave prose and historical URLs alone.
5. Remove regenerated `coga/.relay/` and `coga/.agent-skills/` if present.
6. `coga validate && coga status`, review the diff, commit
   `Migrate relay -> coga`.

## Repo checklist

Replace with the real list (~8–10 repos):

- [ ] `<repo-1>`
- [ ] `<repo-2>`
- [ ] …

## Context

Spun out of `coga-rename-follow-ups-post-repo-rename` (blackboard,
"Host-repo migration"). The rename itself (PRs #454/#455), the PyPI publish
(`coga 0.2.0`, 2026-06-27), and this repo's own migration are all done; this
ticket covers only the *other* installed repos still on the `relay-os/` +
`relay.toml` layout.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
