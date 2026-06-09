---
title: Rewrite Slack messages — titles, prev → new transitions, PR links
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
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
---

## Description

Today's Slack messages are inconsistent across the call sites that post
them: some lack the ticket title, the `bump` posts show where a ticket
*went* but not where it *was*, and the automerge post writes `PR #76` as
plain text instead of a clickable link.

This ticket lands a **pure cosmetic rewrite** — same triggers, same call
sites, same behavior, just better, uniform format strings. No CLI surface
change, no change to `relay/slack.py:post` / `notify`.

> **Ticket rewritten 2026-06-09 (was: "owner suffix, prev → new, PR links").**
> The original spec assumed ticket #2 (split-control-plane-into-relay-mark)
> had not happened and listed ~11 strings. It already has: `relay mark
> active/paused/done`, `relay create`, and `relay retire` are separate
> commands today, so there are ~17 per-ticket message sites, not 11.
> The original "owner suffix" pillar is **dropped**: `post()`/`notify()`
> already prepend `[<project>] [<owner>]` and render the owner as a real
> `<@ID>` ping, so the responsible human is already on every post. Adding an
> in-text `(owner: …)` would just duplicate it. Decision (nick): keep the
> prefix ping, add no suffix. What remains is titles + transitions + the PR
> link + a consistency pass.

## Conventions

These apply to every **per-ticket** Slack post (not the scan-level
`⚠️ recurring scan skipped` summary, which names no single ticket).

- **Owner is the prefix, not the text.** `post()`/`notify()` already emit
  `[<project>] [<owner>]` and ping the owner. Do **not** add an in-text
  `(owner: …)` suffix, and do **not** change `post()`/`notify()`.
- **Title is always present.** `*{slug}* "{title}"` so each post is
  self-contained — you can read one line and know which ticket it is.
- **`→` is a transition.** Use it for step/status moves, and show the prior
  state where there is one: `{prev-step} → {new-step}`, `{prev-step} → done`.
- **`:` introduces the body** after `*{slug}* "{title}"` (the transition,
  reason, or message).
- **`(key: value)` for asides**: `(assignee: …)`, `(step N/total)`. Replaces
  today's ad-hoc `— assignee X` / `— step X` trailers.
- **`—` is reserved for the optional trailing FYI** (`bump --message`, the
  recurring-pause reason, the retire/auto-launch annotations).
- **Actor stays per-site.** Keep each site's existing actor: `cfg.current_user`
  for human-triggered create/mark/launch; `ticket.assignee or cfg.current_user`
  for bump/panic/slack; `script` for `mode: script` steps. No human-vs-agent
  role tagging (deferred — no reliable signal yet).

## Target message set

`{assignee}` falls back to `unassigned`; `{user}` = `cfg.current_user`;
`{finisher}` = `ticket.assignee or cfg.current_user`. The `[project] [owner]`
prefix is added by `post()`/`notify()` and is **not** shown below.

```
✨ {user} created *{slug}* "{title}" in {project}
🚀 {user} created *{slug}* "{title}" in {project} — relay retire (active)
▶️ {user} started *{slug}* "{title}" (assignee: {assignee})
🚀 {user} activated *{slug}* "{title}" (assignee: {assignee}){ — auto on launch}
⏸️ {user} paused *{slug}* "{title}"{ — {reason}}
👉 {finisher} {advanced|rewound} *{slug}* "{title}": {prev-step} → {new-step} (step {N}/{total}){ → assigned to {assignee}}{ — {message}}
🎉 {finisher} finished *{slug}* "{title}": {prev-step} → done{ — {message}}
🔁 recurring scaffolded *{slug}* "{title}" in {project} (assignee: {assignee})
⚠️ recurring scan skipped {N} template{s}
• {name}: {error}
▶️ script started *{slug}* "{title}" (step {S})
👉 script advanced *{slug}* "{title}": {prev-step} → {new-step} (step {N}/{total}){ → assigned to {assignee}}
✅ script completed *{slug}* "{title}"
💥 script failed on *{slug}* "{title}": exit {code} at step {S}
🚨 {panicker} needs help on *{slug}* "{title}": {reason}
💬 {actor} on *{slug}* "{title}": {message}
🎉 *{slug}* "{title}": {prev-step} → done — <{pr-url}|PR #{N}> merged
```

