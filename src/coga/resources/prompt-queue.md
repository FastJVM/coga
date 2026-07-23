## Sequential queue execution

This session is one task in a sequential automated queue (a `coga recurring`
sweep). The REPL has a TTY so work can stream live and a human can interrupt,
but the TTY does **not** mean a human is waiting to approve a plan — the queue
may be running unattended.

- State a concise plan and its tradeoff, then continue. Do not ask for plan
  confirmation or end a turn waiting for permission; a present human can
  redirect you while you work.
- If a concrete decision, credential, permission, or unavailable capability
  truly prevents progress, run
  `coga block --task <slug> --reason "<specific ask>"` as the terminal action.
  Merely saying that you are blocked — or asking a question and waiting for
  the answer — leaves the queue hanging until a liveness timeout tears the
  session down and records the task as failed, notifying nobody.
- If a code step cannot create a linked worktree because the sandbox mounts
  the primary checkout's `.git` read-only, follow the independent `/tmp` clone
  fallback in the `code/implement` skill before treating it as a blocker.
- Finish an ordinary workflow step with `coga bump`, `coga mark done`, or
  `coga block`. An authorized `coga mark canceled` transition also releases the
  queue; use it only when intentional abandonment is the task decision.
- A stateless `bootstrap/<name>` command ticket has no task lifecycle to bump,
  mark, or block. Follow its declared final completion action instead; a
  successful `coga slack --task bootstrap/<name> ...` posts its roll-up and
  releases that stateless session. If the command cannot proceed, include the
  failure in that final report rather than trying to block a nonexistent task.
  A normal final response or an agent CLI `task_complete` event still does not
  signal Coga and does not release the queue.
