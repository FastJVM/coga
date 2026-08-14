---
slug: remove-coga-build-and-project
title: remove-coga-build-and-project
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
step: 4 (review)
---

## Description

Remove the `coga build` and `coga project` entry points — neither has ever
been used — and make `coga chat` (→ `launch bootstrap/orient`) the single
conversational door into a repo. This is a pure-removal ticket: delete both
surfaces and everything only they consume, and repoint every reference
(`coga init` closing message, docs, contexts, alias tables) at `coga chat`
so a fresh repo is never left pointing at a dead command. Do not build a
replacement onboarding flow here — that is deliberately deferred to
`v2/onboarding-v2-first-run-experience-after-removing`.

Done looks like: no references to the `coga build` / `coga project`
commands, the `coga-build` ticket, or the `bootstrap/project` skill anywhere
in live code, packaged templates, or docs (the generic words "build" and
"project" are fine); `pytest` green with `test_project.py` removed and
alias/init tests updated; `coga validate --json` clean.

## Context

What each entry point is:

- `coga build` is an alias (`build = "launch coga-build"` in
  `src/coga/aliases.py` and the packaged `coga.toml` template) that launches
  the packaged first-run onboarding ticket
  `src/coga/resources/templates/coga/tasks/coga-build.md`, backed by the
  `build` workflow (live copy `coga/workflows/build/`, packaged copy under
  `src/coga/resources/templates/coga/workflows/build/`).
- `coga project` is a real Typer command (`src/coga/commands/project.py`,
  registered in `src/coga/cli.py`) that runs the `bootstrap/project` skill
  (`src/coga/resources/templates/coga/bootstrap/skills/bootstrap/project/SKILL.md`)
  against the packaged `bootstrap/project/ticket.md`.

Known reference inventory (grep for `build`/`project`/`coga-build` to
confirm; this list was accurate at authoring time): `src/coga/aliases.py`,
`src/coga/cli.py`, `src/coga/commands/project.py`, `src/coga/commands/init.py`
(init *seeds* the `coga-build` ticket into fresh empty repos — remove the
seeding machinery too: `_ONBOARDING_TICKET_DIRS`, `_prune_onboarding_tickets`,
and the onboarding closing messages, then repoint the closing message at
`coga chat`), `src/coga/dependencies.py`,
packaged templates under `src/coga/resources/templates/coga/` (`coga.toml`,
`log.md`, `tasks/coga-build.md`, `bootstrap/project/`, `bootstrap/skills/
bootstrap/project/`, `bootstrap/contexts/coga/cli/SKILL.md`,
`workflows/build/`), live repo copies (`coga/coga.toml`,
`coga/workflows/build/`, `coga/contexts/coga/codebase/SKILL.md`), tests
(`tests/test_project.py`, `tests/test_aliases.py`, `tests/test_init.py`,
`tests/test_packaging.py`), and docs (`README.md`, `docs/getting-started.md`,
`docs/reference.md`, `docs/cli-extension-audit.md`).

Watch out for:

- Live `coga/` vs packaged `src/coga/resources/templates/coga/` copies must
  stay in sync — remove both sides of each pair (CLAUDE.md rule).
- Repos initialized before this change may still carry `build` alias lines
  in their own `coga.toml`; the alias table change only affects the packaged
  template and built-in fallbacks, which is fine — don't try to migrate
  existing repos.
- Packaged template dirs ship in the wheel via
  `[tool.hatch.build.targets.wheel]` in `pyproject.toml`; check the wheel
  targets when deleting template dirs, and note the wheel-building test in
  `tests/test_packaging.py` silently skips in some environments, so a broken
  wheel won't necessarily fail CI.
- Overlap: two `coga/tasks/v2/cleanup-core-commands/` drafts reference
  `coga project` — `work-orchestration-commands-to-tickets.md` (in its
  migration scope) and `launch-decomposition.md` (callers list, acceptance
  checkboxes). This ticket supersedes those parts by deleting the command
  outright; leave a short note in each rather than migrating.
- Out of scope: any new onboarding flow (see the v2 ticket above), and any
  change to `coga chat` / `bootstrap/orient` behavior beyond doc pointers.
- Accepted tradeoff (owner-confirmed at authoring): `coga init` today seeds
  the `coga-build` ticket into every fresh repo, so this removal leaves new
  repos with only a "run `coga chat`" pointer until the onboarding v2 ticket
  lands. `coga chat` resolves in old repos too — `chat` exists both in the
  packaged `coga.toml` template and as a built-in alias fallback.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/691
branch: remove-build-project
worktree: /tmp/coga-feature.EybenD/repo

Independent clone rebased onto `origin/main` at `9e5a2eb1`; the original linked
checkout held a preserved but stale uncommitted patch.

