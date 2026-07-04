---
slug: allow-creation-of-coga-dir-in-subdir
title: allow creation of coga dir in subdir
status: in_progress
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 2 (self-qa)
---

## Description

Allow `coga init` to scaffold `coga/` in a subdirectory of a host repo
(e.g. `coga init tools/ops` inside a monorepo) instead of requiring the git
root.

**Step 1 — test the current behavior** (in a throwaway repo, before writing
any code) and record the results on the blackboard:

1. `coga init <subdir>` inside a git repo — expected to refuse today:
   `_is_git_repo` (`src/coga/commands/init.py`) checks `(target/".git").exists()`,
   and a subdir has no `.git`. Confirm.
2. With a hand-placed nested `coga/` in a subdir: run `coga status` / `launch`
   from inside the subtree (should work — `find_repo_root` in
   `src/coga/config.py` walks up checking each ancestor and its direct `coga/`
   child) and from the host-repo root (expected NOT to find it — discovery
   never descends more than one level). Confirm both, and check git task-state
   sync behaves with `coga/` below the git root.

**Then fix what the test shows is broken**: relax init's git check to "inside
a git work tree" (`git rev-parse`), decide whether from-the-git-root discovery
of a nested `coga/` is in scope or documented as out, add tests for the nested
layout, and fail loud on layouts that can't work (e.g. a `coga/` inside an
existing `coga/`). If the tests show everything already works, mark the ticket
done with the evidence on the blackboard instead of changing code.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Step-1 findings (throwaway repo, editable install of current main)

Test setup: fresh git repo `throwaway/` with `tools/ops/` subdir; `COGA_REPO_URL`
pointed at the local checkout so init clones offline.

1. **`coga init tools/ops` inside a git repo refuses — confirmed.** Exit 2,
   "…/tools/ops is not a git repository". Cause is `_is_git_repo` checking
   `(target/".git").exists()` as the ticket predicted.
2. **Hand-placed nested `coga/` (copied from `example/coga`) works from inside
   the subtree — confirmed.** From `tools/ops` (and deeper): `coga status`,
   `coga create`, `coga launch <slug> --prompt-report` (full prompt composition),
   and `coga validate --json` all succeed.
