The blackboard is a notepad to be written to often as the human and agent works through a task.

## How this ticket briefly "disappeared" (2026-06-11)

Carried over from the deleted duplicate `establish-marketing-area`, whose
bootstrap session ran the investigation.

- This ticket's creation commit `f916581e` (09:35) landed on origin/main
  via relay's working-tree-free plumbing path (`git.py`: `commit-tree` +
  push + `_try_update_local_ref`), not a normal commit — the `main`
  reflog entry has an empty message, the signature of `git update-ref`.
  That path only runs when the creating process sees HEAD ≠ main.
- The `update-ref` fast-forwarded local `main` without touching the main
  checkout's index/working tree, so the ticket files existed in HEAD but
  not on disk — git status showed them as a staged deletion. Nobody
  deleted anything.
- Because the files weren't on disk, Zach's `relay ticket
  establish-marketing-area` (a valid slug prefix) matched nothing and
  scaffolded a duplicate draft, since deleted; files restored here via
  `git restore --source=HEAD --staged --worktree`.
- ~~Open question: where the 09:35 creating process ran such that it saw
  HEAD ≠ main.~~ **Answered (2026-06-11, second bootstrap session):** the
  creating process ran in *this same checkout* on local branch
  `marketing-area-in-relay-os` — not a worktree. Evidence: that branch's
  commit `5fbf005c` ("what/why body", 09:36:52, one minute after the
  creation commit) and PR #337 opened from it at 09:37. That session
  bootstrapped the ticket, filled it its own way on the branch, and
  opened the PR; nobody knew when this session bootstrapped the same
  ticket again and opened PR #338. #337 closed in favor of #338 (its
  ticket had `workflow: null`, broad context attachments, and pre-dated
  Zach's interview answers); its one valuable fact — the rejected nested
  `relay init` alternative — was folded into the ticket's Context.
- Likely latent bug worth its own ticket: `_try_update_local_ref` should
  refuse when the branch is checked out in ANY worktree
  (`git worktree list`), since `update-ref` bypasses git's own
  checked-out-branch safety.

Also cleaned up in the same session (unrelated, from a 09:10
push-rejection rebase whose autostash conflicted): resolved the UU
conflict in `relay-os/recurring/digest/blackboard.md` by keeping both
sides' JSONL records, verified the rest of the autostash was applied,
and dropped the stale stash entry.
