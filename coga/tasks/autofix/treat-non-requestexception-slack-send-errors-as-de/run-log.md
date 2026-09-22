# Recurring sweep — 2026-09-22 10:18:45

- repo: coga
- mode: bare sweep
- templates scanned: 9
- tasks run: 2
- problems: 3

## Scan

```
address-pr-comments  ready (Tue 07:00)          launch
autoclose-merged     ready (Tue 08:00)          launch
blocker-reminders    ready (Tue 10:00)          launch
branch-sweep         overdue 1d (Mon 07:00)     skip (ran this period)
dream                overdue 1d (Mon 09:00)     skip (done)
resolve-conflicts    overdue 1d (Mon 08:00)     skip (ran this period)
skill-update         overdue 1d (Mon 09:00)     skip (ran this period)
upstream-coga        ready (Tue 08:00)          launch
usage-report         overdue 1d (Mon 08:00)     launch
```

## Unresolved recurring failures

- `recurring/autoclose-merged`: no launch outcome was recorded; an unhandled OSError stopped the sweep at recurring/autoclose-merged
- `recurring/upstream-coga`: admitted as due but never launched: an unhandled OSError stopped the sweep at recurring/autoclose-merged
- `recurring/blocker-reminders`: admitted as due but never launched: an unhandled OSError stopped the sweep at recurring/autoclose-merged

## Task outcomes

### recurring/usage-report — completed

- template: `usage-report`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.
```

### recurring/address-pr-comments — completed

- template: `address-pr-comments`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.
```

## Sweep notes

- launching 5 due task(s) sequentially
- an unhandled OSError stopped the sweep at recurring/autoclose-merged
- 2 of 5 due task(s) never launched after recurring/autoclose-merged: recurring/upstream-coga, recurring/blocker-reminders
