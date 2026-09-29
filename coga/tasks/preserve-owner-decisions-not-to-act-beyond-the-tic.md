---
title: Preserve owner decisions not to act beyond the ticket that recorded them
status: in_progress
owner: nicktoper
agent: claude
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
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
step: 3 (open-pr)
---

## Description

Dream 2026-W35 knowledge-scan finding G2.

Owner decisions *not* to act survive only in the body of the ticket that
recorded them, and the lifecycle retires those tickets. The live example is
`decide-whether-to-keep-imported-google-agents-cli`: it was canceled without
its outcome landing in any context, so the same question is being re-raised
now (see `decide-the-fate-of-the-imported-google-agents-cli`).

A canceled ticket is not a Retro candidate -- Phase 4 only processes `done`
tickets -- so a "we looked at this and chose not to act" decision has no path
into durable knowledge at all today.

## Context

Decide where a no-action decision should land (a decision-register context,
a `## Decision` section the cancel path preserves, or a Retro rule that also
reads canceled tickets), then implement it. Relates to the existing draft
`add-decision-register-authoring-style-context`.
<!-- coga:blackboard -->

## Production notes

Moved from FastJVM/multiply on 2026-09-24: filed there by Dream/autofix against coga itself (status there was `draft`; canceled in multiply as moved). Reset to `draft` for re-triage here. Paths, branches, worktrees and ticket slugs in the notes below refer to the multiply repo unless they say otherwise.


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/918
branch: preserve-no-action-decisions

## Plan (agreed with owner 2026-09-28)

Landing = owning topic + scan backstop. Finding: Dream's knowledge scan already
routes `extract` with `source: canceled` to a Phase 6 proposal PR, but its
qualifier excludes decisions ("abandoned design is not durable; only a gotcha,
verified behavior, measured limit"). So:
- coga/lifecycle: a no-action cancel lands the decision (what, why, revisit
  trigger) in the subject's owning topic; the ticket body is not its home.
- coga/knowledge: owner table/row for no-action decisions -> subject's topic.
- knowledge-scan + Dream Phase 6: an unlanded no-action decision on a canceled
  ticket qualifies as `source: canceled` extract.
Rejected: a separate decision-register topic (second owner, drifts);
Retro reading canceled tickets (duplicates the existing scan path).


## Implement handoff (2026-09-28)

Pushed `preserve-no-action-decisions` (one commit, rebased on origin/main):
- `coga/knowledge` (+ bootstrap twin): new paragraph naming the owning topic of
  the subject as the owner of a no-action decision (what declined, why, what
  reopens it); the ticket is never its home.
- `coga/lifecycle` (+ twin): cancellation bullet: a no-action cancel lands the
  decision in that topic before/with the cancel; reason points there; Dream
  knowledge scan is the backstop.
- `bootstrap/dream/scan/knowledge-scan/SKILL.md`: `source: canceled` qualifier
  now also admits an unlanded no-action decision. Dream Phase 6 `canceled`
  route needed no change (it already opens a proposal PR for "the durable fact").
- `tests/test_dream_worker_templates.py`: one assertion for the new qualifier.
Verification: `.venv/bin/python -m pytest` -> 3050 passed; twins byte-identical.
Not done here: the google-agents-cli decision itself lives in multiply, not this
repo; landing it is that repo's work.

## Peer review

2026-09-28: `codex review --base main` **returned** successfully (exit 0)
with no findings. No review fixes were needed. Reviewed rebased feature head
`02433eb11` against `main` at `24842bd0a`.

Manual review traced an unlanded owner no-action decision through
`source: canceled` to Dream Phase 6's existing proposal PR route, including
its ownership/deduplication check and human merge gate. The scan excludes a
decision already present in the owning topic and still rejects abandoned
design alone. This is an instruction change; preservation depends on following
the cancellation guidance and running Dream. No terminal or rendered-message
surface changed, so terminal-size testing is not applicable.

Verification:

- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest` -> 3050 passed.
- Reviewer also ran `PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/test_dream_worker_templates.py tests/test_packaging.py -q` -> 44 passed.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task preserve-owner-decisions-not-to-act-beyond-the-tic --json` -> 1 valid task, no issues.
- `git diff --check main...HEAD` -> clean; `cmp` confirmed byte identity for
  both changed canonical/packaged topic pairs after rebase.

Ran `git fetch origin main` and `git rebase FETCH_HEAD` unconditionally before
review and testing; no conflicts. Pushed with
`git push --force-with-lease -u origin preserve-no-action-decisions`.
The final fetch confirmed the branch is one commit ahead of current main;
returned to a clean, up-to-date `main` before writing this handoff.

## PR

Owner decisions not to act could remain only in canceled tickets because
Dream's knowledge scan did not count them as durable knowledge. Define the
subject's owning topic as the home for what was declined, why, and what would
reopen it, and direct cancellation reasons to that topic. Extend the scan to
propose unlanded decisions through its existing canceled-ticket PR route.
Update the canonical knowledge/lifecycle topics, their packaged twins, and the
scan contract assertion.

Test plan: `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest` -> 3050 passed; `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task preserve-owner-decisions-not-to-act-beyond-the-tic --json` -> no issues; `git diff --check main...HEAD` and both changed topic-pair comparisons passed.
