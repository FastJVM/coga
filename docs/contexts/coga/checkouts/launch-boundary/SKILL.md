---
name: coga/checkouts/launch-boundary
description: Preparation and return to current control for ordinary tickets and chat/orientation, refusal recovery, and exemptions.
---

# The launch boundary

Part of [coga/checkouts](../SKILL.md).

## Preparation and return

The native Windows agent-session preflight runs before this boundary and
does not publish or prepare a checkout. Its script admission and refusal
contract is owned by [coga/launch](../../launch/SKILL.md#phases-and-routing).

An ordinary ticket launch and a direct `bootstrap/orient` launch (`coga chat`)
prepare the invoking checkout before reading the ticket to compose, run
`ticket.py`, or activate, and return it after every
agent session or `ticket.py` phase and at teardown. Where the boundary sits in
dispatch and chaining is owned by [coga/launch](../../launch/SKILL.md).
On return, the on-disk configuration is reloaded and validated first, so a
session that moved the contexts root publishes both the old and new roots.
Invalid configuration or a changed Git destination stops the return and
withholds the final sweep, preserving the session's edits. Each time it:

1. **Publishes Coga state.** The ordinary state sweep
   lands any dirty file under the Coga roots — tickets, log, recurring
   templates, contexts, skills, workflows, config — that the session or
   script did not publish, plus eligible committed state such as a hand
   commit on local `main` whose control copy has not moved since. Only what
   publication cannot land stays dirty or unpublished.
2. **Pins control.** Under the checkout's state lock, `git fetch origin main`
   and pin that commit, re-pinning a bounded number of times when a sibling
   checkout's publish moves it. Local `main` must exist and be equal to or
   behind the pin, or carry only commits of Coga state whose content is
   already on the pinned commit, in which case it is realigned rather than
   fast-forwarded. A detached HEAD,
   a merge, rebase, cherry-pick, revert, or bisect in progress, `main` checked
   out in another worktree, or any other ahead or diverged `main` refuses.
   Remedies: for local commits of Coga state not yet on control, run
   `git pull --rebase --autostash origin main` on `main` (switch to `main`
   first from a feature branch) and retry the command; for local commits
   touching anything else, reconcile them (`git pull --rebase --autostash
   origin main` and push); otherwise `git worktree remove <path>`, or finish
   or abort the operation.
3. **Proves every change.** Staged, tracked, and untracked changes anywhere
   in the checkout are examined. Only files under the Coga roots may be
   discarded, and only when already on the pinned `origin/main`: the same existence, file mode,
   and bytes; union files must merge without changing control. The audit log
   instead uses event-aware reconciliation: a missing expired source event
   requires exact reachable-history proof before it can be discarded.
   Pending guarded log mutations refuse checkout return until recovered.
   A staged copy must equal HEAD's or the published one. Deletions and both
   sides of a rename count separately. Symlinks, submodules, and mode
   changes refuse even with equal bytes. Ignored files are never candidates;
   one the move would overwrite refuses.
4. **Mutates only after full proof.** The whole plan is re-observed just
   before the first write; changed evidence refuses. Then proven tracked
   paths are restored to HEAD, proven untracked files removed, HEAD switched
   to `main`, and `main` fast-forwarded or realigned to the pinned commit,
   with any dropped commits named on stderr and kept in the reflog. The result is
   verified clean at that commit. It never stashes, rebases, resets hard,
   force-switches, commits, deletes a branch, or pushes code. The feature
   branch stays.

An entry refusal names the blocking paths or branch and the remedy, starts no
work, changes no checkout contents or local ref, and exits 75 so the outer
sweep does not publish the rejected dirt. A refusal after a session is a
prominent warning: the remaining work and the session's own result stand,
chaining stops, and that command's end sweep is withheld. An unexpected Git
or I/O failure after mutation began reports where it stopped; nothing is
rolled back. A killed launch is recovered by the next entry.

The boundary is skipped, and the checkout left as it is, for Git-disabled,
non-Git, and remote-less workspaces (no freshness is claimed); bootstrap targets
other than direct `bootstrap/orient`, including all delegated bootstrap
sessions; `--prompt-report`; a
launch from the ticket's recorded `worktree:` on its recorded `branch:` (the
recorded human assist and the sandbox clone); a ticket holding a released
megalaunch admission; and megalaunch picks. Recurring periods keep their own
entry gates, which already require control, and get the return half,
including a period that delegates to a bootstrap target: the delegated
session itself is exempt, but its period settles once that session ends. A
refusal there exits 75 so the recurring sweep stops launching templates.

Branch preparation ([coga/checkouts](../SKILL.md#in-a-launched-session)) runs
only inside an ordinary ticket launch whose entry prepared control, before
each spawn; its refusals exit 75 the same way. Recurring periods and their
delegated sessions, megalaunch picks, exempt launches, and `--prompt-report`
get no branch setup; a composed prompt then states that no preparation was
supplied, or what launch observed instead.

## Checkout recovery

When preparation refuses, or an agent finds an unexpected starting checkout,
investigate before changing it. A stale branch's ticket is not current task
state, and a merged PR does not establish that uncommitted edits are finished.

1. Inspect HEAD, staged and unstaged diffs, and untracked files. Identify the
   branch's associated ticket from its recorded `branch:` or `pr:`, commit
   history, and PR metadata. Do not infer a ticket solely from the branch name;
   report an unknown or ambiguous association.
2. Fetch the configured remote control branch and read that revision's ticket
   without replacing local files. Check the linked PR's current state and
   merge evidence. Report the ticket, current lifecycle status, and whether
   its work merged; distinguish that from any stale local status. If access
   prevents verification, report the uncertainty rather than calling it done.
3. Account for uncommitted changes separately. Compare them with current
   control and the associated branch, preserving unique work. State which
   changes are already incorporated, which remain needed, and whose purpose
   or ownership is unknown. A stash preserves bytes but does not answer these
   questions; never automatically stash, reset, or discard edits to clear the
   refusal. Do not switch another task's occupied checkout.
4. Explain the proposed recovery and its effect on remaining work. Resolve
   unclear intent, ownership, or permissions through session conduct before
   mutation; then perform the authorized recovery and retry the normal launch.
   Never mark a ticket done or replay a workflow transition merely because
   its PR merged. Launch itself does not query GitHub or make these judgments.

The base prompt links this procedure for agent-led investigation; launch's
refusal prints the key checks before exiting 75 without spawning an agent.
Direct chat gets the same guarantees, with no automatic stash or recovery
bypass; its occupancy guard is in [coga/checkouts/chat](../chat/SKILL.md).
