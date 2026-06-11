The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: slack-message-rewrite
worktree: ../relay-slack-msgs
pr: https://github.com/FastJVM/relay/pull/321

## Decisions (nick, 2026-06-09)
- Rewrote the ticket: #2 (mark/create/retire split) already landed, so scope is
  all ~17 per-ticket sites, consistency-first.
- Owner suffix DROPPED. The `[project] [owner]` prefix + <@ping> from post()/
  notify() already shows the owner; do NOT add in-text `(owner: …)`; do NOT
  change slack.py.
- Frontmatter title updated to drop "owner suffix".
- Remaining work: titles on the 3 missing sites, prev→new transitions on
  bump/done/automerge, `<url|PR #N>` link on automerge, punctuation pass
  (`:` body, `(key: value)` asides, `—` reserved for FYI suffix).

## Findings — codebase diverged from ticket assumptions

The ticket assumes ticket #2 (split-control-plane-into-relay-mark) has NOT
happened, and lists ~11 message strings. But the codebase has already split:
`relay mark active/paused/done` (commands/mark.py), `relay create`
(commands/create.py), and `relay retire` (commands/retire.py) all exist as
separate commands today. So the real per-ticket Slack message sites are wider
than the ticket's "locked message set". Full inventory:

| # | site | current string (emoji + gist) | per-ticket? |
|---|------|-------------------------------|-------------|
| 1 | create.py:107 | ✨ {user} created *slug* "title" in {project} | yes |
| 2 | retire.py:120 | 🚀 {user} created *slug* "title" (active) — relay retire | yes |
| 3 | launch.py:283 | ▶️ {user} started *slug* "title" — assignee X | yes |
| 4 | launch.py:502 | 🚀 {user} activated *slug* "title" — assignee X (auto on launch) | yes |
| 5 | mark.py:58 | 🚀 {user} activated *slug* "title" — assignee X | yes |
| 6 | mark.py:112 | ⏸️ {user} paused *slug* "title" | yes |
| 7 | mark.py:148 | 🎉 {finisher} finished *slug* "title" | yes |
| 8 | bump.py:170 | 👉 {finisher} {verb} *slug* → step N (name){handoff} | yes (NO prev step, NO title) |
| 9 | recurring.py:343/483 | 🔁 recurring scaffolded *slug* "title" in {project} — assignee X | yes |
| 10 | recurring.py:506 | ⚠️ recurring scan skipped N templates | no (scan-level) |
| 11 | recurring.py:424 | ⏸️ {user} paused *slug* "title" — {suffix} | yes |
| 12 | launch_script.py:120 | ▶️ script started on *slug* "title" — step S | yes |
| 13 | launch_script.py:153 | 💥 script failed on *slug* "title" — exit C, stuck at step S | yes (ALERT) |
| 14 | launch_script.py:215 | 👉 script advanced *slug* → step N (name){handoff} | yes (NO title) |
| 15 | launch_script.py:235 | ✅ script completed *slug* "title" | yes |
| 16 | panic.py:50 | 🚨 {panicker} needs help on *slug* "title" — "reason" | yes (ALERT) |
| 17 | slack.py:50 | 💬 {assignee|user} on *slug*: message | yes (NO title) |
| 18 | automerge.py:137 | 🎉 *slug* "title" auto-bumped on merge of {pr_label} | yes (NO PR link) |

