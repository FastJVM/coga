---
slug: clean-up-workflows-and-make-sure-they-re-in-bootst
title: clean up workflows and make sure they're in bootstrap
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/codebase
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
step: 1 (implement)
---

## Description

Audit every workflow that ships with Coga, delete the dead/one-off ones, and
make sure every keeper lives in the **correct** packaged tree. This is a
cleanup + correct-placement task, **not** a packaging-mechanism rewrite.

Explicitly out of scope: do **not** try to consolidate the two packaged
workflow locations into one. They are intentionally distinct lifecycles (see
Context) — collapsing them would lose a real property. The goal is hygiene:
remove cruft, triage the three unclassified one-offs, and ensure each surviving
workflow sits in whichever of the two trees matches its intended lifecycle,
with the live `coga/` copy and packaged copy in sync.

Done looks like: dead workflows deleted; the three one-offs each resolved
(keep / promote to a packaged tree / delete); every keeper in the right tree;
live and packaged copies in sync; `coga validate --json` and `python -m pytest`
clean; PR opened for review.

## Context

**The two packaged trees are intentional — keep both.** Packaged workflows live
in two locations that serve *different lifecycles*, verified in code
(`copy_fresh_templates`, `src/coga/commands/update.py:267`, copies the template
tree with `skip_top={"bootstrap"}`):

- `src/coga/resources/templates/coga/workflows/` — the **seed template**.
  Copied into a new repo's `coga/workflows/` at init, so the repo then *owns
  and can edit* these (e.g. autonomy levels, sweeps, onboarding, direct). They
  freeze at seed time and do not auto-upgrade. Currently holds:
  `autoclose-merged, autonomy, blocker-reminders, branch-sweep, browser,
  build/onboarding, direct, skill-update, _template.md`.
- `src/coga/resources/templates/coga/bootstrap/workflows/` — **bundled
  batteries**. Never copied into a repo; resolved at runtime and therefore
  *upgrade with the installed coga version*. Currently holds:
  `code, digest, docs, dream`.

So placement is a real decision per workflow: repo-owned/customizable →
seed tree; upgrades-with-coga → bootstrap tree. `resolve_workflow_path`
(`src/coga/paths.py:24`) is local-first: a repo's own `coga/workflows/<ref>.md`
overrides the packaged `bootstrap/workflows/<ref>.md` fallback.

**Investigate these three** (decide keep / promote-to-correct-tree / delete per
workflow — not assumed) — they exist in the live repo but in neither packaged
location, so they look like local one-offs:

- `coga/workflows/build/dry-run.md`
- `coga/workflows/coga/cutover.md`
- `coga/workflows/test/relaunch-chain.md`

**Keep the two copies in sync.** Per `CLAUDE.md`, any shipped-workflow change
must touch both the live repo copy under `coga/workflows/` and the packaged
copy under `src/coga/resources/templates/coga/…`. Note the live
`coga/workflows/` currently carries local copies of the batteries (code,
digest, docs, dream, plus coga/, test/) via the local-first override — factor
that into the sync plan. Watch the hatchling packaging gotcha the
`coga/codebase` context calls out (force-include of `_template` dirs).

**Files likely in scope:** the workflow markdown trees in both live and
packaged locations, `src/coga/validate.py`, and `pyproject.toml`/hatchling
include rules if a tree's file set changes. The resolver (`paths.py`) and
init-seed logic should **not** need behavioral changes — if you find yourself
rewriting them, the scope has crept past cleanup; stop and reconsider. Run
`coga validate --json` and `python -m pytest` after changes.

**Autonomy note:** triaged fully-automated, but the chosen `code/with-review`
workflow ends with an owner review gate — the human still approves the PR
before merge. That gate is intentional and fine; treat it as the commit point.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
