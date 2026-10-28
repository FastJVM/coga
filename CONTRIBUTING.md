# Contributing to Coga

Bug reports, documentation fixes, and focused improvements are welcome.
Search the [issues](https://github.com/FastJVM/coga/issues) and
[pull requests](https://github.com/FastJVM/coga/pulls) before starting so you can
join existing work.

## Start with the problem

Use an issue to describe a bug or propose a change. A small reproduction or a
concrete use case is enough to start the conversation.

For substantive changes, open an issue first so maintainers can agree on
scope and create or identify a [Coga ticket](coga/tasks), following the
[design principles](docs/contexts/coga-dev/principles/SKILL.md).
You do not need to install Coga to file an issue or submit a pull request.
Small typo fixes can go straight to a pull request.

## Set up and test

Use Git and Python 3.11+ (not an older system Python). Fork and clone the
repository, then run from its root.

On macOS or Linux:

```sh
python3 --version                 # must be 3.11+ before creating the venv
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

If `python3` is older, choose a 3.11+ interpreter before creating the
environment. For `uv`-created environments (which may not include pip),
follow the [testing guide](docs/contexts/coga-dev/testing/SKILL.md).

The [testing](docs/contexts/coga-dev/testing/SKILL.md) topic covers the CLI smoke
check and test commands; [codebase](docs/contexts/coga-dev/codebase/SKILL.md)
covers source layout, coding style, and commit conventions;
[configuration](docs/contexts/coga/configuration/SKILL.md) covers `coga.toml`
and `coga.local.toml`; and [packaging](docs/contexts/coga-dev/packaging/SKILL.md)
covers keeping the canonical topics and packaged templates in sync. Read the
owning topic under [`docs/contexts/`](docs/README.md) before changing Coga's
behavior.

## Open a pull request

Keep the change focused. Explain the problem and resulting behavior, link the
Coga ticket for substantive work and any related issue, and include the exact
verification commands and results. If a check was not run, say why.
