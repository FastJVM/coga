---
title: The autofix analyst ticket closed without shipping any of its three defects
status: done
owner: nicktoper
agent: claude
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
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
---

## Description

`coga/tasks/fix-the-autofix-analyst.md` is `status: done`, but none of the
three fixes its `## Description` scoped ever reached `src/coga/recurring_autofix.py`.
Verified in the tree during this Dream run:

1. **Both labelled streams in `AutofixUnavailable`.** The ticket asks for the
   stderr *and* stdout streams to be included instead of collapsing them.
   `src/coga/recurring_autofix.py` still reads
   `detail = (result.stderr or result.stdout or "").strip()` — the principle-6
   "loudly wrong" error detail the ticket calls out by name.
2. **`stdin=subprocess.DEVNULL` on the analyst `subprocess.run`.**
   `grep -n stdin src/coga/recurring_autofix.py` returns nothing.
3. **An `[autofix].agent` config key read by `_analyze_agent` before the
   `default_agent()` fallback.** `_analyze_agent` still goes straight from
   `agent_override` to `cfg.default_agent()`, and `src/coga/config.py` has no
   `[autofix]` table.

What actually shipped under this ticket (its blackboard `## Implemented`, PR
#724) is a different change entirely — the Claude subscription auth fallback —
which the Description never asked for. The ticket was marked done on the
strength of that unrelated work, and closing it removed the surface that would
have kept the three defects visible.

A partial prior record exists and has not helped: Dream 2026-W36 captured
defects 1 and 2 as backlog item 8 of
`coga/tasks/dream-2026-w36-extract-backlog-18-findings-phase-4.md`, correctly
flagging them as "a bug carrier, not just knowledge — it likely deserves its own
ticket". That ticket is still `status: draft` and unactioned a Dream cycle
later, and it never captured defect 3.

## Context

This is a real bug ticket carrying all three defects, not another backlog
line — the backlog-line route has already been tried and demonstrably did not
drain.

Re-verify each defect against `src/coga/recurring_autofix.py` and
`src/coga/config.py` before implementing; they were confirmed on 2026-09-08 but
line-level details will move.

Two adjacent decisions for the review step:
- whether `dream-2026-w36-extract-backlog-18-findings-phase-4` should be closed
  or narrowed once this ticket carries its item 8 (note item 2 of that same
  backlog — the validate-before-write rule — is also unlanded, and item 1's
  `append_report` duplication still exists as three private copies in
  `skill_update.py`, `dream_validate_drift.py` and `dream_cleanup_orphan_markers.py`);
- whether `fix-the-autofix-analyst` should be reopened instead of superseded by
  this ticket. It is done with a recorded feature checkout, so it is retirement
  debt; reopening a retired-shape ticket is an owner call.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Re-verification (2026-09-16, implement step)

All three defects confirmed present at `origin/main` `436b6028` before any
edit, against `src/coga/recurring_autofix.py` and `src/coga/config.py`:

1. `analyze_record` still built its detail as
   `(result.stderr or result.stdout or "").strip()`.
2. `grep -n stdin src/coga/recurring_autofix.py` returned nothing.
3. `_analyze_agent` went `agent_override` → `cfg.default_agent()`;
   `_ALLOWED_SHARED_SECTIONS` had no `autofix` entry and `Config` no field.

## Dev

pr: https://github.com/FastJVM/coga/pull/816
branch: autofix-analyst-fixes
worktree: /home/n/Code/claude/coga-autofix-analyst-fixes

Separate-checkout layout (linked worktree, created from `origin/main`).

## Implemented

One commit, `Fix the three autofix analyst defects`, rebased onto
`origin/main` `261045a3`.

- **Defect 1** — new `recurring_autofix._labelled_streams` renders
  `stdout: …` / `stderr: …` (empty streams omitted, each with its own
  `_tail(…, 500)`); `analyze_record` raises `AutofixUnavailable` as
  `<cli> exited <rc>:\n<labelled streams>`. Per-stream tails are deliberate:
  a chatty stderr must not crowd the cause out of stdout.
- **Defect 2** — `stdin=subprocess.DEVNULL` on the analyst `subprocess.run`
  in `analyze_record`, and also on the `claude auth status` probe in
  `_claude_subscription_fallback_env` (same one-shot reasoning; one line, not
  scope creep).
- **Defect 3** — `Config.autofix_agent: str | None`, parsed by new
  `config._parse_autofix` from shared `[autofix] agent = "<type>"`;
  `_ALLOWED_SHARED_SECTIONS` gains `autofix`, `_ALLOWED_AUTOFIX_KEYS` is
  `{"agent"}` (one key, one branch — not a routing table). `_analyze_agent`
  precedence is `--agent` > `[autofix].agent` > `default_agent()`.

Decisions made without an owner (recorded so the review step can overrule):

- The key is validated against the *effective* (shared + local merged)
  agents table **at config load**, so a typo fails on the next command rather
  than at the end of an unattended sweep, where the misconfigured analyst
  would be the thing reporting it.
- `[autofix]` is **shared-only** (rejected in `coga.local.toml`, like
  `[layout]`/`[launch]`): which vendor analyzes the sweep is repo policy. A
  machine can still name a locally declared `[agents.*]` type in it.
- Docs: `coga/recurring` context gains three "Operating it" bullets
  (precedence + rationale, stdin, labelled streams); `coga/architecture`
  fixed-schema list gains `[autofix]`; packaged `coga/cli` context mentions
  the key on `coga run autofix-analyze --agent` and the autofix-loop
  paragraph. Packaged twins byte-identical (`tests/test_packaging.py` green).

## Tests

- `tests/test_recurring_autofix.py`: 9 new (labelled streams ×3, stdin ×2,
  agent precedence ×4). `tests/test_config.py`: 7 new (`[autofix]` parse,
  local-declared type, unknown type, non-string, unknown key, shared-only,
  default None). 15 of the 16 fail against the unfixed source.
- Full suite in the worktree: `2511 passed` (pre-rebase). Post-rebase the
  incoming main commit (`261045a3`) touched only `coga/log.md`, task files,
  and a recurring `ticket.py`; re-ran `test_recurring_autofix`,
  `test_config`, `test_packaging`: 207 passed.
- Implementation deferred `coga validate`; peer review below ran task-scoped
  validation with the feature source.

## Adjacent ticket disposition (peer review, 2026-09-16)

- `dream-2026-w36-extract-backlog-18-findings-phase-4` is already `done`:
  PR #795 landed as `2a7e0290`. Its September 12 triage explicitly assigns
  item 8 to this ticket. Items 1 and 2 were knowledge extraction, not a
  promise to consolidate the helpers or convert the remaining lifecycle
  writers. There is no draft backlog left to close or narrow here; those
  unrelated code changes remain outside this fix.
- `fix-the-autofix-analyst` stays `done`; this ticket supersedes it rather
  than reopening a retired-shape ticket. Reopening or retiring its recorded
  checkout remains an owner decision.

## Peer review

`codex review --base main` ran from the recorded feature worktree at
`16959c72` and **returned**, exit 0, on 2026-09-16: "No actionable regressions
found in agent selection, stdin isolation, or failure reporting." The review
also ran the full suite with the feature `src/` on `PYTHONPATH`: **2511
passed**. No must-fix finding or design rethink; no code amendment needed.

Accepted the shared-only configuration and load-time validation against the
effective agents table: both follow the documented repository policy and
fail-loud configuration contract. The explicit override still wins for valid
configurations, and the default remains unchanged without the key.

Ran `git fetch origin main`, then `git rebase FETCH_HEAD` unconditionally in
the feature worktree. Rebase succeeded without conflicts onto `163b1d12`;
feature HEAD is now `4a5502a5`. The incoming four commits changed only this
ticket and `coga/log.md`; the reviewed nine-file product diff is unchanged.
The required post-rebase full suite returned **2511 passed in 180.23s**:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src" /tmp/coga-pr784-review-venv/bin/python -m pytest -p no:cacheprovider`.
Task validation from the primary checkout with the feature package returned
`ok_count: 1`, no issues (`python -m coga.cli validate --task
the-autofix-analyst-ticket-closed-without-shipping --json`, using the same
venv and the absolute feature `src/` on `PYTHONPATH`).
`git diff --check origin/main...HEAD` also passed.

Independent manual verification passed using real child processes in a
temporary fixture (fake vendor executables, notifications and git sync
disabled). The actual `coga run autofix-analyze --dry-run` path selected
`[autofix].agent`, honored `--agent`, and retained the first-declared fallback;
all three received EOF despite nonempty piped input. The initial Claude call,
auth-status probe, and subscription retry also all received EOF. A failed
child preserved both labelled streams and returned exit 1.

Real-terminal checks at 80×24 and 40×12 displayed the stdout billing cause
and stderr connector warning on separate labelled lines, with the normal
error color and the literal `[account notice]` text preserved. Both calls
returned promptly without reading the terminal. Reproduction script:
`/tmp/coga-autofix-peer-smoke.py` (temporary, not product code), run with
`/tmp/coga-pr784-review-venv/bin/python` and arguments `80 24`, `40 12`, or no
arguments for the pipe/precedence/fallback checks. The default `python` lacks
the declared `tomlkit` dependency; the existing test venv includes it.

Handoff: feature branch `autofix-analyst-fixes` is clean and committed at
`4a5502a5`, one commit ahead of fetched `origin/main` `163b1d12`. Review and
test processes have all returned. The PR body is below; no review findings
remain open.

## PR

Autofix analysis could hide a stdout error behind an unrelated stderr warning
and consume the sweep's stdin. Fix both defects and let recurring sweeps
select an analyst independently of the sweep override or new-ticket default.

- Report both failed-child streams with labels and separate bounded tails.
  Pass `stdin=subprocess.DEVNULL` to the analyst and Claude auth-status probe.
- Add shared `[autofix].agent` with `--agent` > configured analyst >
  first-declared agent precedence. Validate the setting against the effective
  agents table at config load.
- Add 16 regression tests and update the recurring, architecture, and CLI
  contracts, including the packaged copies.

Test plan: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src" /tmp/coga-pr784-review-venv/bin/python -m pytest -p no:cacheprovider` — 2511 passed; `python -m coga.cli validate --task the-autofix-analyst-ticket-closed-without-shipping --json` with the feature package and `git diff --check origin/main...HEAD` passed; real subprocess and terminal smoke checks at 80×24 and 40×12 passed.

## Open-pr (2026-09-16)

`coga open-pr` ran from the primary control checkout on `main`, exit 0. It
judged the four incoming `origin/main` commits as non-overlapping task/log
state and published the branch unchanged. PR #816
(https://github.com/FastJVM/coga/pull/816) is open, non-draft, head
`autofix-analyst-fixes`; `pr:` recorded under `## Dev`. Nothing else changed.
