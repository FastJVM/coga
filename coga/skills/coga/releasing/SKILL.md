---
name: releasing
description: Publish Coga to TestPyPI or PyPI and verify the release. Use for Coga release preparation, Trusted Publishing setup, and post-release acceptance.
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
  gate; see [test receipts](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/testing/SKILL.md). Because it builds from a
  pristine checkout it can catch the wheel collision described in
  [wheel packaging](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/packaging/SKILL.md), but only at release time.

## One-time setup per index

Both indexes already have trusted publishers for this repository; releases
through 0.4.1 published with them. Repeat this only for a new index, or after
renaming the repository, workflow or environment. The form depends on whether
the project already exists on that index:

- **Name not yet registered**: account-level pending publisher (Account
  settings -> Publishing).
- **Project exists**: project-level form (Your projects -> `coga` -> Manage ->
  Publishing -> Add a trusted publisher).

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
2. Run the pre-tag gate on the exact commit you will tag. The workflow runs
   no tests, so this is the only behavioral check before an immutable upload:
   - the full suite against that checkout,
     `PYTHONPATH=<checkout>/src python -m pytest`, with its count recorded
     ([test receipts](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/testing/SKILL.md));
   - build both distributions and `twine check dist/*`;
   - install the built wheel into a fresh Python 3.11 venv (the
     `requires-python` floor), then run `coga --version`,
     `coga init --user tester`, and `coga validate --json` in a scratch Git
     repository. Run the scratch-repo commands under
     `env -u SLACK_WEBHOOK_URL` when your shell exports it: a fresh repo has
     no `[notification.slack] webhook` key, so the config-load guard rejects
     the bare variable and every config-loading command after init exits 2.
     Unset it only for the scratch repo; this repo's own `coga.toml` reads
     it.
3. Releases -> Draft a new release -> tag `v<version>`, target `main`,
   Publish release.
4. The workflow publishes to PyPI.
5. Verify from a fresh environment that bypasses caches:
   `python3.11 -m venv <dir>` then
   `<dir>/bin/python -m pip install --no-cache-dir --index-url https://pypi.org/simple coga`
   (or pin `coga==<version>`), then `coga --version`; any scratch-repo
   `coga init`/`coga validate` here needs the same `env -u SLACK_WEBHOOK_URL`
   as step 2. Right after the upload,
   an unpinned install can still resolve the previous version from a stale
   index or cache: the 0.4.0 release's first check got 0.2.0, and a new fresh
   venv after the index refreshed got 0.4.0. Retry before treating an old
   version as a failed publish; the release page and the workflow run are the
   upload evidence.

Each version uploads once per index. To re-test on TestPyPI, bump to a dev
version such as `0.2.0.dev1`. A bad release can be yanked, not deleted.

## Clean first-install gate

After publishing, use the [clean-install harness release continuation](https://github.com/FastJVM/coga/blob/main/coga/skills/coga/testing/clean-install/SKILL.md#verify-a-published-release)
with the exact published version. It combines a fresh install with an attended,
authenticated agent launch and verifies that the task finished with durable
state and a clean repository. Keep the resulting receipts with the release
verification. Install/init success alone does not satisfy this gate.

The gate is an owner step. The harness continuation and an attended
`coga build` both start an interactive, authenticated agent, which an agent
session must not nest, so a launched agent can prepare the commands and run
the non-interactive checks (wheel contents, fresh-venv install, init,
validate) but cannot pass the gate itself. For 0.4.1 the owner skipped it:
the ticket closed on the agent-run checks with "Attended checks skipped by
owner decision", and no TestPyPI dry run or pre-tag gate receipt exists for
that release.
