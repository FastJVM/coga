---
slug: autofix/stop-the-digest-spool-drain-leaking-a-blank-line-e
title: Stop the digest spool drain leaking a blank line every run
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

`coga digest`'s spool drain re-prepends a newline that the section regex has already absorbed, so every drain adds one permanent blank line under `## Spool (pending)` in `coga/recurring/digest/spool.md`. The job exits 0 and posts correctly, so nothing in the sweep reports it — this is a silent, monotonic growth leak in a git-tracked state file.

## Evidence

This sweep's `recurring/digest` run completed with `script exited with code 0` (`coga/log.md:4379-4381`) and did its real work (the template's `### Digest State` advanced to `last_commit: af7d08ae…`, `range: 865d3d6..af7d08a (78 commit(s), 22 reported)`, `posted: yes`). But the drain it performed also grew the blank-line block. Counting blank lines between the heading and `consumed_through:` across the file's history:

```
f4d9cd59 2026-08-25  blanks=17
88f6fb57 2026-09-01  blanks=17
a88ab00d 2026-09-02  blanks=17
debafdeb 2026-09-02  blanks=18
aa530167 2026-09-03  blanks=18
d9801a23 2026-09-03  blanks=19
e93ad8a5 2026-09-04  blanks=19   <- before this sweep's digest run
6290c7c8 2026-09-04  blanks=20   <- this sweep's digest drain
```

The step from 19 to 20 lands exactly on the commit where the record count drops from 5 to 2 — i.e. on the drain, not on any producer append. The section currently carries 20 blank lines of pure noise.

## Root cause

`src/coga/spool.py`:

- `_SECTION_RE` is `^##\s+Spool \(pending\)\s*$\n?(.*?)…`. Because `\s*` is greedy and matches newlines, it swallows every pre-existing blank line into the heading portion of the match, so `match.start(1)` points at the `consumed_through:` line and the prefix `text[:match.start(1)]` already ends with all N blank lines.
- `drain()` then builds `new_body = f"\n{WATERMARK_KEY}: {new_watermark}\n{anchor_raw}\n"` — an unconditional leading `\n` that assumes group 1 begins right after the heading's own newline. Prefix + that newline = N+1 blank lines.

Minimal repro of the two pieces together (3 blanks in, 4 blanks out):

```
prefix     = '## Spool (pending)\n\n\n\n'
group1     = 'consumed_through: a\n{"id":"a"}\n{"id":"b"}\n'
after drain= '## Spool (pending)\n\n\n\n\nconsumed_through: b\n{"id":"b"}\n'
```

`append_record()` is not implicated — it does `body.rstrip("\n")` and stays flat.

This also interacts badly with the file's `merge=union` attribute: two clones that each drain add blank lines in the same region, and a union merge keeps both sides' additions, so growth is faster than one line per day whenever the repo is used from more than one checkout.

## What a fix has to do

1. Make `drain()` write a normalized section body — one blank line between the heading and `consumed_through:`, watermark, anchor — instead of blindly prepending `\n` to whatever prefix the regex left behind. Either tighten `_SECTION_RE` so `\s*$\n?` cannot swallow following blank lines (the capture should start immediately after the heading line), or have `drain()` reconstruct from `match.start()` of the whole heading rather than `match.start(1)`. Whichever route, `drain()` must be shape-idempotent: draining a section that already has the canonical shape must not change its whitespace.
2. Preserve the existing merge contract while doing it — the trim must still be a top-only prefix delete with the newest record retained in place as the anchor, so a concurrent bottom append stays in a disjoint hunk (see the module docstring in `src/coga/spool.py` and the `coga/sync` context). Do not rewrite the tail or reflow the anchor line.
3. Add a regression test (`tests/test_spool.py`, or alongside the existing spool coverage in `tests/test_digest.py`) that drains the same spool two or three times in a row and asserts the blank-line count under `## Spool (pending)` is stable, plus one that starts from a spool already carrying several leaked blank lines and asserts the drain collapses them rather than adding another.
4. Clean up the accumulated noise in the live file `coga/recurring/digest/spool.md` (20 stray blank lines today) as part of the change. The packaged twin `src/coga/resources/templates/coga/recurring/digest/spool.md` is already at the canonical 1 blank line, so it should need no edit — but confirm the two stay consistent per the live/packaged twin rule in `CLAUDE.md`.

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
