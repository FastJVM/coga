---
slug: install/pip-hash-requirement-breaks-editable-install
title: pip hash-checking mode breaks editable install
status: in_progress
mode: agent
owner: zach
human: zach
agent: claude
assignee: codex
contexts:
- dev/code
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
  - name: review
    skills: []
    assignee: owner
secrets: null
step: 2 (peer-review)
---

## Description

A new user whose pip has global hash-checking mode enabled (a common managed
work-machine setting) can't run `pip install -e .` — editable installs carry no
hashes, so pip aborts. It's only workaroundable via an env var the user had to
dig to find. Make the documented install path either not depend on an editable
install for first-run, or detect the hash-checking failure and surface the exact
remediation instead of a raw pip traceback.

## Context

Reported by Greg, an external new user, on a managed work machine. The
documented quickstart leads with `pip install -e .` (CLAUDE.md "Build, Test,
and Development Commands"). This is the first domino in his install attempt — it
also caused the partial `relay init` failure tracked by
`install/init-does-not-persist-user-then-blocks-on-reinit`. Broader install
robustness is the umbrella `install/harden-packaging-and-install-before-launch`.

**Retest 2026-07-08 (fresh-container):** still broken. `PIP_REQUIRE_HASHES=1`
raw-fails both `pip install coga` ("requirements must have versions pinned")
and `pip install -e .` ("no single file to hash") with no coga-side detection
and no docs mention. Partial mitigation shipped: README now leads with
`uv tool install coga`, which ignores pip config. Remaining work: document
the uv escape hatch next to the pip instructions (README Install), and/or
detect the failure and print the remediation.

<!-- coga:blackboard -->

## Dev
branch: pip-hash-hint
worktree: /home/n/Code/claude/coga/.coga/worktrees/coga-pip-hash-hint

## Plan (implement step)

Two remaining deliverables per the retest note:

1. **README Install docs** — add a short "hash-checking mode" note next to the
   pip instructions: what the failure looks like ("Hashes are required in
   --require-hashes mode" / "no single file to hash"), why (managed-machine
   `PIP_REQUIRE_HASHES=1` or `require-hashes` in pip config), and the escape
   hatches: `uv tool install coga` (ignores pip config) or prefix the pip
   command with `PIP_REQUIRE_HASHES=0`.
2. **Runtime detection** — coga itself runs pip at runtime: `install_venv()`
   and `install_skill_requirements()` in `src/coga/commands/update.py`
   pip-install into `.coga/.venv` during `coga init`/`coga update`. Under
   global hash-checking mode those subprocess pip calls fail with the same raw
   error. Add a helper that recognizes hash-checking-mode stderr and appends
   the exact remediation (`PIP_REQUIRE_HASHES=0 coga init …`) to both failure
   messages, instead of only dumping pip stderr.

Decision: detect + print remediation, do NOT silently set
`PIP_REQUIRE_HASHES=0` on coga's own pip subprocesses — managed machines set
that policy deliberately; overriding it silently changes security posture.

Tests: extend tests/test_skill_requirements.py style (fake subprocess.run,
returncode=1 with hash-mode stderr) asserting the remediation text is printed.

## Implemented (commit c5620c34 on pip-hash-hint)

- **README.md** Install section: after the `pip install -e .` block, a
  paragraph naming the two failure strings, the cause
  (`PIP_REQUIRE_HASHES=1` / `require-hashes` pip config on managed machines),
  and both escape hatches (`uv tool install coga`; `PIP_REQUIRE_HASHES=0`
  prefix on the pip command).
- **src/coga/commands/update.py**: new `hash_checking_hint(stderr)` helper +
  `_HASH_MODE_MARKERS`; both pip-failure paths (`install_venv`,
  `install_skill_requirements`) append the remediation
  (`PIP_REQUIRE_HASHES=0 coga init …`) when stderr matches. No silent
  override of the machine's hash policy (see decision above).
- **tests/test_skill_requirements.py**: 3 new tests — remediation printed on
  hash-mode failure, hint recognizes all three real pip error shapes, hint
  stays empty for unrelated failures.

Verification (all in a python3.12 venv, coga installed editable):
- `python -m pytest` — 1152 passed, 1 skipped, 0 failed. (With coga *not*
  installed for the interpreter, `test_bootstrap_script_launch_is_stateless`
  fails with ModuleNotFoundError — pre-existing environment artifact, fails
  identically on unmodified main.)
- Real-pip check: ran `pip install flask` and `pip install -e .` under
  `PIP_REQUIRE_HASHES=1`; both real stderr shapes match the markers
  (`detected=True`), and the test fixtures use pip's verbatim strings.
- Runtime path end-to-end: `install_skill_requirements` under
  `PIP_REQUIRE_HASHES=1` against the packaged skills fails on the first
  unpinned requirement and prints the full remediation block, exit 2.

Not done (scoping): CLAUDE.md/AGENTS.md still lead with `pip install -e .`
for dev setup — retest note scoped remaining docs work to README Install;
dev-env readers hitting this now get the pointer from coga's own error
message. docs/migrating-to-coga.md also mentions `pip install -e .`
(untouched, same reasoning).
