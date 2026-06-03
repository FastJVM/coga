---
title: stop overloading relay slack
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/sync
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Every state-changing relay command posts to Slack the moment it happens
(`relay draft`, `bump`, `mark active/paused/done`, `retire`, automerge,
recurring scaffolds). Across several projects and many tickets sharing one
channel, the feed becomes high-volume noise. Humans tune it out — which
defeats the whole point of Slack as the human↔agent sync point.

**Goal:** collapse the routine real-time chatter into **one digest per day,
organized per project and per person**, while keeping genuinely urgent
events live so a stuck agent or a failure never waits a day to be seen.

### Decisions (from authoring, 2026-06-02)

1. **Scope — batch the routine, keep urgent live.**
   Batched into the digest: `draft`/`create`, `bump`, `mark`
   (active/paused/done), `retire`, automerge done, recurring scaffolded/
   skipped.
   Still posts immediately: `relay panic` (agent stuck), `mode: script`
   step failures, and the manual `relay slack` FYI (an intentional human
   broadcast — batching it would surprise the sender).

2. **Delivery — one channel message, sectioned.** A single daily post to
   the existing channel, grouped per project then per person, with `<@ID>`
   mentions (and watcher cc) exactly as today's `_mention` does. **Webhook
   only — no Slack bot token, no new secret, no DMs.** People with no mapped
   member ID are named but not pinged (unchanged behavior).

3. **The digest IS a recurring ticket (Nick, stepping in).** Don't bolt on a
   side mechanism. Create a `recurring/digest/` ticket. **Its own
   `blackboard.md` is the spool:** batchable events append to it as they
   happen, and **launching the ticket (via the normal `relay recurring`
   scan) renders + posts the digest and empties the blackboard.** Schedule
   lives in the template's frontmatter (`schedule:` cron), so the cadence is
   reproducible from the repo — no external cron, no new side-channel.

### Design sketch — the spool *is* a (visible) blackboard

Two hard constraints (Nick, 2026-06-02):
- **No hidden state.** A `.digest/spool.md` dotfile is exactly the opaque
  state Relay forbids. A spool is fine — but it must be a real, visible,
  git-tracked **blackboard**, never a dotfile.
- **Don't rely on git.** No `git log` scan to reconstruct the day's events
  — it's too slow on a busy task repo. The event must be captured the
  moment it happens.

The spool is the `recurring/digest/` ticket's own blackboard, and the flow
is a **producer → blackboard → consumer** pipeline:

#### Phase 1 — Producer (events → blackboard)

- **Batchable events append to `recurring/digest/blackboard.md`.** Instead
  of firing the webhook, a batchable event appends **one JSONL record** to
  the digest ticket's blackboard (under a `## Spool (pending)` section).
  One self-describing object per line:

  ```
  {"ts":"2026-06-02T14:03","project":"relay","owner":"nick",
   "ticket":"stop-overloading-relay-slack","kind":"bump",
   "detail":"→ step 3 (pr)","watchers":["bob"]}
  ```

  JSONL chosen over a table/delimited line for robustness — `detail` can
  hold any text (pipes, emoji, arrows) with no escaping, and each record is
  self-contained. Still plain text in a visible blackboard (not a dotfile),
  so it satisfies "no hidden state."
- **Concurrent-safe append.** Multiple agents/commands produce at once, so
  the append takes Relay's existing file lock — records never interleave or
  clobber.
- **Captured at event time, so deletion is safe.** The record lands when the
  event fires, so a task done-and-deleted later the same day is already
  recorded — no git, no re-scan, nothing lost.
- Task `log.md` lines are written as today, unchanged; the digest does not
  depend on scanning them. Urgent events stay live, untouched.

#### Phase 2 — Consumer (blackboard → Slack)

- **Launching the digest ticket flushes it.** When `relay recurring` fires
  the digest ticket on schedule, its `mode: script` step runs `relay digest`,
  which under the same lock: reads the pending JSONL records, groups
  **project → person → ticket**, renders one message, posts via the webhook,
  **then empties the spool section** back to its seed. Idempotent: an empty
  spool is a no-op. Holding the lock across read-and-empty means records
  produced mid-flush aren't dropped.
- **Report layout — full trail per ticket.** Under each person, each ticket
  lists the day's events in order (not just the final state), so the digest
  is a once-a-day replay rather than only a snapshot:

  ```
  [relay] 📋 Daily digest · 2026-06-02

  @nick
   • stop-overloading-relay-slack
       active → in-progress → PR #271 (cc @bob)
   • fix-flaky: done ✅

  @alice
   • redesign-onboarding: draft → active → review
  ```

  Owner pinged as `<@ID>`, watchers cc'd, names without a mapped member ID
  rendered plain — exactly as `slack._mention` does today.