GIFs unchanged: 🎉 done branches get a "done" GIF; 🚨 panic gets a "panic"
GIF.

**Workflow-less collapse.** A ticket with no steps has no `{prev-step}`, so
the `done` posts collapse the transition:

```
🎉 {finisher} finished *{slug}* "{title}"{ — {message}}
🎉 *{slug}* "{title}" finished — <{pr-url}|PR #{N}> merged
```

## Implementation notes

- **`{prev-step}` on bump.** `commands/bump.py` already has `current_idx`
  and `steps`; pass `steps[current_idx - 1]["name"]` as `prev_step_name` and
  `len(steps)` as `total` into `advance_step`. Same for the script-advance
  path in `launch_script.py`.
- **`{prev-step}` on done.** `mark_done` pops `step`, so read the prior step
  name from `ticket.step` *before* the pop and thread it in (None ⇒ collapse).
  Both `mark done` (commands/mark.py) and automerge (`automerge.py`) build the
  `slack_text`, so the prev-step + collapse logic lives at those call sites.
- **PR link on automerge.** `automerge.py` already has the URL (`_read_pr_url`)
  and `pr_label`. Emit `<{url}|PR #{N}>` (Slack link syntax) instead of the
  bare `PR #N`.
- **Title on the three sites missing it:** `bump` (#8), `script advanced`,
  and the `slack` FYI all need `"{title}"` added after `*{slug}*`.
- **Don't drop or rename any call site.** Same triggers, same posts; only the
  strings change. `post()`/`notify()` and the stdout-echo-then-post order are
  untouched.

## Files likely touched

- `src/relay/bump.py` (thread `prev_step_name` + `total` into `advance_step`)
- `src/relay/commands/bump.py` (compute prev-step + total; add title)
- `src/relay/mark.py` (thread prev-step into `mark_done`)
- `src/relay/commands/mark.py` (reformat active/paused; done prev → done)
- `src/relay/commands/launch.py` (reformat started + activated posts)
- `src/relay/commands/launch_script.py` (started/advanced/done/failed; title; prev → new)
- `src/relay/commands/panic.py` (reformat; `:` before reason, drop quotes)
- `src/relay/commands/recurring.py` (reformat scaffold + pause posts)
- `src/relay/commands/slack.py` (add title)
- `src/relay/commands/create.py` (normalize)
- `src/relay/commands/retire.py` (normalize)
- `src/relay/automerge.py` (prev → done; `<url|PR #N>` link)
- `tests/`

## Tests

- New `tests/test_slack_messages.py` (or extend module tests) snapshotting
  each format with mocked actor / ticket / steps / PR data.
- Cover the `unassigned` assignee branch.
- Cover the workflow-less `done` collapse on both `mark done` and automerge.
- Cover the `{prev → new}` transition on bump.

## Out of scope

- Changing `post()`/`notify()` (prefix, ping, digest spool) — untouched.
- Any in-text owner suffix (dropped — see Description).
- Adding/removing commands or changing launch/bump behavior (ticket #2 work
  that already partly landed; not this ticket).
- Human-vs-agent role tagging (deferred — no reliable signal).

## Why now

Surfaced during a chat orient session reviewing the Slack message strings
end-to-end. Failure modes today: (1) several posts omit the title, so a Slack
line isn't self-contained; (2) `bump` shows the new step but not the prior
one — you see where the ticket went, not the transition; (3) the automerge
post writes the PR as plain text instead of a clickable link. All small,
contained legibility fixes.
