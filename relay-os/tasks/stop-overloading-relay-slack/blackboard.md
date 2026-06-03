The blackboard is a notepad to be written to often as the human and agent works through a task.

## Step: implement (claude, 2026-06-03)

Picked up a fresh `implement` step — blackboard was empty. Read the full ticket
design and surveyed the codebase.

### Codebase findings

- `src/relay/slack.py` — single `post()` + `_mention()`. The split point for
  live-vs-spool routing.
- Batchable call sites: `commands/create.py` (draft/create), `commands/bump.py`,
  `commands/mark.py` (active/paused/done), `commands/retire.py`,
  `commands/recurring.py` (per-scaffold + error summary), and
  `automerge.auto_bump_merged` (automerge done). Stay live: `commands/panic.py`,
  `commands/launch_script.py` (script failure), `commands/slack.py` (manual FYI).
- **No file-lock primitive exists.** The design references "Relay's existing
  file lock" but it doesn't exist — only `repl_supervisor.py` uses `fcntl`
  (for PTY sizing), and `git.py` explicitly frames relay as a "no-mutex model."
  Concurrency-safe append+drain needs a new lock. Plan: a small `fcntl.flock`
  exclusive lock scoped to the spool file in `spool.py`. POSIX-only, narrowly
  scoped to one file — not a global mutex.
- Recurring tickets are directories under `relay-os/recurring/<name>/` with
  `ticket.md` + `blackboard.md`; schedule in frontmatter `schedule:` cron.
  `mode: auto` is temporarily refused by `scaffold_template`, so the digest
  ticket must be `mode: script` (which is allowed and runs `relay digest`).
- `recurring.py::_record_run` appends `scaffolded <slug>` lines to the
  template's blackboard — the SAME file as the spool. Flush must be scoped to
  the `## Spool (pending)` section only and must not touch the ledger lines.
  Confirmed benign: `_period_already_scaffolded` only consults the ledger when
  the period's task dir is missing, so emptying the spool section never
  triggers re-scaffolding.
- Packaged templates: `src/relay/resources/templates/relay-os/recurring/`
  exists (dream, _rem, _template) → add a packaged `recurring/digest/` copy.
  `contexts/relay/` is NOT packaged → the `sync/SKILL.md` revision has no
  packaged mirror to keep in sync.
- `mode: script` launch (`launch_script.py`) requires the step's single skill
  to declare `script: <file>` in its SKILL.md frontmatter. So the digest
  ticket needs a workflow step → skill → script that calls `relay digest`.
- CLI commands registered in `cli.py` via `app.command("name")(fn)`.

### Decisions (Nick, 2026-06-03)

1. **Minimal seam, keep `slack.py`.** No module rename, no `[notification]`
   config. `slack.py` gains: `post()` stays the live path (urgent); add
   `spool_event(...)` (batchable → `spool.append_record`) and `render_digest(...)`
   (group + format). `commands/digest.py` calls `render_digest` + `post`. The
   full notification rename stays the sibling ticket's job.
2. **Lockless, simplest.** One process at a time (Nick) — no flock, no CAS
   retry loop. Plain atomic read-modify-write via `atomicio.atomic_write_text`.
3. **Truncate spool, keep ledger.** Flush empties `## Spool (pending)` back to
   its seed; `scaffolded …` period-ledger lines preserved. Git history is the
   audit trail for what was sent.
