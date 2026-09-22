---
title: Autoclose merged tickets
status: in_progress
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: 3a7b821e-3641-4d2f-aadc-234f007a30f8
workflow:
  name: autoclose-merged/sweep
  steps:
  - name: sweep
    skills:
    - coga/autoclose/sweep
    assignee: agent
step: 1 (sweep)
---

## Description

Close Coga tickets whose linked GitHub PR has already merged and whose Coga
workflow is at its final step.

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
   keyed by task slug.

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
ones discharged — worktree directory gone and local branch gone. The rules
are in the `coga/autoclose/sweep` skill.

This sweep is the sole trigger for auto-closing merged tickets — there is
no manual `automerge` command. The recurring task only changes when the
sweep runs; it does not change which tickets are safe to close.

Done events produced by the sweep go through the shared `mark_done` finalizer,
so each closure posts live to Slack exactly as a manual `coga mark done` would.
A quiet day with no merged final-step tickets exits successfully and changes
nothing.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Autoclose Sweep: retire follow-ups

Generated: 2026-09-22T17:21:37+00:00
Task: `recurring/autoclose-merged`

Checkout disposal skipped (the sweep failed before checkout disposal ran) — every recorded checkout was preserved.
- `agent-usage-report` "agent-usage-report": worktree `/home/n/Code/codex/coga-usage-report`, branch `usage-report` — `coga retire agent-usage-report`
- `attribute-headless-recurring-completions-to-system` "Attribute headless recurring completions to system": worktree `/tmp/coga-system-completion`, branch `fix/headless-completion-system` — `coga retire attribute-headless-recurring-completions-to-system`
- `automerge/fix-let-a-lot-of-open-craps` "fix let a lot of open craps": worktree `/home/n/Code/coga-dispose-checkouts`, branch `dispose-checkouts` — `coga retire automerge/fix-let-a-lot-of-open-craps`
- `cleanup/quiet-the-first-run-noise-from-recurring-jobs-and` "Quiet the first-run noise from recurring jobs and managed skills": worktree `/home/n/Code/codex/coga`, branch `quiet-first-run` — `coga retire cleanup/quiet-the-first-run-noise-from-recurring-jobs-and`
- `correct-the-v2-known-stale-surfaces-table-and-rout` "Correct the v2 known-stale-surfaces table and route future Dream gap findings": worktree `/tmp/coga-v2-stale-surfaces`, branch `v2-stale-surfaces` — `coga retire correct-the-v2-known-stale-surfaces-table-and-rout`
- `detect-stranded-ticket-writes-across-checkouts` "Detect stranded ticket writes across checkouts": worktree `/home/n/Code/coga-stranded-ticket-writes`, branch `stranded-ticket-writes` — `coga retire detect-stranded-ticket-writes-across-checkouts`
- `document-how-packaged-contexts-reach-a-repo-and-se` "Document how packaged contexts reach a repo, and settle the packaged-only cli context": worktree `/home/n/Code/coga-packaged-context-states`, branch `packaged-context-states` — `coga retire document-how-packaged-contexts-reach-a-repo-and-se`
- `document-the-remedy-for-a-bloated-blackboard-sibli` "Document the remedy for a bloated blackboard: sibling attachments and unattached contexts": worktree `/home/n/Code/claude/coga-bloated-blackboard-remedy`, branch `bloated-blackboard-remedy` — `coga retire document-the-remedy-for-a-bloated-blackboard-sibli`
- `exclude-superseded-designs-from-launch-prompts` "Exclude superseded designs from launch prompts": worktree `/tmp/coga-exclude-superseded-designs`, branch `codex/exclude-superseded-designs` — `coga retire exclude-superseded-designs-from-launch-prompts`
- `installer-managed-skills-the-local-adaptation-guar` "Installer-managed skills: the local-adaptation guard misses github-backed packs": worktree `/home/n/Code/coga`, branch `gh-backed-readonly-context` — `coga retire installer-managed-skills-the-local-adaptation-guar`
- `make-sure-repo-clietn-don-t-edit-coga` "make sure repo clietn don't edit coga": worktree `/home/n/Code/coga-client-repo-dream`, branch `client-repo-dream` — `coga retire make-sure-repo-clietn-don-t-edit-coga`
- `narrative-candidates-md-publishes-log-text-the-own` "narrative-candidates.md publishes log text the owner ruled confidential": worktree `/home/n/Code/coga-remove-narrative-candidates`, branch `remove-narrative-candidates` — `coga retire narrative-candidates-md-publishes-log-text-the-own`
- `packaged-code-workflows-never-name-coga-retire-as` "Packaged code workflows never name coga retire as the closing act": worktree `/home/n/Code/claude/coga-review-closing-act`, branch `review-closing-act` — `coga retire packaged-code-workflows-never-name-coga-retire-as`
- `preserve-edits-during-released-claim-recovery` "Preserve edits during released claim recovery": worktree `/tmp/coga-released-claim-edits`, branch `fix/released-claim-edits` — `coga retire preserve-edits-during-released-claim-recovery`
- `recurring-task-to-manage-all-open-pr-and-address-c` "recurring task to manage all open pr and address commtns": worktree `/home/n/Code/coga-address-pr-comments`, branch `address-pr-comments-sweep` — `coga retire recurring-task-to-manage-all-open-pr-and-address-c`
- `refresh-recurring-ledger-before-first-create-sync` "Refresh recurring ledger before first create sync": worktree `/tmp/coga-recurring-ledger-freshness`, branch `fix/recurring-ledger-freshness` — `coga retire refresh-recurring-ledger-before-first-create-sync`
- `reject-context-artifacts-that-escape-the-checkout` "Reject context artifacts that escape the checkout": worktree `/tmp/coga-context-artifacts`, branch `fix/context-artifacts` — `coga retire reject-context-artifacts-that-escape-the-checkout`
- `reuse-the-existing-control-worktree-for-recurring` "Run single-repo recurring from the control worktree that already exists": worktree `/home/n/Code/codex/coga-recurring-control-worktree`, branch `recurring-control-worktree` — `coga retire reuse-the-existing-control-worktree-for-recurring`
- `simplify-git-sync` "Simplify git sync": worktree `/home/n/Code/coga-publish-sync`, branch `publish-sync` — `coga retire simplify-git-sync`
- `the-ticket-interview-never-asks-what-done-means` "The ticket interview never asks what done means": worktree `/home/n/Code/coga-ticket-done-criteria`, branch `ticket-done-criteria` — `coga retire the-ticket-interview-never-asks-what-done-means`
Recorded in the durable worklist `/home/n/Code/claude/coga/coga/recurring/autoclose-merged/retires.md`; this period task is deleted at the next period boundary.

