---
slug: fresh-repo-default-branch-mismatch-git-init-master
title: 'Fresh-repo default branch mismatch: git init master vs control_branch main'
status: in_progress
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: claude
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
step: 1 (implement)
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
