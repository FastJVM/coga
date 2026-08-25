---
slug: megalaunch-only-shows-one-page
title: megalaunch-only-shows-one-page
status: active
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

`coga megalaunch --pick` renders only the first screenful of candidates in a
repo with many tickets. Pressing down past the last visible row moves the
cursor into rows that are never drawn, so it appears to vanish and the list
never scrolls. It should page through every candidate, keeping the cursor
visible at every terminal size.

Root cause (reproduced, see `## Context`): `_picker_window` budgets in
*candidates* while the terminal budgets in *lines*. Any candidate whose row
wraps costs more than one line, the render overflows the terminal, and Rich's
`Live` crops it to one screenful.

The fix is to enforce one terminal line per candidate, end to end:

1. `no_wrap=True, overflow="ellipsis"` on the wide table columns (slug, step,
   title) so they truncate instead of wrapping.
2. The same treatment on the hint line and the two scroll-indicator `Text`
   objects — they sit in the `Group` outside the table and wrap independently.
   Skipping this leaves the bug alive on narrow terminals.
3. Correct the reserved-chrome row count from 4 to 5, and always render both
   scroll-indicator slots — blank when there is nothing above or below — so
   chrome is an unconditional 5 lines and the frame stops jittering by a row
   at the list ends.
4. A `_picker_view` regression test asserting rendered height never exceeds
   terminal height, covering a wrapping title, a mid-list cursor, and a narrow
   (~40-50 column) terminal.

The windowing math in `_picker_window` itself needs no change — it is correct
once the one-line-per-candidate invariant actually holds.

Out of scope: PgUp/PgDn, Home/End, a position indicator, relocating the picker
out of `commands/`, and trimming the shared `prompt.md`.

## Context

**Where the code is.** All of it is in `src/coga/commands/megalaunch.py`:
`_pick_selection` (line ~298) owns the key loop and `Live`; `_picker_window`
(~355) is the pure viewport function; `_picker_view` (~371) builds the Rich
`Table` + scroll indicators + hint line. Existing coverage is
`tests/test_megalaunch.py:2673` (`test_picker_window_keeps_cursor_visible`),
which tests `_picker_window` in isolation only — `_picker_view` has no test at
all, which is exactly why this slipped through.

**The picker stays in `commands/megalaunch.py`.** The codebase context says
command modules stay thin, so a reviewer may ask whether `_picker_view` /
`_picker_window` belong in `src/coga/megalaunch.py` instead. That relocation is
deliberately out of scope here — this is a bug fix, keep the diff tight.

**This is not a stale install.** There is one editable coga install
(`/home/zach2179/.venvs/coga/bin/coga`, `.pth` -> `/home/zach2179/dev/coga/src/coga/`),
so every repo on the machine — `weather-events` included, since its `.venv` has
no coga of its own — runs this working tree. The viewport windowing from #616
(`98a014f7`, on `main`) is already present there. The bug is live on current
code; don't spend time chasing versions.

**Fix the misleading docstring in the same pass.** `_picker_window`'s docstring
claims Rich's `Live` "crops a taller-than-terminal render to the last
screenful." That is wrong and inverts the symptom. `Live`'s default is
`vertical_overflow="ellipsis"`, and `LiveRender.__rich_console__` keeps
`lines[: height - 1]` plus an ellipsis line — the **first** screenful. That is
why the cursor disappears going *down*. Verified by reading `rich.live_render`.

**Confirmed reproduction.** Rendering `_picker_view` against 39 fake candidates
(weather-events' non-terminal ticket count) at pinned console sizes. Exact line
counts depend on how long the fake titles are; the invariant, not the number,
is the point:

| terminal | titles wrap? | window chosen | lines rendered |
|---|---|---|---|
| 100x50 | no | (0, 39) — all | 42 (fits) |
| 100x50 | yes | (0, 39) — all | 159 |
| 80x50 | yes | (0, 39) — all | 276 |
| 100x24 | yes | (0, 20) | 84 |

The 100x50 wrapping row is the reported symptom: `total <= rows` holds, so the
window is "everything" and never moves as the cursor descends. The 100x24 row
shows windowing engaging and still overflowing — so truncating rows to one line
is the load-bearing part of the fix, not a cosmetic extra.

**Truncating the table alone is not enough.** With `no_wrap`/`ellipsis` on the
table columns *and* the corrected `height - 5` reserve, the render still
overflows on narrow terminals, because the hint line
(`"up/down move · Space toggle · a all · n none · Enter launch · q quit"`, 64
cells) and the indicator lines wrap on their own: 50x30 and 40x30 both render
31 lines into a 30-line terminal. Give those `Text` objects `no_wrap=True` and
`overflow="ellipsis"` (or `"crop"`) too, and make sure a narrow width is in the
test matrix — a test built only from the table above would pass while the bug
survives.

**Chrome arithmetic.** `_picker_view` reserves `console.size.height - 4`, but a
Rich `Table` costs **2** chrome lines (header row + header rule), not 1. Real
chrome is 2 (table) + 1 (hint) + 2 (both scroll indicators) = 5. Note the
one-line overflow this causes only appears **mid-list**, where both indicators
are drawn; at either end only one shows and `height - 4` happens to fit. The
regression test must therefore place the cursor mid-list to catch it. Required,
not optional: always render both indicator slots, blank when there is nothing
above or below, so the reserve of 5 is unconditional and the list does not
jitter by a row as you scroll past either end. A conditional reserve is not an
acceptable substitute — it reintroduces the same off-by-one in the other
direction.

**Testing.** Assert on `Console.render_lines` of the `Group` that
`_picker_view` returns. `Console(width=100, height=50)` pins `size` directly —
no `Console` subclass is needed. Do **not** pass an explicit `height` into the
render options: Rich then pads or crops to it and the assertion passes
vacuously; the default `console.options.height` of `None` is what you want.
State a floor for degenerate terminals (`rows = max(1, height - 5)` on a 5-line
terminal still needs 6 lines) so the test does not fail on a pathological size.
`python -m pytest tests/test_megalaunch.py` is the relevant suite.

**Manual verification is a hard gate on the peer-review step — the automated
tests never touch a terminal.** Every test here exercises `_picker_view` as a
pure function; the `Live` + raw-terminal loop stays uncovered, and this bug was
found by eye, so a green suite proves nothing on its own. The peer reviewer
must run `coga megalaunch --pick` in a repo with 39+ non-terminal tickets (e.g.
`weather-events`) at roughly 100x50, 80x24, and 50 columns, hold the down arrow
from top to bottom of the list, and confirm the cursor is visible on every row
at every size. Record the three sizes tested and the outcome in the blackboard.
Do not bump out of peer-review without that record; if the terminal cannot be
driven, say so and block rather than passing the step on tests alone.

**Don't regress.** Cursor wrap-around (up at index 0 -> last), the SIGWINCH
self-pipe resize handling, and the `a`/`n`/Space/Enter/`q` bindings all work
today and are unrelated to this bug.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
