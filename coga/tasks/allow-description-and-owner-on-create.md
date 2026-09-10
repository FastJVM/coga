---
slug: allow-description-and-owner-on-create
title: Allow --description and --owner on coga create
status: in_progress
owner: zach
human: zach
agent: claude
assignee: claude
contexts:
- dev/code
skills: []
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 2 (self-qa)
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
  known-users gate. Strip surrounding whitespace from `--owner` before writing
  (`" zach "` → `zach`); an empty/whitespace `--owner ""` fails loud via
  `_bail`, matching the empty-title check. An omitted or empty `--description`
  yields today's blank `## Description`.
- **Reject structure-breaking descriptions before writing.** A description
  written verbatim that contains a level-2 heading line (`## ...`, e.g.
  `## Context`) or the blackboard fence marker (the HTML comment that
  `split_body` in `src/coga/taskfile.py` splits on) corrupts the ticket's
  section/fence structure — and a failed post-write validation leaves the
  broken draft on disk (see
  `test_cli_create_reports_validation_failure_and_leaves_draft`). So check in
  the command, *before* calling `create_task`, and `_bail` with a clear message
  if either is present. Nothing is written on rejection.
- **`coga ticket` shares `create_draft`** (its new-draft branch). Keep the new
  keyword args optional with `None` defaults so that call site is unchanged.
- **Tests:** extend `tests/test_create.py` (see the existing
  `test_cli_create_*` tests for the CLI-invocation pattern). Cover: description
  lands under `## Description`; `--owner` sets `owner:` and `human:`; both
  omitted keeps current defaults; flags compose with a path-prefixed title and
  `--workflow`; empty `--owner` fails; padded `--owner` is stripped; a
  description containing a `## ` heading or the fence marker fails and leaves
  no ticket on disk.
- **Docs, same PR:** `docs/reference.md` (`### coga create TITLE` section) and
  the packaged CLI context
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md`
  (the `## coga create` heading, written with escaped angle brackets as
  `\<title\>` / `\<name\>` — update the heading signature and body). There is
  no live `coga/contexts/coga/cli/` twin, so no twin sync is needed; run
  `python -m pytest tests/test_packaging.py` anyway.
- **Fix a stale line while there:** that CLI context section says `coga create`
  posts `✨` when a notification channel is selected, but the code (and the
  `create.py` docstring) says create never posts to Slack. Correct it in the
  same PR.
- **Leave alone:** other flag-less mentions of `coga create "<title>"` (e.g.
  `src/coga/commands/init.py`, the `bootstrap/ticket` skill) are still correct.
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

## Dev
branch: create-description-owner
worktree: /home/zach2179/dev/coga-create-description-owner

## Implement notes
- Layout: separate feature checkout (sibling linked worktree). Ticket edits and
  `coga bump` stay in the primary checkout on `main`.
- `--description` / `--owner` pass through `create_draft` as keyword args
  defaulting to `None`, so `coga ticket`'s `create_draft(title=target)` call is
  unchanged. `create_task` is untouched.
- Owner: stripped; empty/whitespace -> `_bail("owner cannot be empty")`; no
  known-users gate. Omitted -> `cfg.current_user`, as before.
- Structure guard (human chose "match the parsers"): reject any line matching
  `^##(?:\s|$)`, the shape compose's `_SECTION_HEADING_RE` treats as a section
  (`###` allowed; a `## ` line inside a code block is also rejected, an
  accepted tradeoff). Reject `fence_count(description) > 0`, i.e. the fence on
  its own line, exactly what `split_body` counts; inline mentions allowed.
  Both checks run before `load_config`/`create_task`, so nothing is written on
  rejection.

## What changed
- `src/coga/commands/create.py`: `--description` / `--owner` Typer options;
  `create_draft` gains matching `None`-default kwargs, the owner strip/empty
  check, and `_description_structure_problem` (heading regex +
  `taskfile.fence_count`). Module docstring updated.
- `tests/test_create.py`: new `--description / --owner` section covering
  description placement, owner + human cascade, defaults with neither flag,
  composition with a path-prefixed title + `--workflow`, empty owner (`""`,
  `"   "`), padded owner, four structure-breaking descriptions (nothing on
  disk), and the allowed `###` / inline fence mention.
- `docs/reference.md` and packaged `bootstrap/contexts/coga/cli/SKILL.md`:
  new flags documented. The stale "posts ✨" line is replaced with "does not
  post to Slack".
- No example fixture change: flags are optional and don't touch task layout,
  composition, or workflow semantics.

## Verification (implement)
- `python -m pytest tests/test_create.py tests/test_packaging.py` → 70 passed.
- `coga create --help` renders both options.
- `coga validate --json` (primary checkout): no issues for this ticket.
- `python -m pytest` (full suite, feature worktree) → 2387 passed.
- Committed on `create-description-owner`, then rebased onto `origin/main`
  `449385d9` (4 new commits, task/log files only) -> `c4a554d6`. Targeted
  tests re-run after rebase: 70 passed. Not pushed; no PR (later steps).
