---
title: Offer agent CLI install and setup at init
status: paused
owner: nicktoper
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
step: 1 (execute)
agent: claude
---

## Description

Follow-up to PR #942 (init offers to install missing git/gh/op). New users who have no agent CLI hit 'Agent CLI not found in PATH' on their first `coga build`/`coga launch`. Make interactive `coga init` offer to pick an agent (Claude Code or Codex), install it via its official installer or package manager, run its login, and set the default agent in coga.toml. Non-interactive init must not prompt. Open questions for the owner: which installers to trust (npm, curl script, brew cask), whether init may edit coga.toml agent defaults, and how this interacts with `coga build`'s onboarding. Update `coga/install`, `coga/init`, `coga/agents` and their packaged twins.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## 2026-10-01 — execute session (megalaunch): blocked before implementation

Findings:
- PR #942 ("Offer to install missing git/gh/op during coga init") is still OPEN, unmerged. This ticket builds on its prompt/installer machinery; implementing now would fork or duplicate it.
- Current contract `coga/init` (docs/contexts/coga/init/SKILL.md:76) and `coga/install` (:10) say "Init installs no software" — this ticket reverses that; needs owner sign-off (same as #942).
- Workflow is `direct/body`, which has no branch/PR step and whose `mark done` guard refuses product commits. This ticket changes `src/coga/` + topics + twins, so it belongs on a `code/*` workflow. Agents may not edit `workflow:`.
- Owner questions from the description remain unanswered: trusted installers (npm `@anthropic-ai/claude-code` / `@openai/codex`, Anthropic curl script, brew cask), whether init may write the default agent into coga.toml, interaction with `coga build` onboarding.

Proposed defaults (for owner to accept/adjust): reuse #942's offer-and-confirm prompt; installer order = brew (macOS, if present) → npm global (if node present) → print official URL, no curl|sh; run `claude` / `codex login` only on explicit yes; write `[agent] default` in coga.toml only when it is unset; `coga build` keeps its current not-found hint pointing at `coga init`. Non-interactive (no TTY / --yes-less flags) never prompts.

---

## Blockers

- [x] [2026-10-01 11:12] [agent:claude] id=20261001T111233 Needs: (1) PR #942 (init installs git/gh/op) merged first — this builds on it; (2) workflow switched from direct/body to a code/* workflow (product code + twins, direct/body can't land a PR); (3) answers to the open questions: trusted installers (brew/npm/curl script), may init write the default agent into coga.toml, interaction with coga build onboarding. Proposed defaults on the blackboard.
  resolved: [2026-10-01 15:33] [human:nicktoper] Owner 2026-10-01: (1) PR #942 merged. (2) Owner will switch workflow to code/with-review. (3) Installers: macOS brew cask (claude-code / codex), else npm -g if node on PATH, else print official URL; no curl|sh; always print the command and require yes. coga.toml: init may set or replace [agent] default, always with an explicit confirm. coga build: interactive build also offers the same agent-CLI install/login (shared helper); non-interactive never prompts.

## 2026-10-01 — attended session: owner decisions (blocker resolved)

- #942 merged 2026-10-01; build on `src/coga/dependencies.py` + its offer/confirm prompt in `commands/init.py`.
- Installers: macOS → `brew install --cask claude-code` / `codex`; else `npm i -g @anthropic-ai/claude-code` / `@openai/codex` when `npm` is on PATH; else print the official install URL. No curl|sh. Print the command, require yes, then offer login (`claude` / `codex login`).
- coga.toml: init may set **or replace** `[agent] default`, always behind an explicit confirm (note: deliberate exception to "agents don't edit coga.toml" — this is the CLI, run by the human).
- `coga build`: interactive build offers the same install/login via a shared helper (≥2 consumers → justifies core). Non-interactive (no TTY) never prompts in either.
- Workflow: owner switching to `code/with-review`; implementation waits for the relaunch on that workflow. Nothing implemented yet.
- Topics to update + twins: `coga/install`, `coga/init`, `coga/agents` (and `coga/build` onboarding if it documents the not-found path). Drop "Agent CLIs are not offered" from `coga/install`.
