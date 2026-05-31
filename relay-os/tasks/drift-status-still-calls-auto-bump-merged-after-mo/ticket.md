---
title: 'Drift: status still calls auto_bump_merged after move-out-of-status landed'
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Priority: medium. Code and stated direction disagree right now — resolve
the drift before it confuses the next change.

The `move-automerge-out-of-relay-status` ticket is described as landed (the
intent being that `relay status` should be a pure read-only view with no
automerge side-effect), yet `status.py:79` **still calls `auto_bump_merged`**
(opportunistic, `quiet=True`, swallowing `GhError`). So either that ticket did
not fully land, or this working tree predates it. Separately,
`remove-the-post-merge-automerge-git-hook` (draft) plans to delete the
`init`-installed post-merge hook (`init.py:619`) entirely. Net: the shipped
automerge wiring (status side-effect + git hook + launch freshness check +
explicit `relay automerge`) is mid-retreat and the code disagrees with the
direction docs.

Reconcile:
- confirm the intended end state for automerge triggers (almost certainly:
  explicit `relay automerge` + pre-launch freshness check only; no status
  side-effect; hook removed)
- remove the `auto_bump_merged` call from `status.py:79` if status is meant to be
  read-only
- coordinate with `remove-the-post-merge-automerge-git-hook` so the two land
  coherently
- update whichever direction/context doc records the automerge trigger surface

Acceptance: `relay status` has no automerge side-effect (if that is the decided
end state); the set of automerge triggers in code matches the direction doc;
tests updated.

## Context

Code: `src/relay/commands/status.py:79` (the lingering call),
`src/relay/automerge.py` (`auto_bump_merged`), `src/relay/commands/init.py:619`
(hook install). Related tickets: `remove-the-post-merge-automerge-git-hook`,
`move-automerge-out-of-relay-status`.