3. **Git task-state sync works with `coga/` below the git root — confirmed.**
   `coga create` from `tools/ops` committed `tools/ops/coga/tasks/...` at the
   *host* git root with correct relative paths ("Ticket: nested-sync-smoke —
   created" + "Sync coga state" commits). `git.py` resolves the git root via
   `rev-parse --show-toplevel` (`_toplevel`) and rebases paths with
   `_relative_to_root`, so nesting is already handled. (A `git push origin main`
   error appeared only because the throwaway had no remote — same in any layout,
   not nesting-related.)
4. **Discovery from the host-repo root does NOT find the nested coga —
   confirmed.** From `throwaway/` and `throwaway/tools/`: "No coga.toml found".
   `find_repo_root` walks up and only descends one level into a direct `coga/`
   child.

## Decisions

- **Only init's git check is actually broken** → relax it to "target is inside
  a git work tree" via `git rev-parse --is-inside-work-tree`, run against the
  nearest *existing* ancestor of the target (init may create the target dir).
  `_git_commit_coga_os` shares the predicate, and `git -C <subdir> add/commit`
  already works from a subdir, so the commit path needs no other change.
- **From-the-git-root discovery of a nested coga/ is out of scope** — declared
  out, not implemented. Descending arbitrarily deep from the git root would mean
  scanning the whole tree and inventing a tie-break for multiple nested cogas.
  The rule stays: walk up + one level down; you operate a nested coga from
  inside its subtree. Documented in init's refusal/help text and covered by a
  test asserting the miss.
- **Fail loud on coga-inside-coga**: refuse `coga init` when the target or any
  ancestor already holds a `coga.toml` (i.e. the target sits inside an existing
  coga OS tree) — that layout shadows the enclosing repo and can't work sanely.
- **Nested init counts as a filled repo**: when the target is not the git
  toplevel, skip onboarding-ticket seeding even if the subdir itself is empty —
  the host monorepo is an established project; the bootstrap interview is for
  genuinely new repos.

## Dev

- branch: init-in-subdir
- worktree: /home/n/Code/claude/coga-init-in-subdir
- commit: 56adaf44 "Allow coga init to scaffold coga/ in a subdir of a host repo"

## Implemented (step: implement)

- `src/coga/commands/update.py`: new shared `is_git_repo(target)` — `.git`
  existence fast path (dir or worktree/submodule file, same as before), else
  `git rev-parse --is-inside-work-tree` from the nearest *existing* ancestor
  (the target subdir may not exist yet). `ensure_host_gitignore` now uses it,
  so the coga-managed `.gitignore` block lands at the nested target (git
  scopes a nested ignore file to its own dir — where the symlinks and `.coga/`
  actually live).
- `src/coga/commands/init.py`: dropped `_is_git_repo` in favor of the shared
  predicate (init's up-front check + `_git_commit_coga_os` — `git -C <subdir>
  add/commit` resolves pathspecs relative to the subdir, commit lands in the
  host repo, no other change needed). Added `_enclosing_coga_root` +
  fail-loud refusal when the target sits inside an existing coga OS tree
  (walk up checking `coga.toml`, stopping at the first `.git` boundary).
  Nested init (no own `.git`) always counts as filled → onboarding ticket
  never seeded. Refusal message now says "not inside a git repository" and
  suggests `git init` in the target *or an ancestor*; `PATH` help text
  documents the monorepo form.
- `src/coga/config.py`: `find_repo_root` docstring documents the deliberate
  walk-up + one-level-down scope (host-root discovery of nested coga out of
  scope); "No coga.toml found" error now hints that a nested coga/ is only
  discovered from inside its subtree.
- `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md`:
  init section documents subdir init, subtree-only discovery, and the
  coga-in-coga refusal. (No live `coga/contexts/coga/cli` override exists in
  this repo — packaged copy is the only touchpoint.)
- Tests: `test_init.py` — nested init end-to-end (real git repo, commit paths
  below git root, gitignore block at target, onboarding not seeded),
  coga-in-coga refusal (subdir of coga tree + coga dir itself), `is_git_repo`
  unit tests (missing-subdir walk, fast path); updated the two "not a git
  repository" message asserts. `test_config.py` — nested discovery found from
  inside subtree / not from host root.

## Verification

- `python -m pytest` in the worktree: 1037 passed, 1 skipped (pre-existing).
- Real-CLI e2e in a throwaway host repo (venv-installed worktree package,
  `COGA_REPO_URL` pointed at the worktree): `coga init tools/ops` succeeds
  (full clone+venv), commits `tools/ops/coga/**` into the host repo, skips
  onboarding; from inside the subtree `status` / `create` / `validate --json`
  / `launch --prompt-report` all work and syncs commit at the host git root;
  init inside `tools/ops/coga/...` and init outside any git repo both refuse
  with the new messages.
- `coga/log.md` left dirty after a create-sync is identical at root-level
  layout (lazy catch-all sweep picks it up next invocation) — not a nested
  regression.

Note for follow-up consideration (not fixed here, adjacent): `coga uninstall`
and any other command using a bare `(target/".git").exists()` outside
init/update paths were not audited beyond what the tests cover; uninstall
operates on an already-discovered repo so it should be unaffected.

## Usage

{"agent":"claude","cache_creation_input_tokens":412014,"cache_read_input_tokens":12220441,"cli":"claude","input_tokens":21851,"model":"claude-fable-5","output_tokens":136849,"provider":"anthropic","schema":1,"session_id":"b7defcfd-1766-4f8b-bb30-66374638fd20","slug":"allow-creation-of-coga-dir-in-subdir","step":"implement","title":"allow creation of coga dir in subdir","ts":"2026-07-03T19:38:28.090672Z","usage_status":"ok"}

{"agent":"claude","cache_creation_input_tokens":156970,"cache_read_input_tokens":719974,"cli":"claude","input_tokens":13675,"model":"claude-fable-5","output_tokens":45984,"provider":"anthropic","schema":1,"session_id":"e5137934-8bab-4673-93d9-b808225c418d","slug":"allow-creation-of-coga-dir-in-subdir","step":"self-qa","title":"allow creation of coga dir in subdir","ts":"2026-07-03T19:55:52.565343Z","usage_status":"ok"}