4. Empty-day: skip silently (Nick's stated default).

### Spool location (resolved)

Producers write to the recurring **template's** blackboard,
`relay-os/recurring/digest/blackboard.md` (persistent, exists as soon as the
template ships) — NOT the per-period task blackboard. `relay digest` (run by
the period task's `mode: script` step) drains that same template blackboard.
Spool lives in its own `## Spool (pending)` section; `_record_run`'s
`scaffolded …` lines append at EOF and stay clear of it. drain parses only
valid-JSON lines defensively and rewrites just the spool section.

### Plan

- `src/relay/spool.py` — `append_record(path, record)`, `drain(path)` over a
  `## Spool (pending)` JSONL section; atomic writes; no lock.
- `src/relay/slack.py` — add `spool_event(cfg, *, kind, ticket, owner, watchers,
  detail, ts=None)` → builds record, appends to template spool; add
  `render_digest(cfg, records) -> str` (project→person→ticket, `_mention` pings).
- Reroute batchable call sites to `spool_event`: create, bump, mark, retire,
  recurring (per-scaffold + error summary), automerge done. Keep live: panic,
  launch_script failure, slack FYI.
- `src/relay/commands/digest.py` + `app.command("digest")` in cli.py — drain,
  render, `post`, empty. Empty spool → silent no-op.
- `relay-os/recurring/digest/` ticket (mode: script, daily schedule, workflow
  step → skill with `script:` calling `relay digest`) + packaged copy under
  `src/relay/resources/templates/relay-os/recurring/digest/`.
- Revise `relay-os/contexts/relay/sync/SKILL.md` §"Slack — the team sync point"
  for the two-tier model. (No packaged contexts mirror exists.)
- Tests: `tests/test_digest.py` (+ spool); example fixture if needed.

### Key design refinement (reduces blast radius)

Batchable events route through a new `notify(cfg, slack_text, *, kind, ticket,
owner, watchers, detail, ...)` in slack.py:
- **If the digest template `recurring/digest/blackboard.md` exists → spool** the
  structured record (no live post).
- **Else → fall back to `post(slack_text)`** — exactly today's behavior.

So the feature is **opt-in by installing the digest recurring ticket**. Repos
without it keep live posting; existing tests (no digest template in fixture)
stay green because `notify` degrades to `post`. Finalizers keep `slack_text`
(live fallback) and gain `kind` + `detail` for the spooled record.

Tests stub `requests.post` (autouse `_stub_slack` in conftest), so they don't
assert on `slack.post` directly — confirming the fallback keeps them green.

### in_progress / launch start stays LIVE

Decision #1 batches exactly: draft/create, bump, mark active/paused/done,
retire, automerge done, recurring scaffold/skip. `mark_in_progress` (the
active→in_progress launch-start post) is NOT in that list → stays live. Spec-
faithful reading; flagged for review.

### Spool git-sync: out of scope (deliberate)

Per-event spool appends are local writes, NOT git-synced (matches design's
"don't rely on git", avoids contention; one-machine relay flushes locally).
Task-dir `git.sync_task_state` calls are unchanged.

### Packaged-mirror scope (confirmed)

- Packaged sync context: `…/bootstrap/contexts/relay/sync/SKILL.md` (currently
  IN SYNC) → mirror the §"Slack" edit there. Required by `test_packaging`.
- `relay-dev-update` is **live-only** (not packaged) → precedent for shipping
  the digest recurring ticket + its workflow + skill **live-only** under
  `relay-os/`. No packaged recurring/workflow/skill mirrors this PR.

### Final file plan

Core (`src/relay/`):
- `spool.py` (new): `append_record(path, record)`, `drain(path)` over JSONL
  `## Spool (pending)`; atomic writes; parses only valid-JSON lines.
- `slack.py`: `digest_spool_path(cfg)`, `notify(cfg, slack_text, *, kind,
  ticket, owner, watchers, detail, task_path, image_url)` (spool-if-installed-
  else-post), `spool_event(...)`, `render_digest(cfg, records, *, date_label)`.
- `commands/digest.py` (new) + `cli.py` `app.command("digest")`.
- Reroute: `mark.py` (mark_active/paused/done +kind+detail→notify), `bump.py`
  (advance_step +kind+detail→notify), `commands/mark.py`, `commands/bump.py`,
  `automerge.py`, `commands/create.py`, `commands/retire.py`,
  `commands/recurring.py` (per-scaffold + error summary).

Live scaffolding (`relay-os/`):
- `recurring/digest/{ticket.md,blackboard.md,log.md}` (mode: script, daily
  schedule, workflow `digest/post`, owner nick, assignee claude).
- `workflows/digest/post.md` (one step `run` → skill `relay/digest/flush`).
- `skills/relay/digest/{SKILL.md,run.py}` (`script: run.py` → run_digest()).

Context + mirror:
- `contexts/relay/sync/SKILL.md` §"Slack" revised → two-tier model.
- mirror to `…/bootstrap/contexts/relay/sync/SKILL.md`.

Tests: `tests/test_digest.py`.

Branch: `daily-digest-slack`.

## Dev

branch: daily-digest-slack
worktree: ../relay-daily-digest
pr: https://github.com/FastJVM/relay/pull/275

## Implementation complete (claude, 2026-06-03)

Committed `ec57303` on `daily-digest-slack`. No push / no PR (that's the
`pr` step). Full suite green: **541 passed, 1 skipped**; new
`tests/test_digest.py` (12 tests) all pass. `relay validate --json` shows only
pre-existing errors (broken `bootstrap/ticket` / `relay/cli` refs in unrelated
draft tickets) — none from this change; the new digest ticket/workflow/skill
validate clean.

### What shipped

- **`src/relay/spool.py`** (new) — reusable `append_record` / `drain` /
  `read_records` over a `## Spool (pending)` JSONL section, atomic writes, no
  lock (one process at a time). `drain` preserves non-record lines so
  `recurring._record_run`'s ledger lines survive a flush.
- **`src/relay/slack.py`** — added `notify` (batchable router: spool-if-
  installed-else-`post`), `digest_spool_path`, `render_digest` (project →
  person → ticket, `_mention` pings + watcher cc). `post` unchanged (live).
- **`src/relay/commands/digest.py`** (new) + `relay digest` in `cli.py`
  (+ `_BUILTIN_COMMANDS`). `run_digest`: drain → render → post → empty;
  empty/no-ticket → silent no-op.
- **Reroutes** (batchable → `notify`, with `kind`+`detail`): `mark.py`
  (active/paused/done), `bump.py` (advance_step), `automerge.py`,
  `commands/{create,retire,recurring}.py`. `mark_in_progress` stays live.
- **Live-only scaffolding**: `recurring/digest/` (mode:script, daily 9am,
  workflow `digest/post`), `workflows/digest/post.md`,
  `skills/relay/digest/flush/{SKILL.md,run.py}`.
- **Context**: `contexts/relay/sync/SKILL.md` §"Slack" rewritten for the two-
  tier model + new "The daily digest" section; mirrored to the packaged
  `bootstrap/contexts/relay/sync/SKILL.md`.

### Verified end-to-end (scratch repo, slack+git disabled)

`relay recurring launch digest` → scaffolds `digest-<date>` (mode:script) →
resolves `digest/post` → `relay/digest/flush` → `run.py` → `relay digest` →
drains, renders grouped digest to stderr, empties spool. Confirmed: the
`scaffolded …` ledger line **survives** the flush (the bug the e2e caught and
I fixed in `drain`); a second `relay digest` is a silent no-op; `post`-path
urgent events (panic/slack/launch_script) bypass the spool.

### Notes for review

- **Digest is now ACTIVE in this repo** — installing `recurring/digest/` means
  batchable events spool here instead of posting live. The digest ticket must
  actually run (cron / `relay recurring`) or events pile up. Schedule is daily
  9am in the ticket frontmatter.
- **in_progress/launch start stays live** — spec-faithful read of decision #1
  (which lists active/paused/done, not in_progress). Flagged for owner review.
- **Spool not git-synced per-event** (deliberate; matches "don't rely on git").
- Sibling tickets untouched: notification-module rename, rewrite-slack-messages,
  document-the-blackboard-producer-consumer-pattern.

## Self-QA (claude, 2026-06-03)

Ran `/code-review` (high) and `/simplify` against `daily-digest-slack` vs main.
Applied fixes committed in `3b5be2c` on the branch. Also removed two stray
`</content>`/`</invoke>` lines that had corrupted the end of this blackboard.

### Fixes applied (correctness — from /code-review)

1. **Spool data-loss on post failure** (`commands/digest.py`). `run_digest`
   drained the spool *before* posting, so a transient webhook failure (which
   `post` turns into a crash-loud `typer.Exit`) destroyed the whole day's
   records with no way to recover. Reordered to **post → then drain**: records
   clear only after a successful post; a failed post leaves them for the next
   run. Single-process serialization means nothing spooled mid-run is lost.
   Updated the module + function docstrings to match.
2. **UnicodeEncodeError under a bare locale** (`spool.py` + `atomicio.py`).
   Spool `detail` strings carry non-ASCII (`→`, `✅`, `🔁`, `⚠️`). `atomic_write_text`
   opened the temp file with the platform-default encoding and `spool` read with
   `read_text()` (locale too), so a digest fired from a `LANG=C` cron env — the
   intended trigger host — would crash encoding the arrow/emoji. Pinned
   `encoding="utf-8"` on the atomic write and the three spool reads. Fixed at the
   shared-writer altitude; strictly safer (utf-8 is byte-identical for ASCII).
3. **Owner ordering contradicted its own comment** (`slack.py::_render_people`).
   Comment said "preserving first-seen order" but the code re-sorted owners
   alphabetically, breaking the documented chronological-replay intent and the
   ticket's example (@nick before @alice). Changed to a stable sort that only
   pushes the ownerless bucket last, keeping first-seen order.

### Fixes applied (cleanup — from /simplify)

4. **Empty-spool messaging was split + double-printed** (`commands/digest.py`).
   `digest()` re-derived an "empty" note that `run_digest` could also print, so
   the not-installed case emitted two lines. Folded all empty/no-op messaging
   into `run_digest`; `digest()` now just loads config and calls it.

### Reviewed and deliberately NOT changed (left for the human reviewer)

- **`test_packaging::test_wheel_includes_bootstrap_batteries` fails in this
  linked worktree** — proven NOT a regression. The branch leaves `pyproject.toml`
  and `skills/_template` byte-identical to main; stashing my edits still fails;
  and a pristine `git archive` of *main itself* fails identically, while the real
  primary checkout passes. The pass depends on relay-init'd template artifacts in
  a real checkout that hatchling's file walk keys off — it can't be exercised
  faithfully from a worktree. **Rest of suite: 541 passed** in the worktree;
  `relay validate --json` clean (66 ok, only pre-existing unrelated-draft warns).
- **Reuse: spool vs `blackboard.append_to_section`** — skipped. The existing
  helper is append-only and non-atomic (`write_text`, `---` separators); the
  spool needs atomic writes + a *drain*. Generalizing the pattern is explicitly
  the sibling ticket's job.
- **Batched events lose milestone GIFs / ticket titles / recurring-error bullet
  detail; automerge-on-merge surfaces up to ~a day later** — these are the
  intended consequences of batching (compact records, one daily post), per the
  ticket's own scope decisions. Flagged here so the PR reviewer can confirm the
  tradeoffs are acceptable rather than fix them silently.
- **`_cc_trailer` mildly duplicates `post()`'s inline cc; per-call
  `digest_spool_path` stat** — out-of-diff / negligible; left alone.

## Step: pr (claude, 2026-06-03)

Pushed `daily-digest-slack` and opened **PR #275**
(https://github.com/FastJVM/relay/pull/275). PR is `MERGEABLE`. **No CI
checks are configured on this repo** (`gh pr checks` → "no checks reported"),
so there is no green/red signal to gate on — verification rests on the local
`pytest` (541 passed) + `relay validate --json` from the implement/self-qa
steps. Bumping to the human review step.
