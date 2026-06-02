---
title: auto-commit & push ticket state — git.py helper + same-branch wiring (A)
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/sync
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
---

> **This is ticket A of a 3-ticket split.** B
> (`git-sync-b-cross-branch-to-main`) adds the
> cross-branch-to-`main` mechanism. C
> (`git-sync-c-panic-and-ticket-auth`) wires the bespoke
> sites. A is the foundation B and C build on. Scope A strictly to what's
> below — defer cross-branch and the bespoke sites.

## Description

Every relay CLI command that mutates ticket state today writes files to
disk and posts to Slack, but does **no** git operations — so the
git-backed repo drifts from the team's actual state until a human
commits and pushes by hand. This is the git analogue of the existing
Slack sync layer: **always-on, no opt-out flag**.

Ticket A lays the foundation: a shared `src/relay/git.py` helper that
commits the changed `relay-os/tasks/<slug>/` files and pushes, plus the
config it needs, plus a real-git test fixture — and wires it into the
clean call-site set **for the same-branch case only** (HEAD is already
the control branch). When HEAD is a feature branch, A no-ops with a
warning; making task state reach `main` from a feature branch is B's job.

Done looks like: with the repo checked out on `main`, after `relay draft`
/ `mark` / `bump` / `retire` / `recurring` (and automerge's auto-bump),
the changed task files are committed and pushed automatically, with a
real-git test fixture proving it.

## The control-plane / feature split (core design intent — spans A+B)

The reason for the whole effort is a hard line between two kinds of git
state:

- **Ticket / control-plane state** — `relay-os/tasks/<slug>/` files
  (`ticket.md`, `blackboard.md`, `log.md`). Shared team state; belongs on
  `main` immediately so the repo always reflects what the team is doing.
  Does **not** go through PR review.
- **Feature code** — source under `src/relay/` etc. Lives on a feature
  branch, ships via `code/with-review` → PR → merge.

The full intent is that control-plane state reaches `main` *regardless of
the current branch*. A delivers the same-branch half of that; B delivers
the cross-branch half. Design A's helper interface so B can extend it
(don't bake in a "current branch only" assumption deeper than the wiring).

## Context

- **No git plumbing exists in these commands today.** The only
  subprocess/git usage in the package is `automerge.py` (shells out to
  `gh`). Mirror that subprocess pattern, but factor the commit+push into
  a **shared helper** (e.g. a new `src/relay/git.py`) rather than copying
  inline into each command — the call sites are the same set that already
  call `slack.post`.

- **Call sites for A = the clean injection set** (the rest go to C).
  Wire commit+push in right after the `slack.post()` call in the *logic*
  modules, which is where the file write + log + post sequence finalizes:
  - `relay/mark.py` — all 4 finalizers (`mark_done:50`, `mark_active:162`,
    `mark_in_progress:184`, `mark_paused:205`). This covers `relay mark`
    **and** the automerge auto-bump (`automerge._try_bump_one` → `mark_done`).
  - `relay/bump.py` — `advance_step:102` (covers `relay bump`).
  - `commands/create.py` — after `scaffold_draft:104` (covers `relay draft`
    / `create`, and `relay ticket`'s initial scaffold).
  - `commands/retire.py:116` and `commands/recurring.py` scaffolds.

  **Deferred to C, not A:** `commands/panic.py` (blackboard-only path) and
  the `relay ticket` *authoring* edits (the launched agent edits `ticket.md`
  externally — no `post()` to hook). Don't wire those here.

- **A is same-branch only.** When HEAD is the control branch (`main`):
  commit the task files and `git push` — straightforward. When HEAD is a
  feature branch: **no-op with a clear warning** (e.g. "ticket state not
  synced to main — feature branch; ticket B handles this"). Do **not**
  `git checkout main`. Reaching `main` from a feature branch is ticket B —
  but design `git.py`'s public function so B can slot the cross-branch path
  in without reworking every call site.

- **Auto-push to `main` is a deliberate exception to the PR-review flow.**
  Every *code* change here goes through `code/with-review` → PR → human
  merge. Task-state files are not code, so pushing them straight to `main`
  is intentional — call it out in the PR description, and confirm it
  doesn't conflict with the `automerge` post-merge hook.

- **Config surface.** `Config` (`config.py:54-67`) knows nothing about git
  — no remote name, no branch name, no git root (`find_repo_root` walks for
  `relay.toml`, not `.git`; `repo_root` can even *be* `relay-os/`). Add the
  small surface A needs: resolve the git toplevel separately from
  `cfg.repo_root` (crib the `.git`-walk from `commands/init.py:607`), and
  add config keys for remote/control-branch (e.g. `[git] remote = "origin"`,
  `control_branch = "main"`) with sane defaults. Weigh a `[git].enabled`
  opt-out for repos with no remote (parallel to `slack_enabled`).

- **Failure handling.** With no opt-out flag, decide what happens when
  push fails (offline, no remote, non-fast-forward). `relay/sync`
  documents Slack's "crash loud, don't degrade silently" philosophy — but
  a `git push` failing mid `relay launch` auto-chain could be more
  disruptive than a Slack failure. Define a typed `GitError` and settle
  crash-loud vs warn-and-continue with the peer reviewer.

- **Scope the commit narrowly.** Commit only the affected
  `relay-os/tasks/<slug>/` files (not `git add -A`) so unrelated
  working-tree changes aren't swept in. Never commit `relay.local.toml`
  or secrets (global rule).

- **Commit message style.** Match the existing legible style — see
  `git log`: `Ticket: rename workflow → playbook ...`,
  `Freeze workflow on split-context-to-doc task`. Suggest something like
  `Ticket: <slug> — <transition>`.

- **Build the real-git test fixture — it's foundational (B and C reuse
  it).** Today git is fully *mocked*: `tests/conftest.py:26` autouses
  `_stub_slack`, and `test_automerge.py` monkeypatches `pr_state` rather
  than running git. There is no real-git harness. A must add one:
  `git init` a tmp repo with a **bare `origin`** in `tmp_path` (so `push`
  works without network), run the command, assert the task files were
  committed and pushed. Make it a reusable fixture — B extends it with
  feature-branch + concurrency assertions, C reuses it for its sites.

- **This is `src/relay/` work** (relay itself), the higher review bar.
  Per CLAUDE.md, update the seeded `example/` fixture and `tests/` when
  command behavior changes; run `python -m pytest` and
  `relay validate --json`.
