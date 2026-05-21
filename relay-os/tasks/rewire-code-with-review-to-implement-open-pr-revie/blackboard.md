The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: rewire-with-review-three-steps
pr: https://github.com/FastJVM/relay/pull/84

## Notes

- Edited `relay-os/workflows/code/with-review.md` to the new three-step shape:
  `implement` (skill: `code/implement`) → `open-pr` (skill: `code/open-pr`)
  → `review` (assignee: `owner`).
- Edited `relay-os/skills/code/open-pr/SKILL.md` to drop the
  manual `assignee:` rewrite step. The workflow now declares
  `assignee: owner` on `review`, so role rewrite happens on bump.
  Also removed the hardcoded "merge" step name from the skill so the
  same skill can be reused by workflows that name the next step
  differently (we use `review`).
- Did *not* touch `relay-os/skills/code/implement-and-pr/` — left in
  place per the ticket's "out of scope" note.
- Did *not* touch `example/relay-os/workflows/code/with-review.md`.
  That fixture is its own four-step demo (`implement → pr → approve →
  merge`) that exercises the per-step `assignee:` schema. The smoke
  test relies on its current shape (`for _ in range(4)`, "advanced to
  step 2 (pr)").
- Tests: `python -m pytest` → 207 passed.
- Validate: `relay validate --json` → 30 ok, 0 issues.

## Existing in-flight tickets

The frozen workflow snapshot in their frontmatter is unaffected — only
*new* tickets created against `code/with-review` get the three-step
shape. That matches the ticket's "Existing tickets impact" section.

## Retro

status: processed
skill: retro/done-ticket
result: no-new-durable-knowledge
title: No new durable knowledge for rewire-code-with-review-to-implement-open-pr-revie