## Plan

Pure removal in one commit. Confirmed reference inventory by grep:

- `src/coga/aliases.py` — drop `"project"` from `BUILTIN_COMMANDS`, drop
  `"build": "launch coga-build"` from `DEFAULT_ALIASES`, fix the comment.
- `src/coga/cli.py` — drop the `project_cmd` import, the `app.command("project")`
  registration, and `"project"` from `_SWEEPING_COMMANDS`.
- `src/coga/commands/project.py` — delete.
- `src/coga/commands/init.py` — delete `_ONBOARDING_TICKET_DIRS` /
  `_prune_onboarding_tickets` / the pruned-onboarding message, repoint the
  closing steps at `coga chat`.
- `src/coga/dependencies.py` — swap `coga build` for `coga chat` in the two
  agent-CLI prompts.
- Packaged templates: delete `tasks/coga-build.md`, `workflows/build/`,
  `bootstrap/project/`, `bootstrap/skills/bootstrap/project/`; edit
  `coga.toml`, `log.md`, `bootstrap/contexts/coga/cli/SKILL.md`.
- Live copies: `coga/coga.toml`, `coga/workflows/build/`,
  `coga/contexts/coga/codebase/SKILL.md`.
- Tests: delete `tests/test_project.py`; update `test_aliases.py`,
  `test_init.py`, `test_packaging.py`.
- Docs: `README.md`, `docs/getting-started.md`, `docs/reference.md`,
  `docs/cli-extension-audit.md`.
- Supersede notes (not migrations) in the two `v2/cleanup-core-commands/`
  drafts that list `coga project`.

## Implementation notes

- Reconciled the preserved removal onto fresh `origin/main` in the independent
  clone recorded above; the final mandatory rebase moved the base to
  `a99b33a0`.
- Removal commit: `5a4c1423` (`Remove unused build and project entry points`).
- Peer-review fix: `c9da37d3` (`Peer-review: remove stale project context`).
- Left `/home/n/Code/claude/coga-remove-build-project` untouched; it is the
  superseded linked checkout containing the stale pre-rebase patch.
- Removed init's `new-user` stamping regex/helper as part of the onboarding
  deletion: no remaining packaged template contains that placeholder, so the
  helper had no real consumer.
- The two overlapping cleanup drafts now explicitly remove the deleted command
  from their scopes instead of planning a migration.

## Verification

- Targeted alias/init/packaging tests: 139 passed, 1 skipped (Hatchling absent
  from the ambient pytest interpreter).
- Final post-rebase full suite: 1,721 passed, 1 skipped.
- Explicit final wheel build succeeded with `uv build --wheel`; an archive
  inspection confirmed every removed command/resource path is absent despite
  the pytest packaging skip.
- `coga validate --task remove-coga-build-and-project --json` is clean from the
  control checkout. Repo-wide validation still reports unrelated pre-existing
  errors in parked `v2/` drafts; those are outside this ticket.

## Open PR step

- `coga open-pr` first refused: `origin/main` had advanced past the recorded
  base (#688 plus a state sync), so the branch was stale.
- Rebased the clone onto `origin/main` at `fa48d9de`; clean, no conflicts.
  Commits are now `9eebd4b0` (removal) and `f54b5ea1` (peer-review fix).
- Re-ran the full suite post-rebase with `python3.12 -m pytest`: 1,728 passed,
  1 skipped. (The ambient `python` on this box is 3.9 and cannot import Coga —
  use `python3.12`.)
- `coga open-pr` then succeeded: https://github.com/FastJVM/coga/pull/691,
  recorded as `pr:` under `## Dev`.

## Peer review

- `codex review --base main` found one P2: the live and packaged architecture
  contexts still named the deleted `coga project` spawn path, and the usage
  context still counted project/onboarding interviews.
- Applied the must-fix context cleanup on the feature branch; a multiline
  repository scan now finds no removed command/resource references in live
  contexts, packaged resources, code, tests, examples, or public docs.
- Final rebase onto `origin/main` at `a99b33a0` was clean. The post-rebase full
  suite passed (1,721 passed, 1 skipped), the explicit wheel build succeeded
  and omitted all removed resources, and task-scoped validation is clean.

## PR

Remove the unused `coga build` alias and `coga project` command together with
their single-consumer onboarding/project templates, workflow, init seeding
machinery, tests, and documentation. Route fresh-repo and project-planning
guidance through `coga chat`, and update both live and packaged behavioral
contexts so agent sessions describe only the surviving command surface.

Test plan: `python -m pytest` (1,721 passed, 1 skipped); `uv build --wheel`; `coga validate --task remove-coga-build-and-project --json`.
