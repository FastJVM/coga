---
slug: fresh-repo-default-branch-mismatch-git-init-master
title: 'Fresh-repo default branch mismatch: git init master vs control_branch main'
status: in_progress
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
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
step: 4 (review)
---

## Description

On a brand-new repo where `git init` produced a `master` branch (the default on
many setups), Relay's `[git].control_branch` defaults to `main`. Every
state-mutating command then runs `git fetch origin main` / pushes to
`refs/heads/main` against a branch that doesn't exist, so the git sync fails.
The failure is swallowed (`GitError` → stderr + `log.md`) and the command still
exits 0 — so a first-time user following the README's Getting Started sees a
confusing error but no actual failure.

## Context

Surfaced walking a first-time user through README Getting Started in a clean
repo. Default-branch mismatch: `git init` → `master` on many setups vs
`[git].control_branch` default `"main"` (`src/relay/config.py:138`, `:889`).
The non-fatal-by-design swallow is at `src/relay/git.py:148-159` (failure model
in the module docstring, `git.py:29-40`), which is why it exits 0 and is easy to
miss.

Work happens in the **Relay** codebase (`src/relay/…`), not this coga repo — the
ticket only tracks it. The two configured agents are `claude` (implements) and
`codex` (peer-review).

### Decided direction (Nick, 2026-06-26): flag the mismatch, let the user set the toml

Don't auto-guess the branch. When `control_branch` (default `"main"`) doesn't
match the repo's actual branch (`master` or whatever), detect that and surface a
**clear, actionable message** telling the user to set `[git].control_branch` in
the toml to match their branch. The user fills it in — we just stop the failure
from being silent/confusing.

- Detect the mismatch (configured `control_branch` not present as a branch) at
  the point the git sync would otherwise fail silently (`git.py:148-159`).
- Replace the swallowed/confusing `GitError` with a message that names the fix:
  set `[git].control_branch = "<their branch>"` in the toml.
- No auto-detection of the "right" branch, no changing the default — the user
  owns that choice in config.

Keep it small. Out of scope: redesigning the failure model broadly; a README
note is optional if cheap but not the goal.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: fix-control-branch-mismatch-guidance
worktree: ../coga-control-branch-guidance
pr: https://github.com/FastJVM/coga/pull/469

## Implementation plan (claude, 2026-06-27)

Codebase note: the "Relay" / `src/relay/…` in the ticket is this repo's
`src/coga/…`. Line anchors map: failure model = `src/coga/git.py:35-50` (module
docstring), swallow boundary = `sync_paths` catch at `git.py:223-234` and
`sync_log` control-branch check at `git.py:148-159`, default = `config.py:114`
(`git_control_branch = "main"`) / `_parse_git` at `config.py:1041`.

Decided direction (Nick): detect mismatch, tell user to set
`[git].control_branch`; no auto-guessing. Approach:

- Add `_control_branch_present(root, branch)` via
  `git show-ref --verify --quiet refs/heads/<branch>` — exact, exits non-zero on
  a missing ref (verified: absent on fresh `git init -b master`, both unborn and
  after a commit).
- Add `_current_branch_name(root)` via `git symbolic-ref --short -q HEAD` —
  returns the branch even on an unborn fresh-init branch (where the existing
  `_current_branch`/`rev-parse --abbrev-ref HEAD` *raises*), `None` when
  detached. Used only to suggest the right value in the message.
- In `sync_paths` and `sync_log`, *before* `_current_branch`, if the control
  branch isn't present → write an actionable stderr message naming the
  one-line config fix and return (soft-skip, mirroring the existing
  "not a git repo" / "disabled" no-ops). Placing it before `_current_branch`
  also covers the unborn-branch fresh-repo case, which would otherwise raise.

