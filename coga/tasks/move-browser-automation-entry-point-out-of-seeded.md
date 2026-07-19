---
slug: move-browser-automation-entry-point-out-of-seeded
title: Move browser automation entry point out of seeded tasks
status: blocked
owner: nicktoper
human: nicktoper
agent: codex
assignee: codex
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
script: null
step: 3 (open-pr)
---

## Description

Remove the generic seeded `browser-automation` ticket from fresh Coga installs
and preserve the browser automation entry point as reusable capability instead
of standing user-owned work. The accepted product decision is: delete the
packaged task, move the orchestration methodology into a bundled
`browser/build-automation` skill, expose it through a stateless package-backed
bootstrap launcher, and document how users invoke it.

## Context

Source decision: [why-browser-autoamtion-as-a-ticket](coga/tasks/why-browser-autoamtion-as-a-ticket.md).

The decision ticket investigated the history and found that
`src/coga/resources/templates/coga/tasks/browser-automation.md` is copied into
every `coga init` result as a real `draft` ticket. That is no longer the desired
shape: a ticket should assert chosen work, while this file is a capability
launcher waiting for the user to supply the actual browser task.

Implementation scope:

- Delete `src/coga/resources/templates/coga/tasks/browser-automation.md`.
- Remove the stale packaged `browser-automation` audit line from
  `src/coga/resources/templates/coga/log.md`.
- Move the router/orchestration methodology currently encoded in
  `coga/workflows/browser/build-automation.md` and
  `src/coga/resources/templates/coga/workflows/browser/build-automation.md`
  into a bundled `browser/build-automation` skill.
- Keep `browser/playwright` as the separate lower-level execution skill.
- Expose the orchestration skill through a stateless package-backed bootstrap
  launcher so invoking browser automation setup does not create a standing task
  merely by installing Coga.
- Document the launcher and the distinction between the orchestration skill and
  the Playwright runner in user-facing docs.
- Update init/bootstrap/compose tests so empty and filled installs do not
  contain a seeded browser draft, while the browser contexts, workflow support,
  skills, and runtime capability remain available.

Read `AGENTS.md`, `docs/vision.md`, and the relevant `coga/contexts/coga/`
context before changing behavior. When touching shipped templates or contexts,
keep the live `coga/` copy and packaged
`src/coga/resources/templates/coga/` copy in sync unless the difference is
intentional and documented.

<!-- coga:blackboard -->

## Dev

branch: browser-bootstrap
worktree: /tmp/coga-browser-bootstrap

## Origin

Created from the accepted decision in
`why-browser-autoamtion-as-a-ticket`. Nick chose removal of the seeded ticket
plus a skill/documentation-backed stateless entry point; no further product
destination decision should be needed before implementation.

## Implementation

- Public entry point: `coga launch bootstrap/browser-automation`; no new alias
  or built-in command.
- The former four-phase browser workflow is now the bundled
  `browser/build-automation` skill. The bootstrap target composes it with
  `browser/api-first`, while `browser/playwright` stays a separate runner
  attached only to concrete browser-backed tickets.
- The bundled skill and launcher intentionally live only in package bootstrap
  resources; the live and packaged browser workflow copies are both removed.
- Fresh empty and filled installs keep browser contexts, autonomy workflows,
  the router skill, and Playwright capability without a seeded browser draft.
- The primary checkout's shared Git metadata rejected `index.lock` writes, so
  implementation moved unchanged to the documented writable `/tmp` clone
  fallback; its `origin` points at the real GitHub remote.

## Verification

- `PYTHONPATH=/tmp/coga-browser-bootstrap/src python3.12 -m pytest` — 1327
  passed, 1 skipped (`hatchling` absent from the ambient interpreter).
- Packaging rerun with the cached Hatchling build backend — 3 passed; an
  independent wheel build includes the stateless launcher, router skill, and
  existing Playwright skill, with neither removed seeded artifact present.
- `PYTHONPATH=/tmp/coga-browser-bootstrap/src python3.12 -m coga.cli validate
  --json` from `example/` — 1 ok, 0 issues.
- Source-backed `coga launch bootstrap/browser-automation --prompt-report` —
  composed `browser/api-first` plus `browser/build-automation` successfully
  (about 3.7k tokens) without loading `browser/playwright`; its generic
  end-of-command control sweep then hit the primary checkout's read-only
  `index.lock` boundary.
- Commit: `415a4aee` (`Move browser automation setup to a bootstrap skill`).
- Final `git fetch origin main && git rebase FETCH_HEAD` — branch already up
  to date; recorded checkout is clean and one commit ahead of `origin/main`.
