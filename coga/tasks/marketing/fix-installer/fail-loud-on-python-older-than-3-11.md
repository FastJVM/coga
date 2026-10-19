---
title: Fail loud on Python older than 3.11
status: done
owner: nicktoper
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
agent: claude
---

## Description

On Python 3.10 (Ubuntu 22.04 and other older distros), `pip install coga` silently installs the unyanked `coga 0.0.1` placeholder (`requires_python >=3.9`) and leaves no `coga` command, with no error: a Fail-loud violation. A venv does not help because it reuses the same interpreter. Plan agreed 2026-10-12: (1) owner yanks `coga 0.0.1` on PyPI so pip refuses with a clear Requires-Python error (human-only step; the agent confirms it via the PyPI JSON `yanked` flag and stops to ask if it is still unyanked); (2) update `coga/install` (canonical `docs/contexts/coga/install/SKILL.md` and its packaged twin) and the README install section to lead with `uv tool install coga`, which fetches a managed Python 3.11+ when none is present, give the old-Python remedy (`uv tool install coga` or `pipx install --python python3.11 coga`), and replace the note that calls the 0.0.1 install expected behaviour; (3) optionally add a Python 3.10 case to the Linux clean-install harness asserting that pip fails loudly and uv succeeds. Rejected: lowering the floor to 3.10 via `tomli`, because 3.10 reaches end of life in October 2026. Done means docs and twin are merged, the yank is confirmed, and any harness change has run with recorded evidence.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Yank check (2026-10-14, historical; resolved below)

- `curl -s https://pypi.org/pypi/coga/json`: `coga 0.0.1` wheel and sdist both report `yanked: false` (`requires_python >=3.9`); 0.2.0 and 0.4.0 are `>=3.11`, latest 0.4.0.
- Per the agreed plan, the agent stops and asks while 0.0.1 is unyanked: the doc change claims pip fails loudly on Python < 3.11, which is only true after the yank. No branch created yet; start check passed (clean `main` at `origin/main` 7ddde4be3).
- To resume: owner yanks 0.0.1 at https://pypi.org/manage/project/coga/release/0.0.1/ (Options → Yank), then `coga unblock`; the next session re-checks the JSON flag and proceeds with docs + twin + README (and optional 3.10 harness case).

---

## Blockers

- [x] [2026-10-14 11:46] [agent:claude] id=20261014T114630 coga 0.0.1 is still unyanked on PyPI (JSON yanked=false for wheel and sdist, checked 2026-10-14). Please yank it at https://pypi.org/manage/project/coga/release/0.0.1/ so pip on Python <3.11 fails with a Requires-Python error, then unblock; the docs change depends on that behaviour.
  resolved: [2026-10-16 10:51] [human:nicktoper] Owner confirmed the PyPI yank; verified both coga 0.0.1 wheel and sdist report yanked=true in the PyPI release JSON. Proceed with install documentation updates.

---

## Blocker reminders

- cdbf327e37e9 last_reminded: 2026-10-16 09:31


## Dev

pr: https://github.com/FastJVM/coga/pull/1030
branch: fix-old-python-install

## Implementation plan (2026-10-16)

- Owner yanked 0.0.1; both release files verified `yanked: true` through https://pypi.org/pypi/coga/0.0.1/json. `coga unblock` recorded the resolution.
- Follow the agreed documentation plan: README summary plus canonical install topic and its packaged twin; explain uv-managed Python and explicit pipx interpreter selection, and why a venv alone does not upgrade Python.
- Keep the optional Linux harness extension out of this documentation change. Verify live installer behavior in isolated temporary directories and run the required suite; retain commands and results in the handoff.


## Implement handoff (2026-10-16)

