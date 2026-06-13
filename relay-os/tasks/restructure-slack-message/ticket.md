---
title: restructure slack message
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/sync
- relay/recurring
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
---

## Description

Restructure the daily Slack digest from a chronological replay of every
state-change event into an outcome-focused summary: which tickets were
**done** that day (one line each, linked to their merged PR), plus which
other commits/PRs landed on `main` without a ticket. Fold the
`relay-dev-update` recurring task's job (daily commit summary) into this
digest and retire that recurring task, so the team gets **one** daily post
instead of two overlapping ones.

At the same time, cut the noise at the source: routine lifecycle events
(`draft`, `active`, `bump`, `paused`, `retire`) stop being spooled or
broadcast at all. The per-task `log.md` already keeps the full audit trail;
Slack only needs outcomes. `panic` keeps its existing live-post path
untouched (emergencies post immediately, never wait for the digest).

Done looks like: `relay digest` posts a message shaped roughly as

```
📋 Daily digest · 2026-06-10 · relay
Done:
 • slack-webhook-is-env-only… — PR #330 merged ✅
Also merged (no ticket):
 • abc1234 Fix typo in compose docstring
```

with no post at all on a day with nothing done and nothing merged, and no
more `draft`/`active`/`bump` lines anywhere in Slack.

## Context

- Core code: `src/relay/slack.py` (`notify`, `render_digest`),
  `src/relay/commands/digest.py` (`run_digest`), and the `notify()` call
  sites in `bump.py`, `mark.py`, `commands/create.py`, `commands/retire.py`,
  `commands/recurring.py`. Update the `slack.py` module docstring — it
  documents the two-tier model being changed here.
- Spool policy after this change: only `done` (and `recurring-error`) events
  are spooled. The other kinds stop calling `notify()` entirely — no spool,
  no live fallback. Edge case to handle deliberately: `relay bump --message
  "<FYI>"` currently rides on the bump broadcast; an explicit `--message`
  should still reach Slack (live post or spool — implementer's call), only
  message-less bumps go silent.
- "Also merged" needs a git high-water mark: store `last_commit` state in
  the `recurring/digest/` template blackboard, same pattern as
  `relay-dev-update`'s `### Dev Update State` (persistent state lives on the
  parent recurring task's blackboard, not the period task's). First run
  falls back to last 24h. Attribute commits to done tickets by matching PR
  numbers — automerge `done` records carry "PR #N" in `detail`, and merge
  commits on `main` carry `(#N)` in their subjects; leftovers go in the
  "Also merged (no ticket)" section. Keep `relay digest` `mode: script`
  (deterministic, no agent run).
- **Filter relay's own state-sync commits out of "Also merged"**: relay
  pushes `Sync task state: …` and `Ticket: <slug> — <status>` commits to
  `main` constantly, with no `(#N)`. Without a subject-pattern filter they
  flood the section and recreate the lifecycle noise this ticket exists to
  kill.
- Done records without a PR: manual `relay mark done` and script-mode done
  details carry no PR number (only automerge does). A PR-less done ticket
  still gets its "Done" line — just without the PR link.
- `run_digest` currently early-returns on an empty spool. New rule: empty
  spool no longer implies no post — run the git scan regardless; skip the
  post only when there are no done tickets AND no (post-filter) new commits.
  Decide the fetch semantics deliberately: comparing against `origin/main`
  needs a `git fetch` inside a `mode: script` run (a new network failure
  mode), vs. local `main` which can lag.
- Retiring `relay-dev-update`: remove `relay-os/recurring/relay-dev-update/`
  and the `dev-update/post` workflow if nothing else references it.
- Template copies: of the files this ticket touches, only the `relay/sync`
  context has a packaged copy (at
  `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/sync/`) —
  keep that one in sync. The digest workflow/skill and the recurring
  templates are deliberately *not* packaged; do not add them to the
  packaged tree or to `example/relay-os/`. Update the `relay/sync` context
  body: its two-tier description (live vs. batched) must reflect that
  routine lifecycle events are now silent, not batched.
- Out of scope, decided during bootstrap: per-developer *delivery* (DM or
  per-dev channel digests) — impossible with a single incoming webhook,
  needs multiple webhooks or a bot token. The broader idea (a per-person
  "inbox" of things needing your attention — reviews waiting, stalled runs)
  is a separate future ticket; see blackboard `## Proposals`. All `paused`
  events go silent here, including sweep-paused stalled runs — that signal
  belongs to the inbox ticket. Per-developer *grouping* inside the shared
  digest already exists (owner sections) and should be preserved in the new
  "Done" rendering. Also out of scope: actually driving `relay recurring`
  daily (cron) — separate ticket.
