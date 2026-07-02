---
slug: mode-autonomy-split/2-unblock-unattended-execution-mode-autonomy-auto
title: 'Unblock unattended execution (mode/autonomy: auto)'
status: in_progress
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: codex
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
step: 2 (peer-review)
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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Findings (implement step, code recon)

The three blocks to remove:

- `src/coga/commands/launch.py` ~line 278: hard `_bail` on `autonomy == "auto"`.
  After removal, `spawn_agent_session` mode="auto" falls into a bare
  `subprocess.run(cmd, env=env)` — inherited stdio, no capture, no stdin
  handling, no liveness limits, no fail notification.
- `src/coga/commands/retire.py` lines 61-68: `--autonomy auto` refusal.
- `src/coga/recurring.py` `_effective_autonomy` (~line 513): raises
  RecurringError for agent templates with `autonomy: auto`.

Existing machinery to reuse:

- `run_with_done_marker` (repl_supervisor.py) is PTY/interactive-only; already
  falls back to plain subprocess.run when stdout is not a TTY. Not suitable
  for headless capture — auto path needs its own pipe-based runner.
- Script path (`launch_script.py`) is the model for fail notification:
  non-zero exit → `notification.post` 💥 with slug/title/step. Success-side
  broadcasts already come from `coga bump`/`mark done`/`block` themselves.
- Recurring sweep already arms idle_timeout (900s default) / max_session, but
  only threads them into the *interactive* PTY watcher today.
- Agent CLIs (coga/coga.toml): claude `auto = "-p"`, codex `auto = "exec"`.
  Prompt is always passed as argv (build_agent_command), so stdin should be
  closable (/dev/null) for headless runs — to be verified live during
  implementation before relying on it.

Recurring template audit (the "opt templates in" scope item):

- digest, skill-update, autoclose-merged, blocker-reminders: already
  `autonomy: auto` **script** templates — bypass the agent ban today; only
  their "temporary freeze" comments need updating. No behavioral flip needed.
- dream: `autonomy: interactive` agent template — the only real candidate to
  flip to auto. Product call, not just code.
- megalaunch: auto script but spawns interactive launches (needs TTY) — leave.

## Dev

branch: unblock-auto-launch
worktree: /home/n/Code/claude/coga-unblock-auto-launch

## Decisions (made autonomously — owner was AFK at ask time; redirect welcome)

1. **Capture location**: full stdout+stderr tee'd to `auto-run.log` in the task
   directory (temp fallback for dir-less refs), plus one `log.md` line with
   exit code + path. Not blackboard — captured output would bloat every later
   composed prompt.
2. **Dream stays `autonomy: interactive`** this ticket. Its retro pass deletes
   task dirs — highest failure radius of the templates; flip later once the
   auto path has proven itself. The other four auto templates are scripts and
   need only comment updates.
3. **Liveness**: headless runner honors both idle_timeout (pipe-read activity)
   and max_session, same knobs the sweep already passes; timeout → exit 124,
   kind "timeout", same sweep pause path as interactive.
4. **Silent no-op** (exit 0, no bump/done/block): Slack ⚠️ post + stop —
   an unattended run must never end invisibly. Sweep pauses unfinished auto
   runs (system actor) and continues, mirroring its timeout handling, so one
   wedged template can't starve the rest of an unattended sweep.

## Implemented (commit 331b9e89 on unblock-auto-launch)

- New `src/coga/headless.py` `run_headless`: Popen with stdin=/dev/null,
  stdout+stderr piped, streamed to console AND teed to the capture file;
  idle/max-session liveness (SIGTERM → SIGKILL on own process group, exit
  124 kind "timeout", reusing repl_supervisor's ReplOutcome/constants).
- `launch.py`: bail removed; auto spawns via run_headless with capture at
  `<task_dir>/auto-run.log` (file-form: `<slug>.auto-run.log` sibling);
  exit + path appended to global log; posts 💥 on non-zero exit, ⏱️ on
  non-sweep timeout, ⚠️ on exit-0-without-advance. `--idle-timeout` /
  `--max-session` help updated to cover auto.
- `retire.py`: `--autonomy auto` accepted.
- `recurring.py` `_effective_autonomy`: auto agent templates create; only
  the interactive-needs-TTY refusal remains.
- `commands/recurring.py` `_stop_if_unfinished_after_launch`: unfinished
  unattended run → pause (actor `system`, Slack-quiet — launch already
  posted ⚠️) + continue, replacing the sweep-killing exit 1.
- Templates: 4 script templates' stale freeze comments rewritten (live +
  packaged). Dream left interactive per decision 2. Contexts updated:
  coga/cli (live + packaged), marketing/positioning honest-limits bullet.
- stdin verification: `codex exec --help` documents argv-prompt + optional
  piped stdin (`<stdin>` block); claude `-p` takes argv prompt, stdin
  optional. /dev/null = instant EOF, confirmed live in the e2e smoke
  (`stdin says: []`, no hang).

Verification: `python -m pytest` in worktree — 998 passed, 1 skipped
(includes new tests/test_headless.py, 6 tests, real subprocesses). E2e
smoke with a stub agent CLI in scratchpad: real `coga launch` of an auto
ticket → headless spawn, tee to tasks/smoke.auto-run.log, log.md exit
line, ⚠️ no-advance post fired.

⚠️ FYI for owner: the e2e smoke posted 2-3 stray messages to the real team
Slack ("▶️ nick started smoke", "⚠️ auto run on smoke…", "test message") —
SLACK_WEBHOOK_URL was exported in the dev shell and the bare-env fallback
picked it up. Harmless noise; future smokes will set
`[notification.slack] enabled = false`.

Adjacent notes (not fixed here): `coga launch` still `sys.exit`s the whole
recurring sweep when an agent CLI exits non-zero mid-sweep (pre-existing,
now at least 💥-posted); a script step that advances into a following agent
step returns to the sweep un-chained and now gets paused rather than the
old bail — arguably still not ideal, follow-up material.
