---
title: Autoclose merged tickets
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: c95b9165-d5df-43e0-9adc-4aad49592820
workflow:
  name: autoclose-merged/sweep
  steps:
  - name: sweep
    skills:
    - coga/autoclose/sweep
    assignee: agent
---

## Description

Close Coga tickets whose linked GitHub PR has already merged and whose Coga
workflow is at its final step, then sweep landed branches without live tickets.

Tickets can get stuck `in_progress` after the owner merges the PR on GitHub but
forgets to run `coga mark done`. Once a day this recurring task fires. Its
`ticket.py` runs the existing merged-ticket sweep, which:

1. scans active and in-progress tickets,
2. reads the `pr:` line under each ticket blackboard's `## Dev` section,
3. checks the linked PR state with `gh pr view`,
4. leaves non-final-step tickets alone as suspicious, and
5. marks final-step or workflow-less tickets `done` when the PR is merged,
6. disposes of the feature checkout of each ticket it closed that still
   records a `branch:` or `worktree:`, and of every open entry in the durable
   worklist `retires.md` beside this template — worktree removed, then local
   branch, then remote branch, each under the same safety proofs `coga retire`
   runs (same-repo linked worktree on the recorded branch, locally pristine,
   no other live ticket claiming it, no open PR, landed or at the merged PR's
   exact head), and
7. reports what it disposed of and what a proof refused, with the reason: the
   refusals go to the coga-important Slack channel and into `retires.md`,
   keyed by task slug, and
8. name unresolved, non-outdated review threads with only their opening
   comment on each closed PR in the closure audit line, sweep report, and
   Slack summary. Report only: never resolve or reply.

Step 6 is a direct destructive change, declared here on purpose: the proofs
are deterministic, narrow, and named in the `coga/autoclose/sweep` skill, and
the earlier design — only *naming* a `coga retire` follow-up — left a
ten-entry backlog nobody typed. It runs only when the checkout is on the
control branch (a hand run elsewhere preserves everything and says so) and
only touches worktrees linked to the clone it runs from. Dream preserves
checkout-bearing done tickets rather than deleting the `## Dev` evidence the
proofs need. The worklist is what keeps the *list* of refused checkouts
actionable: this period task is deleted at the next period boundary, so step 7
writes the entries to `coga/recurring/<name>/retires.md` for the template this
task was minted from; every run re-judges the open entries (an entry whose
ticket is gone is proven by the merged PRs for its branch name) and drops the
ones discharged — local branch gone (in the owning repository, for a
worktree another clone owns), and worktree directory gone or this
repository's own primary checkout (a ticket worked in the single-checkout
layout records it; nobody disposes of it, so it is never debt). The rules are
in the `coga/autoclose/sweep` skill.

This sweep is the sole trigger for auto-closing merged tickets — there is
no manual `automerge` command. The recurring task only changes when the
sweep runs; it does not change which tickets are safe to close.

Done events produced by the sweep go through the shared `mark_done` finalizer,
so each closure posts live to Slack exactly as a manual `coga mark done` would.
After the autoclose recipe succeeds, `ticket.py` runs the registered
`branch-sweep` recipe, even when no ticket closed. It then bumps only if both
recipes succeeded. The daily cadence and reporting contract live in
[coga/recurring/scheduling](context:coga/recurring/scheduling); the deletion
proofs and worktree opt-in remain those in
[dev/checkout-cleanup](context:dev/checkout-cleanup).

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Autoclose Sweep: retire follow-ups

Generated: 2026-09-30T01:04:37+00:00
Task: `recurring/autoclose-merged`

10 checkout(s) disposed of under the shared retire proofs (worktree removed, local and remote branch deleted where each proof admitted it):

