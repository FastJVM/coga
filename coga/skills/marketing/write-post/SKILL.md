---
name: marketing/write-post
description: Produce one selected Coga post from an approved brief — objection check, outline, draft, craft review, claim checks, replies and preparation for owner publication.
---

# Write a Coga post

This skill produces a post after the owner has selected it in the current
campaign. It does not select the campaign or inherit the previous essay
sequence.

Read the selected ticket and the relevant current homes:

- `marketing/plan` — the selected deliverables, purpose, prerequisites and
  owners. During fresh planning it lists open decisions instead.
- `marketing/positioning` — the reviewed message and source limits.
- `marketing/distribution` — the selected channel/measurement policy and
  dated account evidence, when channel work is needed.

Use earlier campaign references for inspiration only. Never promote their
post numbers, strategic fork, channel ordering, scorecard or gates into the
current brief.

## Entry condition

The owner has selected this post and its ticket states the intended reader,
desired response, central idea, scope and relationship to the campaign.
Resolve missing choices with the owner under the current session conduct.
A candidate ticket or a historical brief alone does not meet this condition.
The inventory and story-selection tasks do not run post production.

## The division of labour with clarity

`coga/skills/clarity/SKILL.md` is the imported prose-craft dependency.
This skill owns briefing and the first draft. At the craft step, use clarity's
rewrite, review and lint modes. Its co-write interview is not needed for an
already approved brief. If an individual passage lacks support or authorship,
the short existing-draft probe in `references/interview.md` can clarify it.

Invoke clarity by reading the skill, not a slash command. Resolve its
`references/` and `scripts/` paths against `coga/skills/clarity/`.

## Step 1 — Brief

Record one paragraph on the blackboard: reader, desired response, one central
idea, scope/exclusions, chosen format and the channels currently selected for
this piece. Use a post number or phase only if the new campaign defines one.

Resolve a brief containing two competing central ideas before outlining.
Do not make a new campaign decision inside the writing task.

## Step 2 — Test the thesis

Write the strongest relevant reader objection and the actual product
limitation that bears on this idea. Check the product references and source
limits in positioning; do not invent a weaker objection.

For each, decide whether the post answers it, concedes it or leaves it out
with a reason. Identify where each answer or concession will appear before
moving on.

## Step 3 — Outline and support

Build an outline from the selected brief. Attach support to every factual
beat and label authored illustrations. Previously written five-beat arcs and
post-specific requirements apply only if the owner selected them for this
piece.

Observed-event claims need public, checkable sources. An illustration can
explain an interaction without asserting it happened. For a claim of context
reuse, prompt inclusion proves delivery; later behavior must support the
claimed reuse. Narrow or reframe a passage if its evidence is missing.

Resolve any missing structure or required support before drafting. There is
no token experiment or historical-incident quota.

## Step 4 — Draft

Write in the chosen voice. Mark a missing fact or author input as
`[TK: specific question]` rather than inventing it. Resolve each marker from
a source or owner input, or cut/reframe the dependent passage.

Finish with a complete draft and no unresolved markers. When input is needed,
follow the attended/unattended session conduct rather than silently parking
the question.

## Step 5 — Craft pass

Read clarity and apply:

1. **rewrite** mode with `references/edit.md`, plus `longform.md` for an
   essay and `medium.md` for marketing prose as the skill directs;
2. **review** mode, recording each finding and its disposition;
3. **lint** mode, using `scripts/strip_markdown.py` and
   `scripts/prose_stats.py`, then reading each flagged passage.

Treat lint as a prompt to reread, not a score to optimize. Resolve review
findings or give a reason for leaving them before proceeding.

## Step 6 — Check claims

Read the publishable draft for factual claims and numbers. Check that each
source supports the claim at its stated scope and date. Separate observation,
interpretation, product thesis and illustration.

Use `marketing/positioning` for the source limits: private-repo quotations,
invented results, unsupported efficiency claims and measured productivity
multipliers are excluded. The token/time experiment remains dropped.
A public context example does not establish a comparative saving. Preserve
contrary evidence and narrow the claim if necessary.

Finish with supported claims, accurately labeled examples and the relevant
product caveats in the draft. Do not move an unsupported claim into a reply
or title.

## Step 7 — Prepare replies

Write full replies for the objections identified in step 2 and the obvious
questions the chosen piece raises. The previous campaign's standing replies
are available as inspiration; inherit only what fits the new piece.

Finish the replies before publication. A reply must meet the same source
and claim checks as the post.

## Step 8 — Prepare selected channels and verify publication

Read the current campaign and selected distribution policy. Prepare the
owner-approved titles, channel copy, links, order and timing for this piece.
Do not assume a blog-first or Bookface-before-HN sequence unless the new plan
chooses it. If channels or order are undecided, resolve them with the owner.

Verify current rules and required account/link checks for the selected
surfaces, including the founder availability needed for replies. Share links
without soliciting votes. The agent prepares the package; publication and
personal-account actions need explicit owner authorization.

After authorized publication, record the actual URLs and timestamps and
handoff the selected measurements to their named owner or follow-up ticket.
Do not create the former day-14 gate or retrofit its numeric thresholds.

## Completion checks

- The selected brief is clear and its central idea is coherent.
- Objections and limitations have explicit dispositions.
- Factual beats and claims have appropriate support; illustrations are labeled.
- No unresolved draft markers remain.
- Clarity review findings are resolved or explicitly declined with reasons.
- Replies, titles and channel copy meet the same claim checks as the post.
- Publication follows the selected plan and explicit authorization.
- Observations are handed to the owner of the selected measurement plan.

The current plan owns campaign choices, positioning owns the reviewed
message and source limits, and distribution owns selected channel policy.
General prose craft stays in clarity. Historical campaigns remain linked
references outside the current brief.
