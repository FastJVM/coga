---
title: Rewrite Slack messages — owner suffix, prev → new transitions, PR links
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/codebase
- relay/architecture
- dev/code
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
step: 1 (implement)
---

## Description

Today's Slack messages from `relay launch / bump / panic / slack /
recurring / automerge / launch_script` are inconsistent: missing the
human owner, no actor or title in some, no transition info on bump,
no PR link on automerge.

This ticket lands a **pure cosmetic rewrite** — same triggers, same
call sites, same behavior, just better format strings. No CLI surface
change; that's ticket #2 (split-control-plane-into-relay-mark).

After this ticket: messages on the wire are clearer, but `relay launch`
still flips status, `relay bump` still marks done on the final step,
etc. Those branches stay; #2 will retire some of them.

## Conventions

- **Always include `(owner: {owner})`** on per-ticket messages, where
  `{owner}` = `ticket.owner if set else "unassigned"`.
- **`(cc {owner})`** instead of `(owner: …)` on the two alert messages
  (`panic`, `script failed`) — those notify, not just FYI.
- **No human/agent role tagging yet** — the code can't currently tell
  reliably whether the caller is a human or an agent. Defer until we
  decide on a signal (env var, explicit flag, etc.). Use the bare actor
  name for now: `actor = ticket.assignee or cfg.current_user`.
- Title in `"…"` always after `*{slug}*` so each post is self-contained.
- `(key: value)` for parenthetical asides; `— ` reserved for the optional
  FYI suffix; `→` for state transitions.

## Locked message set

```
✨ {actor} scaffolded *{slug}* "{title}" in {project}{ → {assignee}} (owner: {owner|unassigned})
🚀 {actor} activated *{slug}* "{title}" (owner: {owner|unassigned})
👉 {actor} advanced *{slug}* "{title}": {prev-step-name} → {new-step-name} (step {N}/{total}){ — {message}} (owner: {owner|unassigned})
🎉 {actor} finished *{slug}* "{title}": {prev-step-name} → done{ — {message}} (owner: {owner|unassigned})
🎉 *{slug}* "{title}": {prev-step-name} → done — <{pr-url}|PR #{N}> merged (owner: {owner|unassigned})
🚨 {actor} stuck on *{slug}* "{title}": {reason} (cc {owner|unassigned})
💬 {actor} on *{slug}* "{title}": {message} (owner: {owner|unassigned})
🔁 recurring scaffolded *{slug}* "{title}" in {project}{ → {assignee}} (owner: {owner|unassigned})
⚠️ recurring check skipped {N} template{s}
• {name}: {error}
💥 script failed on *{slug}* "{title}" — exit {code} at step {N} ({step-name}) (cc {owner|unassigned})
```

GIFs unchanged: 🎉 (both branches) gets a "done" GIF; 🚨 gets a
"panic" GIF.

For workflow-less tickets (no steps), bump-to-done collapses the
prev → done part:

```
🎉 {actor} finished *{slug}* "{title}"{ — {message}} (owner: {owner|unassigned})
```

Same for automerge on a workflow-less ticket:

```
🎉 *{slug}* "{title}" finished — <{pr-url}|PR #{N}> merged (owner: {owner|unassigned})
```

## Implementation notes

- **Owner helper.** `def fmt_owner(ticket): return ticket.owner or "unassigned"`.
  Place in `relay/format.py` (new) or extend `relay/ticket.py`. Used
  literally as `(owner: {fmt_owner(ticket)})` and `(cc {fmt_owner(ticket)})`.
- **Bump needs prev-step name + total.** `commands/bump.py` already
  computes `current_idx` and reads `steps`; pass `steps[current_idx - 1]["name"]`
  as `prev_step_name` and `len(steps)` as `total` into `advance_step` /
  `mark_done` so the formatter has them. Extend the kwargs on both.
- **Automerge needs the PR URL.** `automerge.py` already reads `pr_label`
  ("PR #76") and the URL via `_read_pr_url`. Pass both through to
  `mark_done` so the formatter can emit `<{url}|PR #{N}>` (Slack's link
  syntax).
- **Don't drop or rename any call sites.** All today's posts continue
  firing from the same triggers; only the strings change. The two posts
  that go away in #2 (`🚀 activated`, `✨ scaffolded` from launch.py)
  stay here, just reformatted.
- **Order of operations stays:** stdout echo first, Slack post second.
  The slack helper (`relay/slack.py:post`) doesn't change.

## Tests

- New `tests/test_slack_messages.py` (or extend existing module tests)
  snapshot-asserting each format with mocked actor / ticket / owner /
  steps / PR data.
- Cover the `unassigned` branch (ticket.owner == None).
- Cover the workflow-less collapse on bump-to-done and automerge-done.
- Cover the bump message containing `{prev → new}` correctly.

## Files likely touched

- `src/relay/bump.py` (extend `mark_done` / `advance_step` kwargs)
- `src/relay/commands/bump.py` (compute and pass prev-step name + total)
- `src/relay/commands/launch.py` (reformat scaffold + activate posts)
- `src/relay/commands/launch_script.py` (reformat fail post; include step name)
- `src/relay/commands/panic.py` (reformat panic; drop quotes around reason)
- `src/relay/commands/recurring.py` (reformat both posts)
- `src/relay/commands/slack.py` (reformat manual FYI)
- `src/relay/automerge.py` (reformat + add PR URL link)
- `src/relay/format.py` or `src/relay/ticket.py` (`fmt_owner` helper)
- `tests/`

## Out of scope

- Adding `relay mark` or any new commands (ticket #2)
- Changing `relay launch` / `relay bump` behavior (ticket #2)
- Decoupling `relay create` from the bootstrap factory (ticket #2)
- Human vs agent role tagging (deferred, no current reliable signal)
- Aliases like `relay activate` (consistency-first, no aliases)

## Why now

Surfaced during a chat orient session reviewing the 11 Slack message
strings end-to-end. Two clear failure modes today:
1. You can't tell from a Slack post who the responsible human is
   (owner is buried in the ticket file).
2. Bump messages tell you where the ticket *went* but not where it
   *was* — you can't see the transition, only the new state.

Fixing the strings is small, contained, and improves the team's
real-time legibility before the bigger CLI redesign in #2.
