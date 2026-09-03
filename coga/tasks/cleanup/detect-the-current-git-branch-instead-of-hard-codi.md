---
slug: cleanup/detect-the-current-git-branch-instead-of-hard-codi
title: Detect the current git branch instead of hard-coding control branch main
status: in_progress
owner: nicktoper
human: nick
agent: claude
assignee: codex
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 2 (peer-review)
---

## Description

`coga init` writes `control_branch = "main"` into the scaffolded config
regardless of the repo's actual branch. On a machine whose `git init` creates
`master`, every subsequent Coga command prints the "control branch 'main' does
not exist (you are on 'master')" warning two or three times. Detect the
checkout's current branch at init time, or fail loud with the one-line fix.

## Context

**Reproduction** (audit, 2026-09-02): on a machine without
`init.defaultBranch=main`, `git init` makes `master`; `coga init --user tester`
succeeds and writes `control_branch = "main"`; from then on `coga status`,
`coga create`, and `coga launch` each emit the nag repeatedly. Every step of
the README quickstart is noisy for such a reader.

**Options.** Read the checkout's current branch and write that value; or keep
the `main` default but detect the mismatch during init and either offer to
rename the branch or print the exact `coga.toml` line to change. Prefer
whichever keeps the first run quiet without silently disagreeing with the
repo. Note the warning itself is correct behavior (fail loud) — the bug is
that init creates the mismatch it then complains about.

**Docs.** If the answer is documentation rather than detection,
`docs/getting-started.md` is where a reader would need it, before the init
step.

Source: `marketing/phase-0-audit` step 1 (2026-09-02), triaged by the owner
in step 2 (2026-09-03). This directory holds the work the owner wants done
before the marketing materials ship.

<!-- coga:blackboard -->

## Dev

branch: init-control-branch
worktree: /home/n/Code/coga-init-control-branch

## Findings

- `coga init` does **not** literally write `control_branch = "main"`. The
  packaged template ships `[git]` fully commented out
  (`src/coga/resources/templates/coga/coga.toml`, the "--- Git sync ---" block);
  the value comes from the `Config.git_control_branch = "main"` default in
  `src/coga/config.py:117`.
- The nag text is `git._control_branch_mismatch_message` (`src/coga/git.py:5908`),
  emitted whenever `git._control_branch_present(root, branch, remote)` is false.
  That predicate is the exact trigger to gate the fix on.
- `git._symbolic_head` (`src/coga/git.py:5873`) already resolves the branch name
  *before the first commit* (unborn HEAD), which is precisely the
  `git init` + `coga init` case. Reused rather than reimplemented.

## Decision (confirmed with the human, 2026-09-03)

Pin the detected branch into the scaffolded `coga/coga.toml` **only when the
configured default control branch is genuinely absent** (no local ref, no
remote ref). Rationale: an unconditional pin would record a *feature* branch as
the control branch when someone runs `coga init` while on a branch of an
established main-based repo — trading one wrong config for another.

- Cannot resolve a branch (detached HEAD / git error) *and* the default is
  absent -> init still succeeds but prints the exact one-line
  `[git] control_branch = "..."` fix (human's call: loud notice, not exit 2).
- Docs: add a bullet to `docs/getting-started.md` under "A few things worth
  knowing about init" (human's call: code + docs).

Tradeoff accepted: a fresh init on a non-`main` repo now writes a real `[git]`
table into a config that previously shipped comments-only, and a later branch
rename still needs a manual edit.

## Implemented (2026-09-03)

Commit `e4a6f82f` on `init-control-branch`, rebased onto `origin/main`.

`src/coga/commands/init.py`:

- `_scaffolded_git_defaults(coga_os)` -> `(control_branch, remote, declared)`.
  Parses only `[git]` with `config._parse_git` rather than calling
  `load_config`: an earlier draft used `load_config` and made init *fail* on an
  unrelated config problem (caught in the live repro — an ambient
  `SLACK_WEBHOOK_URL` aborted and rolled back the whole init). `declared` is
  true when the scaffold ships a real `[git]` table, which init then refuses to
  edit (a second table would not parse).
- `_detect_control_branch(target, *, control_branch, remote)` gates on
  `git._control_branch_present` — the exact predicate behind the nag — then
  reads `git._symbolic_head` (resolves an *unborn* HEAD, so it works before the
  first commit). Soft-skips on `GitError`/`OSError`; the `OSError` arm matters
  because three existing tests run init with `PATH=""`, i.e. no `git` binary.
- `_pin_control_branch` inserts the table above the `# --- Aliases ---` heading
  in the scaffolded `coga.toml`, before `_git_commit_coga_os` commits it.
  Falls back to appending for a scaffold without the shipped headings.
- Post-init output: a plain line naming what was set, or a yellow one-liner
  with the exact `[git] control_branch` fix when nothing could be recorded.

`docs/getting-started.md`: bullet under "A few things worth knowing about init".

`tests/test_init.py`: six tests — `master` repo pins, `main` repo on a feature
branch does *not* pin, detached HEAD warns, an unreadable repo soft-skips, a
scaffold with its own `[git]` table is left alone, and the packaged template
still carries the insertion anchor and no `[git]` table.

## Verification

- `python -m pytest` — 2210 passed (re-run after the rebase). Ran under a
  scratchpad 3.12 venv: the `python` on this machine's PATH is conda 3.9, which
  coga refuses, and no existing env had both coga and pytest.
- Live end-to-end in a throwaway `git init -b master` repo: init printed
  `Set [git] control_branch = "master"`, and `coga status` / `coga create` were
  quiet. Removing the pinned table from that same repo reproduced the ticket
  exactly — the nag twice on one `coga create`.

## Follow-up noted, not fixed here

`git._symbolic_head` and `git._control_branch_present` are now cross-module
imports of underscore-prefixed names (matching how init.py already imports
`_refresh_coga_gitignore` from `commands/update`). Both are genuine shared
infra with two consumers now; promoting them to public names is a separate
tidy-up, out of scope for this ticket.
