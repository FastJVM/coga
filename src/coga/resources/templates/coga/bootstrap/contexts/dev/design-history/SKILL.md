---
name: dev/design-history
description: How a ticket keeps its body describing only current work when the direction changes, archiving abandoned plans in one `## Superseded designs` blackboard section that launch prompts replace with a pointer.
---

# Design pivots and superseded plans

The ticket body is the contract for current work. When the direction changes,
rewrite the body so it describes only what an agent should execute now. Keep
live requirements, including acceptance criteria and proposed shape, inside
`## Description` or `## Context` (use `###` subheadings); other top-level body
sections are omitted from launch prompts
([coga/prompt-composition](../../coga/prompt-composition/SKILL.md)). Do not mix
a dead alternative into the live plan or leave Git history as its only
explanation.

## The archive section

Move the abandoned direction below the blackboard fence into exactly one
`## Superseded designs` section. Reuse it for every later pivot and append
entries oldest to newest:

```markdown
## Superseded designs

### YYYY-MM-DD — <short name of the abandoned direction>

Superseded by: <the current direction or decision>

Reason: <why the ticket pivoted>

<the prior description, proposed shape, acceptance details, and evidence worth
retaining>
```

Keep enough of the old design to understand or reconsider it. Keep retained
headings at `####` or deeper inside each entry so copied sections cannot
escape the archive. Do not scatter history under headings like
`## Design pivot`, `## Open threads`, or `## Previous plan`.

If rewriting the body would hide context a reviewer needs, the body may carry
one short index pointer, such as
`> Design history: pivoted on YYYY-MM-DD; see ## Superseded designs below.`
The design itself stays in the blackboard section.

## How Coga treats it

- Draft-authoring cleanup preserves the section, and draft activation excludes
  only this section from its authoring-note checks; unrelated scratch still
  needs synthesis.
- Launch leaves the stored archive unchanged and composes a short pointer to
  the ticket file instead of the archived text
  (`blackboard.blackboard_for_prompt`). Keep current decisions and their
  reasons in the live body or blackboard; an agent reads history only when it
  deliberately follows the pointer.

## Recognition

Recognition is deliberately narrow and shared by composition and the draft
synthesis gate:

- The heading must be exactly `## Superseded designs` at the start of a line,
  case-sensitive, with optional trailing spaces or tabs.
- The section ends at the next ATX level-1 or level-2 heading outside a fenced
  code block, or at end of file. Deeper headings stay inside.
- Setext underlines (`===`, `---`) are not boundaries, because blackboards use
  `---` as a separator. Write the heading that ends the archive in ATX form.
- Similar names, indented headings, prose mentions, and fenced examples do
  not start an archive.
- Every exact section is excluded if a ticket has duplicates, but keep one.
