---
title: Auto-bump tickets when their PR merges
status: done
mode: interactive
owner: nick
assignee: claude1
contexts:
- relay/codebase
- relay/architecture
- dev/code
---

## Description

Today every step transition is a manual `relay bump`. That's fine
mid-task, but the *last* bump — the one that flips a review-step
ticket to `done` after its PR merges — is pure ceremony: it just
records "the merge happened." Humans (and agents) skip it routinely.
Symptom: tickets sit at `step: 2 (review), status: active` long after
their PRs landed in main. The diagnose-slack ticket itself was an
example — bump only ran because the agent did it explicitly post-merge
on a hand-launched session.

We want: when a ticket's PR merges, its bump fires automatically
(advancing review → done, posting to Slack, releasing the lock).

## Shape (sketch — to nail down in design step)

Three plausible mechanisms, not mutually exclusive:

- **Local `post-merge` git hook.** Fires when the developer pulls
  main. Walk active review-step tickets; for each, check whether its
  branch was merged in the just-pulled commits and bump it. Pro: zero
  infra, fits relay's local-first posture, no new tokens. Con: only
  fires on the machine that pulls — if a teammate merges and the
  original assignee never pulls, nothing happens.
- **`relay status` opportunistic check.** When status runs (humans run
  it often), look up `gh pr view` for each active review-step ticket;
  if merged, bump (or at least flag for the human). Pro: covers the
  "teammate merged, I'm just checking in" case. Con: needs `gh`
  available + authenticated; introduces a network dep on a previously
  fast command.
- **GitHub Action.** On `pull_request.closed && merged`, the action
  commits the bump (ticket frontmatter + log line) directly to main.
  Pro: fires once for everyone, no client setup. Con: requires write
  access from CI to main, feels heavier than the local-first style.

Suggested first cut: **local hook + status fallback**. The hook
covers the active-developer case (90% of merges, since whoever
merges typically pulls); status covers the long tail. Skip the
GitHub Action unless we hit an actual gap.

## Linking ticket → PR

Whichever mechanism fires the bump, it needs to know which PR
belongs to which ticket. Today the link is implicit: branch name ==
ticket slug, by convention from `code/implement-and-pr`. That falls
apart fast — a single PR can bundle changes for two tickets, an
agent can pick a different branch name, the slug can be truncated.
This very PR (`bump-task-positional-and-auto-bump-ticket`) already
breaks the convention.

The fix is to make the link **explicit and recorded by the agent**:
the branch name (and the PR URL once opened) goes into the
blackboard in a known shape. Any auto-bump mechanism reads that, no
inference needed.

Concrete shape: a small `## Dev` section on the blackboard with one
or two named lines, e.g.

```
## Dev
branch: bump-task-positional-and-auto-bump-ticket
pr: https://github.com/FastJVM/relay/pull/70
```

This belongs in a **`dev/` context** that code-style tickets attach
(parallel to the existing `relay/*` contexts). The context teaches
the agent the convention; ticket authors opt in by listing it. Then
the same convention is reused by anything that needs the link
(auto-bump, retro generation, status views).

Out of scope here, but worth filing alongside: a follow-up ticket to
**create the `dev/` context** with this convention written down.
Without that context, agents won't reliably populate the section.

## Open questions

- **What Slack message fires?** Same "🎉 finished" template `bump`
  already posts? Or something distinct ("auto-bumped on merge of
  PR #N") so the team knows it wasn't a human action?
- **Does the bump get attributed to a person or to a bot?** The
  current bump uses `cfg.current_user`. For a hook-driven bump, that's
  whoever just `git pull`-ed. For a status-driven bump, same. For a
  GitHub Action, it'd be a bot identity — different shape entirely.
- **What about non-review-step tickets?** A merge could in principle
  imply earlier steps are done (e.g. for a single-step workflow), but
  scoping v1 to `step: review → done` is simpler and matches 95% of
  cases.
- **Idempotency.** If both the hook and `relay status` see the same
  merge before either has bumped, we don't want a double-bump. Cheap
  guard: re-read ticket status, skip if already `done`.

## Out of scope

- Auto-bumping intermediate steps (e.g. `implement → review`) on PR
  *open*. That belongs to the agent, not to the merge event.
- A general PR-state-tracking system. The ask here is narrow:
  detect merge → bump.
- Replacing manual `relay bump` everywhere. It stays the primary
  interface; this is just the "last bump after merge" automation.

## Why now

Came up while shipping the diagnose-slack-notifications ticket
(PR #69). Nick noted that catching merge → done automatically would
have saved the manual bump, and is the natural next step now that
the prompt edit makes earlier bumps more reliable.
