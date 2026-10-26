---
name: coga/usage-report/post
description: Post last week's agent token usage to Slack once a week.
---

# Agent usage report

This skill documents the weekly post behind the `recurring/usage-report/`
ticket, whose `ticket.py` runs the template's own `report.py` — no agent, no
composed prompt, no `coga run` recipe. The report is single-consumer
deterministic work, so it lives beside its ticket and imports only shared core
infra (`coga.config`, `coga.tasks`, `coga.usage`, `coga.notification`).

1. **Window.** `report.default_window(today)` is the last completed ISO week:
   previous Monday 00:00 to this Monday 00:00 UTC, half-open `[since, until)`.
   `report.build_report` passes tz-aware datetimes to `coga.usage.rollup`
   (`since` at 00:00, `until` at 00:00 minus one microsecond) because
   `rollup`'s `until` is inclusive — a date-only `until` expands to the end of
   that day and `_record_matches` keeps `ts == until`. A record whose `ts` is
   exactly `until` 00:00 belongs to the next week.
2. **Content.** `report.render` prints one header naming the week, then total
   tokens and session count with the `usage_status: unknown` count stated as
   a floor, the four token categories (input, cache write, cache read, output —
   kept distinct because cache tokens dominate and a future dollar line prices
   them differently), and a per-model split largest first. Every rollup bucket
   is a row: `(unknown)` for a null model and `<synthetic>` are never dropped.
   An empty window still renders and says so.
3. **Post.** `ticket.py` finds `report.py` through `$COGA_COGA_OS_ROOT`
   (`coga launch` copies only `ticket.py` into the period task), renders the
   default window, and supplies the period ticket's owner (or
   `cfg.current_user` when absent) to `coga.notification.post` with
   `important=True, fatal=False` — one attempt, on the important route by
   owner exception. The report is an FYI, and `coga/important`'s
   action-needed bar binds the producers Coga ships; the owner keeps this
   repo-local report on important because token consumption is something
   they want treated as needing attention (2026-10-01). Moving it to flow
   was tried in PR #944 and closed unmerged: do not refile that move. The
   notification backend adds the repo name and mapped owner mention,
   retaining plain text for an unmapped owner
   ([owner mapping](../../../../../docs/contexts/coga/notifications/SKILL.md#pinging-the-owner)).
   `fatal=False` means a delivery miss is reported on stderr but the shim
   still closes its step with `coga bump`, so the period never sticks
   `in_progress` over a webhook problem. Known gap: the miss is **not**
   recorded in `log.md`. `SlackChannel.send` writes its failure audit line
   only when the post passes `task_path`, and `ticket.py` passes none, so the
   `ticket.py` comment claiming the miss is loud "in `log.md`" is wrong.
   Check the period's stderr, not the log, for a missed week.
4. **No cursor.** The template declares no `state_keys:`. Given the same
   `coga/log.md`, the same window renders the same text, so a missed or
   undelivered week is recovered by hand:

   ```sh
   python coga/recurring/usage-report/report.py --since 2026-08-31 --until 2026-09-07
   coga slack --task <slug> --message "$(python coga/recurring/usage-report/report.py --since … --until …)"
   ```

   `--since`/`--until` are `YYYY-MM-DD`, each defaulting to its end of the
   last completed week; `--json` emits the report fields instead of the text.
   Ad hoc runs print to stdout and never post or write, and like `coga usage`
   they load config with `require_user=False`, so a fresh clone without a
   `coga.local.toml` user can still render a week.

Out of scope, by the owner's decision: dollar figures and plan comparison
(one API-equivalent-value line is a follow-up once the cost proxy lands),
per-person attribution, and closing the coverage gaps the floor caveats —
unrecorded non-Coga sessions, recipe runs that record nothing, and
`usage_status: unknown` sessions.

Cross-check the renderer by hand with
`coga usage --json --by model --since <since> --until <until minus a day>`.
