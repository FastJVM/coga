The blackboard is a notepad to be written to often as the human and agent works through a task.

## Plan

`Console().width < 100` switches the table build to no-wrap + ellipsis on
every column except `slug`, which stays no-wrap + fold but is pinned to
`min_width = max(len(slug))` so Rich's column balancer can't crop the
primary identifier. At ≥100 cols the build is byte-identical to the
previous code path, satisfying the "≥120 cols unchanged" criterion.

Rejected: char-fold on slug (loses identity, breaks `slug in output`
substring tests in test_smoke); a separate flat one-line-per-task
rendering (more code, more divergence, no clear win over a
ellipsized table).

## Repro

`COLUMNS=60 relay status` against the live repo previously char-wrapped
titles to ~10 lines per row. After the fix each task is a single line.

## Dev

branch: fix-status-narrow-wrap
pr: (pending push)
