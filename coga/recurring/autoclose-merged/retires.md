# Feature checkouts autoclose could not dispose of

Durable worklist of auto-closed tickets whose feature checkout still exists.
The autoclose sweep records follow-ups here rather than in its period task
under `coga/tasks/recurring/`, which `coga recurring` deletes at the start of
the next period.

Every entry is a checkout a safety proof refused. Autoclose disposes of the
recorded worktree and branch itself, under the same proofs `coga retire` runs
(same-repo linked worktree on the recorded branch, locally pristine, no other
live ticket claiming it, no open PR, landed or at the merged PR's exact head);
it re-runs them on every open entry on every run and posts each refusal, with
its reason, to the coga-important Slack channel. An entry therefore stays here
only while a proof keeps refusing it — a dirty worktree, an independent clone,
a branch another live ticket records — and clears on the next run after the
cause is fixed. Run `coga retire <slug>` to see the proofs at first hand.
Entries are keyed by slug, so a later sweep refreshes one rather than
duplicating it, and an entry is dropped once both its worktree directory and
its local branch are gone. An entry whose ticket no longer exists — retire
preserved the checkout and then deleted the ticket — is still walked: the
merge proof then uses the merged PRs for the recorded branch name.

For the line format and field encoding, see the `coga/autoclose/sweep` skill.

## Follow-ups (open)

- `cleanup/quiet-the-first-run-noise-from-recurring-jobs-and` — branch `quiet-first-run`, worktree `/home/n/Code/codex/coga`, recorded `2026-09-22`
- `document-how-to-recover-a-retired-ticket-s-body-fr` — branch `retired-ticket-recovery`, worktree `/home/n/Code/codex/coga`, recorded `2026-09-28`
- `launch-moves-the-checkout-to-main-before-and-after` — branch `launch-normalizes-checkout`, worktree ``, recorded `2026-09-30`
- `make-dream-run-correctly-under-codex` — branch `dream-under-codex`, worktree `/home/n/Code/codex/coga`, recorded `2026-09-28`
- `marketing/fix-installer/linux-clean-install-harness` — branch `linux-clean-install-harness`, worktree ``, recorded `2026-09-30`
- `prevent-parent-ticket-assumptions-during-task-spli` — branch `no-parent-ticket-guidance`, worktree ``, recorded `2026-09-30`
- `record-the-attended-ticket-switch-recipe-launch-do` — branch `attended-ticket-switch-recipe`, worktree ``, recorded `2026-09-30`
- `run-the-landed-branch-sweep-daily-from-autoclose` — branch `daily-autoclose-branches`, worktree `/home/n/Code/codex/coga`, recorded `2026-09-28`
