---
slug: document-the-automerge-bare-pr-line-format-require
title: 'Document the automerge bare pr: line format requirement'
status: done
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
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
  - name: review
    skills: []
    assignee: owner
---

## Description

`relay automerge` only recognizes a PLAIN `pr: <url>` line under `## Dev` when
deciding whether a ticket's linked PR has merged. It does NOT recognize a
`- pr: <url>` list-item bullet. Across at least 6 done tickets, reviewers
repeatedly had to hand-add a bare `pr:` line to a ticket before a merged PR
would auto-close it.

This is a doc task for a human to design and place: the `dev/code` context owns
the `pr:` convention and should explicitly state the bare-line requirement (a
plain `pr: <url>` under `## Dev`, not a `- pr:` bullet) so authors and reviewers
write the line in the form `automerge` actually parses.

## Context

<!-- coga:blackboard -->

## Findings (implement step) — premise is STALE

The ticket's premise no longer holds. It asks `dev/code` to state that the
`pr:` line MUST be bare (`pr: <url>`, not `- pr: <url>`) because the automerge
sweep only parses the bare form. **The sweep already parses both forms.**

- `src/coga/autoclose.py:52`:
  `_PR_LINE_RE = re.compile(r"^\s*(?:-\s*)?pr:\s*(\S+)\s*$", re.MULTILINE)`
  The `(?:-\s*)?` group tolerates an optional `- ` bullet prefix. Bare and
  bulleted `pr:` lines both match. The comment at lines 47–51 says this was
  deliberate ("the bulleted shape is perfectly natural").
- This was fixed in commit `ec325300` — "Parse bulleted `- pr:` lines in the
  autoclose sweep (#444)". The 6-ticket hand-fix pain predates that commit.
- `parse_branch_name` / `_BRANCH_LINE_RE` are likewise bullet-tolerant.

Writing the requested doc ("must be bare, not a bullet") would now be factually
WRONG and contradict the code.

### Decision — close as obsolete

Human (owner: nick, present in interactive session) chose **close as obsolete**.
The motivating problem was fixed in code by PR #444 (`ec325300`), which made the
sweep parse both bare and bulleted `pr:` lines. No `dev/code` edit is made — the
requested doc would contradict the code. No branch, no PR. Closing via
`coga mark done`.
