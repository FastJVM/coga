## Megalaunch queue execution

This session is one step in a sequential `coga megalaunch` queue. The REPL has
a TTY so work can stream live and a human can interrupt, but the TTY does
**not** mean a human is waiting to approve a plan.

- State a concise plan and its tradeoff, then continue. Do not ask for plan
  confirmation or end a turn waiting for permission; a present human can
  redirect you while you work.
- If a concrete decision, credential, permission, or unavailable capability
  truly prevents progress, run
  `coga block --task <slug> --reason "<specific ask>"` as the terminal action.
  Merely saying that you are blocked leaves the queue hanging and does not
  notify the owner.
- If a code step cannot create a linked worktree because the sandbox mounts
  the primary checkout's `.git` read-only, follow the independent `/tmp` clone
  fallback in the `code/implement` skill before treating it as a blocker.
- Finish the workflow step with `coga bump`, `coga mark done`, or `coga block`.
  A normal final response or an agent CLI `task_complete` event does not signal
  Coga and does not release the queue.
