---
slug: megalaunch-only-shows-one-page
title: megalaunch-only-shows-one-page
status: draft
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/with-review
secrets: null
---

## Description

`coga megalaunch --pick` renders only the first screenful of candidates in a
repo with many tickets. Pressing ↓ past the last visible row moves the cursor
into rows that are never drawn, so it appears to vanish and the list never
scrolls. It should page through every candidate, keeping the cursor visible.

Root cause (already reproduced, see `## Context`): `_picker_window` budgets in
*candidates* while the terminal budgets in *lines*. Any candidate whose row
wraps costs more than one line, the render overflows the terminal, and Rich's
`Live` crops it to one screenful.

Fix: make each candidate occupy exactly one terminal line (`no_wrap=True`,
`overflow="ellipsis"` on the wide columns so slug/title/step truncate instead
of wrapping), correct the reserved-chrome row count, and add a `_picker_view`
regression test asserting the rendered height never exceeds the terminal
height. Out of scope: PgUp/PgDn, Home/End, and a position indicator — the
picker only has to stop hiding rows, not grow new navigation.

## Context

**Where the code is.** All of it is in `src/coga/commands/megalaunch.py`:
`_pick_selection` (line ~298) owns the key loop and `Live`; `_picker_window`
(~355) is the pure viewport function; `_picker_view` (~371) builds the Rich
`Table` + scroll indicators + hint line. Existing coverage is
`tests/test_megalaunch.py:2673` (`test_picker_window_keeps_cursor_visible`),
which tests `_picker_window` in isolation only — `_picker_view` has no test at
all, which is exactly why this slipped through.

**This is not a stale install.** There is one editable coga install
(`/home/zach2179/.venvs/coga/bin/coga`, `.pth` → `/home/zach2179/dev/coga/src/coga/`),
so every repo on the machine — `weather-events` included, since its `.venv` has
no coga of its own — runs this working tree. The viewport windowing from #616
(`98a014f7`, on `main`) is already present there. The bug is live on current
code; don't spend time chasing versions.

**Confirmed reproduction.** Rendering `_picker_view` against 39 fake
candidates (weather-events' non-terminal ticket count) at fixed console sizes:

| terminal | titles wrap? | window chosen | lines rendered |
|---|---|---|---|
| 100×50 | no | (0, 39) — all | 42 (fits) |
| 100×50 | yes | (0, 39) — all | 159 |
| 80×50 | yes | (0, 39) — all | 276 |
| 100×24 | yes | (0, 20) | 84 |

The 100×50 wrapping row is the reported symptom: `total <= rows` holds, so the
window is "everything" and never moves as the cursor descends. The 100×24 row
shows windowing engaging and still overflowing — so truncating rows to one
line is the load-bearing part of the fix, not a cosmetic extra.

**Secondary defect, fix in the same pass.** `_picker_view` reserves
`console.size.height - 4`, but a Rich `Table` costs **2** chrome lines (header
row + header rule), not 1. Real chrome is 2 (table) + 1 (hint) + 2 (both
scroll indicators) = 5, so a full window overflows by one line even with no
wrapping. Verified by `Console.render_lines` on a 5-row table → 7 lines.

**Testing.** Build the regression test around `Console.render_lines` on the
`Group` that `_picker_view` returns, with a `Console` subclass whose `size`
property is pinned — that is how the reproduction above was done and it needs
no TTY. Cover both a wrapping-title case and the both-indicators-visible case.
`python -m pytest tests/test_megalaunch.py` is the relevant suite.

**Don't regress.** Cursor wrap-around (↑ at index 0 → last), the SIGWINCH
self-pipe resize handling, and the `a`/`n`/Space/Enter/`q` bindings all work
today and are unrelated to this bug.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
