---
slug: remove-mode-from-ticket-frontmatter-and-deduce-scr
title: Remove mode from ticket frontmatter and deduce script-vs-agent from context
status: in_progress
mode: agent
owner: nicktoper
human: nicktoper
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
script: null
step: 3 (open-pr)
---

## Description

Remove the `mode:` ticket frontmatter field entirely. Whether a launch runs a
script or spawns an agent is deduced from context, per launch:

1. **Step-skill script** — the current workflow step has exactly one skill and
   that skill's SKILL.md declares `script:` → run that script (this is the
   existing `current_step_is_script`, already mode-blind).
2. **Ticket-owned script** — otherwise the ticket's own `script:` is set
   (`inline` or a sibling file) → run that.
3. **Neither → agent** — spawn the assignee's REPL (TTY required).

I.e. `script ⟺ current_step_is_script(ticket) or ticket.script`. The same rule
applied to a recurring template's workflow step 1 (resolving the named workflow
file — it is not frozen yet) replaces the template TTY gate in
`recurring._effective_mode`. That pre-freeze deduction is the only genuinely
new logic; everything else is mechanical removal.

Work items:

- **Dispatch** — `is_script_launch` becomes the deduced rule; delete the
  unknown-mode bail (`launch.py:284`); key the TTY gate, prompt handling,
  session naming, and the assignee-must-be-an-agent guard (`launch.py:305,
  861, 965, 1006, 1202`), `compose.py:120/150/166`,
  `recurring_runner.py:1027`, and `megalaunch.py:245` off the deduction.
