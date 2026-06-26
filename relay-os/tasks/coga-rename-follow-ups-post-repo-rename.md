---
slug: coga-rename-follow-ups-post-repo-rename
title: Coga rename follow-ups (post repo-rename)
status: draft
autonomy: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
skills: []
workflow: null
secrets: null
script: null
---

## Description

Finish the Relay→Coga rename in code once the boss-owned ops land: the GitHub
repo rename `FastJVM/relay` → `FastJVM/coga` and the PyPI trusted-publisher
repoint. Flip the deliberately-preserved `FastJVM/relay` URLs to `FastJVM/coga`,
drop the stopgap README clone target, settle the migrate-tooling decisions the
rename PR left open, and publish `coga 0.2.0` via trusted publishing.

## Context

The rename PR (branch `rename/relay-to-coga`, commit `cc2f6843` + self-qa
`5893b1ad`) deliberately kept every `FastJVM/relay` URL working via GitHub's
redirect, because the actual repo rename and PyPI trusted-publisher update are
sequenced separately and owned by the boss (rename-PR decision C). This ticket
holds the code changes that become correct only *after* those ops land — they
were intentionally NOT made in the rename PR. See that PR's blackboard
"Follow-up — flip repo URLs" and "Structural decisions C/D".

<!-- relay:blackboard -->

## Pending items (gated on the repo rename)

**Prerequisites — boss-owned ops, gate everything below:**
- [ ] Rename GitHub repo `FastJVM/relay` → `FastJVM/coga` (GitHub auto-redirects the old URL)
- [ ] Repoint the PyPI trusted publisher — its repo field still says `relay`

**Flip the preserved URLs `FastJVM/relay` → `FastJVM/coga`** (one sed, mirror of the reversal the rename PR did):
- [ ] `docs/vision.md`
- [ ] `README.md` — AND drop the stopgap clone target: self-qa added `git clone …/FastJVM/relay coga`; once the URL is `…/coga`, the basename is already `coga`, so revert to plain `git clone …/FastJVM/coga` (explicit `coga` target becomes redundant)
- [ ] `src/coga/commands/init.py`
- [ ] `src/coga/commands/update.py` — the `COGA_REPO_URL` default (the functional clone source for `coga init --update`)
- [ ] `tests/test_init.py`
- [ ] `tests/test_skill_manager.py`

**Migrate tooling (deferred from the rename PR):**
- [ ] Build `scripts/migrate-to-coga.sh` — renames `relay-os`→`coga-os`, `relay.toml`→`coga.toml`, `relay.local.toml`→`coga.local.toml`, `RELAY_REPO_URL`→`COGA_REPO_URL` in an existing installed repo.
- [ ] **DECIDE + reconcile** `update.py` `OBSOLETE_PATHS` (~line 60) and `_LEGACY_COGA_GITIGNORE_ENTRIES` (~line 115): their `contexts/coga/*` / `skills/coga` prune literals were token-swept from `contexts/relay/*` / `skills/relay`. These match paths on disk in **pre-rename** repos. Whether the swept `coga` spelling is right depends on whether `migrate-to-coga.sh` renames the inner namespace dirs (`contexts/relay`→`contexts/coga`, `skills/relay`→`skills/coga`) or only the workspace dir + config. Co-design the two so the prune actually matches what migrate leaves on disk. Three QA agents flagged this in the rename PR; it was deliberately left as `coga` there (don't flip blind). Note: the sibling `tasks/relay-setup` literal was correctly preserved as `relay`.
- [ ] Single tracking ticket with a per-repo checklist to migrate the ~8–10 Desktop relay repos (NOT one ticket per repo — a ticket can't cleanly rename the repo it lives in).

**Publish:**
- [ ] Publish `coga 0.2.0` via the trusted-publishing workflow (`.github/workflows/release.yml`) under the `coga` name.

## Post-merge checklist (landing the source rename, PR #454)

Coordination steps for when PR #454 (the `relay`→`coga` source rename) merges to
`main`. The diff is green (924 tests) — these are about *sequencing*, not code.
Order matters.

**Land it in a lull, or `relay-os/` comes back:**
- [ ] Merge #454 during a quiet window — nothing pushing relay bookkeeping to `main`.
  Any *pre-rename* `relay` process that pushes after the merge re-creates a stray
  `relay-os/` next to `coga/` (this is exactly the churn that kept un-mergeable-ing the PR).
- [ ] Immediately after merge, cut every CLI actor over to `coga` (details below) before
  anyone launches/bumps again.

**CLI cutover (the `relay`→`coga` switch):**
- [ ] In each checkout that runs the CLI: `git pull` the renamed `main`, then reinstall —
  `pip install -e .` (or `pipx install --force .`). Entry point is now `coga = coga.cli:main`;
  the old `relay` console script `ImportError`s after pull (its `src/relay` target is gone),
  which is the forcing function to reinstall.
- [ ] Update anything that *invokes* the CLI by name from `relay …` to `coga …` — cron lines,
  `scripts/cron.sh`, launchd plists, shell aliases, wrapper scripts.
- [ ] Restart the scheduled jobs (digest / skill-update recurring) under the new command, and
  have each human (you, Nick) reinstall their checkout so interactive launches use `coga`.
- [ ] Run this ticket's `mark done` (and any bump) with the **`coga`** CLI *after* reinstalling —
  a pre-rename `relay mark done` writes to `relay-os/tasks/` and resurrects the dir.

**Fan-out (other in-flight work):**
- [ ] Rebase/merge the ~15 sibling worktree branches (`relay-ci`, `relay-pkg`, `relay-init`,
  `remove-shim-concept`, …) — each conflicts across the whole rename surface. Land the close
  ones before #454 where practical; rebase the rest after.
- [ ] Migrate the ~8–10 Desktop host repos (still `relay-os/` + `relay.toml`) — they break under
  the `coga` CLI until migrated. This is the `migrate-to-coga.sh` work above.

Note: the migrate item above still says `relay-os`→`coga-os`; **superseded** — the workspace dir
is now bare `coga` (boss reversed `coga-os` mid-PR, commit `8e7b3f76`). migrate renames
`relay-os`→`coga`, not `coga-os`.
