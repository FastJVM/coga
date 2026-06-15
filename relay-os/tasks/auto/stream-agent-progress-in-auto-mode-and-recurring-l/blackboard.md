The blackboard is a notepad to be written to often as the human and agent works through a task.

## Bootstrap session notes (2026-06-10)

- Nick wants this ticket to live under `relay-os/tasks/auto/`, but task
  discovery (`list_tasks()` in `src/relay/tasks.py`) only sees direct
  children of `tasks/`, so moving it now would orphan it from the CLI.
- Decision: drafted a separate ticket,
  `support-task-subdirectories-in-task-discovery`, which extends
  discovery to one-level subdirs and performs the `git mv` of this
  ticket into `tasks/auto/` in the same PR. Nick will execute that
  ticket next; this one stays at top level until it ships.
- Slug-prefix grouping (e.g. `auto-…` names) was explicitly rejected.
- This ticket's own bootstrap interview (workflow, contexts, scope) is
  not finished yet — still a bare draft with only the description from
  create time. Open question carried over: is auto-mode merely silent
  (stream stdout) or actually broken (fix launches)? Nick said "right
  now auto is not working" — clarify before filling the ticket.
