# Releasing coga to PyPI

coga publishes to PyPI via **Trusted Publishing** (OIDC) from
[`.github/workflows/release.yml`](../.github/workflows/release.yml). GitHub
authenticates to PyPI per-run over OIDC, so **no API token is created, stored, or
pasted anywhere.**

## One-time setup (per index)

A trusted publisher must be registered on each index *before* the first upload,
using the "pending publisher" form (the project doesn't exist yet).

### 1. TestPyPI — the dry-run sandbox (do this first)

1. Create/sign in at <https://test.pypi.org>.
2. **Account settings → Publishing → Add a pending publisher** (GitHub).
3. Enter exactly:
   | Field | Value |
   |---|---|
   | PyPI Project Name | `coga` |
   | Owner | `FastJVM` |
   | Repository name | `coga` |
   | Workflow name | `release.yml` |
   | Environment name | `testpypi` |

### 2. PyPI — the real index

Same form at <https://pypi.org> → **Account settings → Publishing → Add a pending publisher**:

| Field | Value |
|---|---|
| PyPI Project Name | `coga` |
| Owner | `FastJVM` |
| Repository name | `coga` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

### 3. (Optional) Require approval for production

The workflow runs the PyPI job in a GitHub environment named `pypi` (auto-created
on first run). In **repo Settings → Environments → `pypi`** you can add a
*required reviewer* so a human must approve every real publish.

## Dry run on TestPyPI

1. Confirm `version` in `pyproject.toml` is what you intend to publish.
2. **Actions → Release → Run workflow** → target `testpypi`.
3. Confirm it landed: <https://test.pypi.org/project/coga/>
4. Install it from TestPyPI to verify (deps resolve from real PyPI):
   ```sh
   python3 -m venv /tmp/coga-test && source /tmp/coga-test/bin/activate
   pip install --index-url https://test.pypi.org/simple/ \
       --extra-index-url https://pypi.org/simple/ coga
   coga --version
   ```

## Real release on PyPI

1. Bump `version` in `pyproject.toml` if needed; get it onto `main`.
2. **Releases → Draft a new release** → tag `v<version>` (e.g. `v0.2.0`), target
   `main`, **Publish release**.
3. The workflow builds and publishes to PyPI automatically.
4. Verify: `pipx install coga && coga --version`.

## Notes

- Each version can be uploaded **once** per index (PyPI/TestPyPI are immutable).
  To re-test on TestPyPI, bump to a dev version such as `0.2.0.dev1`.
- A bad release can be **yanked** (hidden from new installs) but not deleted —
  which is exactly why we dry-run on TestPyPI first.
