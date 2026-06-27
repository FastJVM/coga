---
slug: decouple-autoclose-sweep-test-from-baked-in-period
title: Decouple autoclose sweep test from baked-in period date
status: done
autonomy: interactive
owner: nick
human: nick
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
  - name: review
    skills: []
    assignee: owner
secrets: null
---

## Description

Found by the Dream run on 2026-06-18 (knowledge scan, gap finding G-NEW-1).

`tests/test_autoclose_sweep.py:159` asserts the committed autoclose blackboard
ends with `last_serviced_period: 2026-06-11`, but the live committed value in
`relay-os/recurring/autoclose-merged/blackboard.md` has since advanced (e.g.
`2026-06-17`). As a result `test_autoclose_live_and_packaged_copies_stay_in_sync`
and `test_autoclose_recurring_template_creates_idempotently` fail
deterministically on any run where "today" differs from the baked-in period.

This recurs: the same "2 pre-existing failures, NOT mine" was independently
re-diagnosed in at least four separate dev-task blackboards
(`1password-…`, `fail-loud-…-secret`, `first-run-works-without-slack-configured`,
`marketing/relay-build-command`), each agent burning time rediscovering it — a
recurring verification tax.

Fix direction: decouple the test from the live, mutating blackboard value —
e.g. use a fixture/temp copy, assert structure rather than a hardcoded date, or
freeze the period. Human design judgment needed on the right approach.

## Context

<!-- coga:blackboard -->

## Findings (implement step, 2026-06-26)

**The premise is already addressed.** Both target tests currently pass
deterministically; live `last_serviced_period` is `2026-06-24`, today is
`2026-06-26`, and `python3.12 -m pytest tests/test_autoclose_sweep.py` → 4
passed.

Why: PR **#413** ("Fix autoclose-merged sync tests (reset + make tolerant of
dogfooding drift)", merged 2026-06-19 — the day *after* the Dream scan on
06-18) introduced `_strip_runtime_state()` and wired it into both failing
tests:
- `test_autoclose_live_and_packaged_copies_stay_in_sync` strips any
  `last_serviced_period:` / timestamped log line from **both** live and
  packaged before comparing → no longer compares the mutating value.
- `test_autoclose_recurring_template_creates_idempotently` strips the live
  template's serviced-period after copying into tmp_path, then freezes
  `now = datetime(2026, 6, 11, ...)` and asserts against that frozen value
  (`read_last_serviced_period(...) == "2026-06-11"`), not against "today".

(The single-file `ticket.md` format from #427 carried the strip forward; the
old `blackboard.md` path named in the ticket no longer exists.)

So the Dream finding is **stale** — the four dev-task blackboards that
re-diagnosed "2 pre-existing failures" all predate #413's merge.

**Open question for the human:** since the bug is fixed, options are:
1. Close as already-resolved (recommended) — no code change.
2. Optional hardening only if wanted, e.g. a regression test asserting the
   sync test stays green when the live value drifts, or tightening
   `_strip_runtime_state` to be less lenient. Low value; the current strip is
   adequate.

## Decision (2026-06-26)

Human (nick) chose **option 1 — close as already-resolved**. No code change;
bug was fixed by PR #413. Closing via `coga mark done` rather than running the
implement→PR→review workflow, since there is nothing to ship. The workflow
short-circuits here because the premise no longer holds.
