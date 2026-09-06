---
slug: cleanup/add-a-debug-mode-to-init-for-vendoring-from-source
title: Simplify how coga init picks the CLI it vendors
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

`coga init` decides where the vendored CLI comes from in
`resolve_install_source()` (`src/coga/commands/update.py:66`). Its middle tier
— implicitly using whatever source checkout the running package is imported
from — silently picks the wrong checkout when a developer has more than one,
with no output saying which it chose. The owner wants that implicit path gone
and the whole resolution simplified.

**Design this, then implement it.** The decision the design step owes the
owner is the shape of the tiers, in particular:

1. **Implicit detection goes — how far?** Delete `_running_checkout_root()`
   outright, or keep it purely as a *diagnostic* that refuses with a useful
   remediation naming the detected path when no explicit source was given?
   Deleting it outright means a developer on an unreleased version gets a raw
   `pip` failure instead of an explanation.
2. **Does explicit source-vendoring earn its keep at all?** The minimal end
   state is one tier: always `coga==<running version>` from PyPI, with no
   source path. See the sequencing constraint below before proposing it.
3. **If an explicit path stays,** is it `COGA_REPO_URL` (already exists),
   a `--from-source PATH` flag, or both — and which wins?

Then document whatever survives. The resolution logic is currently
undocumented in every contributor-facing doc; that gap is in scope regardless
of which shape wins.

**Out of scope.** Do not remove or redesign the vendored venv itself. Do not
touch managed-skill installs. Do not publish anything to PyPI.

## Context

**The bug that triggered this, reproduced live (2026-09-05).** The owner's
`coga` is a uv tool install that is *editable*, linked to a different checkout
than the one being worked in:

```
/home/n/.local/bin/coga → ~/.local/share/uv/tools/coga/bin/coga
direct_url.json: {"url":"file:///home/n/Code/claude/coga","dir_info":{"editable":true}}
imports from:    /home/n/Code/claude/coga/src/coga/__init__.py
```

Running `coga init` from `/home/n/Code/codex/coga` therefore vendors the
`claude` checkout. Tier 2 fires, succeeds, and prints nothing about which
source it chose. Wrong bytes, no error — this is the whole reason the ticket
exists.

**Current shape.** `resolve_install_source()` (`update.py:66`) picks, in
order: `COGA_REPO_URL` (a checkout path or a pip-installable git URL,
credential-redacted); the running package's own checkout via
`_running_checkout_root()` (`update.py:114` — package at `<root>/src/coga/`
under a root whose `pyproject.toml` declares `coga`, so only *editable*
installs match); else `coga==<running version>` from PyPI.

**Blast radius is small.** One real caller: `init.py:827`, which resolves
before any writes so a bad source fails loud leaving nothing on disk (plus
`install_venv()`'s default argument, `update.py:609`). Tests are
`tests/test_init.py:320-412`, seven of them; `test_running_checkout_root_finds_this_checkout`
(`:417`) and `test_resolve_install_source_prefers_running_checkout` (`:386`)
are the two that encode the behaviour under question.

**Sequencing constraint on "just always use PyPI".** That is the simplest
possible end state, and it is not free today: this repo is `0.3.1` and PyPI
serves `0.2.0`, so `pip install coga==0.3.1` fails and init cannot run at all
from this checkout. That is precisely the original audit finding. It becomes
safe only after `cleanup/publish-coga-1-0-to-pypi` and
`cleanup/yank-the-pypi-0-0-1-placeholder-and-document-the-f` land — and even
then it re-breaks for anyone working on unreleased main. If the design
proposes this, it must say what a contributor on unreleased main does instead.

**Constraint: the vendored venv stays.** `coga/.coga/.venv` plus
`.coga/COGA_PIN` is the per-repo pinning guarantee — each repo runs the CLI
that initialized it, which `COGA_PIN`, version-skew detection and
`coga uninstall` all depend on. A global `uv tool install` gives one shared
CLI, which is a different property, not a replacement. Do not propose
deleting the venv; that is an architecture change needing its own ticket.
`COGA_PIN` format is likewise fixed: `read_pin_source()` and `read_pin()`
parse it positionally.

**Docs to update once the shape is settled.** `docs/development.md` and
`docs/releasing.md` contain zero mention of `COGA_REPO_URL` or
source-vendoring. `docs/reference.md:14-19` enumerates `coga init`'s
arguments (`PATH`, `--user`) and is where any new flag must land — despite
`docs/README.md` calling it "generated from the CLI's own help", it is
hand-maintained. Two existing mentions to keep consistent rather than
duplicate: `docs/migrating-to-coga.md:14` (Relay→Coga rename table) and the
packaged context
`src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md:27-38`,
which documents the current three-tier behaviour and will need rewriting.
`docs/releasing.md:87` states the install gate "deliberately installs Coga
only from PyPI" — that stance stays true; word around it rather than
contradicting it.

Consider documenting `COGA_PYTHON` (`update.py:420`, the vendored-venv
interpreter override) in the same pass — it is undocumented in exactly the
same way for near-zero extra cost.

**Twin-rule exception.** CLAUDE.md requires live and packaged copies of
shipped contexts to be edited together, but the packaged
`bootstrap/contexts/coga/cli/SKILL.md` has no live twin —
`coga/contexts/coga/cli/` does not exist. `cli` is packaged-only. Do not hunt
for one.

**Prior art** for an operator env var on this path:
`coga/contexts/coga/codebase/SKILL.md:229-240`, on `install_skill_requirements`
and `COGA_PYTHON`. Cited rather than attached — that context is ~27 KB.

**Note on the vendored venv's own tooling:** it is stdlib `python -m venv`
(`update.py:672`) plus `<venv>/bin/python -m pip install <spec>`
(`update.py:693`), with a second pip pass in `install_skill_requirements`
(`update.py:752`). uv is how a developer installs the *CLI*; it is not used to
build `.coga/.venv`, and this ticket does not change that.

Source: `marketing/phase-0-audit` step 1 (2026-09-02), triaged by the owner in
step 2 (2026-09-03) with `code/design-then-implement`; re-scoped 2026-09-05
from "add a debug mode" to "simplify the resolution" after the silent
wrong-checkout behaviour was reproduced. This directory holds the work the
owner wants done before the marketing materials ship.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
