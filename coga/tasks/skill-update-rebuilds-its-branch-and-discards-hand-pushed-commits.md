---
title: Skill update rebuilds its PR branch every period and silently discards hand-pushed commits
status: draft
owner: nicktoper
workflow: null
---

## Description

`coga skill update --all --pr` rebuilds `coga/skill-update` from the control
branch on every run, then force-pushes it. If someone pushes a fix by hand
onto the open skill-update PR, the next weekly run overwrites the branch and
the fix is gone. Nothing rejects the push and nothing reports it. The explicit
`--force-with-lease` that #734 added cannot catch a hand-pushed commit already
on the branch: the lease is resolved moments before the push and accepts the
tip it just observed. It can reject only a concurrent change after that
observation.

The ask: when the remote branch carries commits the job did not make, carry
them forward or refuse to overwrite them. Do not discard them.

Done looks like: a commit pushed by hand onto an open `coga/skill-update` PR
survives the next run. It is either kept on the rebuilt branch, or the run
stops with a named failure that says which commits it would have dropped.
A merged-then-deleted branch, which is the case #734 fixed, still pushes
cleanly.

## Context

Every symbol below was checked on `origin/main` `9203c3b66` (2026-10-08).

- `skill_manager.run_skill_update_pr_flow` calls `_commit_skill_updates`
  with `base_branch=cfg.git_control_branch`.
- `_commit_skill_updates` calls `_checkout(run, cwd, branch, create=True,
  start_point=base_branch)`, which is `git checkout -B <branch> <base>`. The
  branch is recreated from base each period, so every push is a history
  rewrite.
- `open_or_update_pr` takes its lease from `_remote_branch_oid`, which runs
  `ls-remote` against the push URLs at push time. It then pushes with
  `--force-with-lease=refs/heads/<branch>:<that oid>`. Nothing ran in between
  inside the job that could move the remote, so a hand-pushed tip already
  present is accepted. Only a concurrent push after the observation can make
  the lease fail. With no remote branch, it pushes with no lease.

**Where this was agreed.** When #734
(`autofix/fix-skill-update-push-rejected-by-stale-force-with`, merged
2026-09-01) shipped the explicit lease, its review recorded this gap under
"Deliberately not done here — follow-ups to file". The note reads
"Ship-as-is + follow-up ticket agreed with zach". It is in FastJVM/admin
commit `7e6da920`, on that ticket's blackboard. The same note points out that
the old bare lease did not protect this case either. It only rejected when the
tracking ref was stale, so the protection was accidental. This ticket is that
follow-up.

**Fix.** Before the rebuild, read the remote tip. If it carries commits that
are not on the control branch and are not the job's own `Update Coga-managed
skills` commits, there are two options:

- Rebuild on top of the remote tip, so those commits are carried forward.
- Refuse with a named error that lists those commits.

A plain "remote tip must be an ancestor" guard does not work here. The
rebuilt branch never descends from the remote tip, so that guard would reject
every push. Whichever check is chosen has to tell the job's own commits apart
from foreign ones.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
