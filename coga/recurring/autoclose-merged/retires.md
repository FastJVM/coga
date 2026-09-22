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
- `attribute-headless-recurring-completions-to-system` — branch `fix/headless-completion-system`, worktree `/tmp/coga-system-completion`, recorded `2026-09-22`
- `automerge/fix-let-a-lot-of-open-craps` — branch `dispose-checkouts`, worktree `/home/n/Code/coga-dispose-checkouts`, recorded `2026-09-22`
- `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r` — branch `resources-pkg-init`, worktree `/home/n/Code/claude/coga-resources-pkg-init`, recorded `2026-09-21`
- `cleanup/handle-a-bare-slack-webhook-url-during-empty-repo` — branch `init-bare-slack-env`, worktree `/home/n/Code/claude/coga-init-bare-slack-env`, recorded `2026-09-18`
- `cleanup/quiet-the-first-run-noise-from-recurring-jobs-and` — branch `quiet-first-run`, worktree `/home/n/Code/codex/coga`, recorded `2026-09-22`
- `correct-the-v2-known-stale-surfaces-table-and-rout` — branch `v2-stale-surfaces`, worktree `/tmp/coga-v2-stale-surfaces`, recorded `2026-09-22`
- `define-the-recipe-reporting-contract-report-durabi` — branch `recipe-reporting-contract`, worktree `/home/n/Code/claude/coga-recipe-reporting-contract`, recorded `2026-09-18`
- `detect-stranded-ticket-writes-across-checkouts` — branch `stranded-ticket-writes`, worktree `/home/n/Code/coga-stranded-ticket-writes`, recorded `2026-09-22`
- `document-how-packaged-contexts-reach-a-repo-and-se` — branch `packaged-context-states`, worktree `/home/n/Code/coga-packaged-context-states`, recorded `2026-09-22`
- `document-the-remedy-for-a-bloated-blackboard-sibli` — branch `bloated-blackboard-remedy`, worktree `/home/n/Code/claude/coga-bloated-blackboard-remedy`, recorded `2026-09-22`
- `document-when-to-attach-a-large-context-versus-cit` — branch `attach-vs-cite`, worktree `/home/n/Code/claude/coga-attach-vs-cite`, recorded `2026-09-18`
- `exclude-superseded-designs-from-launch-prompts` — branch `codex/exclude-superseded-designs`, worktree `/tmp/coga-exclude-superseded-designs`, recorded `2026-09-22`
- `installer-managed-skills-the-local-adaptation-guar` — branch `gh-backed-readonly-context`, worktree `/home/n/Code/coga`, recorded `2026-09-22`
- `make-sure-repo-clietn-don-t-edit-coga` — branch `client-repo-dream`, worktree `/home/n/Code/coga-client-repo-dream`, recorded `2026-09-22`
- `narrative-candidates-md-publishes-log-text-the-own` — branch `remove-narrative-candidates`, worktree `/home/n/Code/coga-remove-narrative-candidates`, recorded `2026-09-22`
- `packaged-code-workflows-never-name-coga-retire-as` — branch `review-closing-act`, worktree `/home/n/Code/claude/coga-review-closing-act`, recorded `2026-09-22`
- `persist-autoclose-retire-follow-ups` — branch `autoclose-retire-worklist`, worktree `/home/n/Code/claude/coga-autoclose-retire-worklist`, recorded `2026-09-18`
- `preserve-edits-during-released-claim-recovery` — branch `fix/released-claim-edits`, worktree `/tmp/coga-released-claim-edits`, recorded `2026-09-22`
- `record-dochub-s-why-not-the-api-answer-that-browse` — branch `dochub-api-answer`, worktree `/home/n/Code/claude/coga-dochub-api-answer`, recorded `2026-09-18`
- `record-or-clear-the-standing-repo-wide-coga-valida` — branch `validate-baseline`, worktree `/home/n/Code/claude/coga-validate-baseline`, recorded `2026-09-18`
- `recurring-task-to-manage-all-open-pr-and-address-c` — branch `address-pr-comments-sweep`, worktree `/home/n/Code/coga-address-pr-comments`, recorded `2026-09-22`
- `refresh-recurring-ledger-before-first-create-sync` — branch `fix/recurring-ledger-freshness`, worktree `/tmp/coga-recurring-ledger-freshness`, recorded `2026-09-22`
- `reject-context-artifacts-that-escape-the-checkout` — branch `fix/context-artifacts`, worktree `/tmp/coga-context-artifacts`, recorded `2026-09-22`
- `reuse-the-existing-control-worktree-for-recurring` — branch `recurring-control-worktree`, worktree `/home/n/Code/codex/coga-recurring-control-worktree`, recorded `2026-09-22`
- `simplify-git-sync` — branch `publish-sync`, worktree `/home/n/Code/coga-publish-sync`, recorded `2026-09-22`
- `state-which-branch-is-canonical-for-machine-genera` — branch `sync-canonical-policy`, worktree `/home/n/Code/claude/coga-sync-canonical-policy`, recorded `2026-09-18`
- `the-period-task-context-never-covers-the-determini` — branch `period-task-recipe-firing`, worktree `/home/n/Code/claude/coga-period-task-recipe-firing`, recorded `2026-09-18`
- `the-ticket-interview-never-asks-what-done-means` — branch `ticket-done-criteria`, worktree `/home/n/Code/coga-ticket-done-criteria`, recorded `2026-09-22`
- `the-v2-parking-area-premise-check-has-four-holes` — branch `v2-premise-holes`, worktree `/tmp/coga-v2-premise-review.5AX4MD/repo`, recorded `2026-09-18`
- `ticket-specs-should-cite-symbols-not-line-numbers` — branch `design-cite-symbols`, worktree `/home/n/Code/claude/coga-design-cite-symbols`, recorded `2026-09-21`
