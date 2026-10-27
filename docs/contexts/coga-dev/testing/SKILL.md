---
name: coga-dev/testing
description: How to run and trust Coga's test suite and validation from a checkout, the environment and fixture pitfalls, the PR CI posture, and the exact verification receipts reviewers expect.
---

# Testing Coga

## Commands

```sh
python -m pip install -e ".[test]"   # editable, with pytest, hatchling and pip
coga --help                          # or: python -m coga.cli --help
python -m pytest
coga validate --json                 # or: python -m coga.validate --json
```

Coga needs Python 3.11+ (`tomllib`); an older interpreter fails loud. If pip's
hash-checking mode blocks the editable install, use `uv` or prefix the one
command with `PIP_REQUIRE_HASHES=0`. A venv made with `uv venv` (or
`python -m venv --without-pip`) initially has no `pip`; `uv sync --extra test`
or `uv pip install -e ".[test]"` installs all test tools, including pip. Run
`coga validate --json` after config, workflow, or task-model changes.

**Validate `tests/fixtures/seeded-repo/coga` with `env -u SLACK_WEBHOOK_URL coga validate --json`**
when your shell exports that variable. The fixture has notifications off, and
the config-load guard rejects a bare exported `SLACK_WEBHOOK_URL` with no
`webhook` key (the shipped `coga.toml` notification comments). Unset the
variable for the one command; do not edit the fixture's config to satisfy it.

