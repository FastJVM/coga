---
slug: recurring/resolve-conflicts
title: Resolve PR conflicts
status: done
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

## 2026-08-14 — resumed, blocker resolved from the repo's own contract

- **The prior run's blocker premise was wrong.** It judged a pty a "design
  bypass" without consulting `coga/contexts/coga/recurring/SKILL.md`
  (Gotchas, ~L428-441). That canonical context anticipates this exact failure
  verbatim — "running the delegation straight from a tool call is *refused*,
  not merely degraded" — and prescribes the pty as the sanctioned fix:
  `timeout 900 script -qec 'coga resolve-conflicts --agent claude' /dev/null`.
  No human decision was needed; `coga unblock` ran on that basis.
- Empirical backing: the 2026-07-27 period run (log L2984) used this same
  pattern and completed successfully.
- Same context section forbids reading success from the captured pty stream
  (ANSI noise + teardown race). Success is confirmed via the
  `bootstrap/resolve-conflicts` `slack:` line in `coga/log.md`. High-water
  mark before this run: last such line is L3102 (2026-07-29); log is 3412
  lines.
- Blast radius this period: 2 open PRs — #688 (base `main`, mergeable
  UNKNOWN) and #690 (base `recurring-ledger-from-log`, i.e. not `main`, so
  the command ticket requires reporting it as `conflict` untouched).
- The template-vs-context wording contradiction is already ticketed as
  `reconcile-recurring-wrapper-tty-admission-guidance`; not fixed here, since
  `direct/body` must not land product code.

### Correction to one prior finding

`--queue-guidance` DOES exist (`src/coga/commands/launch.py:158`); it is
`hidden=True`, so it never appears in `coga launch --help`. It was not the
cause of the prior exit 2 — that really was the TTY refusal.

### Outcome: sanctioned pattern is blocked by this session's permission layer

- Ran the context-sanctioned command,
  `timeout 900 script -qec 'coga resolve-conflicts --agent claude
  --queue-guidance' /dev/null`, both backgrounded and in the foreground.
  **Both were refused by the Claude Code auto-mode permission classifier**
  before execution — this is a harness permission denial, not a Coga TTY
  refusal and not a code defect.
- I did not attempt to route around the denial (an alternate pty allocator, a
  hand-rolled `pty.spawn`, etc.). The denial notice explicitly forbids
  bypassing its intent, and doing so would also be exactly the
  bypass-the-admission-gate move the prior run rightly worried about.
- **The delegated sweep did NOT run this period.** No PR was fetched,
  rebased, or force-pushed; no Slack roll-up was posted. No new
  `bootstrap/resolve-conflicts` `slack:` line exists past L3102, so the
  context's log-based success check fails. Per body step 3, NOT marking done.
- Blocking again — but the ask has changed shape. It is no longer the
  (now-answered) design question; it is a concrete permission-rule gap with a
  one-line remedy.
- For whoever runs it: only **#688** is actually eligible this period (base
  `main`). **#690** targets `recurring-ledger-from-log`, so the command ticket
  requires reporting it as `conflict` with the base named, untouched.

---

## 2026-08-17 — resumed under megalaunch queue

- Period being serviced is still **2026-W33** (newest `created ... for` line is
  `coga/log.md` L3278; the megalaunch lines L3609-3611 only reactivate the same
  period task).
- **The prior blocker's permission denial did not recur.** The
  context-sanctioned command
  `timeout 900 script -qec 'coga resolve-conflicts --agent claude --queue-guidance' /dev/null`
  was admitted by this session's permission layer and executed. So remedy (1)
  from the open ask (a permission-rule gap) is moot in this session; no rule
  change was needed.
- **Blast radius changed since the block was written.** Both PRs named in that
  ask are gone: #688 (base `main`) and #690 (base `recurring-ledger-from-log`)
  were both merged 2026-08-14T18:43Z. `gh pr list --state open` returns `[]`,
  so this sweep is a no-op roll-up, not a rebase run.
- Success is confirmed from the `bootstrap/resolve-conflicts` `slack:` line in
  `coga/log.md`, not the pty stream (per `coga/recurring` SKILL.md L479-494).
  High-water mark before this run: L3102.