- `autofix/treat-non-requestexception-slack-send-errors-as-de` "Treat non-RequestException Slack send errors as delivery misses": branch `slack-oserror-delivery-miss`
- `fix-recurring-sweep-git-hygiene-blocked-task-escap` "Fix recurring sweep git hygiene: blocked-task escape, shared branch deletion, missing retirement tag": branch `fix-recurring-git-hygiene`
- `preserve-owner-decisions-not-to-act-beyond-the-tic` "Preserve owner decisions not to act beyond the ticket that recorded them": branch `preserve-no-action-decisions`
- `record-that-preserved-tmp-worktrees-do-not-survive` "Record that preserved tmp worktrees do not survive; only the branch does": branch `doc-tmp-checkouts-ephemeral`
- `stop-synthetic-from-claiming-a-claude-session-s-mo` "Stop <synthetic> from claiming a Claude session's model": branch `fix/claude-synthetic-model`
- `add-an-agent-picker-for-recurring` (worklist backlog): branch `authoring-agent-picker`
- `document-the-remedy-for-a-bloated-blackboard-sibli` (worklist backlog): worktree `/home/n/Code/claude/coga-bloated-blackboard-remedy`, branch `bloated-blackboard-remedy`
- `installer-managed-skills-the-local-adaptation-guar` (worklist backlog): branch `gh-backed-readonly-context`
- `record-or-clear-the-standing-repo-wide-coga-valida` (worklist backlog): worktree `/home/n/Code/claude/coga-validate-baseline`, branch `validate-baseline`
- `reuse-the-existing-control-worktree-for-recurring` (worklist backlog): worktree `/home/n/Code/codex/coga-recurring-control-worktree`, branch `recurring-control-worktree`

8 checkout(s) preserved — a proof refused; each stays on the worklist until a human acts:

- `launch-moves-the-checkout-to-main-before-and-after` "Launch moves the checkout to main before and after a ticket session": branch `launch-normalizes-checkout` — local 'launch-normalizes-checkout' has unmerged work and no merged PR vouching for it — left in place. (`coga retire launch-moves-the-checkout-to-main-before-and-after`)
  - Branch cleanup: local 'launch-normalizes-checkout' advanced past the merged PR head 72b7bc284e16 — preserving it.
  - Branch cleanup: local 'launch-normalizes-checkout' has unmerged work and no merged PR vouching for it — left in place.
  - Branch cleanup: skipping remote origin/launch-normalizes-checkout because the local branch remains.
- `marketing/fix-installer/linux-clean-install-harness` "Linux clean-install harness": branch `linux-clean-install-harness` — local 'linux-clean-install-harness' has unmerged work and no merged PR vouching for it — left in place. (`coga retire marketing/fix-installer/linux-clean-install-harness`)
  - Branch cleanup: local 'linux-clean-install-harness' advanced past the merged PR head 1dd89deb9e66 — preserving it.
  - Branch cleanup: local 'linux-clean-install-harness' has unmerged work and no merged PR vouching for it — left in place.
  - Branch cleanup: skipping remote origin/linux-clean-install-harness because the local branch remains.
- `prevent-parent-ticket-assumptions-during-task-spli` "Prevent parent-ticket assumptions during task splits": branch `no-parent-ticket-guidance` — local 'no-parent-ticket-guidance' has unmerged work and no merged PR vouching for it — left in place. (`coga retire prevent-parent-ticket-assumptions-during-task-spli`)
  - Branch cleanup: local 'no-parent-ticket-guidance' advanced past the merged PR head d3d9606dec17 — preserving it.
  - Branch cleanup: local 'no-parent-ticket-guidance' has unmerged work and no merged PR vouching for it — left in place.
  - Branch cleanup: skipping remote origin/no-parent-ticket-guidance because the local branch remains.
- `record-the-attended-ticket-switch-recipe-launch-do` "Record the attended ticket-switch recipe: launch, do not mark active": branch `attended-ticket-switch-recipe` — local 'attended-ticket-switch-recipe' has unmerged work and no merged PR vouching for it — left in place. (`coga retire record-the-attended-ticket-switch-recipe-launch-do`)
  - Branch cleanup: local 'attended-ticket-switch-recipe' advanced past the merged PR head 893284ac4841 — preserving it.
  - Branch cleanup: local 'attended-ticket-switch-recipe' has unmerged work and no merged PR vouching for it — left in place.
  - Branch cleanup: skipping remote origin/attended-ticket-switch-recipe because the local branch remains.
