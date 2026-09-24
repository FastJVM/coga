---
name: coga/testing
description: How to run and trust Coga's test suite and validation from a checkout, the environment and fixture pitfalls, the no-CI test posture, and the exact verification receipts reviewers expect.
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

The only GitHub Actions workflow is the publish-only
`.github/workflows/release.yml` ([coga/releasing](../releasing/SKILL.md)).
Its `twine check` inspects metadata, not behavior. Nothing runs `pytest` or
`coga validate` on any branch, PR, push, or tag, so the local suite plus
validation are the release gate, and the pristine-tree wheel collision is
caught only at release or by hand. The parked
`coga/tasks/v2/minimal-ci-run-pytest-on-prs-and-tags.md` would change this;
update this section when it lands.

Therefore every verifier (self-QA, review, release) states the exact commands
and counts, for example `PYTHONPATH=$PWD/src python3.12 -m pytest` ->
`N passed, M skipped`. "Tests pass" with no command and count is not evidence.

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

### Codex sandbox grant

`coga launch` spawns plain `codex <prompt>`, so a codex session's sandbox
comes entirely from codex's own config layers. In a trusted project that is
`workspace-write`: the checkout and temp dirs are writable, `.git` is
read-only, and network is off. Git sync, `git worktree add`, fetch, push,
`gh`, and `coga slack` then fail. Dream's agent capability preflight checks
for exactly these capabilities and points here. The grant that fixes this
without bypassing the sandbox lives in the repo's project-local
`.codex/config.toml`:

```toml
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = true
writable_roots = ["<absolute repo path>/.git"]
```

- The file is gitignored and machine-local: `writable_roots` needs the
  absolute path of this machine's checkout. Coga ships no launch machinery
  for it.
- Codex reads a project `.codex/config.toml` only for a trusted project
  (`[projects."<absolute repo path>"] trust_level = "trusted"` in
  `~/.codex/config.toml`, which codex's first-run trust prompt writes).
- It covers every codex session launched in that checkout, not only Dream.
- Linked worktrees share the granted `.git`. Create them under an already
  writable root, such as a `mktemp -d` directory, rather than as a sibling of
  the checkout: Dream's Retro pass puts its linked checkout inside its
  temporary run directory for this reason.
- The grant takes effect in a new codex session; relaunch after editing it.
