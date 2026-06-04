---
title: Session-done sentinel from mark done/bump leaks into parent supervised launch
  and tears down orchestrator
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

**Bug class:** orchestrator self-teardown / sentinel leak.

When an agent is running inside a supervised `relay launch` REPL and that agent
shells out to `relay mark done <other-task>` (or, by the same mechanism,
`relay bump` / `relay panic`) against a **child** task, the command prints the
session-done sentinel to stdout:

```
$ relay mark done dream-validate-drift-worker
dream-validate-drift-worker: done
<<<RELAY_SESSION_DONE_a9f3c41e>>>
```

The `relay launch` supervisor is watching the **parent** session's output
stream for that sentinel. The sentinel is not task-scoped in the stream, so the
supervisor reads it, concludes the *parent* session is finished, and tears down
the parent REPL — even though the command targeted a different (child) task and
the parent's own work is unfinished.

**Observed during:** a `[debug] Dream` run in the patents repo. Dream is an
orchestrator: its parent interactive session spawns child `mode: script` worker
tasks (Phase 1 validate-drift, Phase 5 cleanup-orphan-markers). After launching
and reading the child worker's result, the parent ran
`relay mark done dream-validate-drift-worker` to settle the child. That emitted
the sentinel into the parent's supervised stream and killed the orchestrator
mid-run (after Phase 1 of 6), forcing a "Continue from where you left off"
relaunch.

**Why it matters:** Dream-style orchestration is a first-class pattern — a
parent launch that fans out to child script workers and needs to settle their
lifecycle. Today there is no safe way for the parent to `mark done` / `bump` a
child inline, because the child's done-sentinel terminates the parent. This
makes any multi-task orchestrator inside `relay launch` fragile.

## Expected

One of:

- The session-done sentinel should be scoped to the session/task it belongs to
  (e.g. include the slug, and have the supervisor only act on the sentinel for
  *its own* launched task), so marking a child done does not match the parent's
  teardown condition; or
- `relay mark done` / `relay bump` / `relay panic` should suppress (or send to a
  side channel rather than stdout) the supervisor sentinel when the target task
  is not the one the current launch supervisor owns; or
- the supervisor should only honor the sentinel on the launched task's own REPL
  fd, not on arbitrary child output the orchestrator surfaces.

## Reproduction

1. `relay launch <parent>` an interactive task (the orchestrator).
2. From inside that session, create + launch a child `mode: script` task
   (`relay create … --mode script --workflow …`; `relay mark active`;
   `relay launch <child>`), which completes synchronously.
3. From the same parent session, run `relay mark done <child>`.
4. Observe `<<<RELAY_SESSION_DONE_…>>>` printed; the parent `relay launch`
   supervisor tears down the parent REPL.

## Workaround in use

In the Dream run, the parent now defers all child `mark done` / `delete` of
worker tasks to the very end of the parent run (where self-teardown is
harmless anyway), and avoids inline `mark done` of children mid-orchestration.
This is a workaround, not a fix — the underlying sentinel leak remains.

## Notes / related

- Base-prompt guidance already says "Don't paste any marker string yourself"
  and that `mark done`/`bump`/`panic` "signal the supervisor to tear down your
  REPL." The gap is that this is only safe for the *current* task; against a
  child it cross-talks into the parent stream.
- Relevant to the broader Dream contract, which expects a parent run to manage
  child script workers (Phases 1 and 5).

## Context

Filed by the patents-repo Dream run (`dream-dbg-20260604T150329`) on
2026-06-04 after hitting this mid-run. Reporter: claude (interactive, with nick).