Edge cases (from evaluator review) resolved by using *local-branch presence*
as the signal rather than `symbolic-ref HEAD`-as-detection: detached HEAD and
feature branches in a healthy repo still have `refs/heads/<control>` present →
no false positive; we never resolve "the right branch" so there's no drift /
precedence question. No remote needed (show-ref is local). `symbolic-ref` is
used only for the *suggestion text*, best-effort.

RESOLVED (Nick, terminal): skip sync entirely on a real mismatch — no local
commit until config is fixed. Implemented that way.

## Implemented (claude, 2026-06-28) — implement step done

Worktree `../coga-control-branch-guidance`, branch
`fix-control-branch-mismatch-guidance`, commit `9f87baef`. No push / no PR
(that's the open-pr step).

What changed in `src/coga/git.py`:
- `_control_branch_present(root, branch)` — `git show-ref --verify --quiet
  refs/heads/<branch>`; True/False, raises GitError only on an unexpected exit.
- `_symbolic_head(root)` — `git symbolic-ref --short -q HEAD`; resolves the
  branch name even on an unborn fresh-init branch, None when detached. Never
  raises. Used only for the suggestion text.
- `_control_branch_mismatch_message(cfg, root)` — actionable one-liner naming
  the missing control branch, the branch you're on, and the `[git].control_branch
  = "<branch>"` fix.
- Guard wired into both `sync_paths` and `sync_log`, placed *before*
  `_current_branch` (which raises on an unborn branch) and *after* the
  not-a-git-repo check. On mismatch: print message to stderr, return — no commit.
- Module docstring failure-model section extended to document the soft-skip.

Edge cases handled: detached HEAD / feature branch in a healthy repo do NOT
false-trip (guard keys on the control ref existing, not on HEAD); unborn
fresh-init `master` repo (the literal Getting-Started case) handled; no remote
needed (show-ref is local); GitError from the helper stays non-fatal (inside
both callers' `except GitError`).

Tests added to `tests/test_git.py` (mirroring the suite's real-git `git_repo`
fixture style, no new deps): renamed-branch mismatch (sync_task_state +
sync_log), fresh-unborn-`master` repo, and two focused helper tests. Full
suite: 905 passed, 1 pre-existing skip (run with python3.12 — the repo requires
3.11+ and system `python` here is 3.9). Verified the live message on a real
`git init -b master` repo; reads cleanly.

Out of scope / not done (deliberately): no auto-guessing the branch, no change
to the default, no README note (optional per ticket), no touching the
swallow-and-exit-0 behavior broadly.

## Evaluator review

**Description clarity:** Strong. An agent with no prior context could start work. The Description states the symptom (`git init` → `master` vs `control_branch` default `main`), the mechanism (every state-mutating command runs `git fetch origin main` / pushes to `refs/heads/main`), and the user-facing consequence (swallowed `GitError`, exit 0, confusing but non-fatal). The Context section adds exact file:line anchors (`config.py:138`, `:889`, `git.py:148-159`, `git.py:29-40`) and a clearly-labeled decided direction. This is more grounded than most cold tickets.

**Workflow fit:** `code/with-review` is appropriate. The change is a small, contained source edit to branch-resolution logic with a clear correctness risk (it touches git sync behavior on every mutating command), so peer review by `codex` is warranted. No mismatch.

**Contexts:** The frontmatter `contexts: []` is the one real gap. The work lives in the Relay codebase which isn't in this repo, so there are no coga contexts to attach — that part is defensible. But the ticket leans entirely on inline file:line references that the picking agent cannot open from here; nothing is copied into `## Context` verbatim. Worth attaching/inlining at least the current default-resolution code at `config.py:138`/`:889` and the failure-model docstring (`git.py:29-40`), plus any Relay convention doc on config defaults, so the agent isn't blind until it switches repos. As-is, an agent must trust the line numbers are still accurate.

**Scope:** Reasonable and well-bounded — single behavioral change with explicit out-of-scope carve-outs (no touching the swallow-and-exit-0 behavior, README note optional). It does not bundle multiple tickets. If anything it is slightly under-specified on testing: it doesn't ask for a regression test covering the `master`-repo case, which for a with-review code ticket should probably be named as an acceptance criterion.

**Assumptions to question before launch:** The "detect the actual default branch" direction is sound in principle — fixing at the source beats warning/documenting — but the proposed mechanism (`git symbolic-ref --short HEAD`) resolves the *current checked-out branch*, not the repo's *default* branch, and the ticket should name these edge cases before work starts:
- **Detached HEAD:** `git symbolic-ref --short HEAD` fails (no symbolic ref). Need a defined fallback.
- **No commits yet / unborn branch:** immediately after `git init` HEAD points at an unborn branch; `symbolic-ref` behavior differs from a repo with commits — verify it actually returns `master`/`main` pre-first-commit, since that's exactly the "fresh repo" scenario the ticket targets.
- **Detection target mismatch:** the bug is about `git fetch origin <branch>` / `refs/heads/<branch>` against the *remote*, but `symbolic-ref HEAD` reads the *local* current branch. If the user is on a feature branch, this resolves to the feature branch, not the intended default — likely wrong. Consider `git symbolic-ref --short refs/remotes/origin/HEAD` (remote default) or `git config init.defaultBranch` as alternative/secondary signals, and decide precedence explicitly.
- **Bare repo / no remote:** behavior should be defined when there's no `origin` to fetch from.
- **Caching/stability:** the resolved branch shouldn't drift between commands if the user later checks out a different branch — decide whether resolution is per-invocation or pinned once.

Recommend the ticket either pin the exact resolution command and its fallback chain, or explicitly delegate that choice to the implementer with the above edge cases listed as must-handle cases. Right now "`git symbolic-ref --short HEAD` (or equivalent)" is the one soft spot in an otherwise launch-ready ticket.

## Usage

{"agent":"claude","cache_creation_input_tokens":351794,"cache_read_input_tokens":5536860,"cli":"claude","input_tokens":24768,"model":"claude-opus-4-8","output_tokens":87605,"provider":"anthropic","schema":1,"session_id":"68b7d384-07d0-4327-af44-ebdcdace4724","slug":"fresh-repo-default-branch-mismatch-git-init-master","step":"implement","title":"Fresh-repo default branch mismatch: git init master vs control_branch main","ts":"2026-06-28T21:41:14.869547Z","usage_status":"ok"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":2262272,"cli":"codex","input_tokens":208654,"model":"gpt-5.5","output_tokens":19329,"provider":"openai","schema":1,"session_id":"019f104c-2763-7272-ae59-a34852210fcd","slug":"fresh-repo-default-branch-mismatch-git-init-master","step":"peer-review","title":"Fresh-repo default branch mismatch: git init master vs control_branch main","ts":"2026-06-28T22:31:26.942456Z","usage_status":"ok"}
## Peer review (codex, 2026-06-28)

Native review (`codex review --base main`) found one must-fix: the new guard
treated a feature checkout with no local `main` as a mismatch even when the
configured remote branch existed and the old cross-branch path could fetch it.

Fixed in feature worktree `../coga-control-branch-guidance`, branch
`fix-control-branch-mismatch-guidance`, commit `99c810c4`
(`peer-review: handle remote-only control branches`). The guard now accepts a
local branch, a remote-tracking branch, or an exact configured remote branch
before emitting the mismatch guidance. Added regression coverage for a
remote-only control branch with no local `main`/`origin/main` ref.

Verification:
- `python -m pytest tests/test_git.py` — 49 passed
- `python -m pytest` — 906 passed, 1 skipped
- `git diff --check` — clean

## Open-PR (claude, 2026-06-28)

Pushed `fix-control-branch-mismatch-guidance` and opened PR #469:
https://github.com/FastJVM/coga/pull/469 (base `main`). gh auth ok (nicktoper,
repo scope). `gh pr checks 469` → no checks reported (this repo has no CI
configured), so nothing to wait on — ready for human review.
