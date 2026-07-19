# Coga velocity report

This is the evidence note behind the “Measured on itself” section of the
[README](../README.md). It deliberately reports operating facts, not a
productivity multiplier. There is no control group, task sizes vary, and Coga
working on Coga is not an external benchmark.

## What the repository shows

### Agent-initiated work

The append-only [`coga/log.md`](../coga/log.md) identifies who launched and
advanced each task. Entries tagged `agent:claude`, `agent:codex`, or `system`
show work initiated or advanced by the machine; `human:*` entries show human
transitions. Ticket blackboards preserve each agent's plan, findings, and
handoff.

This establishes that agents operated the workflow. It does not establish that
every line of a resulting change was machine-written, nor would that be a
useful quality measure.

### Peer review on shipped development work

The development workflows frozen into tickets include an implementation step
and a review step assigned to the other configured agent. The task file records
the step transition and reviewer; the linked pull request records the resulting
review and merge. “Universal peer review” means every development change shipped
through those review-bearing workflows during the reported period—not every
docs-only, direct-body, or administrative commit in git history.

The contract is inspectable in the workflow snapshots under
[`coga/tasks/`](../coga/tasks/) and the reusable workflow definitions installed
with Coga. Search the snapshots with:

```sh
rg -n -U 'name: (implement|peer-review).*?assignee: (agent|other-agent)' coga/tasks
```

### Peak in the reporting window: 31 agent-operated workstreams in one week

A workstream is a distinct non-bootstrap, non-recurring Coga task with an
`agent:*` or `system` event during the same Monday-through-Sunday week.
“Concurrent” means the streams were active within that weekly operating window;
it does not mean 31 processes ran at the same instant. The reporting window ends
2026-07-05, the end of ISO week 27; the peak through that date was 31. Task size
and lines changed are intentionally not inputs.

The source ledger is [`coga/log.md`](../coga/log.md). Recompute the number from
the repository root with this standard-library-only script:

```sh
python - <<'PY'
import collections, datetime, re

event = re.compile(
    r"^(\d{4}-\d{2}-\d{2}) \d{2}:\d{2} \[([^]]+)] \[([^]]+)]"
)
weeks = collections.defaultdict(set)
for line in open("coga/log.md", encoding="utf-8"):
    match = event.match(line)
    if not match:
        continue
    date_text, task, actor = match.groups()
    date = datetime.date.fromisoformat(date_text)
    if date > datetime.date(2026, 7, 5):
        continue
    if task.startswith(("bootstrap/", "recurring/")):
        continue
    if actor.startswith("agent:") or actor == "system":
        weeks[date.isocalendar()[:2]].add(task)
print(max((len(tasks), week) for week, tasks in weeks.items()))
PY
```

The output is `(31, (2026, 27))`. Pinning the end date matters: the repository
is live, and a later week can exceed the earlier launch-period peak.

### Shipping while a founder was half-time

During the reported period, one of FastJVM's two founders was available roughly
half-time while development work continued through the same ticket, review, and
merge path. This is an operating-history observation, not a causal claim: the
repository can show the work and its timestamps, but it cannot independently
prove a person's hours. We retain it because the constraint is the story behind
the system; we do not convert it into an efficiency percentage.

## Why there is no multiplier here

Lines changed reward churn. Commit and ticket counts reward splitting. A
comparison with an imagined ten-person team cannot be audited. Those measures
do not survive scrutiny, so this report makes no “5x,” “10x,” or percentage
productivity claim.

The stronger experiment measures the input the repository can expose:
**human-minutes per shipped task**. Its pre-registered report will count every
attempt—completed, blocked, rescued, or abandoned—and link each row to its
receipt. Until that run finishes, the two-person/output-of-ten statement stays
where it belongs: in [the vision](vision.md), labeled as the bet.