- **Recurring** — replace `_effective_mode` (`recurring.py:478`) with
  template-level deduction; update its TTY-skip error message ("give the
  template a script", not "make it `mode: script`").
- **Schema/writers** — drop `mode` from the canonical frontmatter set
  (`ticket.py:30`), `Ticket.mode` (`ticket.py:130`), `VALID_MODES` /
  `invalid-mode` (`validate.py`), the reserved-extension-name list
  (`config.py:586`), `create.py:177`, `--mode` on `commands/create.py`, and
  the authoring stamp in `commands/ticket.py:182`.
- **Cosmetic** — drop `mode=` from launch log/echo strings
  (`launch.py:174, 1093, 1098`) and the `mode` column from
  `coga recurring list` (`commands/recurring.py:196, 208`).
- **Migration** — strip `mode:` lines from all tickets and recurring templates
  in this repo, the packaged templates under
  `src/coga/resources/templates/coga/`, and the `example/` fixture. Leftover
  `mode:` on old tickets surfaces as validate's warn-only orphan key.
- **Docs sync** — rewrite the "Mode and execution" section of the
  `coga/architecture` context, update `coga/cli`, and the calendar-reminder
  skill's examples; keep live `coga/` and packaged copies in sync.
- **Tests** — update tests pinning `--mode` / `_effective_mode` /
  `ticket.mode`; add coverage for the deduced dispatch and the template
  pre-freeze deduction.

Out of scope: `[agents.<name>].mode = "local"` in config is an unrelated
homonym (agent-type transport) — untouched.

## Context

Decided in a bootstrap/orient session (2026-07-13, PR #541 removed the status
`mode` column first). Rationale: `mode` was a cached copy of what
`_resolve_script` already derives. Verified across all 109 tickets (repo +
packaged templates + example fixture): no ticket's deduced substance disagrees
with its declared mode — every `mode: agent` ticket has `script: null`, and all
six `mode: script` recurring templates deduce via their workflow step-1 skill
(none has a ticket-level `script:`; the bootstrap script targets carry
`script: run.py` directly). The `_rem` template's placeholder workflow can't
resolve but is `_`-prefixed and skipped by discovery.

Accepted behavior change: a script ticket whose script vanishes (skill
`script:` renamed away, workflow edit) now deduces to an agent launch instead
of bailing loud; TTY-less contexts still fail on the TTY gate.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: remove-ticket-mode
worktree: /home/n/Code/codex/coga-remove-ticket-mode

## Implement notes (2026-07-13)

- Ticket's `launch.py:NNN` references map to `src/coga/commands/launch.py`
  (line numbers match). `launch_script.py` holds `is_script_launch` /
  `current_step_is_script` / `run_script_mode`.

### Implemented (commit 8c36fa72 on `remove-ticket-mode`)

- **Dispatch**: `is_script_launch(cfg, ticket) = current_step_is_script or
  bool(ticket.script)`. launch.py's `run_current_as_script` is now just that
  call; unknown-mode bail deleted; TTY gate, human-handoff guard, blocked
  resume, prompt-report rejection, session naming, usage capture all keyed
  off the deduction. `mode` param removed from `spawn_agent_session` /
  `build_agent_command` / `_launch_log_message` (callers in commands/ticket.py
  and commands/project.py updated). Log line is now
  `launched (assignee=…, agent=…)`.
- **Recurring**: `_effective_mode` → `_template_runs_as_script(cfg, template)`
  (template `script:`, else named-workflow step 1 exactly-one-script-backed
  -skill, resolved pre-freeze; workflow-less templates check `direct/body`
  like `_create_at_slug` does). Unresolvable workflow → agent (per ticket's
  accepted behavior). TTY-skip error: "an agent run requires a TTY … give the
  template a script …". `recurring_runner.py:1027` keys off
  `is_script_launch`.
- **Schema/writers**: `mode` dropped from `CANONICAL_TICKET_KEYS`,
  `Ticket.mode`, `REQUIRED_TASK_KEYS`, `VALID_MODES`/invalid-mode,
  `_RESERVED_TICKET_FIELD_NAMES`, `create_task`, `coga create --mode`,
  `commands/ticket.py` authoring stamp, `commands/retire.py`. Also removed
  the invalid-mode classifier from the packaged dream validate-drift run.py.
- **views.py**: `coga status` mode column removed — required here because
  `Ticket.mode` is gone; this duplicates open PR #541 (same 8-line diff),
  rebase will reconcile whichever lands first.
- **Migration**: 170 files — `mode:` stripped from frontmatter of every
  ticket/template in `coga/`, `example/`, and
  `src/coga/resources/templates/coga/` (script via scratchpad, frontmatter
  block only). Bootstrap script targets keep `script: run.py` so they deduce
  script.
- **Docs**: architecture context "Mode and execution" → "Script vs agent
  execution" (deduction rule); frontmatter key list updated; cli context,
  calendar-reminder examples, recurring/usage/roadmap contexts,
  vision/market-thesis/cli-extension-audit docs, script-skill SKILL.mds —
  live `coga/` and packaged copies kept in sync.
- **Tests**: 1174 passed, 1 skipped (`PYTHONPATH=<worktree>/src python3.12 -m
  pytest`; miniconda default python is 3.9 — must use python3.12). Removed
  obsolete tests (build_agent_command mode rejection, compose script-mode
  preamble — compose is agent-only now). New coverage: three-rule
  `is_script_launch` deduction, vanished-script→TTY-gate behavior change,
  template pre-freeze deduction (own script / multi-skill step / unresolvable
  workflow). `coga validate --json` clean on `example/`; repo validate shows
  only pre-existing unrelated warns.

### Decisions

- `--agent` with a deduced script launch now bails loud ("--agent is only
  supported for agent launches") — previously a mode:agent ticket on a script
  step silently ignored it.
- Composed prompt header no longer prints a `Mode:` line; the agent-mode
  layer composes unconditionally (compose is only reached by agent launches).
- `coga/tasks/*` body text and `coga/log.md` history mentioning the old
  `mode:` field left untouched (historical record).

## Usage

{"agent":"claude","cache_creation_input_tokens":660827,"cache_read_input_tokens":56303156,"cli":"claude","input_tokens":593,"model":"claude-fable-5","output_tokens":227861,"provider":"anthropic","schema":1,"session_id":"98eb70fc-7cb4-46c9-9447-255c77bfdc0f","slug":"remove-mode-from-ticket-frontmatter-and-deduce-scr","step":"implement","title":"Remove mode from ticket frontmatter and deduce script-vs-agent from context","ts":"2026-07-14T02:56:53.900933Z","usage_status":"ok"}

## Peer Review (2026-07-13)

- Native `codex review --base main` completed after rerunning outside the
  restricted sandbox. Four actionable findings were fixed in commit
  `b9ba1139` (rebased as `299d2f84`): the stale megalaunch spawn argument,
  script deduction cached before draft workflow activation, malformed
  recurring skills aborting the whole sweep, and obsolete mode guidance in
  shipped recurring templates.
- Added regressions for draft bare-workflow script dispatch and per-template
  recurring error isolation; megalaunch mocks now enforce the mode-free
  `spawn_agent_session` signature.
- Rebased unconditionally onto `origin/main` at `b5e9df72`. The sole conflict
  preserved the newer live state of
  `auto/launch-should-refresh-local-coga-state-at-end-of-r` while removing its
  obsolete `mode:` line. Branch is clean with two commits ahead of main.
- Verification after rebase: `1176 passed, 1 skipped` using absolute
  `PYTHONPATH` and Python 3.12; task-scoped validation and the `example/coga`
  fixture both report zero issues; `git diff --check` is clean.

## PR

### Summary

- Remove the `mode:` field from ticket schema, writers, CLI, validation,
  status/recurring views, repository tickets, packaged templates, and the
  example fixture.
- Deduce each launch from its current context: a single script-backed step
  skill first, then a ticket-owned `script:`, otherwise an attended agent
  session.
- Apply the same pre-freeze deduction to recurring templates, update the
  durable architecture/CLI guidance, and keep live and packaged templates in
  sync.
- Preserve fail-loud behavior around malformed recurring skills and cover the
  draft-activation and megalaunch call paths found during peer review.

### Test plan

`PYTHONPATH=/home/n/Code/codex/coga-remove-ticket-mode/src PYTHONDONTWRITEBYTECODE=1 python3.12 -m pytest -p no:cacheprovider` — 1176 passed, 1 skipped.
