---
title: Remove the post-merge automerge git hook
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: codex
contexts:
- relay/principles
- relay/cli
- relay/codebase
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 2 (peer-review)
---

## Description

Sibling of `move-automerge-out-of-relay-status`. That ticket removed
the `relay automerge` side effect from `relay status`. This one removes
the other implicit automerge trigger: the `post-merge` git hook.

`relay init` symlinks `relay-os/bootstrap/hooks/post-merge` into
`.git/hooks/post-merge`, so every `git pull` that merges shells out to
`gh` for each active ticket and may bump tickets / post to Slack. The
hook script is `relay automerge || true` — the `|| true` swallows
*every* failure (missing `gh`, unauthed, offline), the same fail-loud
violation that motivated removing the `status` side effect. Removing it
makes `relay automerge` a purely explicit surface.

Decided with Nick (2026-05-21): the long-tail catch-up will be a
cron-driven sweep, added in a later ticket. In the interim, automerge
is explicit-only (`relay automerge`) plus the `relay launch`
freshness check (sibling `verify-ticket-freshness-on-relay-launch`).

## Scope

Remove the hook and all of its machinery:

- Delete `relay-os/bootstrap/hooks/post-merge` and the packaged
  `src/relay/resources/templates/relay-os/bootstrap/hooks/post-merge`
  (the `bootstrap/hooks/` directory then goes away).
- `commands/init.py` — remove `_install_post_merge_hook`,
  `_print_post_merge_status`, their four call sites, and the
  `relay status covers the gap` comments (lines ~423, ~514). Check
  whether `_find_git_dir` is left unused.
- `commands/update.py` — drop the `"hooks"` prune-list entry, the
  `bootstrap/hooks` mentions in the docstrings, and the hook chmod
  loop in `_chmod_packaged_executables`.
- `automerge.py` module docstring — drop the `post-merge git hook`
  caller mention.
- `commands/automerge.py` — drop any hook reference in help text.
- `tests/test_init.py` — remove the post-merge hook install tests and
  the hook entries in fixtures / expected-path lists.
- `README.md` and the `relay/cli` context — drop the
  `relay init symlinks this into .git/hooks/post-merge` claims (live
  project-local copy + packaged copy).

## Out of scope

- The cron-driven sweep — its own future ticket.
- Any change to `relay automerge`'s sweep logic.

## Sequencing

Land after `move-automerge-out-of-relay-status`. The future
cron-sweep ticket lands after this one.
