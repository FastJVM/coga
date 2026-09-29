---
title: Linux clean-install harness
status: in_progress
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
step: 3 (open-pr)
agent: claude
---

## Description

Build and commit a reusable Linux clean-install harness, so installer issues
can be reproduced from nothing and each fix can later be proven with the same
run. The harness has three parts:

- a Docker image based on Python 3.11 (the declared floor) with a fresh
  non-root user and nothing preinstalled beyond the prerequisites that
  `coga/install` lists;
- a script that installs Coga into it from either **the current PyPI
  release** or **a wheel built from `main`** with `uv build` (chosen by an
  argument), then walks the documented path: `uv tool install coga`,
  `coga --version`, `git init` of a scratch repo, `coga init --user <name>`,
  and `coga ticket "<first task>"`;
- a short runbook covering how to build, run, and drop into the container
  interactively for the attended agent-login and first-task steps.

Done means the harness and runbook are merged via PR, and one run per
artifact reaches `coga init` (or records exactly where it failed) in the PR
description. This ticket does not file or fix installer issues; that is
`marketing/fix-installer/run-clean-installs-and-file-issues`.

## Context

Part of the `marketing/fix-installer/` set, which replaced the single
`marketing/fix-installer` ticket (V1 prerequisite for
`marketing/build-the-launch-plan`). Sibling tickets: `macos-clean-install-harness-on-aws`
and `run-clean-installs-and-file-issues`. The Windows (`v2/windows-native-clean-install`)
and CI matrix (`v2/install-smoke-ci-matrix`) work is deferred to V2.

The expected behavior is the documented path. It is cited, not attached, in
`README.md` and in the `coga/install`, `coga/init` and `coga/first-task`
topics (`docs/contexts/coga/<ref>/SKILL.md`). `coga/install` prerequisites:
Python 3.11+ (`tomllib`), git (the only tool `coga init` enforces), an
authenticated agent CLI for `launch`/`ticket`/`build`, `gh` recommended, and
`op` only for `op://` secrets. Note that `README.md` currently has two
"Getting Started" blocks that disagree (one still says `coga build`); follow
the topics and leave the README to `marketing/readme-top`.

The harness is repo dev tooling, not package code. It stays out of
`src/coga/` (`coga/extension-model` microkernel rule); place it per
`coga/codebase` and `coga/testing` (both cited). Keep it minimal: no new
installer tier or onboarding framework. Test the installed artifact, not an
editable tree.

<!-- coga:blackboard -->

## Dev

branch: linux-clean-install-harness

## Implementation handoff — 2026-09-29

Pushed commit `caa7b187d` on the recorded branch, rebased onto
`origin/main` at `d619606dff7776ae7fe56281a3a01636af212ea0`. Returned the launch
checkout to fast-forwarded, clean `main` before writing this handoff. No PR
opened; review and PR publication remain later steps.

Owner confirmed a separate harness in the attended session on 2026-09-28.
`scripts/clean-install/` now holds a Python 3.11 Dockerfile, a `pypi|main`
host runner, and an in-container install/init script with a separate attended
`ticket` continuation. The runbook is owned by
`docs/contexts/coga/testing/clean-install/SKILL.md`, linked from the testing
overview; both topics have byte-identical packaged twins, and the new topic
is registered in `tests/test_packaging.py`.

The main mode exports the freshly fetched commit and builds a wheel with
`uv build --wheel --no-sources`, so local edits cannot leak into the artifact.
The install container has a fresh non-root home and receives only the wheel,
not a source mount or credentials. Runs retain containers and copy receipts
to `.coga/clean-install/<container>/`. First-failure exit codes survive logging.
The attended `coga ticket` phase preserves terminal stdin/stdout and records
only its command and exit code. Existing release gate and installer behavior
were not changed.

## Verification

- `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest`
  after the final rebase: **3058 passed in 252.37s**.
- `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest tests/test_packaging.py tests/test_clean_install_harness.py -q`:
  **31 passed** after the network-option and legacy-Docker compatibility changes.
- `bash -n scripts/clean-install/run.sh scripts/clean-install/container.sh`:
  passed. `git diff --check origin/main...HEAD`: passed.
- Harness coverage proves artifact selection, exact error/exit preservation,
  refusal to reuse an installed environment, terminal preservation, and use of
  fetched main despite dirty feature-branch source.

## PR evidence — include both artifact outcomes

Build command:
`docker build --network host --pull -t coga-clean-install:py311 scripts/clean-install`

Image ID: `sha256:9cffb930e30a22c56d780e085a5fbe1af6e8c3a4124b05f0fae17e09c0bd00a9`.
Both runs used UID/GID 1000 (`coga`), Python **3.11.16**, Git **2.39.5**, uv
**0.12.20**, and a fresh container. Host Docker's bridge timed out on Debian
HTTP downloads and HTTPS handshakes; host networking worked. The runbook
documents this explicit opt-in, and each receipt records `network=host`.
The Dockerfile also works with the host's legacy builder (no BuildKit required).

