---
slug: rename-relay-to-coga
title: Rename relay to coga (full rebrand)
status: in_progress
autonomy: interactive
owner: zach
human: zach
agent: claude
assignee: zach
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
step: 4 (review)
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

## Dev

- branch: `rename/relay-to-coga`
- worktree: `/private/tmp/relay-coga`
- pr: https://github.com/FastJVM/relay/pull/454

## PR step (pushed + opened)

Pushed `rename/relay-to-coga` and opened PR #454 (base `main`). gh auth green
(lilfedor, `repo`+`workflow` scopes). **No CI checks configured** on the repo —
"no checks reported on the branch" — so nothing to be green; verification rests
on the local suite (924 pass) recorded above. **Merge caveat surfaced in the PR
body:** main advanced 7 commits since the branch was cut — all relay-os
bookkeeping (task records / `log.md` / step bumps), no source — and they land in
`relay-os/`, which this branch renamed to `coga-os/`. They must be re-homed into
`coga-os/` at merge time or they resurrect a stray `relay-os/` dir. No source is
missing; rename is complete as-is. Merge reconciliation is the human's next step.

## Execution decisions (this session, refining the plan)

- **Boss handles the GitHub repo rename + PyPI trusted-publisher** (decision C ops).
  So this PR **preserves `FastJVM/relay` URLs** (README, `COGA_REPO_URL` default in
  `update.py`, docs, tests) — they keep working via GitHub redirect; a follow-up flips
  them to `FastJVM/coga` once the repo is actually renamed. Sweep does `relay→coga` then
  reverses `FastJVM/coga`→`FastJVM/relay`.
- **`relay-os` is overloaded** today: it is BOTH the on-disk dir AND the PyPI dist name.
  The rename un-overloads it — dir → `coga-os`, but the dist name (`pyproject name=`,
  `cli.py _pkg_version(...)`) → bare **`coga`**. Two hand-fixes after the sweep.
- **Workspace dir keeps the `-os`** (`coga-os`, confirmed w/ owner): unambiguous workspace
  marker inside host repos, avoids `coga/` vs `src/coga/` self-collision. Only the
  command/package/import collapse to bare `coga`.
- **Brand namespaces rename**: `contexts/relay/`→`contexts/coga/`, `skills/relay/`→`skills/coga/`.
- **History preserved (decision D)**: `git mv relay-os coga-os` moves the 139 task records +
  `log.md` + `recurring/digest/spool.md`; their *content* is NOT swept. Task dirs/files whose
  names contain "relay" (e.g. `tasks/install/relay-help-...`) keep their names.
