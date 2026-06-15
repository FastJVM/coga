The blackboard is a notepad to be written to often as the human and agent works through a task.

## Bootstrap notes (2026-06-10)

Interview findings and decisions behind the filled ticket:

- The daily digest (spool + `relay digest` + `recurring/digest/`) is already
  fully implemented and installed; it has just never fired on schedule —
  nothing drives `relay recurring` daily (no cron). Nick: that driver is a
  **separate ticket**, out of scope here.
- This ticket = restructure *what the digest says*: done tickets (with PR
  links) + other commits merged to `main`, nothing else. Folds in and
  retires the overlapping `relay-dev-update` recurring task (both fire at
  9am today and overlap).
- Decisions by nick:
  1. Fold dev-update into digest, retire `relay-dev-update` — yes.
  2. Stop spooling `draft`/`active`/`bump`/`paused`/`retire` entirely (not
     just hide at render time). Per-task `log.md` keeps the audit trail.
  3. `panic` = emergency, stays live-post as today. `paused`/`retire` need
     no Slack presence at all.
- Edge case flagged for the implementer: `relay bump --message` FYIs ride on
  the bump broadcast; explicit messages must still reach Slack even though
  message-less bumps go silent.
- Per-developer delivery (DMs / per-dev channels): impossible with one
  incoming webhook; explicitly out of scope, noted in ticket Context.
  Per-owner grouping inside the shared message already exists and stays.

## Proposals

- **Per-person inbox (future ticket, nick 2026-06-10):** a per-developer
  "what needs your attention" surface — PRs waiting on your review, stalled
  /sweep-paused runs, panics on your tickets. Came out of two threads in this
  bootstrap: per-developer *delivery* is impossible with one incoming webhook
  (needs per-dev webhooks or a bot token), and silencing `paused` drops the
  "a run of yours is stalled" signal. Decision for *this* ticket: all
  `paused` events go silent; the attention-routing problem is the inbox
  ticket's job, not the digest's.

## Evaluator review

I've read the ticket cold and verified its claims against the code, contexts, workflows, and recurring templates. Assessment below.

### Ticket review: restructure-slack-message

**1. Clarity.** Strong overall. The Description gives a concrete target shape, a clear "done looks like", and the Context section correctly names the real code surface (`src/relay/slack.py::notify`/`render_digest`, `commands/digest.py::run_digest`) and the actual `notify()` call sites — I verified all five modules listed. An agent could start without the interview.

**2. Workflow fit.** `code/with-review` fits: multi-file Python change with tests, peer review, PR. No mismatch.

**3. Contexts.** Both attachments are right, and for the right reason — `relay/sync` is being *edited* by this ticket (its "Batched surface" list and two-tier framing become wrong), and `relay/recurring` carries the parent-blackboard state pattern the `last_commit` mark relies on. Nothing important missing; the key facts from both are already copied into `## Context`, so question 4 is satisfied.

**4. Factual errors to fix before launch.**
- The shipped-template-sync bullet is wrong. The packaged copy under `src/relay/resources/templates/relay-os/` contains **no** digest workflow, no `relay/digest/flush` skill, and no `digest`/`relay-dev-update` recurring templates (`recurring/` there has only `dream`, `_rem`, `_template`; `workflows/` only `autonomy`, `browser`). Only `relay/sync` has a packaged copy, and it lives at `bootstrap/contexts/relay/sync/`, not where the ticket implies. `example/relay-os/` has no `recurring/` dir at all. Risk: an agent "keeping them in sync" may *create* packaged copies that were deliberately never shipped.
- "Done … linked to their merged PR" only holds for automerge records (`automerge.py:134` builds `PR #N`). Manual `relay mark done` (`commands/mark.py:161`) and script-mode done (`launch_script.py:248`) details carry **no** PR number. The ticket should say what a PR-less Done line renders as.