The `non-executable-script` validation contract is in [coga/skill-management](../../coga/skill-management/SKILL.md#executable-skill-scripts).

For artifact-level reproduction, use the
[Linux clean-install harness](https://github.com/FastJVM/coga/blob/main/coga/skills/coga/testing/clean-install/SKILL.md). It covers current PyPI
and a wheel from `main` in a fresh Python 3.11 container, with an attended
continuation for agent login, the first-run `coga build`, and the first
ticket. The
[macOS harness on AWS](https://github.com/FastJVM/coga/blob/main/coga/skills/coga/testing/clean-install/macos-aws/SKILL.md) runs the same walk on
an EC2 Mac dedicated host, and the
[Windows harness on AWS](https://github.com/FastJVM/coga/blob/main/coga/skills/coga/testing/clean-install/windows-aws/SKILL.md) on EC2 Windows
Server.

## Which code you are actually testing

- **Run the suite with an absolute `PYTHONPATH` whenever you are not in the
  primary checkout.** In-process imports are safe: `pyproject.toml` sets
  `[tool.pytest.ini_options] pythonpath = ["src"]`, so tests import the
  checkout's own `coga`. Subprocess children (`sys.executable -m coga.cli`,
  `coga`, `ticket.py`) inherit the environment instead, and a healthy editable
  install's `.pth` names one checkout's `src`, so without an exported absolute
  `PYTHONPATH` they run the primary checkout's package: a mixed run where
  in-process assertions exercise your branch and CLI-driven ones do not. Use
  `PYTHONPATH=$PWD/src python3.12 -m pytest`. The same spelling recovers when
  the `.pth` points at a deleted worktree.
- `PYTHONPATH` must be absolute (some subprocess tests change cwd). Name a
  3.11+ interpreter explicitly; the ambient `python3` on dev machines is often
  3.9.
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
- **Codex runs its commands in a login shell** (`bash -lc`), which re-reads
  `~/.profile`; one that prepends `~/.local/bin` puts the uv tool `coga` back
  in front of a checkout venv you put first on PATH before launching. To
  dogfood a branch's `coga` under codex (for example a Dream run in a scratch
  clone), set top-level `allow_login_shell = false` in that checkout's
  gitignored `.codex/config.toml` and confirm with `command -v coga` from a
  codex session.
- **Live-test a launch-path branch from a non-editable install.** To exercise
  a branch's launch, supervisor, or capture code in a real `coga launch` or
  `coga chat` session, install the branch commit non-editable into a scratch
  venv and run that venv's `coga` by absolute path (`<venv>/bin/coga launch
  ...`) without activating the venv: launch prepares the control checkout
  (`main`), so an editable install of the checkout would run main's code.
  The agent inherits the supervisor's `PATH` unchanged (`build_launch_env`
  copies the parent environment), so commands it runs inside the session (for
  example `coga mark done`) resolve the `coga` on that `PATH`. Without
  activation only the supervisor/capture side runs the branch; activating the
  venv or prepending its `bin/` would put the branch install on both sides.
  Confirm with `command -v coga` from the session, and read the results with
  that split in mind (seen in the 2026-10-15 Codex SIGINT reproduction).
- Installed-versus-source skew warnings from `launch`/`validate` are owned by
  [coga/launch](../../coga/launch/SKILL.md).

## Test-writing rules

- Name tests after the command or module (`tests/test_launch.py`). Coga's own
  bundled ticket scripts are exercised from `tests/` against `tests/fixtures/seeded-repo/`.
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
- **Native Windows fixtures use UTF-8 and LF explicitly.** `conftest` isolates
  HOME, USERPROFILE, APPDATA, LOCALAPPDATA and the temp variables. Fixture
  paths are resolved to their canonical spelling, including HOME and TEMP,
  so a reused directory with different username casing matches Git's path
  reports on Windows. `init_git_repo` disables `core.autocrlf` for ordinary
  fixtures. Dedicated Git tests still exercise CRLF clean filters.
  `write_executable` supplies a
  Python shebang on POSIX and a `.cmd` launcher on Windows. Use
  `remove_test_checkout` when a fixture deliberately removes a Git clone;
  Git for Windows marks object files read-only.
- **All Windows exclusions use `conftest.windows_skip(reason)`.** The shared
  `windows_interactive_skip` names the interactive Windows ticket. Keep
  mocked orchestration tests running; skip only actual PTY/agent behavior,
  POSIX modes or Unix host/runbook scripts, and list every non-interactive
  exclusion with its reason in the PR. Native locks and Job Object recovery
  tests must run on Windows, without externally enabling Python UTF-8 mode.
  This repository keeps `.gitignore` LF because Git for Windows can interpret
  CR-only blank ignore lines as matches; this does not change init's policy
  for adopting repositories.
- **`coga.config` and `coga.launch` share one `subprocess` module
  object.** Use one argv-dispatching mock on `coga.config.subprocess.run`.
- `hatchling` is a tracked test extra, not a runtime dependency, because
  `tests/test_packaging.py::test_wheel_includes_bootstrap_batteries` builds
  with `--no-build-isolation` and fails (not skips) without it; see
  [coga-dev/packaging](../packaging/SKILL.md). The wheel tests shell out to
  `python -m pip`, so `pip` is also an explicit test extra for uv-created
  environments that otherwise omit it.

## CI posture and receipts

**Test CI is paused** (owner decision, 2026-10-26). The `Test` workflow is
disabled in GitHub (`disabled_manually`); its YAML remains in the repo.
Repeated packaging-twin failures, multiplied by automatic ticket/log pushes,
made the all-PR/all-main cadence too noisy. Repair the failures and settle the
trigger policy before resuming it; do not restore the existing cadence just
because the tests pass. The owner suggested the full matrix only for releases;
a gate before publication plus manual platform checks is the proposed direction,
with the final cadence still to be decided. Step-level verification remains
required while CI is paused.

The retained `.github/workflows/test.yml` definition (introduced by the
2026-10-23 decision reversing the 2026-09-24 no-CI policy) runs
`python -m pip install -e
".[test]"` then `python -m pytest` on Python 3.11 on `ubuntu-latest` and
`windows-latest` for every pull request and push to `main`. Superseded PR
runs are canceled; each main push has a separate concurrency group so queued
main runs are preserved. The POSIX migration-runbook test requires ripgrep
(`rg`) on PATH; CI installs it in the Linux job. The test step uses
`TERM=dumb` so Typer's forced terminal formatting in Actions does not insert
ANSI codes into plain-text assertions. It does not run
`coga validate`, interactive launch (checked on EC2), or anything needing a
real agent CLI, network, or AWS; such tests must skip cleanly rather than be
excluded from CI. The publish-only `.github/workflows/release.yml`
([coga/releasing](https://github.com/FastJVM/coga/blob/main/coga/skills/coga/releasing/SKILL.md))
still inspects only metadata with `twine check`.

CI does not replace step-level verification: implement / self-QA / review
still run the suite themselves, and a green CI run is evidence for exactly
its interpreter and platforms. Reusable workflows cannot assume Python 3.11
is installed in a user's environment. Evidence for Coga's declared 3.11
floor requires a run on a real Python 3.11 interpreter; a green 3.12 run is
not evidence for it. When 3.11 is unavailable locally, report that
verification gap with the actual interpreter and results, or cite the CI
run. Raising `requires-python` requires an owner decision.

Therefore every verifier (self-QA, review, release) states the exact commands
and counts, for example `PYTHONPATH=$PWD/src python3.12 -m pytest` ->
`N passed, M skipped`. "Tests pass" with no command and count is not evidence.

- **Verify fix claims by exact token.** A done ticket's claim that it fixed a
  failing test is not proof of what reached `main` (a half-applied fixture fix
  once stayed red for weeks while four tickets re-diagnosed it). Check with
  `git log -S'<exact token>' -- <test file>` and the absolute-`PYTHONPATH`
  run, and record a partial fix as half-applied, not absent.
- **Scope validation with `coga validate --task <slug>`.** The repo-wide run
  has no known error baseline: its last standing error sat on a draft now
  parked under `_v2/`, which validation never reads. Any repo-wide error is a
  real change, not drift to report and move on from.

## Reviewer test environment

- **`codex review`'s own test attempt is expected to fail collection** (for
  example `No module named 'tomlkit'`): it runs pytest under an ambient
  interpreter without Coga's dependencies. That is not a finding against the
  branch and does not void the review verdict. Run the suite yourself with a
  Coga-capable interpreter (`PYTHONPATH=$PWD/src .venv/bin/python -m pytest`)
  and record that command and count as the evidence.