| Artifact / exact run command | Outcome |
| --- | --- |
| `env COGA_CLEAN_INSTALL_NETWORK=host ./scripts/clean-install/run.sh pypi clean-pypi-20260929 installer` | `uv tool install coga` installed **0.2.0**; `coga --version` passed; reached `coga init --user installer`, which exited **2** because `gh` was absent. Exact message: `coga needs these external command-line tools, but they are not on PATH: ... gh: install from https://cli.github.com`. |
| `env COGA_CLEAN_INSTALL_NETWORK=host ./scripts/clean-install/run.sh main clean-main-20260929 installer` | Built and installed **0.3.2** from main SHA `d619606dff7776ae7fe56281a3a01636af212ea0`; version check and `coga init --user installer` passed; wrapper exited **0**. Init committed the scratch repo as `6fde3f9ccc4c`. |

Wheel: `coga-0.3.2-py3-none-any.whl`, SHA-256
`1585bb8c57da64fd0159eecfeb9b88c9ce1bb43a705689fb738a690fd8bc7986`.
Host receipts: `.coga/clean-install/clean-pypi-20260929/` and
`.coga/clean-install/clean-main-20260929/` (ignored, not committed).
Both named containers remain running for inspection with `docker exec -it
<container> bash`. **Agent login and the attended first-ticket interview were
not run.** The runbook gives that continuation; the PyPI container first needs
the recorded init prerequisite addressed. This ticket records the failure;
issue filing and installer fixes belong to the sibling ticket.

## Follow-up commit `2dbc34bbf` — 2026-09-29 (claude, attended)

A parallel Claude implement session produced a second harness; the owner
chose to merge the two. The branch was rebased onto `origin/main` and
force-pushed with a lease pinned to `caa7b187d`: `09f97edb4` is the
harness above, unchanged apart from the rebase, and `2dbc34bbf` adds:

- `run.sh` builds the image itself (`docker build --pull`, passing
  `--network` only for a non-`bridge` network), so one command reaches init.
  `COGA_CLEAN_INSTALL_IMAGE` skips the build and reuses that image.
- `container.sh` runs `coga validate --json` after `coga init`.
- Tests cover validate success and failure and the build call; the
  runbook and its twin are updated to match.

Reviewers: review `2dbc34bbf`, not `caa7b187d`. For the PR description,
prefer these runs of the merged harness (image
`sha256:51832fd6f697fa1e8e3a75c0fd7292028c4acdabf5272dd65b3472692844b252`):

| Exact run command | Outcome |
| --- | --- |
| `env COGA_CLEAN_INSTALL_NETWORK=host ./scripts/clean-install/run.sh main clean-main alice` | Wheel 0.3.2 from main `8ce7d8b10038ef557cc94e34ea5b0b7294c5b34c` (sha256 `1585bb8c…7986`); every step passed through `coga init --user alice` and `coga validate --json`; exit 0. |
| `env COGA_CLEAN_INSTALL_NETWORK=host ./scripts/clean-install/run.sh pypi clean-pypi alice` | `uv tool install coga` installed 0.2.0; `coga init --user alice` exited 2 because `gh` is not on PATH (same finding as above). |

`PYTHONPATH=$PWD/src .venv/bin/python -m pytest` on the merged branch:
**3059 passed**. Receipts are in `.coga/clean-install/clean-{pypi,main}/`
in `/home/n/Code/coga` (ignored). Agent login and the attended first-ticket
interview were still not run.

## Adjacent findings

The existing `scripts/verify-clean-install-container.sh` release gate imports
`coga.resources` using the base Python after a uv tool install and later reads
unset `local_version` under `set -u`. These are inspection findings, not
reproduced installer failures. Leave them for
`marketing/fix-installer/run-clean-installs-and-file-issues`; do not repair the
release gate in this ticket.

## Peer review

Completed 2026-09-29. Both native Codex reviews **returned**, exit 0:

- `codex review --base main` found one P2: the test fixtures required the
  host's GNU `sha256sum`, which stock macOS lacks. Reproduced with a restricted
  PATH: seven setup errors and one failure. The owner approved a portable
  Python checksum stand-in; commit `6583f0e4e` supplies it to both fixtures.
- After incorporating the owner's concurrent `2dbc34bbf` follow-up,
  `codex review --base origin/main` found one P2: an inherited
  `COGA_CLEAN_INSTALL_IMAGE` makes the default-build test skip its expected
  build. Commit `3b95fa74d` clears that override in the test. No installer or
  harness behavior needed a review fix. Both findings are addressed.

The initial sandboxed review could not initialize its app-server; both
completed reviews ran with the required filesystem access. Review logs are
`/tmp/coga-linux-clean-install-peer-review-20260929.log` and
`/tmp/coga-linux-clean-install-peer-review-final-20260929.log`.

Final verification on the pushed branch:

