---
title: 'Decide the final automerge trigger surface (status side-effect removed in #254)'
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

Priority: medium. Narrow the surface to one decision: which automerge
triggers does Relay ship?

**Done — the `relay status` side-effect.** PR #254 removed the
`auto_bump_merged` call from `status.py`, so `relay status` is now strictly
read-only (no network, no state mutation as a side effect of rendering —
principle 6). Tests assert it; cli/sync contexts, README, and the automerge
docstrings were updated to match. This ticket no longer covers that.

**Open — the rest of the trigger surface.** After #254 the live automerge
triggers are: explicit `relay automerge`, the `init`-installed post-merge git
hook (`init.py`), and the pre-launch freshness check in `relay launch`. The
question that remains is whether that's the intended end state or whether the
hook should also go (see the sibling `remove-the-post-merge-automerge-git-hook`
draft). The hook is being treated as a separate decision from the status fix —
this ticket is the place to settle the whole surface coherently.

Decide and reconcile:
- confirm the intended end state for automerge triggers — candidates: keep
  {explicit + hook + launch freshness}, or drop to {explicit + launch
  freshness} by removing the hook
- coordinate with `remove-the-post-merge-automerge-git-hook` so the hook
  decision and any doc changes land together
- make the direction/context docs (cli, sync, README) match whatever surface
  is chosen

Acceptance: the set of automerge triggers in code matches the direction docs,
the hook's fate is decided (kept or removed, not left ambiguous), and tests
cover the chosen surface.

## Context

Status side-effect already removed — see PR #254
(`Make relay status read-only: drop opportunistic automerge`).

Remaining code: `src/relay/automerge.py` (`auto_bump_merged` / `auto_bump_one`),
`src/relay/commands/init.py` (post-merge hook install),
`src/relay/commands/launch.py` (pre-launch freshness check). Related ticket:
`remove-the-post-merge-automerge-git-hook`.
