---
title: Autoclose merged tickets
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: 9c59c0c0-48a8-42e2-8960-9e7dfd898445
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
workflow is at its final step.

Tickets can get stuck `in_progress` after the owner merges the PR on GitHub but
forgets to run `coga mark done`. Once a day this recurring task fires. Its
`ticket.py` runs the existing merged-ticket sweep, which:

1. scans active and in-progress tickets,
2. reads the `pr:` line under each ticket blackboard's `## Dev` section,
3. checks the linked PR state with `gh pr view`,
4. leaves non-final-step tickets alone as suspicious, and
5. marks final-step or workflow-less tickets `done` when the PR is merged, and
6. names the `coga retire` follow-up for each ticket it closed that still
   records a `branch:` or `worktree:`, and records it in the durable worklist
   `retires.md` beside this template, keyed by task slug.

Autoclose never disposes of a checkout itself — `coga retire` owns those safety
proofs. Without step 6 an auto-closed ticket's worktree and branch outlive it
silently. Dream preserves checkout-bearing done tickets rather than deleting
the `## Dev` evidence the named command needs, so that debt stays actionable
until a human retires it. The worklist is what keeps the *list* of that debt
actionable: this period task is deleted at the next period boundary, so step 6
writes the entries to `coga/recurring/<name>/retires.md` for the template this
task was minted from and, on every run, drops the entries already discharged —
worktree directory gone and local branch gone. The rules are in the
`coga/autoclose/sweep` skill.

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

Generated: 2026-09-21T17:02:13+00:00
Task: `recurring/autoclose-merged`

5 auto-closed ticket(s) still have a recorded feature checkout. Autoclose never removes one — `coga retire` owns the worktree and branch safety proofs:

- `cleanup/add-contributing-docs-issue-templates-and-a-repo-d` "Add contributing docs, issue templates and a repo description": worktree `/tmp/coga-contributing-docs`, branch `docs/contributing` — `coga retire cleanup/add-contributing-docs-issue-templates-and-a-repo-d`
- `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r` "Fix coga init crash on Python 3.11 by adding the resources package init": worktree `/home/n/Code/claude/coga-resources-pkg-init`, branch `resources-pkg-init` — `coga retire cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r`
- `cleanup/yank-the-pypi-0-0-1-placeholder-and-document-the-f` "Yank the PyPI 0.0.1 placeholder and document the failure": worktree `/tmp/coga-pypi-placeholder-note`, branch `docs/pypi-placeholder-note` — `coga retire cleanup/yank-the-pypi-0-0-1-placeholder-and-document-the-f`
- `ticket-specs-should-cite-symbols-not-line-numbers` "Ticket specs should cite symbols, not line numbers": worktree `/home/n/Code/claude/coga-design-cite-symbols`, branch `design-cite-symbols` — `coga retire ticket-specs-should-cite-symbols-not-line-numbers`
- `vendored-skills-carry-no-coga-source-json-so-coga` "Correct recurring/skill-update's provenance claim to match how skills are actually managed": worktree `/tmp/coga-skill-attribution`, branch `docs/skill-attribution` — `coga retire vendored-skills-carry-no-coga-source-json-so-coga`

Recorded in the durable worklist `/home/n/Code/claude/coga/coga/recurring/autoclose-merged/retires.md`; this period task is deleted at the next period boundary.
