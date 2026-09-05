---
slug: cleanup/add-a-debug-mode-to-init-for-vendoring-from-source
title: Document and surface vendoring init from a source checkout
status: draft
owner: nicktoper
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
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
step: 1 (implement)
---

## Description

`coga init` can already vendor the CLI from a local source checkout instead of
a PyPI release — it auto-detects an editable/in-tree run, and honours a
`COGA_REPO_URL` override — but no contributor-facing doc says so, and the mode
has no explicit command-line surface. Add `coga init --from-source [PATH]` as
that surface, and document both it and the existing env vars.

The design decisions were closed when this ticket was scoped (2026-09-05); do
not reopen them. **Build exactly this:**

1. Add `--from-source [PATH]` to `coga init`. It feeds the *existing*
   `resolve_install_source()` override path — the same code `COGA_REPO_URL`
   already uses — with the flag taking precedence over the env var. Do not add
   a second resolution path.
2. Document source-vendoring in `docs/development.md` (contributor
   explanation), `docs/reference.md` (the new flag, in the `coga init` option
   list), and `docs/releasing.md` (how the release path differs). Include
   `COGA_PYTHON` in the same env-var table — it is undocumented in exactly the
   same way and costs almost nothing to add here.
3. Extend the existing tests in `tests/test_init.py:320-412`.

**Out of scope, deliberately.** Do not change the `.coga/COGA_PIN` format
(reasoning below). Do not touch managed-skill installs. Do not fix the
PyPI-version-not-published problem — that belongs to the sibling tickets
`cleanup/publish-coga-1-0-to-pypi` and
`cleanup/yank-the-pypi-0-0-1-placeholder-and-document-the-f`.

**Done means:** running `coga init --from-source .` from a wheel install
vendors the named checkout; `docs/development.md`, `docs/reference.md` and
`docs/releasing.md` each describe the source-vs-release distinction and name
`COGA_REPO_URL` and `COGA_PYTHON`; `python -m pytest` passes with new
coverage for the flag; nothing else in the resolution logic changed.

## Context

**What already exists — read before writing code.** Commit `a96c3e1e`
("Vendor CLI from installed package not git clone", #590) landed the
resolution logic. It lives in `src/coga/commands/update.py`, not `init.py`:
`init.py:827` only calls `resolve_install_source()`, before any writes, so a
bad source fails loud and leaves nothing on disk. `resolve_install_source()`
(`update.py:66`) picks a source in this order:

1. `COGA_REPO_URL` — a local checkout path, or a git URL pip can install
   from. Credential-redacted for display.
2. The source checkout the running package is imported from, via
   `_running_checkout_root()` (`update.py:114`): package at `<root>/src/coga/`
   under a root whose `pyproject.toml` declares project name `coga`. A wheel
   install in site-packages never has that shape.
3. Otherwise `coga==<running version>` from PyPI.

The new flag becomes tier 0. The original audit finding ("no way to init from
a development checkout by default") is stale for the editable case — tier 2
already handles it. What it does not cover is a *wheel* install pointed at an
arbitrary checkout without knowing the env var, which is what the flag is for.

**Doc surfaces, all three.** `docs/development.md` and `docs/releasing.md`
contain zero mention of `COGA_REPO_URL` or source-vendoring.
`docs/reference.md:14-19` is where `coga init`'s `PATH` argument and `--user`
option are enumerated — the new flag must land there. `docs/README.md`
advertises reference.md as "generated from the CLI's own help", but there is
no generator; it is hand-maintained.

Two existing mentions to stay consistent with, rather than duplicate:
`docs/migrating-to-coga.md:14` lists `COGA_REPO_URL` in the Relay→Coga rename
table (a name mapping, not an explanation), and the packaged context
`src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md:31`
describes it in passing.

**A collision to amend, not contradict.** `docs/releasing.md:87` ("Clean
first-install gate") states the harness "deliberately installs Coga only from
PyPI." That is deliberate and should stay true of the release gate; word the
new section so it explains the contributor path *alongside* that stance.

**Twin-rule exception.** CLAUDE.md requires live and packaged copies of
shipped contexts to be edited together, but the packaged
`bootstrap/contexts/coga/cli/SKILL.md` has **no live twin** — `coga/contexts/
coga/cli/` does not exist in this repo. `cli` is packaged-only. Do not go
hunting for a live copy to sync.

**Why COGA_PIN stays as-is.** `write_pin()` (`update.py:204`) records
`InstallSource.display` — for a checkout the bare path
(`_checkout_install_source`, `update.py:133`), for a release
`coga==<version> (PyPI)`. A reader can already tell source from release. It
cannot distinguish an explicit override from auto-detection, because the
`origin` string is only used in error text — but the file is parsed
positionally by `read_pin_source()` and `read_pin()`, so changing its format
is a persisted-format change well outside "contributor convenience". Leave it.

**Why managed skills are out of scope.** Init's other network reach is
`install_managed_skills` (`init.py:897` → `src/coga/managed_skills.py`), which
shells out to `gh skill` per install. There is no local coga checkout
containing those skills, so vendoring from source cannot help them; it is a
different subsystem with a different failure mode.

**Closest prior art** for an operator env var on the init/vendoring path:
`coga/contexts/coga/codebase/SKILL.md:229-240`, on `install_skill_requirements`
and on `COGA_PYTHON` as the vendored-venv interpreter override. Cited rather
than attached — that context is ~27 KB and would triple this prompt.

Source: `marketing/phase-0-audit` step 1 (2026-09-02), triaged by the owner in
step 2 (2026-09-03), re-scoped and decisions closed 2026-09-05 against the
post-#590 code. This directory holds the work the owner wants done before the
marketing materials ship.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
