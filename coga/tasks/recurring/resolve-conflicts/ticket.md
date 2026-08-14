---
slug: recurring/resolve-conflicts
title: Resolve PR conflicts
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/period-task
skills: []
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
secrets: null
step: 1 (execute)
---

## Description

Run the stateless `coga resolve-conflicts` command once a week, after
`branch-sweep` has pruned merged branch residue.

This recurring entry owns only the schedule. The command ticket under
`bootstrap/resolve-conflicts` owns the operation: enumerate open PRs, rebase
conflicting heads onto `origin/main`, resolve semantic conflicts with agent
judgment, verify before an explicit lease-safe force-push, print one line per
PR, and post the final Slack roll-up.

Delegate through the ordinary command alias; do not reproduce or improvise a
second runbook here:

1. Run `coga resolve-conflicts --agent <current-agent-type>`, replacing the
   placeholder with the configured Coga agent type running this wrapper
   (normally `claude` or `codex`). This preserves an explicit recurring
   `--agent` override for the command that performs the conflict work.
2. If this launch includes automatic queue guidance, also pass
   `--queue-guidance`; omit it for an interactive recurring launch. Wait for
   the delegated command to return. Recurring's outer agent supervisor remains
   responsible for TTY admission and the idle/max-session liveness bounds over
   the whole process tree.
3. After a successful delegated run, finish this period task with
   `coga mark done recurring/resolve-conflicts`. Surface a delegated failure;
   do not mark the period task done as if the sweep succeeded.

The replacement intentionally covers **open PRs only**. The removed
`rebase-stale-worktrees` task also found pre-PR branches through worktrees and
ticket `branch:` lines; that extra coverage is deliberately not preserved.
For an on-demand run, call `coga resolve-conflicts` directly instead of forcing
this recurring template.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## 2026-08-13 — period 2026-W33 run

- Parent blackboard already records `last_serviced_period: 2026-W33`; the
  command is stateless, so no cursor work belongs to this run.
- Ran `coga resolve-conflicts --agent claude --queue-guidance` per the body
  (queue guidance is active for this launch). It exited 2 immediately:
  the alias expands to `coga launch bootstrap/resolve-conflicts --agent claude
  --queue-guidance`, and that launch refuses without a real TTY ("an agent
  launch requires a TTY (stdin and stdout must both be terminals)").
- Verified this session's shell tool provides no TTY on stdin or stdout
  (`[ -t 0 ]` / `[ -t 1 ]` both false), so the nested agent launch can never
  be admitted from inside this wrapper session. Faking a pty (e.g. `script
  -qec`) would bypass the TTY admission the recurring design explicitly
  assigns to the outer supervisor, so I did not attempt it.
- The delegated sweep did NOT run; no PRs were touched, no Slack roll-up was
  posted. Per body step 3, not marking done. Blocking instead (queue
  directive: unavailable capability → terminal `coga block`).
- Likely fix is structural: the recurring wrapper agent cannot itself admit a
  second agent launch. Either run `coga resolve-conflicts --agent claude`
  from a real shell for this period, or change the recurring template so the
  supervisor performs the delegated launch directly instead of asking the
  wrapper agent to shell out to it.

---

## Blockers

- [x] [2026-08-13 09:40] [agent:claude] id=20260813T094004 Delegated sweep never ran: 'coga resolve-conflicts --agent claude --queue-guidance' exits 2 because the underlying 'coga launch bootstrap/resolve-conflicts' requires stdin/stdout TTYs, and the wrapper agent's shell has neither (verified). Need a human to either run 'coga resolve-conflicts --agent claude' from a real shell for period 2026-W33, or restructure the recurring template so the outer supervisor performs the delegated launch instead of the wrapper agent shelling out to it.
  resolved: [2026-08-14 10:54] [human:nicktoper] Resolved from the repo's own contract, no human decision needed. The canonical coga/recurring context (SKILL.md Gotchas, ~L428-441) explicitly anticipates this exact failure -- 'coga launch refuses an agent launch without a TTY on both stdin and stdout, and an agent's own tool shell supplies neither -- so running the delegation straight from a tool call is refused, not merely degraded' -- and prescribes the fix: run it under a pty, e.g. 'timeout 900 script -qec "coga resolve-conflicts --agent claude" /dev/null'. The prior run judged the pty a design bypass without consulting that section; it is the sanctioned pattern, not a bypass. Same section also says NOT to read success from the captured pty stream (ANSI noise + teardown race) but to confirm via the bootstrap/resolve-conflicts slack: line in coga/log.md. Proceeding with the delegated sweep on that basis. The template-vs-context wording contradiction is separately ticketed as reconcile-recurring-wrapper-tty-admission-guidance and is not this period task's work (direct/body cannot land product code).
