---
slug: install/document-where-to-run-init-and-adopt-existing-repo
title: Document where to run relay init and how to adopt an existing project
status: done
owner: zach
human: zach
agent: claude
assignee: zach
contexts:
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
secrets: null
---

## Description

Greg didn't realize `relay init` is meant to be run inside the root of the repo
he wants to work on; he created a fresh empty directory to try it, then couldn't
figure out how to bring his actual project in. Getting Started should state
plainly that Relay is adopted into an existing project's git root — and what to
do if you started in an empty directory — so the mental model is clear before the
first command.

## Context

Reported by Greg. This is a docs/onboarding-clarity fix, not a behavior change.
Touchpoint: README Getting Started, under editorial revision in
`marketing/readme-and-docs`. Related behavior ticket:
`marketing/relay-init-git-inits-a-fresh-dir` (fail loud when the init target
isn't a git repo).

**Retest 2026-07-08 (fresh-container):** the behavior half is fixed — init in
a non-git dir fails loud with "Run `git init` … first". The docs half is
worse than before: the current README (73 lines) has **no Getting Started at
all** — it never mentions `coga init`, `--user`, running in the project's git
root, adopting an existing repo, or that git *and gh* are required at init
(no External CLI Tools section). Also: the "No coga.toml found" error tells
you to run coga "from inside a Coga repo" without naming `coga init` — add
the hint there too (`src/coga/cli.py`).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
pr: https://github.com/FastJVM/coga/pull/543
branch: docs/init-adopt-existing-repo
worktree: /tmp/coga-init-adoption-docs

## Implement

- Scope confirmed from the 2026-07-08 retest: add a compact README Getting Started path covering prerequisites, existing-repo-root adoption, `--user`, and empty-directory recovery; add `coga init` to the missing-config CLI hint.
- Product edits are isolated in the feature worktree above; launch checkout changes remain control-plane-only.
- README now says Coga is adopted inside the target project's Git root, names Git and `gh` as init prerequisites, shows `coga init --user <your-name>`, and distinguishes moving to an existing repo from running `git init` for a genuinely new project.
- `src/coga/cli.py` now turns the missing-config result for known repo commands into a direct `coga init --user NAME` adoption hint while preserving repo-free help/init/uninstall behavior. Regression coverage lives in `tests/test_aliases.py`.
- Verification: `PYTHONPATH=/tmp/coga-init-adoption-docs/src python3.12 -m pytest` -> 1122 passed, 1 skipped; `git diff --check` clean.
- Commit: `66f505f3e15ef20cf491b9bd217bfa6c8c07a160` (`Clarify how to initialize Coga in a project`). Feature worktree is clean. No push or PR created in this step.

## Peer Review

- Native `codex review --base main` found one must-fix P2: default aliases such as `coga build` and `coga chat` still emitted the old missing-repo error without the new `coga init --user NAME` adoption hint.
- Fixed the finding by recognizing public default aliases on the same missing-config path, while preserving alias help outside a Coga repo. Regression coverage now exercises both `status` and `build` plus `chat --help`.
- Peer-review commit: `7b3aca7fe077d7be788f67e397a65d90ebce1b59` (`peer-review: add init hint for default aliases`). The implementation commit was rewritten to `2cee388265b160a6b035792e2f259b7e72735cf3` when the branch was rebased onto current `main`.
- Post-rebase verification: `PYTHONPATH=$PWD/src python3.12 -m pytest` -> 1123 passed, 1 skipped; `git diff --check main...HEAD` clean; real `coga build` outside a repo exits 2 with the adoption hint. Feature worktree is clean and `main` is an ancestor of the branch.

## PR

Add a compact Getting Started path that tells operators to initialize Coga from their project's Git root, names the required Git and GitHub CLIs, explains recovery from an empty directory, and gives missing-repo commands and default aliases a direct `coga init --user NAME` hint.

Test plan: `PYTHONPATH=$PWD/src python3.12 -m pytest` (1123 passed, 1 skipped).
