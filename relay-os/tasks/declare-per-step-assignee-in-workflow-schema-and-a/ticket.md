---
title: Declare per-step assignee in workflow schema and apply on bump
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/codebase
- relay/cli
- relay/architecture
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement-and-pr
  - name: review
---

## Description

Today, `relay bump` only advances `step:`. Assignee changes between
steps are done by the agent hand-editing `assignee:` frontmatter as
part of the skill body — see `code/implement-and-pr` step 9
("Edit the ticket's `assignee:` frontmatter to the ticket's
`owner:`"). Two operations, not atomic; relies on the agent
remembering to do it; not declarative.

The ownership shape of a workflow belongs in the workflow file. A
human reading `code/with-review.md` should see at a glance which
step is the agent's and which is the human's, without grepping
through skills.

This ticket also unblocks the harness-loop work (separate ticket):
the loop's "is this still my step or did it hand off?" check needs
to be a deterministic read of workflow data, not a "did the agent
remember to update frontmatter" check.

## Fix

Add an optional `assignee:` field to workflow step entries:

```yaml
steps:
  - name: implement
    skill: code/implement
  - name: open-pr
    skill: code/open-pr
  - name: review
    assignee: owner
```

Values:

- A concrete nickname (`nick`, `claude2`, …) → on bump into this
  step, set ticket `assignee:` to that.
- The literal token `owner` → resolve at bump time to whatever the
  ticket's `owner:` field says. Most natural for human-review steps.
- Absent → bump leaves `assignee:` unchanged. Existing workflows
  unaffected.

Implementation:

- `src/relay/workflow.py` (or wherever step schema is parsed) —
  accept the new optional field.
- `src/relay/commands/bump.py` — after computing `next_step`, look
  up `next_step.get("assignee")`. If present, resolve `owner` → ticket
  `owner:`, otherwise pass the literal value, and write to
  `ticket.frontmatter["assignee"]` alongside the `step:` update.
- Slack post on bump should mention the assignee change when one
  occurred, e.g. "advanced to step 3 (review) → assigned to nick".

Add `relay bump --assignee <name>` as an explicit override flag for
unusual cases (skip workflow's declaration). Optional but cheap.

## Spec / docs

- `docs/spec.md` workflow schema section needs the new field.
- `relay/architecture` context needs a one-liner on per-step assignee.

## Tests

- Bump into step with concrete assignee → ticket assignee updated.
- Bump into step with `assignee: owner` → ticket assignee = ticket owner.
- Bump into step with no assignee declared → ticket assignee unchanged
  (back-compat).
- `--assignee` flag overrides the declared value.

## Out of scope

- Removing manual "edit assignee" instructions from existing skills.
  That happens in the workflow-rewire ticket
  (`rewire-code-with-review-to-…`), where the new
  split-skill workflow declares assignees and the skills lose those
  instructions.
- Validating that assignee values resolve to a known nickname in
  `relay.toml`. Useful but separate concern.

## Open question

Should `assignee: owner` be the only special token, or do we also
want `assignee: agent` / `assignee: human` for role-typed handoffs
that aren't tied to the specific creator? Defer unless a real use
case shows up — `owner` covers the dominant pattern.
