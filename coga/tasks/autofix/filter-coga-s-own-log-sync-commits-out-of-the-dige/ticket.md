---
slug: autofix/filter-coga-s-own-log-sync-commits-out-of-the-dige
title: 'Filter Coga''s own Log: sync commits out of the digest'
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

The daily Slack digest's "Also merged (no ticket)" section is dominated by Coga's own bookkeeping commits. `_is_coga_state_sync_commit` does not recognize the `Log: <slug>` prefix that `git.sync_log` writes, so every log.md sync commit is reported to the shared channel as if it were merged work.

## Evidence

This sweep's digest run completed with exit 0 and `posted: yes`, so the sweep recorded `problems: 0`. The damage is in what it posted.

`coga/recurring/digest/ticket.md` `### Digest State` after the run:

```
range: f2f7eb1..3e9249b (130 commit(s), 47 reported)
```

Replaying the filter over that range locally reproduces the count exactly (49 survive the subject filters, minus 2 whose PR numbers matched the Done tickets autoclose had just closed, `#761` and `#779`, = 47). Of those 47 reported commits, **25 are `Log: <slug>` commits** — `Log: recurring/digest`, `Log: bootstrap/ticket`, `Log: bootstrap/orient`, `Log: make-sure-repo-clietn-don-t-edit-coga`, and so on.

The previous run is worse and makes the defect unambiguous. Its recorded range was `034c5a8..f2f7eb1 (51 commit(s), 4 reported)`, and all four reported commits were:

```
Log: recurring/digest
Log: recurring/autoclose-merged
Log: recurring/dream
Log: recurring/blocker-reminders
```

That digest posted a section whose entire contents were Coga writing to its own log — 100% noise, delivered as "merged work" to humans.

## Where it lives

`src/coga/commands/digest.py:277`:

```python
def _is_coga_state_sync_commit(subject: str) -> bool:
    return (
        subject.startswith("Sync task state:")
        or subject.startswith("Sync coga state")
        or (subject.startswith("Ticket: ") and " \u2014 " in subject)
    )
```

The three recognized shapes cover task-state and ticket-status syncs but miss the log sync. Every producer of that subject is Coga itself, via `git.sync_log`: `src/coga/recurring_runner.py:2698`, `src/coga/commands/launch.py:3487` and `:3664`, `src/coga/launch_script.py:184`, `src/coga/open_pr.py:373`, and `src/coga/bump.py:321` (`Log: <slug> — rewind notification failure`). There is no human-authored `Log: ` commit convention in this repo.

This is the filter step the ticket contract already promises. `coga/recurring/digest/ticket.md` step 4 reads "filters Coga's own state-sync commits out of 'Also merged'", and `coga/workflows/digest/post.md` repeats it. The behavior is a straightforward failure to meet the documented contract, not a design question.

## What a fix has to do

- Add the `Log: ` prefix to `_is_coga_state_sync_commit`, including the `Log: <slug> — rewind notification failure` variant from `bump.py`.
- Cover it in `tests/` alongside the existing state-sync-filter cases — assert that a `Log: recurring/digest` subject is excluded and that a digest whose entire candidate set is `Log: ` commits takes the no-post path (`should_post` false, note `no done tickets or new commits`) rather than posting an empty-of-substance "Also merged" section.
- Check the same subject list against the branch-sweep and autoclose scanners if they classify commit subjects independently; the `Log: ` shape is repo-wide, not digest-specific.
- Leave the watermark and drain semantics alone. This is a rendering/classification fix; `### Digest State` and `spool.drain` behavior are correct and must keep advancing on a successful post.

Note that suppressing these will often flip a run to the documented silent path, since on quiet days `Log: ` commits are the only thing left after filtering — that is the intended outcome, not a regression.

---

Written by the `coga recurring` autofix loop from the sweep this
ticket's `run-log.md` records. The finding is an agent's
reading of that run, not a verified diagnosis: confirm it against
`run-log.md` before changing anything, and close the ticket
through the workflow's already-satisfied path if the problem was
transient or already fixed.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