- Owner's yank is confirmed for both 0.0.1 release files; `coga unblock` resolved the ask before implementation.
- Pushed `fix-old-python-install` at `c7ec5b99c39efaac1f2cc3ed48d9bff13442f2c4`, based on current main `985673f1b60930e87f24a465c2b64f3b5bc0f118`. No PR opened; peer review is next.
- README leads with uv and summarizes managed Python. Canonical install topic and byte-identical packaged twin describe old-Python errors, explicit pipx Python selection, uv configuration caveats, the yanked placeholder and why a venv alone cannot upgrade Python.
- Live check: Python 3.10.20 pip install fails with Requires-Python diagnostics; uv 0.11.28 with only Python 3.10 visible downloads Python 3.11.15 and installs Coga 0.4.0; help/version pass from /tmp. These external checks are receipts, not a permanent Linux harness extension.
- Full suite: 3672 passed on Python 3.12.12. Final freshness rebase imported only unrelated ticket/log updates; code/docs/tests/package config are unchanged. Fresh final packaging run: 22 passed. No new regression test or fixture changes for this docs-only PR; live installer behavior is externally controlled by the verified PyPI yank.
- Tests ran on committed documentation. Earlier installer probes exercised live PyPI independently of repository content; receipt OIDs are kept as historical evidence, not relabeled after rebase.
- No unresolved implementation issue. Independent review and merge remain. Repository-local logs: `/tmp/coga-old-python-check/pytest.log` and `/tmp/coga-old-python-check/packaging.log` (temporary, not durable evidence owners).

## Peer review

- Direct Codex review **completed** on head `ff906aac46d3a5c95869977f6cb44e43ca96e952` against base `c8db8ab524c5da7b782d3dcbda95b6c0f27d2b85`: **no must-fix findings**. All three diff paths reviewed; no code or documentation fixes needed.
- Actual implementer and reviewer are both Codex; recorded as **self-review**, with no claim of independence from configured peer selection or a fresh session. No child review CLI or subagents used.
- Rebased onto fetched main, re-reviewed the resulting diff, and pushed with `--force-with-lease`. The final freshness fetch found main unchanged. The installation diff remained identical through both rebases.
- Full suite: `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest` → **3683 passed, 5 skipped**, Python 3.12.12, 548.43s. Windows PowerShell tests account for the skips. An earlier partial run was interrupted when main advanced; it is not claimed as a successful check.
- Fresh external checks confirmed both placeholder files yanked, pip on Python 3.10.20 exiting 1 with Requires-Python diagnostics, and isolated uv downloading Python 3.11.15 and installing Coga 0.4.0. Help/version smoke passed from `/tmp`. Those probes ran before the final rebase; their receipts keep their actual OIDs.
- Reviewed uv's current [Python management](https://docs.astral.sh/uv/concepts/python-versions/) and [tool Python selection](https://docs.astral.sh/uv/concepts/tools/#python-versions) documentation. No raw-terminal, pager, TTY prompt, or Slack surface changed; terminal interaction gate is inapplicable.
- Advisory **skim**: bounded docs-only change with fresh verification; self-review, unexecuted pipx alternative, and omitted optional permanent harness are disclosed. PR remains unopened for the next mechanical step. Launch owns checkout return (`COGA_LAUNCH_RETURNS_CHECKOUT=1`).

## PR

