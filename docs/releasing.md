# Releasing coga to PyPI

coga publishes to PyPI via **Trusted Publishing** (OIDC) from
[`.github/workflows/release.yml`](../.github/workflows/release.yml). GitHub
authenticates to PyPI per-run over OIDC, so **no API token is created, stored, or
pasted anywhere.**

## One-time setup (per index)

A trusted publisher must be registered on each index *before* the workflow can
publish. **Which form to use depends on whether the project already exists on
that index:**

- **Name not yet registered** → the account-level **"pending publisher"** form
  (Account settings → Publishing). This is the case for TestPyPI below.
- **Project already exists** → the project-level form under **Manage →
  Publishing → Add a trusted publisher**. This is the case for **PyPI**: the
  `coga` name was reserved with a `0.0.1` placeholder, so the project already
  exists and the pending-publisher form does **not** apply.

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

`coga` **already exists on PyPI** (the `0.0.1` placeholder), so use the
*project-level* form, not the account-level pending-publisher one:
<https://pypi.org> → **Your projects → `coga` → Manage → Publishing → Add a
trusted publisher** (GitHub). The project name is implied by the page, so you
only enter:

| Field | Value |
|---|---|
| Owner | `FastJVM` |
| Repository name | `coga` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

### 3. (Optional) Require approval for production

The workflow runs the PyPI job in a GitHub environment named `pypi` (auto-created
on first run). In **repo Settings → Environments → `pypi`** you can add a
*required reviewer* so a human must approve every real publish.

## Dry run on TestPyPI

Optional — recommended for a *first-ever* release, but you can skip straight to
the real release below. PyPI uploads are immutable, so the dry run is the only
no-cost way to catch a packaging problem before it's permanent.

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