- No push and no PR in this step.

## Peer review

Reviewed the branch diff vs `main` from the recorded worktree. `/code-review`
is user-triggered only and cannot be self-invoked, so the review was done
directly against the diff rather than blocking on the tool.

Checks performed:

- Repo-wide sweep for references to the removed `browser/build-automation`
  *workflow* and the removed `tasks/browser-automation` template. The only
  surviving mention is prose in `coga/contexts/autonomy/triage/SKILL.md:47`
  (and its packaged twin), which names `browser/build-automation` as the
  narrower browser triage — still accurate now that the name is a skill. Not a
  dangling ref; no change needed.
- Both `coga/workflows/browser/` and the packaged twin are fully removed, with
  no empty leftover directories.
- Every target the new skill and launcher reference exists:
  `browser/api-first`, `browser/dom-backed`, `browser/playwright`, and
  `autonomy/{fully-automated,human-verify,human-only}`.
- Skill-ref convention matches the existing layout — refs mirror the path under
  `bootstrap/skills/`, so `browser/build-automation` is consistent with the
  sibling `browser/playwright`.
- Packaging: `pyproject.toml` excludes `bootstrap/` from the `packages` walk and
  force-includes the whole tree, so the new skill ships; `test_packaging.py`
  asserts both new paths.
- The package-only placement of the bundled skill is the established convention
  for bootstrap resources (`bootstrap/skills/browser/playwright`,
  `bootstrap/skills/bootstrap/ticket`), so no live `coga/` twin is owed here —
  the sync rule applies to shipped contexts/templates, not bootstrap skills.

No must-fix findings. No code changes applied in this step, so no additional
commit.

## PR

**Summary**

Fresh `coga init` no longer seeds a generic `browser-automation` draft ticket.
The browser automation entry point survives as reusable capability rather than
standing user-owned work:

- Deletes the packaged `tasks/browser-automation.md` template and its stale
  audit line from the packaged `log.md`.
- Moves the four-phase router/orchestration methodology out of the
  `browser/build-automation` *workflow* (both the live and packaged copies are
  removed) and into a bundled `browser/build-automation` *skill*.
- Exposes it through a stateless package-backed launcher,
  `coga launch bootstrap/browser-automation`, which composes the router skill
  with the `browser/api-first` context. Launching it creates no standing task;
  only the concrete ticket the skill authors becomes durable work.
- Keeps `browser/playwright` as the separate lower-level runner, attached to a
  concrete ticket only when browser execution is actually needed.
- Documents the launcher and the orchestration-vs-runner split in `README.md`
  and the packaged `coga/cli` context.

Browser contexts, autonomy workflows, the router skill, and Playwright
capability all remain available on both empty and filled installs.

**Test plan**

`python -m pytest` — 1327 passed, 1 skipped (the skip is the packaging test when
`hatchling` is absent; rerun with the build backend available it passes).
`coga validate --json` from `example/` reports 1 ok, 0 issues, and
`coga launch bootstrap/browser-automation --prompt-report` composes
`browser/api-first` plus `browser/build-automation` without loading
`browser/playwright`.

## Dream Skill: validate-drift

Generated: 2026-07-19T05:39:18+00:00
Command: `coga validate --json --fix`
Task: `move-browser-automation-entry-point-out-of-seeded`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-19T05:47:19+00:00
Command: `coga validate --json --fix`
Task: `move-browser-automation-entry-point-out-of-seeded`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-19T05:51:07+00:00
Command: `coga validate --json --fix`
Task: `move-browser-automation-entry-point-out-of-seeded`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-19T05:52:17+00:00
Command: `coga validate --json --fix`
Task: `move-browser-automation-entry-point-out-of-seeded`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

---

## Blockers

- [ ] [2026-07-18 22:58] [agent:codex] id=20260718T225852 Publication prerequisites are unavailable: the live checkout is not on main and its shared Git metadata is read-only, github.com DNS resolution fails, and gh has no authenticated host. Restore a writable main control checkout, GitHub reachability, and gh authentication, then unblock and rerun coga open-pr.

- [ ] [2026-07-19 12:44] [agent:codex] id=20260719T124435 Publication remains blocked: the live control checkout is still on status-updated-git-fallback rather than main, github.com DNS resolution still fails, and gh has no authenticated host. Provide a writable main control checkout with GitHub reachability and authenticated gh, then unblock and rerun coga open-pr.
