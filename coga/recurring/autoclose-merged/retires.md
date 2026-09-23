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

- `adjudicate-parked-and-active-tickets-whose-premise` — branch `adjudicate-moved-premises`, worktree `/home/n/Code/claude/coga-adjudicate-moved-premises`, recorded `2026-09-18`
- `agent-usage-report` — branch `usage-report`, worktree `/home/n/Code/codex/coga-usage-report`, recorded `2026-09-22`
- `cleanup/quiet-the-first-run-noise-from-recurring-jobs-and` — branch `quiet-first-run`, worktree `/home/n/Code/codex/coga`, recorded `2026-09-22`
- `document-the-remedy-for-a-bloated-blackboard-sibli` — branch `bloated-blackboard-remedy`, worktree `/home/n/Code/claude/coga-bloated-blackboard-remedy`, recorded `2026-09-22`
- `installer-managed-skills-the-local-adaptation-guar` — branch `gh-backed-readonly-context`, worktree `/home/n/Code/coga`, recorded `2026-09-22`
- `persist-autoclose-retire-follow-ups` — branch `autoclose-retire-worklist`, worktree `/home/n/Code/claude/coga-autoclose-retire-worklist`, recorded `2026-09-18`
- `record-or-clear-the-standing-repo-wide-coga-valida` — branch `validate-baseline`, worktree `/home/n/Code/claude/coga-validate-baseline`, recorded `2026-09-18`
- `reuse-the-existing-control-worktree-for-recurring` — branch `recurring-control-worktree`, worktree `/home/n/Code/codex/coga-recurring-control-worktree`, recorded `2026-09-22`
- `the-period-task-context-never-covers-the-determini` — branch `period-task-recipe-firing`, worktree `/home/n/Code/claude/coga-period-task-recipe-firing`, recorded `2026-09-18`
