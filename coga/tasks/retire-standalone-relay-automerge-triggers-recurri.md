---
slug: retire-standalone-relay-automerge-triggers-recurri
title: Retire standalone relay automerge triggers — recurring sweep is sole trigger
status: done
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- coga/sync
- coga/recurring
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

**Depends on `autoclose-merged-recurring-task` landing first** (that ticket
adds the daily recurring sweep). Once the scheduled sweep exists and is
proven, this ticket makes it the **sole** trigger for auto-closing merged
tickets by retiring the other surfaces.

Re-baselined against current `main`: the post-merge git hook is **already
gone** (a prior PR removed it; `init.py` no longer installs one), and `relay
status` already stopped calling the sweep (PR #254). So only **two** live
triggers remain to remove, plus dead artifacts to clean up:

1. **Remove the explicit `relay automerge` CLI command** — its registration in
   `cli.py` and the thin wrapper `src/relay/commands/automerge.py`.
2. **Remove the pre-launch freshness check** in `relay launch` — the
   `auto_bump_one` call in `launch.py`'s freshness block. `auto_bump_one`
   loses its only caller, so drop it too.
3. **Rename the module / public surface** now that the recurring sweep is the
   only consumer: `automerge.py` → e.g. `autoclose.py`, `auto_bump_merged` →
   e.g. `sweep_merged`. The public surface (`auto_bump_merged`, `auto_bump_one`,
   `pr_state`, `parse_pr_url`, `__all__`) has external importers — chase every
   one, including the script skill added by the first ticket.
4. **Clean up dead hook artifacts** — delete the orphaned
   `bootstrap/hooks/post-merge` file and the vestigial `_remove_post_merge_hook`
   migration in `init.py` if it is no longer needed.

## Context

- **Trigger-surface decision (settled):** the recurring daily sweep is the
  *only* path that auto-closes merged tickets. Accepted tradeoff: with the
  launch-freshness check gone, a ticket merged today won't auto-close until the
  next daily run (≤24h lag). That's intentional — one legible trigger over
  several.
- **This ticket settles `drift-status-still-calls-auto-bump-merged-after-mo`**
  (the open "which automerge triggers does Relay ship?" draft) and the related
  `remove-the-post-merge-automerge-git-hook` draft if it still exists. Both are
  partly stale already (they list the hook as live; it isn't). Reconcile/close
  them to reflect the settled end state — this is bookkeeping on
  already-decided drafts, not a fresh decision.
- **Docs/contexts to update in the same PR** (per CLAUDE.md "update the
  matching context when behavior changes"): the `relay/sync` and cli contexts
  and README wherever they describe automerge triggers. Specific drift sites
  flagged on cold review: `relay-os/workflows/code/with-review.md` (its
  `review` step still tells the human to "run `relay automerge` explicitly"),
  and the module docstring in `automerge.py` ("Two callers" — both will be
  gone). Grep `automerge` across `relay-os/`, `src/`, and `README` to catch
  the rest. Keep the live `relay-os/` copy and the packaged
  `src/relay/resources/templates/relay-os/` copy in sync.
- **Tests:** update/replace coverage for the removed `relay automerge` command
  and the launch-freshness side-effect; confirm the recurring sweep path
  (added by the first ticket) still passes after the rename. Run `python -m
  pytest` and `relay validate --json` before opening the PR.
- **Out of scope:** broadening detection beyond automerge's current rule
  (final-step + `pr:` link). That's a separate decision.

## Done when

- [ ] `relay automerge` CLI command removed (`cli.py` + `commands/automerge.py`).
- [ ] Launch-freshness `auto_bump_one` call removed; `auto_bump_one` dropped.
- [ ] Module/public surface renamed; all importers (incl. the recurring sweep
      skill) updated.
- [ ] Dead hook artifacts removed.
- [ ] Docs/contexts/README updated; `with-review.md` review step + module
      docstring no longer reference the command; live + packaged copies synced.
- [ ] `drift-…-auto-bump-merged` (and hook draft) reconciled/closed.
- [ ] `python -m pytest` green and `relay validate --json` clean.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: retire-standalone-automerge-triggers
pr: https://github.com/FastJVM/relay/pull/414

Implemented directly on the primary checkout (no worktree). Peer review
(independent agent) came back clean — zero must-fix findings. Full suite
829 passed / 1 skipped; `relay validate --json` clean (5 pre-existing
unrelated `missing-step` errors).

Open question for owner review: `_remove_post_merge_hook` migration was
**kept** (only messaging updated), not dropped — it still prunes stale
hooks off old installs. See PR description.