- `cleanup/quiet-the-first-run-noise-from-recurring-jobs-and` (worklist backlog): worktree `/home/n/Code/codex/coga`, branch `quiet-first-run` — '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place. (`/home/n/Code/codex/coga` is an independent checkout with its own repository, which no proof removes — inspect and remove it by hand, unless it is another clone's primary checkout in active use: then never remove it; verify the branch is gone in that clone and delete this `retires.md` line by hand (see `dev/checkout-cleanup`))
  - Worktree cleanup: '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place.
  - Branch cleanup: local 'quiet-first-run' not present.
  - Branch cleanup: remote origin/quiet-first-run already gone.
- `document-how-to-recover-a-retired-ticket-s-body-fr` (worklist backlog): worktree `/home/n/Code/codex/coga`, branch `retired-ticket-recovery` — '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place. (`/home/n/Code/codex/coga` is an independent checkout with its own repository, which no proof removes — inspect and remove it by hand, unless it is another clone's primary checkout in active use: then never remove it; verify the branch is gone in that clone and delete this `retires.md` line by hand (see `dev/checkout-cleanup`))
  - Worktree cleanup: '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place.
  - Branch cleanup: local 'retired-ticket-recovery' not present.
  - Branch cleanup: remote origin/retired-ticket-recovery already gone.
- `make-dream-run-correctly-under-codex` (worklist backlog): worktree `/home/n/Code/codex/coga`, branch `dream-under-codex` — '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place. (`/home/n/Code/codex/coga` is an independent checkout with its own repository, which no proof removes — inspect and remove it by hand, unless it is another clone's primary checkout in active use: then never remove it; verify the branch is gone in that clone and delete this `retires.md` line by hand (see `dev/checkout-cleanup`))
  - Worktree cleanup: '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place.
  - Branch cleanup: local 'dream-under-codex' not present.
  - Branch cleanup: remote origin/dream-under-codex already gone.
- `run-the-landed-branch-sweep-daily-from-autoclose` (worklist backlog): worktree `/home/n/Code/codex/coga`, branch `daily-autoclose-branches` — '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place. (`/home/n/Code/codex/coga` is an independent checkout with its own repository, which no proof removes — inspect and remove it by hand, unless it is another clone's primary checkout in active use: then never remove it; verify the branch is gone in that clone and delete this `retires.md` line by hand (see `dev/checkout-cleanup`))
  - Worktree cleanup: '/home/n/Code/codex/coga' is not a linked worktree of this repository (independent clone, unrelated repo, or the primary checkout) — left in place.
  - Branch cleanup: local 'daily-autoclose-branches' not present.
  - Branch cleanup: remote origin/daily-autoclose-branches already gone.

Recorded in the durable worklist `/home/n/Code/coga/coga/recurring/autoclose-merged/retires.md`; this period task is deleted at the next period boundary.

## Branch Sweep

Generated: 2026-09-30T01:06:09+00:00
Task: `recurring/autoclose-merged`

Result: 22 local and 11 remote branch(es) deleted, 0 worktree(s) removed, 0 skipped-worktree-pinned, 12 skipped.
- deleted local: attended-ticket-switch-recipe, codex/retro-independent-clone-worklist-knowledge, docs/command-classification, dream-block-on-stranded-retro, dream-w40-direction-topics, fix-authoring-publication, fix-positioning-owner-links, fix-stale-testing-skill-docs, no-parent-ticket-guidance, park-v2-out-of-tasks, record-dev-loop-verification-gotchas, recurring-ledger-from-log, recurring-sync-wedge, resolve-conflicts-default-agent, retire-worklist-owner, settle-after-delegated-recurring, worktree-agent-a4b9c5f006566f8f3, worktree-agent-a564c8d54cf352d3a, worktree-agent-a78917c8bf8e5acc2, worktree-agent-aacb979a5c7a1e4bc, worktree-agent-ab9ce9bb7f8a4e82e, worktree-agent-ad2152611d3e44a0b
- deleted remote: codex/retro-independent-clone-worklist-knowledge, dream-w40-agent-instruction-text, dream-w40-canceled-gotchas, dream-w40-cli-docs, dream-w40-direction-topics, dream-w40-dream-adjacent-bugs, dream-w40-recurring-docs, dream-w40-repoint-stale-refs, dream-w40-usage-pricing-facts, no-parent-ticket-guidance, settle-after-delegated-recurring
- skipped: clean-install-merge, dream-w40-testing-baseline, pr849, pr870, publish-off-control, recurring-crlf-lease, retire-worklist-linked-only, slack-important-alert, split-ticket-contract, v2-premise-adjudication, wedge-ticket-admin-reproduction, wip/numbered-drain-order-stale-base