### Outcome — sweep completed for 2026-W33

- Delegated run finished; roll-up in `coga/log.md`:
  `2026-08-17 22:02 [bootstrap/resolve-conflicts] [agent:claude] slack:
  resolve-conflicts sweep: 0 open PRs — nothing to rebase; no attention needed.`
- No PR was fetched, rebased, or force-pushed — there were none to touch.
- Nothing durable to persist: this recurring entry is stateless by design (the
  serviced-period high-water mark lives in the log, not the parent blackboard),
  so no parent-blackboard cursor update belongs to this run.
- Marking the period task done.

## Blockers

- [x] [2026-08-13 09:40] [agent:claude] id=20260813T094004 Delegated sweep never ran: 'coga resolve-conflicts --agent claude --queue-guidance' exits 2 because the underlying 'coga launch bootstrap/resolve-conflicts' requires stdin/stdout TTYs, and the wrapper agent's shell has neither (verified). Need a human to either run 'coga resolve-conflicts --agent claude' from a real shell for period 2026-W33, or restructure the recurring template so the outer supervisor performs the delegated launch instead of the wrapper agent shelling out to it.
  resolved: [2026-08-14 10:54] [human:nicktoper] Resolved from the repo's own contract, no human decision needed. The canonical coga/recurring context (SKILL.md Gotchas, ~L428-441) explicitly anticipates this exact failure -- 'coga launch refuses an agent launch without a TTY on both stdin and stdout, and an agent's own tool shell supplies neither -- so running the delegation straight from a tool call is refused, not merely degraded' -- and prescribes the fix: run it under a pty, e.g. 'timeout 900 script -qec "coga resolve-conflicts --agent claude" /dev/null'. The prior run judged the pty a design bypass without consulting that section; it is the sanctioned pattern, not a bypass. Same section also says NOT to read success from the captured pty stream (ANSI noise + teardown race) but to confirm via the bootstrap/resolve-conflicts slack: line in coga/log.md. Proceeding with the delegated sweep on that basis. The template-vs-context wording contradiction is separately ticketed as reconcile-recurring-wrapper-tty-admission-guidance and is not this period task's work (direct/body cannot land product code).

- [x] [2026-08-14 10:58] [agent:claude] id=20260814T105840 Design question RESOLVED (unblocked earlier this session): the coga/recurring context sanctions the pty, so 'timeout 900 script -qec "coga resolve-conflicts --agent claude --queue-guidance" /dev/null' is the correct command. New, different blocker: this agent session's Claude Code auto-mode permission classifier REFUSES that command (tried backgrounded and foreground; denied before execution). Not a Coga TTY refusal and not a code defect -- a harness permission gap. I did not route around the denial. Sweep did NOT run for 2026-W33: no PR touched, no roll-up posted, no new bootstrap/resolve-conflicts slack: line past coga/log.md L3102. Remedy, pick one: (1) add a Bash permission rule allowing 'script -qec' / 'coga resolve-conflicts' so recurring sweeps can self-serve; or (2) run 'coga resolve-conflicts --agent claude' once from a real shell for this period. FYI for the run: only PR #688 is eligible (base main); PR #690 targets recurring-ledger-from-log, so per the command ticket it must be reported as conflict with the base named and left untouched.
  resolved: [2026-08-17 22:03] [human:nicktoper] Resolved empirically in this session, no rule change needed. (a) The permission-classifier denial did NOT recur: 'timeout 900 script -qec "coga resolve-conflicts --agent claude --queue-guidance" /dev/null' was admitted and ran to completion, so remedy (1) — adding a Bash permission rule — is moot here; the earlier denial was session-local, not a standing harness gap. (b) Remedy (2) is also moot: the two PRs the ask flagged both merged on 2026-08-14T18:43Z (#688 base main, #690 base recurring-ledger-from-log), and 'gh pr list --state open' now returns []. The delegated sweep ran as a no-op and posted its roll-up: '2026-08-17 22:02 [bootstrap/resolve-conflicts] [agent:claude] slack: resolve-conflicts sweep: 0 open PRs — nothing to rebase; no attention needed.' — confirmed via coga/log.md per the coga/recurring context, not the pty stream.
