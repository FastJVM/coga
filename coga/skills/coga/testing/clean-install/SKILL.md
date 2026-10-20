---
name: clean-install
description: Run Coga's Linux clean-install harness against PyPI or a main-branch wheel, then verify onboarding or a published release in the retained container.
---

# Linux clean-install harness

Repository tooling lives in `scripts/clean-install/`; it is not installed with
Coga. It exercises the documented [install](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/install/SKILL.md),
[init](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/init/SKILL.md), and [first-task](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/first-task/SKILL.md) path
against an installed artifact. The release continuation below also checks a
pinned release and a completed agent launch. The
[macOS harness on AWS](https://github.com/FastJVM/coga/blob/main/coga/skills/coga/testing/clean-install/macos-aws/SKILL.md) runs the same walk script as a fresh
user on an EC2 Mac. The [Windows harness on AWS](https://github.com/FastJVM/coga/blob/main/coga/skills/coga/testing/clean-install/windows-aws/SKILL.md) runs the
same walk steps natively on EC2 Windows Server and backs the native-port fix
loop.

The image starts from `python:3.11-slim-bookworm`, adds Git, TLS certificates
and uv, and creates an empty non-root `coga` home. Coga, agent CLIs, `gh` and
`op` are absent. uv is constrained to the image's Python 3.11 and cannot
download a newer interpreter. The walk script refuses to run without
`UV_PYTHON` and `UV_PYTHON_DOWNLOADS=never`, records the selected
interpreter, and stops before installing if it is not 3.11. No host home,
credentials, source directory, editable install, or tool cache is mounted into
an install run.

## Build and run

On a Linux host with Bash, Git and Docker available, from the Coga checkout:

```sh
./scripts/clean-install/run.sh pypi clean-pypi alice
./scripts/clean-install/run.sh main clean-main alice
```

`main` mode also needs host uv. It fetches `origin/main`, exports that exact
commit, runs `uv build --wheel --no-sources`, and copies only the resulting
wheel into the container. It does not switch branches or build the working
tree. `pypi` installs the latest Coga unless `COGA_CLEAN_INSTALL_VERSION` is
set, in which case it installs `coga==<version>`; `main` uses the wheel
path with the same tool installer and refuses that version override. Both then check the CLI version, initialize
a scratch Git repo with a local test identity, run `coga init --user alice`,
and run `coga validate --json`.
The optional third argument is the Coga user name (default `installer`).

Each invocation first rebuilds `coga-clean-install:py311` with `--pull`, then
requires a new container name and evidence directory. The container stays
running after success or failure. Set `COGA_CLEAN_INSTALL_IMAGE=<tag-or-id>`
to skip the build and reuse a specific built image. Builds
follow the current Python 3.11 patch and uv release; the image ID, tool versions,
resolved Coga version, and main SHA/wheel checksum are recorded for comparison.

If this host's Docker bridge cannot reach the package indexes (for example,
`apt-get update` times out on large index files), prefix each run with
`COGA_CLEAN_INSTALL_NETWORK=host`; the build and the container then share the
host network. The default is `bridge`. The chosen network is saved
in `result.txt` and the container-creation command in `host.txt`.

## Inspect and continue interactively

Both modes stop after init and validate; a zero exit proves only that phase. Enter either
retained container, including after a failure, with:

```sh
docker exec -it clean-pypi bash
```

A retained container stops when the Docker daemon or host restarts; `docker
exec` then fails with "container ... is not running". Start it first, then
exec; its filesystem, evidence, and any saved agent login are intact:

```sh
docker start clean-pypi
```

Install and authenticate an agent **inside that container** before either
attended continuation. For example, add curl for Claude Code's installer from the host:

```sh
docker exec --user root clean-pypi apt-get update
docker exec --user root clean-pypi apt-get install -y --no-install-recommends curl
docker exec -it clean-pypi bash
```

Then, inside the container, follow the vendor's
[Claude Code setup and login](https://code.claude.com/docs/en/setup):

```sh
curl -fsSL https://claude.ai/install.sh | bash
claude --version
claude
# Complete browser login using the URL shown, then exit the agent.
coga-clean-install build --agent claude
coga-clean-install ticket "Write a hello-world script" --agent claude
```

Use your authenticated agent's configured name with `--agent` if different.
Each continuation changes into the scratch repo, refuses to run without
`init-passed.txt`, and runs the named command with the supplied options,
preserving the real terminal. Neither records login output or the agent
conversation.

`build` exercises the advertised first-run command, `coga build` (an alias for
`launch coga-build`), against the `coga-build` ticket that init seeds active at
step 1 (gather-and-spec). Answer the agent's question and let it work the
step; under the launch supervisor it may chain into step 2. The record shows
whether the step was reached and bumped: the ticket's `status:` and `step:`
before and after the launch (a `done` ticket has no `step:`; `*_ticket=absent`
if the file is gone), the `[coga-build]` audit-log lines the launch appended
to the scratch repo, and the exit code. The `[system]` usage records (JSON
messages) quote the conversation and are left out; agent and human lines are
the audit trail and are kept, so a bump message, block reason, or unblock
answer may name what the operator asked to build. Read `build.txt` before
quoting it in a PR.

`ticket` runs `coga ticket` with the supplied title and records the command and
exit code. Complete the interview with the agent; its exit code alone does not
prove a task was authored. Inspect `~/clean-install/repo/coga/tasks/` for that
result.

Run `build` first: it is the documented first step, and a ticket authored first
would change the repo it onboards. Repeat the attended continuations in the
other artifact's container when needed.

## Verify a published release

Start a fresh pinned PyPI run (replace the example version with the release):

```sh
COGA_CLEAN_INSTALL_VERSION=0.4.0 ./scripts/clean-install/run.sh pypi release-040 installer
```

Install and authenticate the chosen agent inside the retained container as
above. Then run the release continuation on a real terminal:

```sh
docker exec -it release-040 coga-clean-install release claude
```

The command uses the Python environment installed by uv for Coga to check
bundled workflow/skill resources. It refuses legacy nested Git, vendored venv,
or shim directories, creates a minimal `direct/body` ticket, and launches the
chosen agent. The ticket tells the agent to record success and finish with
`coga bump`. Completion requires `status: done`, a matching audit-log entry,
validation success, and a clean scratch repository. An agent exit code alone
is insufficient. A repeated attempt in the same scratch repository refuses;
start a fresh install run after a failed release check.

Only full success writes `release-passed.txt`. The evidence directory also
holds `release-environment.txt` (installed version, Python, agent),
`release-task.md`, `release-log.md`, and `release-git-log.txt`. The log receipt
contains only this task's new audit entries, excluding system usage JSON as
in `build.txt`. Login and the agent conversation stay on the terminal. Refresh
the host copy after this continuation as described below. The obsolete
`verify-clean-install*.sh` gate is replaced by this path.

## Evidence and cleanup

Host receipts live in `.coga/clean-install/<container>/` (gitignored):
`host.txt`, `image.txt`, `result.txt`, and, for `main`, `source.txt` and the wheel.
The copied `container/` holds `transcript.txt`, ordered `steps.txt` with the
first failing command and exit code, and `init-passed.txt` only after success.
Attended continuations add `build.txt` and `ticket.txt`.
Host preparation failures appear in `host.txt` even if no container was created.
The wrapper returns non-zero on failure and leaves the container inspectable.
After an attended continuation, refresh the copied evidence:

```sh
docker cp clean-pypi:/home/coga/clean-install/evidence/. .coga/clean-install/clean-pypi/container/
docker cp clean-main:/home/coga/clean-install/evidence/. .coga/clean-install/clean-main/container/
```

For each artifact, put the exact command, image ID, installed version (or
failure before it), main SHA when applicable, and init outcome/failing command
in the PR description. State whether the attended `coga build`, first-ticket,
and release checks ran and, for `build`, whether it reached and bumped step 1.
Init success alone is not a release pass.
Recording a failure is evidence, not an installer fix. Keep issue filing and
repairs in their own tickets.

When finished, remove these disposable containers; this also removes any agent
login saved inside them. Keep the host receipts for comparison:

```sh
docker rm -f clean-pypi clean-main
```
