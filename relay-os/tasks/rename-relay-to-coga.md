---
slug: rename-relay-to-coga
title: Rename relay to coga (full rebrand)
status: in_progress
autonomy: interactive
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Rename the project from **Relay** to **Coga**, top to bottom — the package
(`relay-os` → `coga`), the CLI command (`relay` → `coga`), the import package
(`src/relay/` → `src/coga/`), the on-disk convention (`relay-os/` → `coga-os/`;
`relay.toml`/`relay.local.toml` → `coga.toml`/`coga.local.toml`;
`RELAY_REPO_URL` → `COGA_REPO_URL`), the canonical `contexts/relay/` behavioral
contracts, all docs, and the `FastJVM/relay` repo references.

**Why:** the intended PyPI name `relay-os` is blocked — PyPI rejects it as
confusable with an active package `relayos`, and `relay`/`relay-cli` are
taken/blocked too. The owner chose **Coga**, which is now claimed on PyPI
(placeholder `coga 0.0.1` published). This ticket adopts Coga everywhere so the
published package, the command, and the brand are all consistent.

## What "done" looks like

- `pyproject.toml`: `name = "coga"`, `[project.scripts]` → `coga = "coga.cli:main"`.
- `src/relay/` → `src/coga/`; every `import relay` / `from relay.x` updated; suite green.
- On-disk convention renamed everywhere it's read/written: `relay-os/` → `coga-os/`,
  `relay.toml` → `coga.toml`, `relay.local.toml` → `coga.local.toml`,
  `RELAY_REPO_URL` → `COGA_REPO_URL` — in source, config loading, and the packaged templates.
- `contexts/relay/` → `contexts/coga/`; every live/shipping doc + `--help` says "Coga".
- `FastJVM/relay` references updated; repo-rename + trusted-publisher update sequenced (blackboard).
- A `migrate` helper that renames `coga-os/` + config in an existing repo, so the
  ~10 existing FastJVM/Desktop repos move over in one sweep.
- Historical task records (done-task blackboards/logs) **left as-is** — they're accurate
  history of when it was "relay" and git history retains it regardless.
- Full `pytest` green; `relay validate --json` clean (modulo pre-existing unrelated failures);
  the built wheel is `coga` shipping the `coga-os` templates.

## Context

- Name saga: `relay-os` is confusable with the active `relayos` PyPI project; `relay` is a
  dead 2013 package; `relay-cli` collides with `relaycli`. **Coga** chosen by owner + claimed.
- Rename surface: **444 files / ~9,211 "relay" references** — the bulk is in `relay-os/`
  task records, which are explicitly NOT rewritten (see blackboard decision D).
- Work happens on branch `rename/relay-to-coga` (worktree `/tmp/relay-coga`), one PR.
- This is a brand/PyPI-driven follow-on to the install-hardening + PyPI-publishing work.

<!-- relay:blackboard -->

## Plan (one PR on `rename/relay-to-coga`, careful passes, suite green before push)

1. **Import package** — `git mv src/relay src/coga`; fix every `import relay` / `from relay.x`.
2. **pyproject** — `name = "coga"`; `[project.scripts] coga = "coga.cli:main"`.
3. **On-disk convention** (the breaking change) — `relay-os/`→`coga-os/`, `relay.toml`→`coga.toml`,
   `relay.local.toml`→`coga.local.toml`, `RELAY_REPO_URL`→`COGA_REPO_URL`, in source +
   config loading + the packaged templates (`src/coga/resources/templates/`).
4. **Contexts + docs** — `contexts/relay/`→`contexts/coga/`; README + `docs/` prose; `FastJVM/relay` URLs.
5. **Migrate helper** — renames `coga-os/` + config in an existing repo (sweeps the Desktop repos).
6. **Verify** — full `pytest` green, `relay validate` clean, build wheel and confirm `coga` + `coga-os` templates.

## Structural decisions (resolved with owner this session)

- **A — `src/relay`→`src/coga`:** YES (clean rebrand; import name follows the brand).
- **B — on-disk `relay-os/`→`coga-os/` + config/env names:** YES. It breaks every existing repo,
  but that's only ~10 (all FastJVM/Zach's, pre-launch); the migrate script handles them. No
  backward-compat "also accept relay-os/" cruft — full rename, clean code.
- **C — repo `FastJVM/relay`→`FastJVM/coga`:** YES, **sequenced**: rename repo → update the PyPI
  trusted publisher (its repo field still says `relay`) → update workflow/clone defaults.
  GitHub auto-redirects the old URL. (PyPI name `coga` is already owned — repo rename can't affect it.)
- **D — history:** do **not** rewrite done-task logs/blackboards (revisionist, buries the real
  diff, and git history keeps "relay" anyway). Rename active + shipping pieces only.

## Out of scope

- Rewriting historical task records (decision D).
- The actual `coga 0.2.0` PyPI publish — happens after this lands, via the trusted-publishing
  workflow under the `coga` name.
