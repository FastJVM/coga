---
name: coga-dev/testing
description: How to run and trust Coga's test suite and validation from a checkout, the environment and fixture pitfalls, the agent-run verification tiers (no hosted CI), and the exact verification receipts reviewers expect.
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

**A repo-wide `coga validate` refuses a shebang script that is not
executable** (`non-executable-script`); the user-facing rule, remedy, and
mode sources live in [coga/first-task](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md#0-check-readiness).
When adding a script under `src/coga/resources/templates/coga/bootstrap/skills/`,
commit it `100755` if it starts with `#!`; import-only modules carry no
shebang and stay `100644`. A packaged-tree finding in an adopting repo is
fixed here, upstream; Dream routes it as human-needed rather than a local PR.
The walk skips symlinks and prunes `.git`, `__pycache__`, `node_modules`, and
`.venv` (`validate._check_shebang_executables`).

For artifact-level reproduction, use the
[Linux clean-install harness](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/SKILL.md). It covers current PyPI
and a wheel from `main` in a fresh Python 3.11 container, with an attended
continuation for agent login, the first-run `coga build`, and the first
ticket. The
[macOS harness on AWS](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/macos-aws/SKILL.md) runs the same walk on
an EC2 Mac dedicated host, and the
[Windows harness on AWS](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/windows-aws/SKILL.md) on EC2 Windows
Server. The
[attended human walk](https://github.com/FastJVM/coga/blob/main/coga/skills/coga/testing/clean-install/human-walk/SKILL.md)
is their hand-run counterpart: a first-time user installs on a fresh
`cogatest` VM while an agent records findings.

## Which code you are actually testing

- **Package-owned definitions.** Tests and harnesses read shipped skills,
  workflows and recurring definitions from the package tree
  (`src/coga/resources/templates/coga/...`). The inverse inventory in
  `test_packaging` rejects unapproved live copies, including identical ones;
  required package resources are pinned independently of local state. The
  publication regressions in `test_git` run the control tree's own imports
  and packaging/navigation/runtime checks: the first conversion uses the
  pinned Stage A merge, and final-state dirty/committed package edits must
  stay on the feature branch during a mutating CLI exit sweep. The historical
  transition test needs Git history containing that merge; a shallow checkout
  reports an explicit skip and cannot supply that transition receipt. Pass
  `--basetemp` on a roomy volume for full runs: the suite creates many
  temporary repos and can fill a small `/tmp` tmpfs. On Windows, use a short
  root such as `C:\ct`; nested control checks and wheel copies can otherwise
  exceed MAX_PATH. Control clones disable `core.autocrlf` to preserve pinned
  definition bytes. The Stage A check backports one explicit-LF test-fixture
  write; its product code and assertions remain pinned to the historical tree.

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
  [coga/launch](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md).

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
- **Stand in for a tool interpreter with an `exec` wrapper, not a symlink.**
  Python finds `pyvenv.cfg` beside the path it was invoked by, so a symlink
  to `sys.executable` placed elsewhere runs the base interpreter without the
  venv's packages; globally installed packages then hide the loss.
  `tests/test_clean_install_harness.py` `_tool_python` writes a `/bin/sh`
  wrapper that `exec`s the quoted interpreter, and its regression test
  imports a module present only in a throwaway venv so no global package can
  stand in.
- **Native Windows fixtures use UTF-8 and LF explicitly.** `conftest` isolates
  HOME, USERPROFILE, APPDATA, LOCALAPPDATA and the temp variables. Fixture
  paths are resolved to their canonical spelling, including HOME and TEMP,
  so a reused directory with different username casing matches Git's path
  reports on Windows. `init_git_repo` disables `core.autocrlf` for ordinary
  fixtures. Dedicated Git tests still exercise CRLF clean filters.
  A fresh child interpreter does not inherit pytest's monkeypatches. Launch
  fixtures that fake the supervisor inside that child must also fake the
  Windows CLI resolver there, so command planning can reach the simulated
  agent without requiring an installed agent CLI.
  `write_executable` supplies a
  Python shebang on POSIX and a `.cmd` launcher on Windows. Use
  `remove_test_checkout` when a fixture deliberately removes a Git clone;
  Git for Windows marks object files read-only.
- **All Windows exclusions use `conftest.windows_skip(reason)`.** A POSIX
  PTY-mechanics test (`pty.fork`, `TIOCSWINSZ`, SIGWINCH, fork gates) may skip
  only when its reason names the Windows-run equivalent of the same contract,
  usually in `tests/test_repl_supervisor_nt.py`. Keep
  mocked orchestration tests running; skip only actual PTY/agent behavior,
  POSIX modes or Unix host/runbook scripts, and list every non-interactive
  exclusion with its reason in the PR. Native locks and Job Object recovery
  tests must run on Windows, without externally enabling Python UTF-8 mode.
  This repository keeps `.gitignore` LF because Git for Windows can interpret
  CR-only blank ignore lines as matches; this does not change init's policy
  for adopting repositories.
- **`coga.config` and `coga.launch` share one `subprocess` module
  object.** Use one argv-dispatching mock on `coga.config.subprocess.run`.
- **Scope standard-library mocks to the operation under test.** For example,
  restore `shutil.get_terminal_size` with `monkeypatch.context()` before
  pytest reports the result; pytest also calls it with `fallback=`.
- `hatchling` is a tracked test extra, not a runtime dependency, because
  `tests/test_packaging.py::test_wheel_includes_bootstrap_batteries` builds
  with `--no-build-isolation` and fails (not skips) without it; see
  [coga-dev/packaging](../packaging/SKILL.md). The wheel tests shell out to
  `python -m pip`, so `pip` is also an explicit test extra for uv-created
  environments that otherwise omit it.

## Known suite failures

Rule these out before blaming the change under test.

- **The full suite can exhaust `/tmp` inodes.** Each run creates thousands of
  fixture repositories. On a `/tmp` with free bytes but few free inodes, one
  run ended with 1,413 passed, 10 skipped and 2,708 errors, with 36 inodes
  left. Check `df -i /tmp`, remove only that run's fixtures, and rerun with
  `TMPDIR` on the main disk.
- **`control_relay_started` leaks between tests (open, no ticket).**
  `recurring_runner` sets the `git.control_relay_started` ContextVar when it
  relays to a control worktree, and nothing resets it between tests. Running
  `tests/test_recurring.py::test_recurring_scan_relays_into_existing_control_worktree`
  before
  `tests/test_git.py::test_recurring_all_child_retains_the_control_worktree_sweep`
  fails the second one: `_sweep_coga_state` makes no sync call
  (`assert 0 == 1`). Reproduced on control on 2026-11-02. The default
  full-suite order passes, so the failure only shows up in reordered or
  focused selections. Confirm by running the failing test alone.
- **A Windows checkout and temp directory on different drives** break
  `os.path.relpath`, which raises `ValueError` across drives. A path computed
  between package resources and a fixture repo must fall back to an absolute
  target, as `agent_skills` does for skill links. The retired hosted Windows
  runner (package on `D:`, temporary repos on `C:`) failed 228 tests this
  way; the Windows AWS harness's default layout keeps both on `C:`, so it
  does not exercise this split.

## Verification tiers and receipts

**Coga has no hosted test CI** (owner decision, 2026-11-05). Agents and the
release operator run every check on real machines. The only workflow is the
publish-only `.github/workflows/release.yml`
([coga/releasing](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/bootstrap/skills/coga/releasing/SKILL.md)).
It builds, runs `twine check` (metadata only), and uploads. It runs no tests.

History, so nobody re-adds CI without the reasons: a 2026-09-24 no-CI policy
was reversed on 2026-10-23 by PR #1097, which added a `Test` workflow running
the suite on Linux and Windows for every pull request and every push to
`main`. Automatic ticket/log publication turned that into repeated full runs,
and a packaging-twin inconsistency (live blocker-reminders template published
before its package twin) made every run fail and notify. The owner disabled
the workflow on 2026-10-26 and deleted it on 2026-11-05
(`v1/13-repair-ci-and-resume-with-release-focused-triggers`). The tradeoff:
nothing mechanical blocks a merge or an upload. Tiers 2 and 3 are
procedures enforced by the implementer, the reviewer and the release
operator. In exchange there are no hosted runs, queues or failure
notifications, and platform checks run natively on the AWS harnesses.

1. **Every change.** Implement, self-QA and review steps run the full suite
   locally (Linux) and record receipts.
2. **Platform-sensitive changes: required before merge.** A change is
   platform-sensitive when it touches OS-dependent imports,
   process/terminal handling, locks, filesystem/path/encoding/Git behavior,
   dependency or Python requirements, packaging/install behavior, executable
   templates, or native test fixtures and skip rules. The implementer runs the
   full suite natively on Windows through the
   [Windows AWS harness](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/windows-aws/SKILL.md#fix-loop-checkout-and-remote-commands)
   (its "Long native runs" procedure; a full run takes about two hours) at
   the PR's head commit, and records the receipt in the PR and the ticket.
   Once macOS is supported, also run it on macOS through the
   [macOS AWS harness](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/macos-aws/SKILL.md#full-suite-at-a-commit).
   A source-affecting change after the receipt needs a new run. The reviewer
   does not approve a platform-sensitive PR without it.
3. **Every release, before tagging.** The full suite at the exact commit to
   be tagged on Linux, on Windows (AWS harness), and on macOS (EC2 Mac host)
   once macOS is supported, plus the build, `twine check` and clean-install
   checks. [coga/releasing](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/bootstrap/skills/coga/releasing/SKILL.md)
   owns the release procedure. A failure or missing receipt means no tag.

macOS is supported once its full suite passes on the EC2 Mac host (owner's
threshold). Until then, macOS receipts are not required, and a macOS run is
informational.

**Python 3.11 floor evidence.** At least one tier-3 suite run uses a real
Python 3.11 interpreter, Coga's `requires-python` floor. Examples are the
Linux clean-install harness's Python 3.11 container, or the Windows
harness's `checkout`, which syncs the test environment with a uv-managed
Python 3.11 (`uv sync --python 3.11 --extra test`). A green 3.12 run
is not evidence for the floor. For tiers 1 and 2, when 3.11 is unavailable,
report that gap with the actual interpreter and results. Reusable workflows
cannot assume Python 3.11 is installed in a user's environment. Raising
`requires-python` requires an owner decision.

**Receipt fields.** Each run records the full commit SHA, the platform and OS
version, the Python version, the exact command, pass/skip/fail counts, and
runtime. For example: `3f1c…` (full SHA), Ubuntu 24.04, Python 3.12.12,
`PYTHONPATH=$PWD/src .venv/bin/python -m pytest` -> `4058 passed, 10 skipped`
in 410s. "Tests pass" with no command and counts is not evidence. A receipt
is evidence for exactly its commit, interpreter and platform. Runs on
uncommitted changes count for a commit only when the committed tree is
identical.

**Local-run environment.** The POSIX migration-runbook test requires ripgrep
(`rg`) on PATH. Set `TERM=dumb` when output formatting matters (for example
under a forced-terminal environment), so Typer does not insert ANSI codes
into plain-text assertions. The suite does not run `coga validate`,
interactive launch (checked on EC2), or anything needing a real agent CLI,
network or AWS; such tests must skip cleanly rather than be excluded.
Windows skips about 90 more tests than Linux. The native Windows run exists
for behavior that differs there (paths, processes, locks, encoding), not for
extra Windows-only tests.

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