- **`update.py` cleanup literals**: swept wholesale EXCEPT `tasks/relay-setup` (targets a
  relay-named leftover the migrate script doesn't rename — preserved). Other entries
  (`contexts/relay/*`, `skills/relay`) sweep correctly since `--update` only runs on
  already-migrated repos.
- **Migrate helper + per-repo tracking**: deferred — agreed to circle back after the rename
  lands. Leaning: one-shot `scripts/migrate-to-coga.sh` + a SINGLE tracking ticket with a
  per-repo checklist (NOT one ticket per repo — chicken-and-egg: a ticket can't cleanly rename
  the repo it lives in). Not built yet.

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

## Progress / verification (implement step)

- **Done:** `git mv` of all structural `relay`→`coga` paths (`src/coga`, `coga-os`,
  `contexts/coga`, `skills/coga`, templates, `example/coga-os`, 3 brand docs); content
  sweep of 259 files; 157 historical files left untouched (decision D); `FastJVM/relay`
  URLs preserved via post-sweep reversal.
- **Dist-name collisions caught & fixed** (`relay-os` was both dir AND PyPI name → these
  must be bare `coga`, not `coga-os`): `pyproject name`, `cli.py _pkg_version`,
  `COGA_PIPX_PACKAGE`, `skill_manager` pip msg, `uninstall.py` prose, `update.py` comment,
  **`release.yml` PyPI env URLs** (`pypi.org/p/coga`), README install/uninstall commands,
  `docs/releasing.md` PyPI Project Name, and test fixtures/assertions. Audited: no
  dist-name `coga-os` remains; every remaining `coga-os` is a directory path.
- **Tests:** full suite green — 923 pass / 1 skip. NOTE: 4 script-skill tests shell out to
  `python -m coga.cli`; they need `coga` importable in the subprocess. They pass with
  `PYTHONPATH=<worktree>/src` (and will pass in CI, which pip-installs `coga`); they "fail"
  only in a bare local env where the editable install is still the old `relay`. Same test
  design as pre-rename (those needed `relay` installed too) — not a regression.
- `coga --help` / `coga validate --json` on the `coga-os/` fixture both clean.
- `test_packaging.py` (builds a real wheel, checks it ships `coga/` + `coga-os/` templates)
  is green → wheel packaging verified.
- **Real rename bug found & fixed:** `is_coga_source_checkout` matched the pyproject name
  against `"coga-os"` — must be bare `"coga"` (the dist name). Surfaced once the test fixture
  was made realistic; fixed in source (`update.py`).
- **Committed** on `rename/relay-to-coga` as `cc2f6843` (442 files: 250 renames, 192
  rename+edit, 67 edits). Tree clean. **NOT pushed, no PR, no bump** — awaiting Zach's review.
  Decision D verified: `log.md` / digest spool / historical tasks are byte-identical renames.

## Follow-up — flip repo URLs (do WITH the boss's `FastJVM/relay`→`FastJVM/coga` rename)

Deferred deliberately (decision C sequencing): `FastJVM/relay` URLs are kept so they keep
working — incl. the functional `COGA_REPO_URL` default that `coga init --update` clones from.
Once the GitHub repo is renamed, flip `FastJVM/relay`→`FastJVM/coga` in these 6 files:
`docs/vision.md`, `README.md`, `src/coga/commands/init.py`, `src/coga/commands/update.py`,
`tests/test_init.py`, `tests/test_skill_manager.py`. (One sed, mirror of the reversal this PR did.)

**Now tracked as ticket `coga-rename-follow-ups-post-repo-rename`** (created this session, on
main): captures these 6 URL flips + dropping the README stopgap clone target + the migrate
tooling + the `update.py` OBSOLETE_PATHS decision below.

## Self-QA (self-qa step)

`/code-review` (xhigh) + `/simplify` ran against the branch diff vs `main`. The diff is a
mechanical rename (512 files, balanced ins/del), so finders were scoped to the real-bug surface:
leftover/wrong-direction tokens, import + entry-point integrity, the hand-edited source files, and
test semantics. Imports/entry points clean (`import coga`, `coga --help`, wheel build all green).

Two findings fixed + committed (`5893b1ad`):
- `tests/test_packaging.py`: wheel glob `coga_os-*.whl` → bare dist name `coga-*.whl`. The build
  produces `coga-0.2.0-*.whl`; the old glob matched nothing and `ValueError`'d on unpack in CI,
  masked locally by the hatchling `importorskip`. With hatchling present the test now RUNS and
  passes against a real wheel (suite went 923 pass/1 skip → **924 pass**).
- `README.md`: clone `…/FastJVM/relay` into an explicit `coga` target so `cd coga` works while the
  URL is still `relay` (stopgap; dropped when the URL flips — see tracking ticket).

One finding DEFERRED (deliberately not flipped): `update.py` `OBSOLETE_PATHS` (~L60) +
`_LEGACY_COGA_GITIGNORE_ENTRIES` (~L115) `contexts/coga/*` / `skills/coga` prune literals. Three QA
agents flagged the sweep may have gone one token too far (these match on-disk paths in PRE-rename
repos). Correctness depends on the unbuilt `migrate-to-coga.sh` — left as `coga` (the implement-step
choice) and tracked in the follow-up ticket to co-design with the migrate script. Don't flip blind.

Tests: full suite **924 pass**; `coga validate --json` clean on `example/coga-os`. Tree clean.

## Out of scope

- Rewriting historical task records (decision D).
- The actual `coga 0.2.0` PyPI publish — happens after this lands, via the trusted-publishing
  workflow under the `coga` name.

## Usage

{"agent":"claude","cache_creation_input_tokens":569781,"cache_read_input_tokens":38943937,"cli":"claude","input_tokens":39111,"model":"claude-opus-4-8","output_tokens":410662,"provider":"anthropic","schema":1,"session_id":"4caf93c5-6417-4422-85a6-b763e45b5b22","slug":"rename-relay-to-coga","step":"implement","title":"Rename relay to coga (full rebrand)","ts":"2026-06-26T02:38:20.026874Z","usage_status":"ok"}

{"agent":"claude","cache_creation_input_tokens":307610,"cache_read_input_tokens":6301433,"cli":"claude","input_tokens":33255,"model":"claude-opus-4-8","output_tokens":161862,"provider":"anthropic","schema":1,"session_id":"ab985f7d-0141-4c3e-a195-d564f23a83b0","slug":"rename-relay-to-coga","step":"self-qa","title":"Rename relay to coga (full rebrand)","ts":"2026-06-26T03:05:34.685368Z","usage_status":"ok"}
