---
title: Offer agent CLI install and setup at init
status: done
owner: nicktoper
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

## Dev

pr: https://github.com/FastJVM/coga/pull/970
branch: agent-cli-install-offer

Plan (implement session 2026-10-06): shared core helper `coga.agent_cli_setup.offer_agent_cli(name)` (consumers: `coga init`, `coga launch` of the `coga-build` onboarding ticket) — brew cask on macOS, else `npm i -g`, else print URL; prints the command and requires yes; then offers login (`claude` / `codex login`). Init (interactive only) offers to pick + install an agent CLI and, behind a confirm, makes the chosen agent the default. Note: coga has no `[agent] default` key — the default is the first-declared `[agents.*]` table (`Config.default_agent`), so init reorders the scaffolded `[agents.*]` tables rather than inventing a new key.

## 2026-10-06 — implement handoff

Pushed `agent-cli-install-offer` (1 commit, rebased on origin/main). No PR yet.

What changed:
- New core module `src/coga/agent_cli_setup.py` `offer_agent_cli(name)` — 2 consumers (init, launch/build). Installer: macOS + brew → `brew install --cask claude-code|codex`; else `npm install -g @anthropic-ai/claude-code|@openai/codex` if npm on PATH; else print URL (no curl|sh). Prints the command, requires yes, then offers login (`claude` bare / `codex login`).
- `src/coga/dependencies.py`: `Dependency.login`, agent `packages` (brew/npm), `PACKAGE_MANAGERS["npm"]`, `AGENT_CLIS`.
- `commands/init.py`: `_offer_agent_cli(default_agent)` runs after `_offer_optional_tools` (before any write); picker claude/codex/skip when none installed; if exactly one agent CLI ends up on PATH and it isn't the packaged default, confirm → `_make_default_agent` moves its `[agents.*]` table first (text swap, verified by tomllib equality; comments preserved) and `_stamp_agent_into_delivered_tickets` repoints `agent: claude` in the onboarding ticket — inside init's atomic block, before the commit. Clone path (`_setup_initialized_clone`) offers install only, never edits committed coga.toml. Next-steps `coga build` line follows the chosen default.
- `commands/launch.py`: missing agent CLI on the `coga-build` onboarding launch (TTY already proven) → `offer_agent_cli`, then re-check; other launches unchanged.
- Topics + twins: coga/install, coga/init, coga/agents, coga/first-task, coga/codebase; README install line.

Decision: coga has no `[agent] default` key — the default is the first-declared `[agents.*]` table (`Config.default_agent`), so "set default" = reorder, not a new config key.

Tests: new `tests/test_agent_cli_setup.py`; added init picker/reorder/full-init tests and launch build-offer tests; conftest stubs `_offer_agent_cli`. Full suite: 3294 passed, 1 failed — `tests/test_edge_distribution.py::test_documented_legacy_adoption_preserves_state_and_reconciles_callers`, which also fails on clean origin/main (pre-existing, unrelated; recurring ticket.py ordering assertion).

For review: `claude` login runs the bare REPL (no reliable `claude auth` subcommand assumed); `npm -g` is not sudo-wrapped (fails with a printed hint on root-owned prefixes).

## Peer review

2026-10-06: `codex review --base main` **returned**, exit 0, with no actionable regressions. The first attempt could not initialize its app-server in the read-only sandbox; the permitted unsandboxed retry completed. Its focused run (`.venv/bin/python -m pytest -q tests/test_agent_cli_setup.py tests/test_init.py tests/test_launch.py tests/test_packaging.py`) passed 365 tests. No must-fix changes were needed.

Freshness: ran `git fetch origin main && git rebase FETCH_HEAD`, then the full suite, and pushed `agent-cli-install-offer` with `--force-with-lease` at `a032595e9`. Returned to clean `main` and fast-forwarded it; the subsequent main changes were ticket/log state only.

Verification:
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest` — **3295 passed**, 260.05s. The earlier edge-distribution failure did not recur. The ambient `python -m pytest` initially failed collection because that interpreter lacks `tomlkit`; the complete passing run used the repository virtualenv.
- `git diff --check` — clean.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task marketing/fix-installer/offer-agent-cli-install-and-setup-at-init --json` — 1 OK, no issues.
- Ran actual fresh init in disposable Git repos through real PTYs at **80×24** and **40×12**, using `/tmp/agent-cli-tty.py`. Only external installer/login execution and unrelated optional-tool offers were simulated; the new prompts, scaffolding, commit, and config rewrite ran normally. Codex selection showed the command before install consent, then separate login and default-agent confirmations; config declaration order and onboarding `agent:` both became Codex. Claude at the narrow size showed its sign-in/exit instruction and continued after login was declined. Declining installation and having no installer both completed init with Claude still the default; the latter printed the official URL. Prompts remained readable and accepted input at both sizes.
- The same harness with stdin `/dev/null` and redirected stdout completed without any agent prompts or installer calls. `env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/python -m coga.cli validate --json` in the generated Codex-default repo returned 1 OK, no issues. Real vendor installation and account authentication were not performed.

## PR

New users without an agent CLI currently hit a missing-binary error on their first build. Interactive init now offers Claude Code or Codex installation through a printed, confirmed Homebrew cask or npm command, followed by a separate login offer. The same installer helper handles a missing agent CLI during build onboarding; non-interactive calls never prompt.

With explicit confirmation, fresh init makes the available agent the default by moving its existing `[agents.*]` table first and updating the delivered onboarding ticket. Clone setup preserves team config. Updated the install, init, agents, first-task, and codebase topics and their packaged twins, plus the README.

Test plan: `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest` (3295 passed); `git diff --check`; scoped task and generated-repo validation (no issues); real PTY init checks at 80×24 and 40×12 plus non-TTY checks, with installer/login subprocesses simulated. Codex review returned with no actionable findings.
