---
slug: cleanup/add-a-debug-mode-to-init-for-vendoring-from-source
title: Vendor the init venv from PyPI only, dropping source-install paths
status: draft
owner: nicktoper
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (design)
---

## Description

`coga init` currently resolves the CLI it vendors through three tiers in
`resolve_install_source()` (`src/coga/commands/update.py:66`): a
`COGA_REPO_URL` override, the source checkout the running package is imported
from, then `coga==<running version>` from PyPI. Collapse that to the last one.
A user's repo should always vendor a release; the two source paths are
complexity serving a workflow nobody uses.

**Scrub, in the implement step:**

1. Delete the `COGA_REPO_URL` override and `_running_checkout_root()` from the
   resolution path, leaving `resolve_install_source()` as
   `coga==<running version>` from PyPI. `InstallSource.kind` collapses to a
   single case; `_checkout_install_source()`, `_pyproject_project_name()` and
   `pip_git_source()` go with it. Keep `redacted_git_source()` — it has 8
   other callers.
2. Fail clearly when the running version isn't on PyPI (the unreleased-main
   case), rather than surfacing a raw pip error. The message should say init
   vendors releases only and name the version it tried.
3. Rewrite the packaged
   `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md:27-38`
   paragraph, which documents the three-tier behaviour.
4. Drop the now-dead tests in `tests/test_init.py:320-412` (seven tests, of
   which the override and checkout ones go entirely) and cover the new failure
   message.
5. Document the resulting behaviour in `docs/development.md` and
   `docs/releasing.md`, which say nothing about it today. Consider documenting
   `COGA_PYTHON` (`update.py:420`) in the same pass — it is undocumented in
   exactly the same way.

**The design step's remit is narrow**, because the decision above is made. It
owes the owner: the sequencing call (see the blocker below), the exact wording
and exit behaviour of the new failure, and confirmation that nothing outside
`init.py:827` / `install_venv()` depends on the removed tiers.

**Out of scope.** Do not remove or redesign the vendored venv itself. Do not
touch managed-skill installs. Do not change the `COGA_PIN` format. Do not
publish to PyPI.

## Context

**Blocker: this cannot land before 1.0 is on PyPI.** This repo is `0.3.1` and
PyPI serves `0.2.0`. Once the source tiers are gone, `coga init` run from
either coga checkout resolves `coga==0.3.1`, which does not exist, and fails.
The implement step must wait for `cleanup/publish-coga-1-0-to-pypi` (and
`cleanup/yank-the-pypi-0-0-1-placeholder-and-document-the-f`). The
`review-design` gate is the checkpoint for that: design now, implement after
1.0 ships. Note the same failure recurs for anyone running unreleased main
afterwards — that is accepted, which is why item 2 above exists.

**Why the source tiers aren't needed (verified 2026-09-05).** Neither coga
development checkout has a vendored venv at all — no `coga/.coga/.venv`, no
`COGA_PIN`, in either `/home/n/Code/codex/coga` or `/home/n/Code/claude/coga`.
Both run the global `uv tool` editable install (`~/.local/bin/coga` →
`~/.local/share/uv/tools/coga/bin/coga`, `direct_url.json` pointing at the
claude checkout). Coga developers install the CLI from source and run it
globally; the vendored venv is a user's-repo artifact. So the "developers need
a source lever to test init" justification does not hold.

**The bug that started this, and why removal beats a flag.** The middle tier
silently picks whatever checkout the running package is imported from. With
the owner's editable install linked to `/home/n/Code/claude/coga`, running
`coga init` from `/home/n/Code/codex/coga` vendors the *claude* checkout —
wrong bytes, no warning, no output naming the source. The original plan was to
add `--from-source PATH` to disambiguate; deleting the implicit tier removes
the ambiguity instead of adding surface to manage it.

**Blast radius.** One real caller of `resolve_install_source()`:
`init.py:827`, which resolves before any writes so a bad source fails loud
leaving nothing on disk. Plus `install_venv()`'s default argument
(`update.py:609`). Tests are `tests/test_init.py:320-412`.

**Docs surfaces.** `docs/development.md` and `docs/releasing.md` contain zero
mention of `COGA_REPO_URL` or source-vendoring — nothing to delete there, only
the new behaviour to describe. `docs/migrating-to-coga.md:14` lists
`COGA_REPO_URL` in the Relay→Coga rename table and must lose the row.
`docs/reference.md:14-19` enumerates `coga init`'s arguments; no flag is being
added, so it needs no new option, but check it says nothing stale.
`docs/releasing.md:87` states the install gate "deliberately installs Coga
only from PyPI" — after this change that becomes true of *all* init runs, so
the paragraph can be simplified rather than contradicted.

**Twin-rule exception.** CLAUDE.md requires live and packaged copies of
shipped contexts to be edited together, but the packaged
`bootstrap/contexts/coga/cli/SKILL.md` has no live twin —
`coga/contexts/coga/cli/` does not exist. `cli` is packaged-only. Do not hunt
for one.

**Unchanged by this ticket:** the vendored venv is built with stdlib
`python -m venv` (`update.py:672`) and `<venv>/bin/python -m pip install`
(`update.py:693`), with a second pip pass in `install_skill_requirements`
(`update.py:752`). uv is how a developer installs the CLI, not how init builds
`.coga/.venv`. Leave that alone.

Source: `marketing/phase-0-audit` step 1 (2026-09-02), triaged by the owner in
step 2 (2026-09-03) with `code/design-then-implement`; re-scoped 2026-09-05
from "add a debug mode" through "simplify the tiers" to "delete the source
tiers", after confirming no development checkout uses a vendored venv. This
directory holds the work the owner wants done before the marketing materials
ship.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
