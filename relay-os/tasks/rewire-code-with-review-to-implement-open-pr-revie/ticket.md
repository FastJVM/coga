---
title: Rewire code/with-review to implement → open-pr → review
status: active
mode: interactive
owner: nick
assignee: claude1
workflow: code/with-review
step: 1 (implement)
contexts:
  - relay/codebase
---

## Description

`code/with-review` today uses the monolithic `code/implement-and-pr`
skill — one step that branches, implements, tests, commits, pushes,
opens the PR, hands off, and bumps. This ticket splits it into the
shape we already have skills for:

```
implement → open-pr → review
```

The split skills already exist: `code/implement` (stops before
push), `code/open-pr` (push + PR + handoff). `code/self-review` and
`code/apply-review` exist too but are out of scope here — adding
self-review can be a follow-up.

## Why split

- The PR step is a meaningful checkpoint distinct from "code
  written". A failed push or a `gh` auth issue is a different kind
  of blocker than "implementation is wrong".
- Once the harness loop ticket lands, the agent flows through
  `implement → open-pr` automatically and stops at `review`. No
  re-launch needed for the PR step. Today's monolithic skill
  obscures that boundary.
- Per-step assignee declaration (prerequisite ticket) is more
  expressive when there are real handoff points to declare on.

## Fix

Edit `relay-os/workflows/code/with-review.md` to:

```yaml
---
name: code/with-review
description: Code change implemented by an agent, PR opened by an agent, reviewed and merged by a human.
steps:
  - name: implement
    skill: code/implement
  - name: open-pr
    skill: code/open-pr
  - name: review
    assignee: owner
---

## review

Human reviews the open PR. Edit, request changes locally, or merge
when satisfied. After merging, run `relay bump` to mark the task
done.
```

Then drop the "edit assignee:" instruction from `code/open-pr`'s
SKILL.md — the workflow declares the handoff now, the skill just
runs `relay bump`.

## Existing tickets impact

Tickets currently mid-flight on `code/with-review` are unaffected:
the workflow snapshot is frozen into ticket frontmatter at create
time. Only *new* tickets created against this workflow get the
three-step shape.

## Tests / fixture

- Update `example/` fixture if it seeds a `code/with-review` ticket.
- Re-run `relay validate --json` against example.
- No new unit tests strictly required (the workflow change is data,
  not code), but a smoke test that creates a ticket on the new
  workflow and bumps through it end-to-end is worth having.

## Out of scope

- Adding `code/self-review` to the workflow. Useful but separate.
- Deleting `code/implement-and-pr` skill. Other workflows might
  still want the monolithic shape; leave it in place until proven
  unused.

## Order

Lands after `declare-per-step-assignee-…` (so `assignee: owner` on
the review step is meaningful). Could land before the harness-loop
ticket — it's data only, no behavior change beyond the new step
shape.
