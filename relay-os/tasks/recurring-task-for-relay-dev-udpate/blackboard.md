The blackboard is a notepad to be written to often as the human and agent works through a task.

## Outcome — 2026-05-22

Started as a `bootstrap/ticket` session. Mid-interview the human redirected
twice: first, the deliverable was a recurring task (not an implementation
ticket) so write the template directly; then, the recurring **system** itself
needed to change — recurring tasks should be ticket-format directories so
last-run state can persist across runs.

### Recurring system change

Recurring templates were single `.md` files under `relay-os/recurring/`. They
are now ticket-format directories: `relay-os/recurring/<name>/` with
`ticket.md` (the schedule + run body), `blackboard.md` (persists across every
run — durable last-run state lives here), and `log.md` (append-only run
history; `relay recurring` adds a line each time it scaffolds a period task).
The scanner skips `_`-prefixed directories so `_template/` and `_rem/` ship
inert.

Each scheduled firing still scaffolds a **fresh** per-period task under
`relay-os/tasks/<name>-<period_key>/`. That per-period blackboard is gone next
period; durable state belongs in the recurring directory's own blackboard.
The pattern every such run follows: read `relay-os/recurring/<name>/blackboard.md`
at the start to learn where the last run stopped, do the work, write the same
file at the end with whatever the next run needs.

Files touched for the system change:

- `src/relay/recurring.py` — `Template.load` reads `<dir>/ticket.md`; `name` is
  the directory name; `blackboard_path`/`log_path` properties added.
  `scan_due` iterates directory entries (a non-`_` `.md` file now emits a
  legacy-format error). `scaffold_template` records each created run to the
  template's `log.md` via `_record_run`.
- `src/relay/commands/recurring.py` — `launch <name>` help text updated to
  point at the directory.
- `src/relay/commands/update.py` — `VENDORED_RECURRING_TEMPLATES` now lists
  `recurring/dream/ticket.md` (file-only refresh; per-repo `blackboard.md` and
  `log.md` survive `--update` untouched).
- Migrated `relay-os/recurring/{dream,_template,relay-dev-update}/` and
  `src/relay/resources/templates/relay-os/recurring/{dream,_rem,_template}/`
  to the directory layout (each with `ticket.md` + `blackboard.md` + `log.md`).
- `relay-os/contexts/relay/recurring/SKILL.md` — rewritten for the directory
  model; a dedicated "Last-run state lives in the recurring task's
  blackboard" section documents the read-at-start / update-at-end pattern.
- `tests/test_recurring.py`, `tests/test_init.py`, `tests/test_create.py`,
  `tests/test_dream_worker_templates.py` — updated for the directory layout.
  Full suite: 397 passed, 1 skipped.

### What the recurring task does

A daily digest (every day 9am): each run looks at every commit merged to
`main` since the previous run, summarizes it in a few lines, and posts that
to Slack. The last-processed commit SHA is carried in
`relay-os/recurring/relay-dev-update/blackboard.md`'s `### Dev Update State`
section; the run reads it at start and overwrites it at end.

### Files created

- `relay-os/recurring/relay-dev-update/` (ticket-format directory):
  - `ticket.md` — `mode: auto`, no workflow (body is the run instruction),
    `schedule: "0 9 * * *"`, owner `nick`, assignee `claude`. Repo-specific,
    so not packaged under `src/relay/resources/templates/`.
  - `blackboard.md` — persistent state, with an empty `### Dev Update State`
    block (`last_commit:`, `range:`, `posted:`) populated by each run.
  - `log.md` — append-only run history (one line per scaffold).

### To run it

- `relay recurring launch relay-dev-update` runs it now (ignores schedule).
- `relay recurring` (from `scripts/cron.sh`) picks it up daily.

### This task

Its purpose is served. Safe to delete:
`relay delete recurring-task-for-relay-dev-udpate`.

## Evaluator review

(Reviewed an earlier draft framing this as a code/with-review implementation
ticket — superseded by writing the template directly. Kept for reference.)

The draft was well-formed and launch-ready. Key points raised: the
last-run-SHA persistence mechanism is load-bearing and should be settled
before launch (now settled: the recurring directory's own blackboard, read
at start of run, updated at end); `code/with-review` was heavier than a
single markdown file needs (now moot — written directly); and there was no
context for the recurring system itself (now created: `relay/recurring`).
