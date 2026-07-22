## Megalaunch queue execution

This session is one step in a sequential `coga megalaunch` queue. The REPL has
a TTY so work can stream live and a human can interrupt, but the TTY is
transport, not evidence that a human is waiting to answer. This queue
directive overrides the attended ask-and-wait default in Agent mode.

- State a concise plan and its tradeoff, then continue. Do not ask for plan
  confirmation or end a turn waiting for permission; a present human can
  redirect you while you work.
- Do not ask-and-wait for missing input here. If a concrete decision,
  credential, permission, or unavailable capability truly prevents progress,
  run `coga block --task <slug> --reason "<specific ask>"` as the terminal
  action. Merely saying that you are blocked leaves the queue hanging and
  does not notify the owner.
- When another Coga task is the blocker, include that task's exact
  path-qualified slug in `--reason`. Megalaunch can then recognize when the
  dependency finishes later in this run and retry this task automatically.
- **Existing blocker-resolution exception.** If the composed prompt includes
  `Resolve the open blocker first`, the human explicitly selected this task
  to resolve those already-open asks. Discuss those asks with them, then run
  `coga unblock <slug> --answer "<resolution>"` and continue if resolved, or
  terminally `coga block` again if unresolved. This exception is only for the
  existing asks; new unavailable input still follows the queue rule above.
- If a code step cannot create a linked worktree because the sandbox mounts
  the primary checkout's `.git` read-only, follow the independent `/tmp` clone
  fallback in the `code/implement` skill before treating it as a blocker.
- Finish the workflow step with `coga bump`, `coga mark done`, or `coga block`.
  An authorized `coga mark canceled` transition also releases the queue; use it
  only when intentional abandonment is the task decision.
  A normal final response or an agent CLI `task_complete` event does not signal
  Coga and does not release the queue.