- `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest`:
  **3059 passed in 189.86s**, after the final fix and rebase.
- `COGA_CLEAN_INSTALL_IMAGE=coga-clean-install:py311 PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest tests/test_clean_install_harness.py -q`:
  **9 passed**, reproducing the second reviewer's environment after its fix.
- `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest tests/test_clean_install_harness.py -q --tb=short`
  with PATH restricted to temporary links for `bash`, `git`, `mkdir`, `tee`,
  `dirname`, `basename`, `mktemp`, `tar`, `cp`, and `rm` (no host checksum
  utility): **9 passed**. This is a Linux simulation of the missing utility,
  not a run on macOS.
- `bash -n scripts/clean-install/run.sh scripts/clean-install/container.sh`
  and `git diff --check origin/main...HEAD`: passed. Both changed context
  pairs were also checked with `cmp`; they are byte-identical.

Manual terminal gate: opened `docker exec -it clean-main-20260929 bash
--noprofile --norc`, set `stty rows 24 cols 80`, then ran
`coga-clean-install ticket --pick-agent` and selected `1`. Repeated at
`stty rows 40 cols 120`, entered `invalid`, saw the retry prompt, then selected
`codex`. Prompts and input remained visible; both runs reached the expected
missing-agent-CLI error and recorded `ticket_exit_code=2`. The ticket
continuation is unchanged by `2dbc34bbf`. Receipts were copied back to
`.coga/clean-install/clean-main-20260929/container/ticket.txt`. Agent login and
a completed first-ticket interview were not exercised.

Independently inspected the newer merged-harness receipts in
`/home/n/Code/coga/.coga/clean-install/clean-{pypi,main}/`; their outcomes and
provenance are the PR evidence below.

Final branch head: `3b95fa74d`. Preserved remote commit `2dbc34bbf` and used
the owner's requested `git pull --rebase origin linux-clean-install-harness`
and normal `git push origin linux-clean-install-harness`. The required
fetch/rebase of main also ran; main's only newer change was this ticket's
state, and its replay was omitted from the feature branch. No task or log
paths are in the implementation diff. Returned to clean, fast-forwarded
`main` at `71cc796e5` before writing this handoff. No PR opened in this step.

## PR

Make Linux installer failures reproducible with a fresh non-root Python 3.11
Docker environment. The runner builds the image and installs either current
PyPI Coga or a wheel exported from freshly fetched `origin/main`, then checks
the version, initializes a scratch Git repo, runs `coga init`, and validates
the result. It preserves command receipts and the first failure, retains the
container for inspection, and provides an attended first-ticket continuation.

The runbook lives in `docs/contexts/coga/testing/clean-install/SKILL.md`, with
a matching packaged twin and a link from the testing overview. Tests cover
artifact selection, failure propagation, clean-environment refusal, fetched
source provenance, and terminal preservation; review also fixed checksum
portability and isolation from an exported image override in the fixtures.

Test plan: `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest` — **3059 passed**; the nine harness tests also pass with a host PATH lacking `sha256sum` and with `COGA_CLEAN_INSTALL_IMAGE` exported. Shell syntax, diff whitespace, and context-twin checks pass.

### Artifact verification — 2026-09-29

Both commands below built image
`sha256:51832fd6f697fa1e8e3a75c0fd7292028c4acdabf5272dd65b3472692844b252`
and used a fresh container: UID/GID 1000, Python **3.11.16**, Git **2.39.5**,
uv **0.12.20**. Host networking was explicitly selected because the host's
Docker bridge timed out during downloads; receipts record `network=host`.

| Exact command | Installed artifact and outcome |
| --- | --- |
| `env COGA_CLEAN_INSTALL_NETWORK=host ./scripts/clean-install/run.sh pypi clean-pypi alice` | Installed **Coga 0.2.0**; version check passed. `coga init --user alice` exited **2** because `gh` was not on PATH. Validation was not reached. |
| `env COGA_CLEAN_INSTALL_NETWORK=host ./scripts/clean-install/run.sh main clean-main alice` | Installed **Coga 0.3.2** from main `8ce7d8b10038ef557cc94e34ea5b0b7294c5b34c`. `coga init --user alice` and `coga validate --json` passed; validation reported no issues and the wrapper exited **0**. |

Wheel: `coga-0.3.2-py3-none-any.whl`, SHA-256
`1585bb8c57da64fd0159eecfeb9b88c9ce1bb43a705689fb738a690fd8bc7986`.
Receipts are retained under
`/home/n/Code/coga/.coga/clean-install/clean-{pypi,main}/` (gitignored).

The attended wrapper's agent picker was driven in a real Docker terminal at
80x24 and 120x40, including an invalid selection and retry. It accepted input
and preserved the missing-agent exit code. **Agent login and a completed
first-ticket interview were not run.** The PyPI failure is recorded for the
installer-issues sibling ticket; no installer repair or issue filing is
included here.
