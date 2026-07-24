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
script: null
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

## Run 2026-W30

Plan: delegate to `coga resolve-conflicts --agent claude --queue-guidance`
(this launch carries queue guidance), then `coga mark done`.

Open PRs at start: #648 fix/spawn-error-misattribution, #647
feat/megalaunch-numbered-drain-order, #646 packaged-resource-read-guard
(mergeable UNKNOWN — GitHub had not finished computing).

### Delegation is structurally blocked (wrapper defect)

`coga resolve-conflicts --agent claude --queue-guidance` bailed:

    Cannot launch 'bootstrap/resolve-conflicts': an agent launch requires a TTY
    (stdin and stdout must both be terminals).

`bootstrap/resolve-conflicts` is agent-backed (`assignee: claude`), and
`launch.py:325` refuses an agent launch unless stdin *and* stdout are TTYs. A
tool subprocess inside an agent session never has one, so this recurring
wrapper can never delegate as its body describes — the failure is structural,
not environmental, and will repeat every Monday. The base prompt independently
forbids `coga launch`-ing another agent session from inside one.

Decision: executed `coga/bootstrap/resolve-conflicts/ticket.md`'s runbook
inline instead. That is the one durable runbook, so following it is not the
"second runbook" the body prohibits. Flagged the defect to the human rather
than patching the template inside this sweep.

### Result

Enumerated open PRs (`gh pr list --state open --limit 10000` → 3 rows, not
truncated). All three target `main`. Initial `mergeable` reads were UNKNOWN
(main had just advanced 838b3af8..e8f38c88); re-read until settled:

    PR #646 packaged-resource-read-guard        — up-to-date — MERGEABLE, no conflict with main
    PR #647 feat/megalaunch-numbered-drain-order — up-to-date — MERGEABLE, no conflict with main
    PR #648 fix/spawn-error-misattribution       — up-to-date — MERGEABLE, no conflict with main

No rebase, no worktree created or modified, no push. #646's branch is this
session's dirty primary checkout — it would have been `skipped-dirty` had it
conflicted, but the conflict test never selected it.

Roll-up folded into `coga mark done --message` rather than posted as a separate
`coga slack --task bootstrap/resolve-conflicts` FYI: that FYI's second job is
releasing a stateless launch supervisor, and no such supervisor exists on this
inline path, so a separate post would only double-notify.

### `mark done` product-code guard fired — verified false positive

First `coga mark done` was refused by the `direct/body` product-code guard,
naming 9 tracked files (`src/coga/blackboard.py`, `commands/launch.py`,
`commands/retire.py`, `compose.py`, `megalaunch.py`, `paths.py`,
`tests/test_compose.py`, `test_megalaunch.py`, `test_packaging.py`) as
committed product code absent from the control branch.

Verified the premise is false. This sweep was launched from the
`packaged-resource-read-guard` checkout, which is the head branch of **open PR
#646**:

    git diff --name-only 28b11016 HEAD | grep -v '^coga/'   -> empty

i.e. every flagged product file is byte-identical to the pushed PR head
`28b11016`. Local HEAD (`754913f8`) is ahead of the pushed head only by Coga
state commits (`Sync coga state`, `Ticket:`, `Log:`) touching `coga/**` alone.
Nothing can strand: the code is durable on a pushed branch under review.

The guard compares against `main` and is worktree-local by design, so it cannot
see the open PR that already makes these commits durable. Finished with
`--force` on that verified basis and recorded the evidence here. This sweep
authored none of the flagged commits.
