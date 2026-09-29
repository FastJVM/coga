---
name: coga/testing/clean-install
description: The Linux clean-install harness, artifact provenance, install/init evidence, and attended agent-login and first-ticket continuation.
---

# Linux clean-install harness

Repository tooling lives in `scripts/clean-install/`; it is not installed with
Coga. It exercises the documented [install](../../install/SKILL.md),
[init](../../init/SKILL.md), and [first-task](../../first-task/SKILL.md) path
against an installed artifact. The separate
[release gate](../../releasing/SKILL.md#clean-first-install-gate) checks a pinned
release and a completed agent launch.

The image starts from `python:3.11-slim-bookworm`, adds Git, TLS certificates
and uv, and creates an empty non-root `coga` home. Coga, agent CLIs, `gh` and
`op` are absent. uv is constrained to the image's Python 3.11 and cannot
download a newer interpreter. No host home, credentials, source directory,
editable install, or tool cache is mounted into an install run.

## Build and run

On a Linux host with Bash, Git and Docker available, from the Coga checkout:

```sh
./scripts/clean-install/run.sh pypi clean-pypi alice
./scripts/clean-install/run.sh main clean-main alice
```

`main` mode also needs host uv. It fetches `origin/main`, exports that exact
commit, runs `uv build --wheel --no-sources`, and copies only the resulting
wheel into the container. It does not switch branches or build the working
tree. `pypi` runs the unpinned `uv tool install coga`; `main` uses the wheel
path with the same tool installer. Both then check the CLI version, initialize
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

Install and authenticate an agent **inside that container** before the first
ticket. For example, add curl for Claude Code's installer from the host:

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
coga-clean-install ticket "Write a hello-world script" --agent claude
```

Use your authenticated agent's configured name with `--agent` if different.
The final command changes into the scratch repo and runs `coga ticket` with
the supplied title and options, preserving the real terminal. It records the
command and exit code, not login output or the agent conversation. Complete
the interview with the agent; its exit code alone does not prove a task was
authored. Inspect `~/clean-install/repo/coga/tasks/` for that result. Repeat the
attended continuation in the other artifact's container when needed.

## Evidence and cleanup

Host receipts live in `.coga/clean-install/<container>/` (gitignored):
`host.txt`, `image.txt`, `result.txt`, and, for `main`, `source.txt` and the wheel.
The copied `container/` holds `transcript.txt`, ordered `steps.txt` with the
first failing command and exit code, and `init-passed.txt` only after success.
Host preparation failures appear in `host.txt` even if no container was created.
The wrapper returns non-zero on failure and leaves the container inspectable.
After an attended continuation, refresh the copied evidence:

```sh
docker cp clean-pypi:/home/coga/clean-install/evidence/. .coga/clean-install/clean-pypi/container/
docker cp clean-main:/home/coga/clean-install/evidence/. .coga/clean-install/clean-main/container/
```

For each artifact, put the exact command, image ID, installed version (or
failure before it), main SHA when applicable, and init outcome/failing command
in the PR description. State whether the attended first-ticket step ran.
Recording a failure is evidence, not an installer fix. Keep issue filing and
repairs in their own tickets.

When finished, remove these disposable containers; this also removes any agent
login saved inside them. Keep the host receipts for comparison:

```sh
docker rm -f clean-pypi clean-main
```
