---
name: dev/checkouts/launch-boundary
description: The launch boundary: how an ordinary ticket launch publishes Coga state, pins control, proves every change and only then moves the invoking checkout to `main` before and after each session, how it refuses, and which launches skip it.
---

# The launch boundary

Part of [dev/checkouts](../SKILL.md).

An ordinary ticket launch prepares the invoking checkout before it reads the
ticket to compose, run `ticket.py`, or activate, and returns it after every
agent session or `ticket.py` phase and at teardown. Where the boundary sits in
dispatch and chaining is owned by [coga/launch](../../../coga/launch/SKILL.md).
On return, reload and validate the on-disk configuration before publishing or
preparing the checkout, so a session's new contexts root is included. Keep the
previous contexts root in that return's publication and cleanup membership
too, so a relocation publishes both sides together. The boundary captures that
root at admission and each successful return; a script's own config reload
before its return callback cannot replace it. Invalid
configuration or a changed Git destination stops the return and withholds the
final sweep, preserving the session's edits. Each time it:

1. **Publishes Coga state.** The ordinary state sweep (`sync_coga_state`)
   lands any dirty file under the Coga roots — tickets, log, recurring
   templates, contexts, skills, workflows, config — that the session or
   script did not publish, plus eligible committed state such as a hand
   commit on local `main` whose control copy has not moved since. Only what
   publication cannot land stays dirty or unpublished.
2. **Pins control.** `git fetch origin main` and pin that commit. Local
   `main` must exist and be equal to or behind it, or carry only commits of
   Coga state whose content is already on the pinned commit (proved commit
   by commit and path by path; [coga/internals/git-refresh](../../../coga/internals/git-refresh/SKILL.md)),
   in which case it is realigned rather than fast-forwarded. A detached HEAD,
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
   and bytes, or, for a `merge=union` file such as `coga/log.md`, every working
   line already on control (union-merging it onto control changes nothing).
   A staged copy must equal HEAD's or the published one. Deletions and both
   sides of a rename count separately. Symlinks, submodules, and mode
   changes refuse even with equal bytes. Ignored files are never candidates;
   one the move would overwrite refuses.
4. **Mutates only after full proof.** The whole plan is re-observed just
   before the first write, and changed evidence refuses. Then proven tracked
   paths are restored to HEAD, proven untracked files removed, HEAD switched
   to `main`, and `main` fast-forwarded to the pinned commit — or realigned
   to it (`read-tree -m -u` and an old-value-guarded `update-ref`), with the
   dropped commits named on stderr and kept in the reflog. The result is
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
non-Git, and remote-less workspaces (no freshness is claimed); bootstrap and
chat targets, including delegated bootstrap sessions; `--prompt-report`; a
launch from the ticket's recorded `worktree:` on its recorded `branch:` (the
recorded human assist and the sandbox clone); a ticket holding a released
megalaunch admission; and megalaunch picks. Recurring periods keep their own
entry gates, which already require control, and get the return half,
including a period that delegates to a bootstrap target: the delegated
session itself is exempt, but its period settles once that session ends. A
refusal there exits 75 so the recurring sweep stops launching templates.
