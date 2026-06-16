The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dedup pass — 2026-06-16

Re-verified the discovery set against the live board (it had not moved). Owner
(nick) gave explicit approval for the full delete set via interactive prompt.

Delivery: per owner instruction, NOT via `relay delete` (which auto-commits the
removal to `main` and pushes — `git.sync_paths` lands on the control branch even
from a feature branch). Instead the deletions are `git rm` on a feature branch
`dedup-duplicate-draft-tickets` and shipped as a PR for review. No autocommit to
main.

### Deleted (6 task dirs)

| Deleted | Reason | Canonical |
|---|---|---|
| `rename-workfflow` | empty stub | `rename-workflow-primitive-to-playbook` |
| `change-workflow-dname` | empty stub; owner confirmed it's the same rename, not a distinct idea | `rename-workflow-primitive-to-playbook` |
| `uncommitted-stuff-not-handled` | empty stub | `clean-uncommitted-work` |
| `autocleanup-worktree-branche` | empty stub; canonical ticket explicitly says "Supersedes the `autocleanup-worktree-branche` draft" | `use-worktree-when-starting-a-dev-task` |
| `drift-status-still-calls-auto-bump-merged-after-mo` | had content, but already absorbed: `retire-…` documents the settled trigger decision and states "This ticket settles `drift-status-…`" | `retire-standalone-relay-automerge-triggers-recurri` |
| `sync-dirty-files` | empty, ambiguous stub; owner read it as stranded-dirty-work | `clean-uncommitted-work` |

### Folds performed

None. The five empty stubs carried no intent to preserve, and the open decision
in `drift-status-…` was already folded into `retire-standalone-…` before this
pass.

### Left alone (verified not dupes)

- `automerge-ticket` [active] — different feature (`code/optimistic-merge`), not a dupe.
- `improve-prompt-for-relay-launch` vs `improve-prompt-for-relay-ticket` — distinct targets.

### Status

PR opened for owner review. Holding off on `relay mark done` until the PR merges
(deletions aren't live on `main` until then). Recovery for any deletion is
`git restore` / closing the PR.
