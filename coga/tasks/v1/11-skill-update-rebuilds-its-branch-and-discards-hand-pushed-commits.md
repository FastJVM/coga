---
title: Skill update rebuilds its PR branch every period and silently discards hand-pushed
  commits
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (design)
agent: claude
launch_generation: c4675b27-864b-4610-910a-e07ac167a507
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

Every symbol below was checked on `origin/main` `9203c3b66` (2026-10-08) and
re-checked on `f9bebb53b` (2026-11-04).

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

**Telling the job's commits apart.** `_commit_skill_updates` hard-codes the
commit subject `Update Coga-managed skills`. The `--pr-title` option on
`coga skill update` and on the `skill-update` recipe
(`skill_update.recipe_parser`) changes only the PR title, not that subject.
A subject match is therefore a usable first signal, but a human can type the
same subject. The design step should decide whether the subject alone is
enough, or whether to also check the author, a trailer, or that the commit's
tree matches a rebuild. `recurring_activity` matches the same subject for
inactivity detection, so do not change it casually.

**Choice left to design.** The owner left carry-forward versus refuse to the
`design` step. That step chooses one, records why, and turns the done sentence
above into the acceptance checklist. Things to weigh:

- Carry-forward can conflict with the regenerated skill files.
- Refuse needs a human to resolve the PR before the weekly job can proceed.
- A failure must surface through the recurring job's normal failure path.
  It must not be swallowed.

**Neighbouring work.** `v1/10-preflight-dirty-tracked-files-before-skill-update`
(in progress) changes the same `run_skill_update_pr_flow` checkout path.
Reconcile with it. The same remote-tip read may also fit its preflight.

**Tests.** The existing coverage is in `tests/test_skill_manager.py`, which
covers `open_or_update_pr` and the lease, and `tests/test_skill_update.py`.
Add cases for three remote states: a hand-pushed commit on the branch, only
the job's own commits, and no remote branch (the #734 merged-then-deleted case).

**Docs owner.** `coga/skill-management` owns the skill-update behaviour.
This ticket edits it, so it is cited here, not attached. The package copy is
`src/coga/resources/templates/coga/bootstrap/contexts/coga/skill-management/SKILL.md`
and the legacy twin is `docs/contexts/coga/skill-management/SKILL.md`. Read
"Rules for managed packs" there, and document the new guard in the same PR.
`coga/pr-publication` describes the `open-pr` lease. It is not this code
path, but its "leased push" step is the pattern `open_or_update_pr` mirrors.

**Design questions from ticket review (2026-11-04).** The design step must
answer these:

- **State on refusal.** `update_skills` writes the new skill files into the
  working tree before `run_skill_update_pr_flow` runs. A refusal must leave
  the caller's branch and working tree as they were. Either run the guard
  before `update_skills`, or restore on refusal. Add a test for it. This
  interacts with v1/10's dirty-file preflight.
- **Getting the commits.** `_remote_branch_oid` returns only an OID from
  `ls-remote`. Listing foreign commits needs a fetch of the remote branch.
  `_checkout` builds from the local `cfg.git_control_branch`, not
  `<remote>/<control>`. Decide which one "on the control branch" means, so a
  stale local `main` does not make commits look foreign.
- **Identifying the job's own commits.** The job commits as whoever runs the
  sweep, usually the owner, so the author cannot tell the job from a human.
  The choice is the subject, a trailer, or both. A trailer only marks commits
  made after this change, so commits already on the branch still need the
  subject match. Today `--pr-title` defaults to the same string as the
  commit subject.
- **Remote states to handle:**
  - GitHub "Update branch" merge commits from the control branch. They are
    foreign by subject but harmless.
  - A PR merged or closed with its branch left behind. After a squash merge,
    the hand commit is in main but not as an ancestor, so a naive refuse
    blocks the job forever. Check for an open PR, or use patch equivalence
    (`git cherry`).
  - Weeks with no updates. The flow returns early before any check; done
    should say that this is fine.
- **Failure path.** `recurring/skill-update/ticket.py` → `run_recipe` records
  stderr on the period blackboard and exits non-zero. That is where the named
  failure should appear.
- **Extra docs.** Also update the package `recurring/skill-update/ticket.md`,
  which describes the flow and has a legacy twin in the inventory.
- **Test churn.** `tests/test_skill_manager.py` matches exact command
  sequences (`_lease_stub`), so a new fetch or `ls-remote` changes many
  expected sequences.

Previous ref: `skill-update-rebuilds-its-branch-and-discards-hand-pushed-commits` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
