---
slug: allow-description-and-owner-on-create
title: allow-description-and-owner-on-create
status: draft
owner: zach
human: zach
agent: claude
assignee: zach
contexts:
  - dev/code
skills: []
workflow: code/with-self-review
secrets: null
---

## Description

Add two optional flags to `coga create`:

```
coga create "<title>" --description "<short description>" --owner <coga-name>
```

`--description` writes the text into the new ticket's `## Description`
section; `--owner` sets `owner:` to a coga name (e.g. `zach`, `nicktoper`)
instead of always defaulting to the local `user` from `coga.local.toml`. Both
stay optional — `coga create "<title>"` with neither flag must behave exactly
as it does today. The point is to scaffold a useful, correctly-owned draft in
one command, without opening the file or running the `coga ticket` interview.

## Context

- **Where:** `src/coga/commands/create.py` — the Typer command `create()` and
  the shared helper `create_draft()`. `create_draft` currently hardcodes
  `owner=cfg.current_user` and passes no description. Update the module
  docstring too.
- **Core already supports both — this should be a thin pass-through.**
  `create_task()` in `src/coga/create.py` already accepts `description=`
  (builds `## Description\n\n<text>\n\n## Context\n\n`, stripping whitespace)
  and `owner=` (falls back to `cfg.current_user` when `None`). No change to
  `create_task` should be needed.
- **Owner cascade is intended:** `create_task` sets `human = human or owner`,
  and a workflow-less create sets `assignee = assignee or owner` (with a
  workflow, step 1's role resolves against the owner). So `--owner nicktoper`
  also makes `human:` (and a workflow-less `assignee:`) `nicktoper`. Expose
  only `--owner`; no separate `--human` / `--assignee` flags.
- **Owner values:** coga names are the tokens in
  `[notification.slack.users]` in `coga/coga.toml` (today `zach` and
  `nicktoper`). Humans aren't otherwise enumerated in config and validation
  doesn't reject unknown owners, so accept any non-empty string — don't add a
  known-users gate. An empty/whitespace `--owner ""` should fail loud via
  `_bail`, matching the empty-title check. An omitted or empty `--description`
  yields today's blank `## Description`.
- **`coga ticket` shares `create_draft`** (its new-draft branch). Keep the new
  keyword args optional with `None` defaults so that call site is unchanged.
- **Tests:** extend `tests/test_create.py` (see the existing
  `test_cli_create_*` tests for the CLI-invocation pattern). Cover: description
  lands under `## Description`; `--owner` sets `owner:` and `human:`; both
  omitted keeps current defaults; flags compose with a path-prefixed title and
  `--workflow`; empty `--owner` fails.
- **Docs, same PR:** `docs/reference.md` (`### coga create TITLE` section) and
  the packaged CLI context
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md`
  (`## coga create "<title>" [--workflow <name>]` — update the heading
  signature and body). There is no live `coga/contexts/coga/cli/` twin, so no
  twin sync is needed; run `python -m pytest tests/test_packaging.py` anyway.
- **Reviewer:** Nico (`nicktoper`) reviews the PR. `coga open-pr` can't
  request GitHub reviewers, so the ticket owner (zach) adds him on GitHub once
  the PR opens; the `review` gate stays with the owner. Write the PR body
  (`## PR` on the blackboard, in `self-qa`) for a reviewer without this
  ticket's context: the behavior change, and the exact test commands run.
- **Out of scope:** adding these flags to `coga ticket`; reading the
  description from stdin or a file; multi-section bodies; validating owner
  names against config.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
