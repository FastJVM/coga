---
name: code/split-ticket
description: The one contract for splitting an oversized ticket into sibling drafts — outcome-named `coga create` drafts with their complete body, a `## Split` record on the source, a `Split from` cross-link, co-equal versus sequenced order, and narrowing or canceling the source. Composed alongside `code/design` and `code/implement`.
---

# Splitting a ticket

Split when the honest scope is more than one PR, or when two concerns that
would merge separately are coupled under one ticket. The steps that can reach
that decision (`code/design`, `code/implement`) compose this skill beside their
own; it is the only owner of the mechanic.

1. **Siblings are drafts made by `coga create`, complete when created.** Run
   it from the checkout you bump from, in the source ticket's own directory
   (`coga create "v2/<title>" --description "…"` when the source sits under
   `v2/`). `coga create` publishes the draft to control as soon as it writes
   it, and no later step publishes a hand edit to a sibling, so everything the
   sibling needs goes in `--description`: the cross-link of rule 3, then the
   slice it owns. Do not edit a sibling after creating it. The slug is
   whatever `coga create` makes of the title, so give each sibling a title
   that names its own outcome — no shared prefix, numbering, or "part 2 of …":
   `slugify` truncates at 50 characters and the slug never changes, so the
   relationship lives in the body, not the filename. Create sequenced
   siblings in order, so each successor can name a prerequisite that already
   exists. Do not activate a sibling; scheduling stays with the owner.
2. **Record the split under one blackboard heading, `## Split`, on the source
   ticket.** Date it, mark the whole split `Co-equal` or `Sequenced`, and give
   one line per sibling: its exact path-qualified slug and the slice it owns.
   This is the split's roster; the source's own terminal action publishes it.

   ```markdown
   ## Split

   Sequenced (2026-09-16). The source keeps slice 1.

   1. `define-the-report-durability-contract` — the contract itself
   2. `cite-the-report-contract-from-the-period-context` — after 1, the
      context rewrite that cites it
   ```
3. **Cross-link from every sibling in its composed body.** Each sibling's
   `--description` opens with a bold paragraph that survives the source
   ticket's deletion:

   ```markdown
   **Split from `<source-slug>` (<date>).** After: `<prerequisite-slug>`.
   ```

   `After:` appears only on a sequenced successor and names the one sibling
   that must merge first. The paragraph names no other siblings: an earlier
   draft cannot know a later one's slug, and the source's `## Split` holds the
   full roster. A ticket whose `## Description` opens this way is the only way
   a later reader learns the split existed once the source is retired.
4. **Co-equal versus sequenced.** *Co-equal* siblings are independently
   mergeable in any order; the cross-link is all they need. *Sequenced*
   siblings depend on a predecessor's merge, and that order stays prose until
   the successor is activated, because a draft cannot be blocked. When you
   pick up a successor whose `After:` ticket is not yet `done`, run
   `coga block --task <successor> --reason "Needs <exact prerequisite slug> merged first"`
   as the terminal action: that ask is the declared dependency, and the
   megalaunch dependency drain retries the successor once the prerequisite
   finishes. Do not invent a `dependencies:` field or a second heading.
5. **Narrow the source or retire it.** If the source keeps a slice that fits
   one PR, rewrite `## Description` to that slice and continue the step. If
   nothing remains, `coga mark canceled <slug> --message "Split into <a>, <b>"`
   and stop: that is the intentional-abandonment transition, and it releases a
   queue. Never leave the source describing work its siblings now own.
