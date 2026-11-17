## Session conduct — recurring queue

This session is one task in a sequential automated queue (a `coga recurring`
sweep). The REPL has a TTY so work can stream live and a human can interrupt,
but the TTY is transport, not evidence that a human is waiting to approve a
plan — the queue may be running unattended. Input you do not already have is
unavailable.

- State a concise plan and its tradeoff, then continue. Do not ask for plan
  confirmation or end a turn waiting for permission; a present human can
  redirect you while you work.
- If a concrete decision, credential, permission, or unavailable capability
  truly prevents progress, run
  `coga block --task <slug> --reason "<specific ask>"` as the terminal action.
  Merely saying that you are blocked — or asking a question and waiting for
  the answer — leaves the queue hanging until a liveness timeout tears the
  session down and records the task as failed, notifying nobody.
- If a code step cannot create the feature branch because the sandbox mounts
  `.git` read-only, follow the independent `/tmp` clone fallback in the
  `code/implement` skill before treating it as a blocker.
- Finish an ordinary workflow step with `coga bump`, `coga mark done`, or
  `coga block`. An authorized `coga mark canceled` transition also releases the
  queue; use it only when intentional abandonment is the task decision.
- A stateless `bootstrap/<name>` command ticket has no task lifecycle to bump
  or block. Follow its declared final completion action instead:
  `coga mark done bootstrap/<name>` releases that stateless session, while
  `coga slack` is only a non-terminal FYI. If the command cannot proceed,
  include the failure in your final report rather than trying to block a
  nonexistent task, then still run that completion.
  A normal final response or an agent CLI `task_complete` event still does not
  signal Coga and does not release the queue.
