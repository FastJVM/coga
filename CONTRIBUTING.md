# Contributing to Coga

Bug reports, documentation corrections, and focused code improvements are
welcome. You don't need to install or use Coga to open an issue or submit a
pull request.

## Start with the problem

Search the existing [issues](https://github.com/FastJVM/coga/issues),
[pull requests](https://github.com/FastJVM/coga/pulls), and
[Coga tickets](coga/tasks) before starting. For a bug, describe what you did,
what happened, and what you expected; a small reproduction is more useful
than a broad proposed fix.

For a change in behavior or a new feature, open an issue first if no ticket
already covers it. Maintainers can help agree on the scope and create or
identify a Coga ticket. Substantive work is coordinated through these
Markdown tickets; external contributors are not required to operate Coga.
Small typo fixes can go directly to a PR.

Coga is deliberately a thin layer on top of existing coding agents. Read
the [design principles](docs/contexts/coga-dev/principles/SKILL.md)
before proposing a larger change.

## Set up and test

Fork and clone the repository. You need Git and Python 3.11 or newer;
verify which Python your terminal uses before creating a virtual environment.

On macOS or Linux:

```sh
python3 --version             # must report 3.11+
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[test]"
python -m pytest
```

On Windows PowerShell, with Python 3.11 installed:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest
```

If the system Python is older, choose a 3.11+ interpreter before creating
the environment. The [testing guide](docs/contexts/coga-dev/testing/SKILL.md)
covers `uv` environments without pip, CLI smoke checks, platform-specific
tests, and the current CI policy.

## Make a focused change

Before editing behavior, read the topic that owns it in the
[documentation index](docs/README.md). Keep the documentation and code
consistent. The [codebase guide](docs/contexts/coga-dev/codebase/SKILL.md)
covers layout and coding conventions; [configuration](docs/contexts/coga/configuration/SKILL.md)
explains `coga.toml`; and [packaging](docs/contexts/coga-dev/packaging/SKILL.md)
explains why changes to shipped contexts and templates often need matching
edits in both the canonical and packaged files.

## Open a pull request

Explain the problem, what you changed, and how you checked it. Link the
relevant ticket and issue for substantive work. Include the exact test
commands and results; if tests were not run, say so and why. Keep the PR
scoped to one problem so it can be reviewed independently.