```yaml
title: Clarify Coga installation on older Python versions
author: codex
author_evidence: Implemented by Codex in the prior implementation session, per its recorded handoff; ticket-configured
  Claude was not the implementer. No subagents used.
head: ff906aac46d3a5c95869977f6cb44e43ca96e952
base: c8db8ab524c5da7b782d3dcbda95b6c0f27d2b85
depth: skim
rationale: Bounded documentation change; direct Codex review completed with no must-fix findings and fresh
  full-suite and live installer checks passed. Read the self-review disclosure and optional harness omission.
implementation: Lead with uv, explain automatic managed Python downloads, document explicit pipx interpreter
  selection and venv limitations, and replace the placeholder-install caveat with the confirmed yank behavior.
deviations: Optional Linux harness extension omitted; isolated live PyPI checks exercise Python 3.10 pip
  rejection and uv-managed Python installation without changing the harness.
limitations: Codex implemented and reviewed, so recorded as self-review rather than independent review.
  Full repository suite ran on Python 3.12.12; live PyPI Coga 0.4.0 was smoke-tested on uv-managed Python
  3.11.15. pipx was not executed. Optional permanent Linux harness extension omitted; fresh isolated pip/uv
  checks verify the externally controlled yank and installer behavior. Five Windows PowerShell-dependent
  tests skipped on this Linux host. Earlier receipts retain their original OIDs.
files:
  README.md: Keep the install summary centered on uv and link to pip/pipx alternatives.
  docs/contexts/coga/install/SKILL.md: Own the Python requirement, yanked placeholder behavior, and remedies
    for older interpreters.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md: Ship the byte-identical
    install topic to downstream repositories.
review:
  reviewer: codex
  kind: self
  status: passed
  head: ff906aac46d3a5c95869977f6cb44e43ca96e952
  base: c8db8ab524c5da7b782d3dcbda95b6c0f27d2b85
  detail: 'Direct review completed on the final rebased diff: no must-fix findings. Reviewed all three
    changed files, Python metadata, packaging contract, uv documentation, and fresh pip/uv outcomes. No
    child reviewer or subagent. Same actual agent identity as implementation; independence not claimed.
    No interactive terminal behavior changed.'
checks:
- command: curl -fsSL https://pypi.org/pypi/coga/0.0.1/json
  status: passed
  head: e4420c21ed774703e964c00185bbb50f5eb9d82d
  base: 6e30afa3c2ed43157c5d3acf3bc24948f5f3fa2d
  detail: Both wheel and sdist reported yanked=true; owner-supplied reason explains the unusable placeholder.
    External-state check performed before documentation edits.
- command: /tmp/coga-old-python-check/venv/bin/python -m pip --isolated install --index-url https://pypi.org/simple
    coga
  status: passed
  head: e4420c21ed774703e964c00185bbb50f5eb9d82d
  base: 6e30afa3c2ed43157c5d3acf3bc24948f5f3fa2d
  detail: 'Python 3.10.20, pip 23.0.1: expected exit 1, Requires-Python >=3.11 diagnostics, no matching
    distribution. Venv created with /tmp/coga-old-python-check/python/cpython-3.10.20-linux-x86_64-gnu/bin/python3.10
    -m venv /tmp/coga-old-python-check/venv.'
- command: env -u UV_PYTHON PATH=/tmp/coga-old-python-check/path UV_PYTHON_INSTALL_DIR=/tmp/coga-old-python-check/python
    UV_TOOL_DIR=/tmp/coga-old-python-check/isolated-tools UV_TOOL_BIN_DIR=/tmp/coga-old-python-check/isolated-bin
    UV_CACHE_DIR=/tmp/coga-old-python-check/cache /home/n/.local/bin/uv --no-config tool install coga
    --default-index https://pypi.org/simple
  status: passed
  head: e4420c21ed774703e964c00185bbb50f5eb9d82d
  base: 6e30afa3c2ed43157c5d3acf3bc24948f5f3fa2d
  detail: uv 0.11.28, run from /tmp. Isolated managed-Python directory initially contained only Python
    3.10.20 and PATH exposed only its python3 symlink. uv downloaded Python 3.11.15, installed Coga 0.4.0
    and its executable, exit 0.
- command: /tmp/coga-old-python-check/isolated-bin/coga --version
  status: passed
  head: e4420c21ed774703e964c00185bbb50f5eb9d82d
  base: 6e30afa3c2ed43157c5d3acf3bc24948f5f3fa2d
  detail: 'Run from /tmp: coga 0.4.0, exit 0; pyvenv.cfg confirms Python 3.11.15. Running the public release
    inside this newer source repository initially rejected its newer launch_args config; the isolated
    smoke correctly avoids repository config.'
- command: /tmp/coga-old-python-check/isolated-bin/coga --help
  status: passed
  head: e4420c21ed774703e964c00185bbb50f5eb9d82d
  base: 6e30afa3c2ed43157c5d3acf3bc24948f5f3fa2d
  detail: 'Run from /tmp: help rendered, exit 0.'
- command: git diff --check
  status: passed
  head: c7ec5b99c39efaac1f2cc3ed48d9bff13442f2c4
  base: 985673f1b60930e87f24a465c2b64f3b5bc0f118
  detail: No whitespace errors.
- command: cmp docs/contexts/coga/install/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md
  status: passed
  head: c7ec5b99c39efaac1f2cc3ed48d9bff13442f2c4
  base: 985673f1b60930e87f24a465c2b64f3b5bc0f118
  detail: Byte-identical canonical and packaged topic.
- command: coga validate --json
  status: not-run
  detail: Documentation-only change; no config, validation, task-model, prompt-composition, or workflow
    behavior changed.
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest
  status: passed
  head: e4420c21ed774703e964c00185bbb50f5eb9d82d
  base: 6e30afa3c2ed43157c5d3acf3bc24948f5f3fa2d
  detail: 3672 passed in 496.15s on Python 3.12.12. Historical receipt retained at its actual tested OIDs;
    final rebase changed only two unrelated tickets and coga/log.md.
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest tests/test_packaging.py
  status: passed
  head: c7ec5b99c39efaac1f2cc3ed48d9bff13442f2c4
  base: 985673f1b60930e87f24a465c2b64f3b5bc0f118
  detail: 22 passed in 16.04s on final rebased commit, including resource twins and wheel packaging.
- command: git diff --exit-code e4420c21ed774703e964c00185bbb50f5eb9d82d HEAD -- README.md docs src tests
    pyproject.toml
  status: passed
  head: c7ec5b99c39efaac1f2cc3ed48d9bff13442f2c4
  base: 985673f1b60930e87f24a465c2b64f3b5bc0f118
  detail: No differences from full-suite-tested revision in code, documentation, tests or package configuration.
    Full suite not repeated after unrelated ticket/log-only rebase; focused packaging checks rerun.
- command: curl -fsSL https://pypi.org/pypi/coga/0.0.1/json
  status: passed
  head: 8053ee363da846108d3305cfef722649d6a60329
  base: 2a97a8f339b3c33da36b62fb3c776e4a7a0f6370
  detail: Both wheel and sdist yanked=true; rechecked during peer review.
- command: /tmp/coga-old-python-check/venv/bin/python -m pip --isolated install --index-url https://pypi.org/simple
    coga
  status: passed
  head: 8053ee363da846108d3305cfef722649d6a60329
  base: 2a97a8f339b3c33da36b62fb3c776e4a7a0f6370
  detail: 'Python 3.10.20, pip 23.0.1, from /tmp: expected exit 1, Requires-Python >=3.11 and no matching
    distribution diagnostics.'
- command: env -u UV_PYTHON PATH=/tmp/coga-old-python-check/path UV_PYTHON_INSTALL_DIR=/tmp/coga-old-python-peer/python
    UV_TOOL_DIR=/tmp/coga-old-python-peer/tools UV_TOOL_BIN_DIR=/tmp/coga-old-python-peer/bin UV_CACHE_DIR=/tmp/coga-old-python-peer/cache
    /home/n/.local/bin/uv --no-config tool install coga --default-index https://pypi.org/simple
  status: passed
  head: 8053ee363da846108d3305cfef722649d6a60329
  base: 2a97a8f339b3c33da36b62fb3c776e4a7a0f6370
  detail: 'From /tmp with only Python 3.10 exposed on PATH and new managed-Python/tool/cache directories:
    downloaded Python 3.11.15 and installed Coga 0.4.0, exit 0.'
- command: /tmp/coga-old-python-peer/bin/coga --version; /tmp/coga-old-python-peer/bin/coga --help
  status: passed
  head: 8053ee363da846108d3305cfef722649d6a60329
  base: 2a97a8f339b3c33da36b62fb3c776e4a7a0f6370
  detail: 'From /tmp: version coga 0.4.0 and help rendered successfully, exit 0.'
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest
  status: passed
  head: ff906aac46d3a5c95869977f6cb44e43ca96e952
  base: c8db8ab524c5da7b782d3dcbda95b6c0f27d2b85
  detail: 3683 passed, 5 skipped in 548.43s on Python 3.12.12. Skips require Windows PowerShell. Complete
    run after final rebase; earlier partial peer run was interrupted to incorporate moving main and is
    not a passed receipt.
- command: git diff --check origin/main...HEAD
  status: passed
  head: ff906aac46d3a5c95869977f6cb44e43ca96e952
  base: c8db8ab524c5da7b782d3dcbda95b6c0f27d2b85
  detail: No whitespace errors on final reviewed diff.
- command: cmp docs/contexts/coga/install/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md
  status: passed
  head: ff906aac46d3a5c95869977f6cb44e43ca96e952
  base: c8db8ab524c5da7b782d3dcbda95b6c0f27d2b85
  detail: Canonical and packaged install topic are byte-identical after final rebase.
```