Key gaps the ticket targets:
- No `(owner: ...)` anywhere in message TEXT.
- bump (#8, #14) and slack (#17) lack `"title"`.
- bump (#8) lacks prev→new transition (only shows new step).
- automerge (#18) has `PR #N` as plain text, not a Slack link `<url|PR #N>`.

IMPORTANT nuance: `slack.post()` / `notify()` ALREADY prepend `[<project>] [<owner>]`
to every message and render the owner as a real `<@ID>` ping (slack.py:86-88),
using `owner = ticket.owner or cfg.current_user`. So adding a `(owner: ...)`
text suffix duplicates the owner (once as ping prefix, once as legible suffix).
Need a decision on whether that redundancy is intended (see questions to nick).

## Implemented (step: implement)
All message construction lives at the call sites — `advance_step`/`mark_done`
just receive a finished `slack_text` — so NO library signature changes were
needed; only the callers changed.

Changed files (in worktree ../relay-slack-msgs):
- commands/bump.py — `👉 {finisher} advanced *slug* "title": {prev} → {new} (step N/total)`
- commands/mark.py — active uses `(assignee: …)`; done shows `{prev} → done` (collapses workflow-less)
- commands/launch.py — started `(assignee: …)`; activated `(assignee: …) — auto on launch`
  (changed `suffix` from `(auto on launch)` to `— auto on launch`; updated test_launch.py:828)
- commands/launch_script.py — started `(step N: name)`; advanced prev→new + title;
  failed `: exit C at step N (name)` AND now passes `owner=`/`watchers=` so the
  owner is pinged on failure (the "alert" intent; replaces the dropped `(cc owner)`)
- commands/panic.py — `: {reason}` (dropped quotes)
- commands/slack.py — added `"title"`
- commands/recurring.py — both scaffold posts use `(assignee: …)`
- commands/retire.py — `in {project} — relay retire (active)`
- automerge.py — `{prev} → done — <{url}|PR #N> merged` (collapses workflow-less)
- create.py — already matched the convention; left as-is.

Tests:
- New tests/test_slack_messages.py — 9 tests, capture requests.post, assert
  message BODY (prefix-agnostic). Covers bump transition, mark done prev→done +
  workflow-less collapse, mark active assignee aside, panic, slack FYI,
  automerge link (both workflow + collapse), recurring assignee aside.
- Full suite: 589 passed, 1 FAILED — `test_dream_worker_templates.py::
  test_cleanup_orphan_markers_declares_contract`. PRE-EXISTING (fails on clean
  main; a line-wrap mismatch in a dream SKILL.md I never touched). NOT my change.

Findings:
- The `(assignee: unassigned)` / `… or 'unassigned'` fallbacks are effectively
  dead code: `assignee` is a required non-empty frontmatter key (validate.py),
  so `mark active` fails validation before posting if empty. Left the fallback
  in (defensive), no live-path test for it. Possible follow-up ticket.
- example/ fixture NOT touched (no task-layout / prompt / workflow change).
- src/relay/resources/templates sync NOT needed (only .py source changed, no
  relay-os contexts/templates).

## Peer Review (codex, 2026-06-09)

Ran `codex review --base main` from `../relay-slack-msgs`.
The sandboxed attempt failed with the known read-only app-server error, then
the approved rerun produced one must-fix:
- automerge live Slack text had the new transition/link, but the installed
  digest path still spooled `auto-bumped on merge of PR #N ✅`, so digest users
  would miss `{prev} → done` and `<url|PR #N>`.

Applied fix in feature-worktree commit `0318bfb`:
- `src/relay/automerge.py` digest detail now includes the transition and
  Slack PR link.
- `tests/test_slack_messages.py` now installs a digest spool and asserts the
  queued automerge record, not just the live fallback.
- `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/cli/SKILL.md`
  now documents the updated automerge Slack line. This supersedes the
  implementation note above that no packaged context/template sync was needed.

Verification:
- `PYTHONPATH=src python -m pytest -q tests/test_slack_messages.py tests/test_launch.py`
  -> 60 passed.
- `PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/test_slack_messages.py`
  -> 10 passed after the peer-review fix.
- `PYTHONPATH=src python -m pytest -q -p no:cacheprovider`
  -> 589 passed, 1 skipped, 1 failed. Failure is the pre-existing untouched
  `tests/test_dream_worker_templates.py::test_cleanup_orphan_markers_declares_contract`
  line-wrap mismatch already recorded from the implement step.

## Plan (DONE — kept for history)
1. Add `fmt_owner(ticket)` helper (ticket.owner or "unassigned") — likely in ticket.py.
2. Apply conventions uniformly to all per-ticket sites above.
3. bump.py + commands/bump.py: thread prev_step_name + total into advance_step;
   emit `prev → new (step N/total)`. Same for launch_script advance + done.
4. automerge.py: pass PR url through mark_done, emit `<url|PR #N>`.
5. New tests/test_slack_messages.py snapshotting each format.

## Retro

status: processed
skill: retro/done-ticket
result: knowledge-pr
title: relay/sync: document the uniform Slack message format conventions
