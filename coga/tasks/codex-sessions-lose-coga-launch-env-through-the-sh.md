---
title: Codex sessions lose COGA_* launch env through the shared app-server daemon
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (design)
agent: claude
---

## Description

Since 2026-09-25, interactive Codex sessions launched by `coga launch` / megalaunch run their shell commands without the `COGA_*` variables the supervisor sets (`COGA_SUPERVISED`, `COGA_EXPECTED_TASK`, `COGA_EXPECTED_STEP`, `COGA_DONE_SENTINEL`, `COGA_TASK_*`, and from PR #1015 `COGA_EXPECTED_AGENT`). Effects:

- `coga bump` from Codex is credited `human:<user>`. `coga/log.md` shows 61 such bumps since 2026-09-25 and none earlier; before that date Codex bumps logged `agent:codex`.
- The stale-session bump guard (`commands/bump.py`, gated on `COGA_SUPERVISED`) does not run.
- The done sentinel is never signalled, so the supervisor does not end the session on bump. Example: `add-a-failed-terminal-status` evaluate-design bumped at 17:39 on 2026-10-14, but its session ended at 17:53.

### Evidence (2026-10-14, orient session)

- `~/.codex/packages/app-server-daemon/releases/` first appeared on 2026-09-25 at 11:06, exactly when the log changed. `codex features list` shows `daemon_auto_start` stable/true. The Codex transcript shows its bump ran with `"source": "unified_exec_startup"`.
- The shared daemon (`codex app-server`, running since 2026-10-12) has no `COGA_SUPERVISED`/`COGA_EXPECTED_*` in `/proc/<pid>/environ`.
- `COGA_PROBE=hello COGA_SUPERVISED=1 codex exec ... printenv` prints both values. So the non-daemon `exec` path inherits env; the interactive daemon path is the suspect.
- Not yet verified: an interactive `codex` launched with `--no-daemon`, or with `[features] daemon_auto_start = false`, receives the env. The design step must confirm this before choosing a fix.

### Acceptance criteria

- [ ] Reproduce with a real interactive Codex launch (or document why that cannot be done), and show which launch configuration preserves `COGA_*` in Codex's shell commands.
- [ ] A supervised Codex session's `coga bump` is credited `agent:<nickname>`, the stale-step guard applies, and the session ends on bump.
- [ ] The fix stays within Coga's boundaries. No vendor special-casing in core unless `coga/extension-model` and `coga/agents` justify it. Prefer config, such as an `[agents.codex]` argv flag in the seeded `coga.toml` template or documented user config, and update `coga/agents` / `coga/testing` "Restricted sandboxes" accordingly.
- [ ] Coga detects or warns when supervised env is missing inside a session (fail loud), instead of silently treating an agent as a human.

### Related

- PR #1015 fixes the separate routed-vs-spawned agent name mislabel.
- `fix-git-sync-read-only-errors-after-successful-tra` covers the Codex `.git` write grant (root cause: missing `.codex/config.toml`).

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