### Touchpoints

- `src/relay/slack.py` — split into live-post vs append-to-digest-
  blackboard; classify each call site urgent/batchable. Batchable events
  write their `log.md` line as today *and* append a line to the visible
  digest blackboard, instead of firing the webhook.
- Call sites to reroute to spool: `commands/create.py`, `bump.py`,
  `mark.py`, `commands/retire.py`, `commands/recurring.py`.
  Call sites left live: `commands/panic.py`, `commands/launch_script.py`,
  `commands/slack.py`.
- New `recurring/digest/` ticket (`mode: script`, daily `schedule:`). Its
  launch body runs the flush — read blackboard → group → post → empty.
- New `src/relay/spool.py` — reusable lock-guarded `append_record` /
  `drain` over a blackboard's `## Spool (pending)` section (JSONL). The
  generalized primitive (see "Generalize" below); `slack.py` and `digest.py`
  are its first callers.
- New: `src/relay/commands/digest.py` (the flush logic the digest ticket's
  script step calls) + a grouping/render module; wire into `cli.py`.
- Config: `relay.toml` `[slack]` — opt-in/out flag + digest schedule.
- **Context (same PR, required):** revise
  `relay-os/contexts/relay/sync/SKILL.md` "Slack — the team sync point" to
  describe the two-tier model (live urgent + daily digest). Mirror to the
  packaged copy under
  `src/relay/resources/templates/relay-os/contexts/...` if present.
- Tests: `tests/test_digest.py` (grouping, collapse, empty-spool no-op,
  urgent-bypasses-spool); update fixtures in `example/relay-os/`.

### Generalize: blackboard producer/consumer pattern

This digest is the first concrete instance of a reusable shape — a durable,
human-visible, lock-guarded queue on a blackboard, drained by a recurring
consumer. **Naming and documenting that pattern is split into its own
ticket: `document-the-blackboard-producer-consumer-pattern`.**

For this ticket: build the producer/consumer helpers as a small reusable
primitive (`src/relay/spool.py`: lock-guarded `append_record` / `drain`),
not bespoke to Slack — the digest is its proving ground. Keep it minimal;
the pattern write-up and any broader surface belong to the sibling ticket.

### Naming: Slack is one channel of a notification system

Slack is not the abstraction — it's the first **channel**. "Digest" already
implies delivery-agnostic; email (and others) are obvious future channels.
So the delivery layer should be named for what it is:

- Rename `src/relay/slack.py` → a `notification` module (Slack as the first
  channel backend); `[slack]` config → `[notification]` (or
  `[notification.slack]`) with back-compat. `_mention`, webhook posting,
  and the digest renderer become Slack-channel specifics behind a
  channel-agnostic `notify(...)` / digest-delivery interface.
- The digest consumer renders a channel-neutral report, then hands it to the
  configured channel(s) — so adding email later is a new backend, not a
  rewrite.

This rename is broader than the digest (it touches every `post()` call
site). Tracked separately — see the rename ticket — but the digest should
build against the notification interface, not `slack.post`, from the start.

### Non-goals

- Slack bot token / real per-person DMs (revisit only if channel sections
  prove insufficient).
- Changing the git sync layer or Slack's crash-loud failure policy.
- Cross-repo aggregation into one digest — each repo digests its own
  project; a shared channel is disambiguated by the per-project sections.

### Open questions (resolve during implementation)

- **Period-ledger interaction (minor).** `recurring.py`'s `_record_run`
  appends a `scaffolded <slug>` line to the digest template's `blackboard.md`
  — the same file we use as the spool. Re-reading the logic this is benign:
  `_period_already_scaffolded` is consulted only when the *current* period's
  task directory is missing, so emptying past lines on flush doesn't trigger
  re-scaffolding. Just confirm during impl, and keep the flush scoped to the
  spool section if we mix ledger + event lines.
- Digest ticket blackboard line format, and whether the flush truncates or
  keeps a dated `## Sent` history.
- Empty-day behavior: skip silently (default) vs a one-line "quiet day."

### Verification

- `python -m pytest`
- `relay validate --json`
- Manual: spool a few events, run `relay digest` with the webhook disabled
  (`[slack].enabled = false`) and inspect the rendered message on stderr;
  confirm `panic` still posts live.

## Context

Current behavioral contract: `relay-os/contexts/relay/sync/SKILL.md`
(§"Slack — the team sync point") — this ticket revises it.
Live poster: `src/relay/slack.py`. Recurring mechanism (trigger host):
`src/relay/recurring.py`.
