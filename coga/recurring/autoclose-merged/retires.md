# Stranded `coga retire` follow-ups

Durable worklist of auto-closed tickets whose feature checkout still exists.
The autoclose sweep records follow-ups here rather than in its period task
under `coga/tasks/recurring/`, which `coga recurring` deletes at the start of
the next period.

Every entry means the same thing: run `coga retire <slug>` to dispose of the
recorded worktree and branch. Autoclose only ever names the follow-up; retire
owns the safety proofs. Entries are keyed by slug, so a later sweep refreshes
one rather than duplicating it, and an entry is dropped once both its worktree
directory and its local branch are gone. An entry whose ticket no longer
exists — retire preserved the checkout and then deleted the ticket — is still
debt: dispose of the recorded worktree and branch by hand (or let the weekly
branch sweep take the branch) and the entry clears by the same rule.

For the line format and field encoding, see the `coga/autoclose/sweep` skill.

## Follow-ups (open)

- `adjudicate-parked-and-active-tickets-whose-premise` — branch `adjudicate-moved-premises`, worktree `/home/n/Code/claude/coga-adjudicate-moved-premises`, recorded `2026-09-18`
- `cleanup/handle-a-bare-slack-webhook-url-during-empty-repo` — branch `init-bare-slack-env`, worktree `/home/n/Code/claude/coga-init-bare-slack-env`, recorded `2026-09-18`
- `define-the-recipe-reporting-contract-report-durabi` — branch `recipe-reporting-contract`, worktree `/home/n/Code/claude/coga-recipe-reporting-contract`, recorded `2026-09-18`
- `document-when-to-attach-a-large-context-versus-cit` — branch `attach-vs-cite`, worktree `/home/n/Code/claude/coga-attach-vs-cite`, recorded `2026-09-18`
- `persist-autoclose-retire-follow-ups` — branch `autoclose-retire-worklist`, worktree `/home/n/Code/claude/coga-autoclose-retire-worklist`, recorded `2026-09-18`
- `record-dochub-s-why-not-the-api-answer-that-browse` — branch `dochub-api-answer`, worktree `/home/n/Code/claude/coga-dochub-api-answer`, recorded `2026-09-18`
- `record-or-clear-the-standing-repo-wide-coga-valida` — branch `validate-baseline`, worktree `/home/n/Code/claude/coga-validate-baseline`, recorded `2026-09-18`
- `state-which-branch-is-canonical-for-machine-genera` — branch `sync-canonical-policy`, worktree `/home/n/Code/claude/coga-sync-canonical-policy`, recorded `2026-09-18`
- `the-period-task-context-never-covers-the-determini` — branch `period-task-recipe-firing`, worktree `/home/n/Code/claude/coga-period-task-recipe-firing`, recorded `2026-09-18`
- `the-v2-parking-area-premise-check-has-four-holes` — branch `v2-premise-holes`, worktree `/tmp/coga-v2-premise-review.5AX4MD/repo`, recorded `2026-09-18`