## Recipe Failure

Recipe: `autoclose`
Exit: 1
Task: `recurring/autoclose-merged`
Recorded: 2026-09-22T17:21:37+00:00

    Traceback (most recent call last):
      File "/home/n/Code/claude/coga/src/coga/autoclose.py", line 1033, in run_autoclose_recipe
        sweep_merged(
      File "/home/n/Code/claude/coga/src/coga/autoclose.py", line 599, in sweep_merged
        _sweep_merged_into(
      File "/home/n/Code/claude/coga/src/coga/autoclose.py", line 563, in _sweep_merged_into
        _try_bump_one(
      File "/home/n/Code/claude/coga/src/coga/autoclose.py", line 514, in _try_bump_one
        mark_done(
      File "/home/n/Code/claude/coga/src/coga/mark.py", line 221, in mark_done
        announce()
      File "/home/n/Code/claude/coga/src/coga/mark.py", line 192, in announce
        notify(
      File "/home/n/Code/claude/coga/src/coga/notification/__init__.py", line 161, in notify
        post(
      File "/home/n/Code/claude/coga/src/coga/notification/__init__.py", line 96, in post
        channel.send(
      File "/home/n/Code/claude/coga/src/coga/notification/slack.py", line 140, in send
        resp = requests.post(
               ^^^^^^^^^^^^^^
      File "/home/n/.local/share/uv/tools/coga/lib/python3.12/site-packages/requests/api.py", line 134, in post
      File "/home/n/.local/share/uv/tools/coga/lib/python3.12/site-packages/requests/api.py", line 71, in request
      File "/home/n/.local/share/uv/tools/coga/lib/python3.12/site-packages/requests/sessions.py", line 651, in request
      File "/home/n/.local/share/uv/tools/coga/lib/python3.12/site-packages/requests/sessions.py", line 784, in send
      File "/home/n/.local/share/uv/tools/coga/lib/python3.12/site-packages/requests/adapters.py", line 668, in send
      File "/home/n/.local/share/uv/tools/coga/lib/python3.12/site-packages/requests/adapters.py", line 332, in cert_verify
    OSError: Could not find a suitable TLS CA certificate bundle, invalid path: /home/n/.local/share/uv/tools/coga/lib/python3.12/site-packages/certifi/cacert.pem
    
    During handling of the above exception, another exception occurred:
    
    Traceback (most recent call last):
      File "/home/n/Code/claude/coga/src/coga/runner.py", line 132, in run_recipe
        code = recipe(cfg, list(argv))
               ^^^^^^^^^^^^^^^^^^^^^^^
      File "/home/n/Code/claude/coga/src/coga/autoclose.py", line 1048, in run_autoclose_recipe
        _report_retire_followups(cfg, result)
      File "/home/n/Code/claude/coga/src/coga/autoclose.py", line 993, in _report_retire_followups
        post(
      File "/home/n/Code/claude/coga/src/coga/notification/__init__.py", line 96, in post
        channel.send(
      File "/home/n/Code/claude/coga/src/coga/notification/slack.py", line 140, in send
        resp = requests.post(
               ^^^^^^^^^^^^^^
      File "/home/n/.local/share/uv/tools/coga/lib/python3.12/site-packages/requests/api.py", line 134, in post
      File "/home/n/.local/share/uv/tools/coga/lib/python3.12/site-packages/requests/api.py", line 71, in request
      File "/home/n/.local/share/uv/tools/coga/lib/python3.12/site-packages/requests/sessions.py", line 651, in request
      File "/home/n/.local/share/uv/tools/coga/lib/python3.12/site-packages/requests/sessions.py", line 784, in send
      File "/home/n/.local/share/uv/tools/coga/lib/python3.12/site-packages/requests/adapters.py", line 668, in send
      File "/home/n/.local/share/uv/tools/coga/lib/python3.12/site-packages/requests/adapters.py", line 332, in cert_verify
    OSError: Could not find a suitable TLS CA certificate bundle, invalid path: /home/n/.local/share/uv/tools/coga/lib/python3.12/site-packages/certifi/cacert.pem