### Decisions

- Branch sweep: archived 'attended-ticket-switch-recipe' at d34c2336ce5336cad1395ef7d6bdb019281d42fe as 'retired/attended-ticket-switch-recipe' on origin.
- Branch cleanup: force-deleted local 'attended-ticket-switch-recipe' (was d34c2336ce5336cad1395ef7d6bdb019281d42fe) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: local 'clean-install-merge' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: archived 'codex/retro-independent-clone-worklist-knowledge' at 82461f50b5b1e0d97a76f7d69fa6f76db263c76f as 'retired/codex/retro-independent-clone-worklist-knowledge' on origin.
- Branch cleanup: force-deleted local 'codex/retro-independent-clone-worklist-knowledge' (was 82461f50b5b1e0d97a76f7d69fa6f76db263c76f) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/codex/retro-independent-clone-worklist-knowledge.
- Branch sweep: 'codex/retro-recurring-branch-sweep-knowledge' is recorded on a live ticket — left in place.
- Branch sweep: 'coga/skill-update' is the shared skill-update branch — left in place.
- Branch sweep: 'doc-context-boundary' is recorded on a live ticket — left in place.
- Branch sweep: archived 'docs/command-classification' at 7abde3019b56f72db44f653b56f79fa47f18c0fd as 'retired/docs/command-classification' on origin.
- Branch cleanup: force-deleted local 'docs/command-classification' (was 7abde3019b56f72db44f653b56f79fa47f18c0fd) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch sweep: 'docs/v2-batch-verdicts' is recorded on a live ticket — left in place.
- Branch sweep: archived 'dream-block-on-stranded-retro' at 8c792fd2b6b55ded91bb9d2cb2d91a73f2e74cc2 as 'retired/dream-block-on-stranded-retro' on origin.
- Branch cleanup: force-deleted local 'dream-block-on-stranded-retro' (was 8c792fd2b6b55ded91bb9d2cb2d91a73f2e74cc2) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch sweep: archived 'dream-w40-agent-instruction-text' at 3d33e2590a8fee87eccf5d21523302f99c4898a2 as 'retired/dream-w40-agent-instruction-text' on origin.
- Branch cleanup: deleted remote origin/dream-w40-agent-instruction-text.
- Branch sweep: archived 'dream-w40-canceled-gotchas' at c11c56d31d38482b34642dd344c8e9963909f249 as 'retired/dream-w40-canceled-gotchas' on origin.
- Branch cleanup: deleted remote origin/dream-w40-canceled-gotchas.
- Branch sweep: archived 'dream-w40-cli-docs' at 7048b6066a999af3ca91847f41042b61f7120809 as 'retired/dream-w40-cli-docs' on origin.
- Branch cleanup: deleted remote origin/dream-w40-cli-docs.
- Branch sweep: archived 'dream-w40-direction-topics' at 4e2867b20910f7d966f532521e6fea2325eee2c2 as 'retired/dream-w40-direction-topics' on origin.
- Branch cleanup: force-deleted local 'dream-w40-direction-topics' (was 4e2867b20910f7d966f532521e6fea2325eee2c2) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/dream-w40-direction-topics.
- Branch sweep: 'dream-w40-doc-corrections' is recorded on a live ticket — left in place.
- Branch sweep: archived 'dream-w40-dream-adjacent-bugs' at 121a94073b3675c6494b3da39ed2b9d01c8183d2 as 'retired/dream-w40-dream-adjacent-bugs' on origin.
- Branch cleanup: deleted remote origin/dream-w40-dream-adjacent-bugs.
- Branch sweep: archived 'dream-w40-recurring-docs' at d1adbefadcf18c0360bbf847e2cc10e3f4aeac82 as 'retired/dream-w40-recurring-docs' on origin.
- Branch cleanup: deleted remote origin/dream-w40-recurring-docs.
- Branch sweep: archived 'dream-w40-repoint-stale-refs' at 1b5ea2d4799e27cb88b020c87f9cda8b03e6ea63 as 'retired/dream-w40-repoint-stale-refs' on origin.
- Branch cleanup: deleted remote origin/dream-w40-repoint-stale-refs.
- Branch cleanup: skipping remote origin/dream-w40-testing-baseline (no merged PR).
- Branch sweep: archived 'dream-w40-usage-pricing-facts' at 7c5afe970e6553e3f1c1e2f854e682372462abce as 'retired/dream-w40-usage-pricing-facts' on origin.
- Branch cleanup: deleted remote origin/dream-w40-usage-pricing-facts.
- Branch sweep: archived 'fix-authoring-publication' at 96f2a37c4391879554eb411cf91380fc987d43e1 as 'retired/fix-authoring-publication' on origin.
- Branch cleanup: force-deleted local 'fix-authoring-publication' (was 96f2a37c4391879554eb411cf91380fc987d43e1) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch sweep: archived 'fix-positioning-owner-links' at 8eece603cb18c51d134f112b631b9834aa9f6e14 as 'retired/fix-positioning-owner-links' on origin.
- Branch cleanup: force-deleted local 'fix-positioning-owner-links' (was 8eece603cb18c51d134f112b631b9834aa9f6e14) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch sweep: archived 'fix-stale-testing-skill-docs' at 0dd8b6342c4c1a182b9b8820f2a6231b9120d0e1 as 'retired/fix-stale-testing-skill-docs' on origin.
- Branch cleanup: force-deleted local 'fix-stale-testing-skill-docs' (was 0dd8b6342c4c1a182b9b8820f2a6231b9120d0e1) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch sweep: 'fix/retire-followup-owner' is recorded on a live ticket — left in place.
- Branch sweep: 'launch-normalizes-checkout' is recorded on a live ticket — left in place.
- Branch sweep: 'linux-clean-install-harness' is recorded on a live ticket — left in place.
- Branch sweep: archived 'no-parent-ticket-guidance' at d3d9606dec17c15be51af59eece17b5cb6e59f78 as 'retired/no-parent-ticket-guidance' on origin.
- Branch cleanup: force-deleted local 'no-parent-ticket-guidance' (was c259480e1fbc95a6f6cc152b3c4537dbcc00fcde) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/no-parent-ticket-guidance.
- Branch sweep: archived 'park-v2-out-of-tasks' at 007523ff5aa886e4fa6b43fd6c60c691a951a1c1 as 'retired/park-v2-out-of-tasks' on origin.
- Branch cleanup: force-deleted local 'park-v2-out-of-tasks' (was 007523ff5aa886e4fa6b43fd6c60c691a951a1c1) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: local 'pr849' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: local 'pr870' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: skipping remote origin/publish-off-control (no merged PR).
- Branch sweep: archived 'record-dev-loop-verification-gotchas' at f5a52825bcf2247b29d95ca9787891d858e55042 as 'retired/record-dev-loop-verification-gotchas' on origin.
- Branch cleanup: force-deleted local 'record-dev-loop-verification-gotchas' (was f5a52825bcf2247b29d95ca9787891d858e55042) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: skipping remote origin/recurring-crlf-lease (no merged PR).
- Branch sweep: archived 'recurring-ledger-from-log' at 8dc468c0fe1c0d93f637e9f6e07d9ddd28566e13 as 'retired/recurring-ledger-from-log' on origin.
- Branch cleanup: force-deleted local 'recurring-ledger-from-log' (was 8dc468c0fe1c0d93f637e9f6e07d9ddd28566e13) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: skipping remote origin/recurring-ledger-from-log (no merged PR).
- Branch sweep: archived 'recurring-sync-wedge' at e1044d5f128c7c1fd0e49fdac94bc4983e2c0335 as 'retired/recurring-sync-wedge' on origin.
- Branch cleanup: force-deleted local 'recurring-sync-wedge' (was e1044d5f128c7c1fd0e49fdac94bc4983e2c0335) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch sweep: archived 'resolve-conflicts-default-agent' at 2d731f76c718b06982bdfababf554f051c720cd6 as 'retired/resolve-conflicts-default-agent' on origin.
- Branch cleanup: force-deleted local 'resolve-conflicts-default-agent' (was 2d731f76c718b06982bdfababf554f051c720cd6) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: skipping remote origin/retire-worklist-linked-only (no merged PR).
- Branch sweep: archived 'retire-worklist-owner' at c6f776c8630b3f6fe1bee30bd6cdae58cc5948e0 as 'retired/retire-worklist-owner' on origin.
- Branch cleanup: force-deleted local 'retire-worklist-owner' (was c6f776c8630b3f6fe1bee30bd6cdae58cc5948e0) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch sweep: archived 'settle-after-delegated-recurring' at 7458fc169f5727dea35ea5979af39b979011b6d6 as 'retired/settle-after-delegated-recurring' on origin.
- Branch cleanup: force-deleted local 'settle-after-delegated-recurring' (was 7458fc169f5727dea35ea5979af39b979011b6d6) — PR merged; recover with `git checkout -b` from the reflog SHA.
- Branch cleanup: deleted remote origin/settle-after-delegated-recurring.
- Branch sweep: 'shebang-exec-check' is recorded on a live ticket — left in place.
- Branch sweep: 'skill-update-per-skill' is recorded on a live ticket — left in place.
- Branch cleanup: skipping remote origin/slack-important-alert (no merged PR).
- Branch cleanup: local 'split-ticket-contract' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: local 'v2-premise-adjudication' has unmerged work and no merged PR vouching for it — left in place.
- Branch cleanup: skipping remote origin/wedge-ticket-admin-reproduction (no merged PR).
- Branch cleanup: local 'wip/numbered-drain-order-stale-base' has unmerged work and no merged PR vouching for it — left in place.
- Branch sweep: archived 'worktree-agent-a4b9c5f006566f8f3' at c2137625afc3db7c070d3c3354cdaf963f45e641 as 'retired/worktree-agent-a4b9c5f006566f8f3' on origin.
- Branch cleanup: deleted local 'worktree-agent-a4b9c5f006566f8f3'.
- Branch sweep: archived 'worktree-agent-a564c8d54cf352d3a' at c2137625afc3db7c070d3c3354cdaf963f45e641 as 'retired/worktree-agent-a564c8d54cf352d3a' on origin.
- Branch cleanup: deleted local 'worktree-agent-a564c8d54cf352d3a'.
- Branch sweep: archived 'worktree-agent-a78917c8bf8e5acc2' at c2137625afc3db7c070d3c3354cdaf963f45e641 as 'retired/worktree-agent-a78917c8bf8e5acc2' on origin.
- Branch cleanup: deleted local 'worktree-agent-a78917c8bf8e5acc2'.
- Branch sweep: archived 'worktree-agent-aacb979a5c7a1e4bc' at c2137625afc3db7c070d3c3354cdaf963f45e641 as 'retired/worktree-agent-aacb979a5c7a1e4bc' on origin.
- Branch cleanup: deleted local 'worktree-agent-aacb979a5c7a1e4bc'.
- Branch sweep: archived 'worktree-agent-ab9ce9bb7f8a4e82e' at c2137625afc3db7c070d3c3354cdaf963f45e641 as 'retired/worktree-agent-ab9ce9bb7f8a4e82e' on origin.
- Branch cleanup: deleted local 'worktree-agent-ab9ce9bb7f8a4e82e'.
- Branch sweep: archived 'worktree-agent-ad2152611d3e44a0b' at c2137625afc3db7c070d3c3354cdaf963f45e641 as 'retired/worktree-agent-ad2152611d3e44a0b' on origin.
- Branch cleanup: deleted local 'worktree-agent-ad2152611d3e44a0b'.
