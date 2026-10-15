---
name: coga/recurring/scheduling/ledger
description: How a recurring scan buckets a template's last firing into a period key, and the append-only serviced-period ledger in `coga/log.md` that stops a period from re-firing.
---

# Periods and the serviced-period ledger

Part of [coga/recurring/scheduling](../SKILL.md).

The scan takes each template's last firing strictly before now
(`recurring._last_firing`) and buckets it (`_period_key`): hourly →
`YYYY-MM-DD-HH`, daily → `YYYY-MM-DD`, weekly (day-of-week set) → `YYYY-Www`,
monthly (day-of-month set) → `YYYY-MM`, anything else → `YYYYMMDDTHHMM`.

The high-water mark is a `created|reused <task-ref> for <period>` line tagged
`recurring/<name>` in the repo-global `coga/log.md` — one writer and one parser
(`format_serviced_log`, `parse_serviced_period_entries`), pinned by a test. It
is not in the template blackboard, where any run rewriting a region could erase
it and re-fire the period. The line is append-only, union-merged, outlives the
reaped task, and is never composed into prompts.

Records are validated for exact shape and calendar values and compared by
calendar position. A malformed record is a template error in the sweep,
`coga recurring list` and `coga status`, never "ran this period". A period at
or below the newest valid record is not re-created or re-launched.
`read_serviced_ledger` reads the log **backwards** and stops once every
requested ref has a valid record at or after its target period; because
`merge=union` can put a newer record above an older one, an older hit never
stops the read. The first scan of a new period therefore walks the whole log;
later scans resolve from the tail. Malformed history older than the stop point
is allowed to heal. Freshness against control at publication is in
[recurring-admission](../../../internals/recurring-admission/SKILL.md).

Current period only: missed periods are not chased, so a monthly run of a
weekly template produces one run.
