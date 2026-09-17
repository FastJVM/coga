# Contributing to Coga

Bug reports, documentation fixes, and focused improvements are welcome.
Search the [issues](https://github.com/FastJVM/coga/issues) and
[pull requests](https://github.com/FastJVM/coga/pulls) before starting so you can
join existing work.

## Start with the problem

Use an issue to describe a bug or propose a change. A small reproduction or a
concrete use case is enough to start the conversation.

Substantive work belongs in a [Coga ticket](coga/tasks/), following the repo's
[ticketed-work principle](coga/contexts/coga/principles/SKILL.md#7-ticketed--every-unit-of-work-is-a-durable-directable-task).
If there is no ticket for your change, open an issue first so maintainers can
help agree on scope and create or identify the ticket. You do not need to set
up Coga to file an issue. Small typo fixes can go straight to a pull request.

## Set up and test

Use Python 3.11+ and Git. Fork and clone the repository, then run from its root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test]"
python -m pytest
```

The [development guide](docs/development.md) covers the CLI smoke check,
source layout, coding style, configuration, and keeping behavioral docs and
packaged templates in sync. Read it before changing Coga's behavior.

## Open a pull request

Keep the change focused. Explain the problem and resulting behavior, link the
Coga ticket for substantive work and any related issue, and include the exact
verification commands and results. If a check was not run, say why.
