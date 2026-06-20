---
title: 'Unblock unattended execution (mode/autonomy: auto)'
status: active
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- autonomy/triage
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

Make `autonomy: auto` actually runnable. This is the follow-up to
`1-represent-autonomy-tier-in-ticket-mode-field`, which splits `mode` into
`mode: agent|script` + `autonomy: interactive|auto` and migrates the repo, but
deliberately **preserves** the blocks on unattended execution. This ticket
removes those blocks and builds the machinery that makes an unattended run
observable — so recurring/scheduled tickets can run with no human.

Depends on `1-represent-autonomy-tier-in-ticket-mode-field` landing first (the
two-field vocabulary must exist).

Scope:

- **Remove the `auto` hard-bail** (launch.py, now keyed `autonomy == "auto"`),
  the `retire.py` auto ban, and the `recurring.py` auto refusal.
- **Build the unattended agent run path** — there is no capture machinery today;
  the PTY done-marker supervisor (`run_with_done_marker`) is interactive-only.
  Need: capture headless stdout/stderr → task log, and a done/fail
  notification mechanism for runs with no interactive supervisor.
- **stdin handling** — verify how each configured agent CLI (`claude -p`,
  `codex exec`) consumes its prompt before redirecting stdin; close stdin for
  unattended runs only where it's safe, so input-needing work fails fast instead
  of hanging. Gate capture/stdin handling on unattended only (piping an attended
  TTY run would clobber interactivity).
- **Opt recurring templates in** — decide which of `digest`, `dream`,
  `skill-update`, `autoclose-merged` should flip to `autonomy: auto`.

Out of scope: remote/cloud dispatch of unattended runs — a separate, later
"when mature" ticket.

## Context

Needs its own `bootstrap/ticket` interview to finalize workflow/contexts/scope
before activation. Workflow likely `code/with-review` (owner gate — this undoes
a deliberate safety bail). Likely context: `autonomy/triage`.

The original reason `auto` was disabled (`launch.py` bail message): unattended
`claude -p` / `codex exec` buffer output until completion, so live runs are
unobservable. The justification for unblocking is that recurring/scheduled runs
have no live watcher anyway — their observability bar is "output landed in the
log + Slack notify on done/fail," which the capture path above provides.

See `1-represent-autonomy-tier-in-ticket-mode-field/blackboard.md` (## Evaluator
review) for the analysis that motivated splitting this out — especially the note
that the agent-side output-capture + done-notification path is novel engineering
with no existing machinery, which is why it's its own ticket.
