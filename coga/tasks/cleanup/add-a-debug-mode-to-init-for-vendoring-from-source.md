---
slug: cleanup/add-a-debug-mode-to-init-for-vendoring-from-source
title: Add a debug mode to init for vendoring from source instead of PyPI
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

Give `coga init` an explicit, documented way to vendor the CLI from a local
source checkout instead of a PyPI release. Coga already *does* this — it
auto-detects an editable/in-tree run and accepts a `COGA_REPO_URL` override —
but neither behaviour is documented anywhere, and there is no explicit flag,
so a contributor still has to be told the trick or read `update.py` to know
the mode exists. Add the surface and write the docs.

## Context

**What already exists (read this before designing anything).** Commit
`a96c3e1e` ("Vendor CLI from installed package not git clone", #590) landed
the resolution logic. It lives in `src/coga/commands/update.py`, not
`init.py` — `init.py:827` only calls `resolve_install_source()`, before any
writes, so a bad source fails loud and leaves nothing on disk.
`resolve_install_source()` (`update.py:66`) picks a source in this order:

1. `COGA_REPO_URL` — a local checkout path, or a git URL pip can install
   from. Credential-redacted for display.
2. The source checkout the running package is imported from, detected by
   `_running_checkout_root()` (`update.py:113`): package at `<root>/src/coga/`
   under a root whose `pyproject.toml` declares project name `coga`. A
   wheel install in site-packages never has that shape.
3. Otherwise `coga==<running version>` from PyPI.

So running `coga init` from an editable checkout of this repo already vendors
that checkout — the original audit finding ("no way to init from a development
checkout by default") is stale. Do not re-litigate auto-detection; it works.

**What is actually missing.**

1. **No explicit surface.** `coga init` has exactly one option, `--user`
   (`init.py:430`). There is no `--from-source [PATH]`, so the mode can only
   be entered implicitly (be running from a checkout) or via an env var no
   doc mentions. Decide whether to add the flag, bless the env var in docs,
   or both — and whether the flag should just set the same override path
   `COGA_REPO_URL` already takes.
2. **Zero documentation.** Neither `docs/development.md` nor
   `docs/releasing.md` mentions `COGA_REPO_URL`, source-vendoring, or the
   auto-detection. `docs/development.md` is the natural home for the
   contributor-facing explanation; `docs/releasing.md` should say how the
   release path differs. The packaged context
   `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md:31`
   already mentions `COGA_REPO_URL` in passing — keep it consistent.
3. **Provenance is only half-recorded.** `write_pin()` (`update.py:213`)
   writes `InstallSource.display` to `.coga/COGA_PIN`. For a checkout that is
   the bare path (`_checkout_install_source`, `update.py:147`); for a release
   it is `coga==<version> (PyPI)`. A reader can tell source from release, but
   the pin does not distinguish an explicit override from auto-detection — the
   `origin` string ("running source checkout" / "`COGA_REPO_URL` override")
   is used only in error text. Decide whether that distinction is worth
   recording, or whether path-vs-PyPI is enough.
4. **`coga skill` installs also reach the network** and were never considered
   here. Decide in-scope or explicitly out-of-scope, and say so.

**Scope.** This is a contributor convenience, not a new packaging system.
Keep the change small: a flag and/or a documented env var plus docs, reusing
`resolve_install_source()` rather than adding a second resolution path. Tests
for the existing behaviour are in `tests/test_init.py:323-404`; extend those
rather than starting a new file.

Source: `marketing/phase-0-audit` step 1 (2026-09-02), triaged by the owner
in step 2 (2026-09-03), re-scoped 2026-09-05 against the post-#590 code. This
directory holds the work the owner wants done before the marketing materials
ship.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
