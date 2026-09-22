---
name: coga/releasing
description: How Coga is published to PyPI and TestPyPI through Trusted Publishing, the one-time index setup, and the clean first-install gate run after a release.
---

# Releasing Coga

Coga publishes via **Trusted Publishing** (OIDC) from
`.github/workflows/release.yml`. GitHub authenticates to the index per run; no
API token is created, stored, or pasted anywhere.

## The release workflow

- Triggers: a published GitHub Release (publishes to PyPI) or a manual
  `workflow_dispatch` with `target` `testpypi` (default) or `pypi`.
- Each job builds and publishes in one job with no artifact handoff:
  `uv build`, `uvx twine check dist/*`, then
  `pypa/gh-action-pypi-publish` in environment `testpypi` or `pypi`, with
  only `contents: read` and `id-token: write`.
- It is the only workflow and runs no tests. The local suite is the release
  gate; see [coga/testing](../testing/SKILL.md). Because it builds from a
  pristine checkout it can catch the wheel collision described in
  [coga/packaging](../packaging/SKILL.md), but only at release time.

## One-time setup per index

Recorded as of 2026-09 (`pyproject.toml` version 0.3.2); re-check the index
state before relying on it. A trusted publisher must be registered on each
index before the workflow can publish. The form depends on whether the project
already exists there:

- **Name not yet registered**: account-level pending publisher (Account
  settings -> Publishing). This applied to TestPyPI.
- **Project exists**: project-level form (Your projects -> `coga` -> Manage ->
  Publishing -> Add a trusted publisher). This applies to PyPI, where `coga`
  was reserved with a `0.0.1` placeholder.

| Field | TestPyPI | PyPI |
| --- | --- | --- |
| PyPI Project Name | `coga` | implied by the page |
| Owner | `FastJVM` | `FastJVM` |
| Repository name | `coga` | `coga` |
| Workflow name | `release.yml` | `release.yml` |
| Environment name | `testpypi` | `pypi` |

Optional: in repo Settings -> Environments -> `pypi` (created on first run),
add a required reviewer so a human approves every real publish.

## Dry run on TestPyPI

Recommended for a first release; uploads are immutable, so this is the only
no-cost way to catch a packaging problem.

1. Confirm `version` in `pyproject.toml`.
2. Actions -> Release -> Run workflow -> target `testpypi`.
3. Check <https://test.pypi.org/project/coga/>.
4. Install from TestPyPI, resolving dependencies from PyPI:

   ```sh
   python3 -m venv /tmp/coga-test && . /tmp/coga-test/bin/activate
   pip install --index-url https://test.pypi.org/simple/ \
       --extra-index-url https://pypi.org/simple/ coga
   coga --version
   ```

## Real release

1. Bump `version` in `pyproject.toml` if needed and land it on `main`.
2. Releases -> Draft a new release -> tag `v<version>`, target `main`,
   Publish release.
3. The workflow publishes to PyPI.
4. Verify: `pipx install coga && coga --version`.

Each version uploads once per index. To re-test on TestPyPI, bump to a dev
version such as `0.2.0.dev1`. A bad release can be yanked, not deleted.

## Clean first-install gate

After publishing, run the public install and first-task path in a disposable
Linux container with `scripts/verify-clean-install.sh`. It installs the given
version from PyPI, initializes an ordinary Git repository, checks bundled
batteries, launches a minimal task with a real authenticated agent CLI,
validates the repo, and saves a transcript plus markdown and Git evidence.

```sh
COGA_GATE_AGENT=codex \
COGA_GATE_AGENT_INSTALL='npm install -g @openai/codex' \
./scripts/verify-clean-install.sh 0.3.0 -- --env OPENAI_API_KEY
```

- `COGA_GATE_AGENT_INSTALL` is required and must install the chosen agent CLI
  in the container; the script exits 2 without it or without the engine.
- Arguments after `--` go to `docker run` before the image (credential mounts,
  environment variables). Nothing from the host is forwarded implicitly.
- Defaults: `COGA_GATE_AGENT=codex`, `COGA_GATE_IMAGE=python:3.11-slim`,
  `COGA_GATE_CONTAINER_ENGINE=docker` (or `podman`),
  `COGA_GATE_EVIDENCE_DIR=./coga-install-gate-evidence`.