**5. The biggest unstated problem: state-sync commits will flood "Also merged".** Relay itself pushes commits straight to `main` constantly — `Sync task state: …`, `Ticket: <slug> — active/in_progress/deleted` (see the repo's recent log). None carry `(#N)`, so under the proposed rule they all land in "Also merged (no ticket)", recreating exactly the chronological lifecycle noise the ticket is trying to kill. The ticket needs an explicit filter policy for relay-generated commits.

**6. Logic gaps an implementer must guess at.**
- `run_digest` currently early-returns on an empty spool. "Post when nothing done but commits merged" requires running the git scan even with an empty spool — a restructure of the no-op/idempotency logic the ticket doesn't call out. Related: what renders when the spool holds only a `recurring-error` record?
- Fetch semantics are unspecified: `relay-dev-update` did `git fetch` + `last..origin/main`; a `mode: script` digest doing a network fetch adds a new crash-loud failure mode, and the high-water mark means something different against local vs. `origin/main`.
- `render_digest` groups by project (multi-repo channels), but the git scan is single-repo — fine in practice, worth one sentence.
- Silencing `paused` includes the sweep-pauses-an-unfinished-run path (`launch_script.py`, `recurring.py:882`) — that pause signals a stalled run, arguably sync-relevant. Worth a deliberate yes/no.

**7. Scope.** Large but coherent: silencing, digest restructure, and `relay-dev-update` retirement are interlocked (retiring dev-update only makes sense once the digest covers commits). I'd keep it one ticket, but it's at the upper bound; the `bump --message` edge case is the first thing to cut if it balloons.

**Verdict:** launchable after correcting the packaged-copy bullet and adding a filter rule for relay's own task-state commits — the latter is the difference between this ticket achieving its goal and reproducing the noise in a new section.

### Bootstrap response to the review (2026-06-10)

Applied to the ticket: packaged-copy bullet corrected (only `relay/sync` is packaged, at `bootstrap/contexts/relay/sync/`; do not create packaged copies of the rest), relay state-sync commit filter added, PR-less Done-line rendering specified, empty-spool early-return + fetch-semantics decision called out. Left open for nick: whether a sweep-pausing-a-stalled-run `paused` event deserves a Slack line (current ticket says all `paused` go silent).

## Dev

branch: digest-outcomes
worktree: /home/n/Code/codex/relay-digest-outcomes
pr: https://github.com/FastJVM/relay/pull/344

Implementation note (2026-06-10): use the old relay-dev-update behavior of fetching `origin/main` during `relay digest` rather than relying on potentially stale local `main`; this adds a network failure mode to the script run, but keeps the digest tied to the shared branch humans care about.

Implementation complete (2026-06-10):

Commit: `a8523e7` (`Focus Slack digest on outcomes`)

- Changed Slack digest output to outcome-focused Done / Also merged / Recurring errors sections, with done records grouped by owner and PR numbers extracted from done details.
- Changed `relay digest` to scan `origin/<control_branch>` using a `last_commit` high-water mark in `relay-os/recurring/digest/blackboard.md`; first run falls back to the last 24 hours. Relay task-state sync commit subjects are filtered out of Also merged.
- Stopped routine lifecycle events (`draft`, `active`, message-less `bump`, `paused`, `retire`, recurring create success) from calling `notify()`. `done` and `recurring-error` still spool; `relay bump --message` now sends a live FYI.
- Retired `relay-dev-update` by removing its recurring template and workflow, and updated the digest skill/workflow docs plus the live and packaged `relay/sync` context.

Verification:

- `PYTHONPYCACHEPREFIX=/tmp/relay-digest-pyc python -m compileall -q src/relay`
- `git diff --check`
- `PYTHONPATH=/home/n/Code/codex/relay-digest-outcomes/src PYTHONPYCACHEPREFIX=/tmp/relay-digest-pyc python -m pytest -q -p no:cacheprovider tests/test_digest.py tests/test_slack_messages.py tests/test_recurring.py tests/test_commands.py tests/test_launch.py` — 195 passed
- `PYTHONPATH=/home/n/Code/codex/relay-digest-outcomes/src PYTHONPYCACHEPREFIX=/tmp/relay-digest-pyc python -m pytest -q -p no:cacheprovider` — 632 passed, 1 skipped

## Peer review (2026-06-11)

Native review command: `codex review --base main` from
`/home/n/Code/codex/relay-digest-outcomes`. First sandboxed attempt failed with
the known read-only app-server initialization error, then the escalated review
completed.

Must-fix finding:

- `relay digest` unconditionally fetched `origin/main` even when
  `[git].enabled = false`. That broke the documented no-remote/solo opt-out by
  failing before otherwise valid Done/error digest records could post and drain.

Fix committed on `digest-outcomes`:

- `c01cd4c` (`peer-review: honor git opt-out in digest`) makes the digest commit
  scan return "no commits" when git sync is explicitly disabled, matching the
  existing non-git behavior.
- Added a regression test covering a real git checkout with the remote removed
  and `[git].enabled = false`, verifying a spooled Done record still posts,
  drains, and does not write `last_commit` state.

Peer-review verification:

- `PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/relay-digest-pyc python -m pytest -q -p no:cacheprovider tests/test_digest.py tests/test_slack_messages.py` — 28 passed
- `PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/relay-digest-pyc python -m pytest -q -p no:cacheprovider` — 633 passed, 1 skipped
- `PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/relay-digest-pyc python -m pytest -q -p no:cacheprovider tests/test_digest.py` — 17 passed after final formatting cleanup
- `git diff --check`

## Open PR (2026-06-11)

- Pushed `digest-outcomes` (tip `c01cd4c`) and opened
  https://github.com/FastJVM/relay/pull/344 (`gh pr create`, base `main`).
- CI: no checks are configured on this repo (`gh pr checks` reports "no checks
  reported"), so there is no green/red signal to wait on — noting per the
  open-pr acceptance rule rather than treating it as a failure.
