# Publishing the placeholder to PyPI

This directory exists to reserve the `relay-os` name on PyPI before
someone else takes it. After the first publish, this directory is
mostly historical — subsequent real releases will be cut from
`relay-cli/`.

## One-time setup (per machine)

If you don't already have a PyPI account and `twine` configured:

1. Create an account at https://pypi.org/account/register/
2. Generate an API token: https://pypi.org/manage/account/token/
   Scope it to "Entire account" the first time. After the first publish
   you can re-issue a token scoped to the `relay-os` project only.
3. Save the token. Either configure `~/.pypirc`:

   ```ini
   [pypi]
     username = __token__
     password = pypi-AgENd...your-token-here
   ```

   Or export it just before running upload:

   ```bash
   export TWINE_USERNAME=__token__
   export TWINE_PASSWORD=pypi-AgENd...your-token-here
   ```

4. Install the build/upload tools:

   ```bash
   pip install --upgrade build twine
   ```

## Publish

From this directory:

```bash
cd pypi-placeholder

# Wipe any old build artifacts.
rm -rf dist build src/*.egg-info

# Build sdist + wheel into dist/
python -m build

# Sanity-check the artifacts before uploading.
twine check dist/*

# Upload to PyPI. THIS IS PERMANENT — once 0.0.1 is published, you
# cannot re-use that version number. Yank-only is the closest to undo.
twine upload dist/*
```

## Verify

In a fresh shell (or virtualenv), confirm the upload worked:

```bash
pip install relay-os
python -c "import relay_os; print(relay_os.__version__)"
# Should print: 0.0.1
```

The name `relay-os` is now reserved. Future real releases bump the
version (e.g. `0.1.0`) and publish from `relay-cli/`.

## Notes

- PyPI is unforgiving about version reuse. If `twine upload` fails for
  any reason after PyPI accepted the version, you must bump to `0.0.2`
  for the next attempt — you cannot re-upload `0.0.1`.
- If you accidentally publish broken metadata, run
  `pip install pkginfo` then `pkginfo dist/relay_os-0.0.1*.whl` to
  inspect what got built before deciding whether to yank.
- TestPyPI (`https://test.pypi.org/`) exists for dry-runs. To use it,
  add a `[testpypi]` section to `~/.pypirc` and run
  `twine upload -r testpypi dist/*`. Test uploads are isolated from
  the real index.
