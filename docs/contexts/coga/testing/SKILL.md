---
name: coga/testing
description: How to run and trust Coga's test suite and validation from a checkout, the environment and fixture pitfalls, the CI test posture, and the exact verification receipts reviewers expect.
---

# Testing Coga

## Commands

```sh
python -m pip install -e ".[test]"   # editable, with pytest and hatchling
coga --help                          # or: python -m coga.cli --help
python -m pytest
coga validate --json                 # or: python -m coga.validate --json
```

Coga needs Python 3.11+ (`tomllib`); an older interpreter fails loud. If pip's
hash-checking mode blocks the editable install, use `uv` or prefix the one
command with `PIP_REQUIRE_HASHES=0`. Run `coga validate --json` after config,
workflow, or task-model changes.

## Which code you are actually testing

- **Run the suite with an absolute `PYTHONPATH` whenever you are not in the
  primary checkout.** A healthy editable install's `.pth` names one checkout's
  `src`, so pytest from a feature worktree collects that worktree's tests
  against the primary checkout's unchanged package, and the suite is green
  against code you did not edit. Use
  `PYTHONPATH="$PWD/src" python3.11 -m pytest`. The same spelling recovers
  when the `.pth` points at a deleted worktree.
- `PYTHONPATH` must be absolute (some subprocess tests change cwd). Name the
  interpreter explicitly; the ambient `python3` on dev machines is often 3.9.
  `requires-python = ">=3.11"` is a promise: a green 3.12 run is not evidence
  for the floor. Install `.[test]` into a 3.11 interpreter (or a venv created
  with it) and run newer interpreters as extra coverage, not substitutes.
- **The `coga` on PATH may be a uv tool editable install**, not a checkout
  venv. Its interpreter is the `python` beside the resolved entry point:

  ```sh
  python3 -c 'from pathlib import Path; from shutil import which; print(Path(which("coga")).resolve().parent / "python")'
  ```

  That environment's `coga-*.dist-info/direct_url.json` names the checkout it
  imports, regardless of your cwd. Scripts that must `import coga` against the
  active CLI run under that interpreter. Repoint it (`uv tool install --force
  -e <checkout>`; the tool env has no `pip`) only to the long-lived checkout;
  verify branches with `PYTHONPATH`. A checkout `.venv/` is the test
  environment, not what `coga` on PATH runs. If `src/coga/` edits do not show
  up, check which checkout the install imports.
- Installed-versus-source skew warnings from `launch`/`validate` are owned by
  [coga/launch](../launch/SKILL.md).

## Test-writing rules

- Name tests after the command or module (`tests/test_launch.py`). Coga's own
  bundled ticket scripts are exercised from `tests/` against `example/`.
- **Launch metadata is scrubbed for you.** `tests/conftest.py`
  `_clear_supervised_session_env` clears `LAUNCH_OWNED_ENV`, derived from
  `coga.task_env.TASK_ENV_KEYS`, so a worker cannot write into the outer
  launched ticket. Add new launch-owned variables to `TASK_ENV_KEYS`; do not
  add per-test `delenv` opt-outs. `tests/test_env_isolation.py` proves it.
- **Do not pin to live dogfooded state.** Files under `coga/` mutate as the
  repo is used. Strip runtime fields (see `_strip_runtime_state` in
  `tests/test_autoclose_sweep.py`) or freeze the period; assert structure.
- **Fixture shell scripts must be portable.** Avoid GNU-only `sed -i`,
  `readlink -f`, `date -d`; prefer Python or `sed ... > tmp && mv tmp file`.
- **`coga.config` and `coga.commands.launch` share one `subprocess` module
  object.** Use one argv-dispatching mock on `coga.config.subprocess.run`.
- `hatchling` is a tracked test extra, not a runtime dependency, because
  `tests/test_packaging.py::test_wheel_includes_bootstrap_batteries` builds
  with `--no-build-isolation` and fails (not skips) without it; see
  [coga/packaging](../packaging/SKILL.md).

## CI posture and receipts

`.github/workflows/tests.yml` runs the full pytest suite on Python 3.11 and
3.12 for pull requests and pushes to `main`. Each job starts from a clean
checkout, installs `.[test]`, and sets an absolute `PYTHONPATH`; one
interpreter's failure does not cancel the other. Because the suite includes
`tests/test_packaging.py::test_wheel_includes_bootstrap_batteries`, the
pristine-tree wheel collision ([coga/packaging](../packaging/SKILL.md)) is
exercised on every PR. The workflow does not run `coga validate` against the
live ticket tree or change branch protection.

`.github/workflows/release.yml` still publishes independently
([coga/releasing](../releasing/SKILL.md)): it does not wait for the test
workflow, so check the intended commit's test results before releasing.

Every verifier (self-QA, review, release) names the interpreter, command, and
result: counts for a local run, for example
`PYTHONPATH="$PWD/src" python3.11 -m pytest` -> `N passed, M skipped`, or a
link to the CI run. "Tests pass" with no command and result is not evidence,
and a newer interpreter's green run is not proof of 3.11 compatibility.

- **Verify fix claims by exact token.** A done ticket's claim that it fixed a
  failing test is not proof of what reached `main` (a half-applied fixture fix
  once stayed red for weeks while four tickets re-diagnosed it). Check with
  `git log -S'<exact token>' -- <test file>` and the absolute-`PYTHONPATH`
  run, and record a partial fix as half-applied, not absent.
- **Scope validation with `coga validate --task <slug>`.** The repo-wide run
  has a known red baseline. As of 2026-09-16 it exits 1 on exactly four
  `unsynthesized-draft-blackboard` errors, all `v2/` drafts:
  `v2/autotrigger-ticket-type`,
  `v2/measure-relay-prompt-scope-and-agent-precision`,
  `v2/split-context-to-doc-user-accessible-and-editable`,
  `v2/use-worktree-when-starting-a-dev-task`. Report a matching set as known
  baseline and move on; never synthesize, cancel, or touch those drafts to
  turn the gate green. Any extra or missing error is a real change. A PR that
  clears one updates this date, count, and list; delete the item when none
  remain.

## Restricted sandboxes

- `codex review --base main` fails in a read-only app-server sandbox; rerun
  unsandboxed.
- State-changing commands (`create`, `bump`, `mark`) fail when the sandbox
  forbids `.git/index.lock`; rerun unsandboxed or grant `.git` write access.
- When `git worktree add` cannot write the primary `.git`, use the
  independent-clone fallback in [dev/checkouts](../../dev/checkouts/SKILL.md).
