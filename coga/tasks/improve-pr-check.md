---
title: improve PR check
status: draft
owner: nicktoper
workflow: code/with-review
---

## Description

Make Coga-generated PRs clear enough for the owner to choose quickly between
merging without rereading, reading the description, and reviewing the diff in
detail. Titles should describe the actual change, identify the authoring and
reviewing agents, and indicate a recommended review depth; descriptions should
justify that recommendation, reproduce the ticket verbatim, explain the
implementation and any departures from the request, describe each changed file,
and report which tests ran and their results. Test requirements belong to the
applicable workflow: this change must not introduce a universal full-suite gate,
and skipped or unrun tests must be visible with a reason. Done means the normal
PR publication flow produces this presentation from actual task and change
evidence, with representative examples demonstrating all three review depths
and explicit reporting when tests or an independent review were not performed.

## Context

- The owner currently cannot choose a review depth from the PR list and has to
  open and investigate each PR. Make the title useful for that first decision,
  and put the short explanation at the top of the body. The recommendation is
  advisory; merging stays the owner's decision. Passing tests alone does not
  justify recommending that the owner skip review. Define the review-depth
  rubric before implementing formatting, with examples showing the evidence
  supporting each recommendation.
- Show actual author/reviewer identities, not simply the GitHub account used
  to publish. A configured agent or peer is not evidence that it performed
  the work: launch overrides and self-review exist. Report unavailable identity
  or absent independent review honestly. Keep the title readable; select a
  compact convention during implementation and show examples for review.
- Reproduce the ticket's title, Description, and Context as written at PR
  preparation time, in a clearly separated, preferably collapsible section.
  This is a snapshot of the requested work, not a paraphrase by the agent.
  Omit operational frontmatter and the blackboard, including the generated PR
  body itself. Keep the agent's commentary outside that snapshot, identifying
  what was delivered, any deviations, and remaining limitations.
- Explain every changed file using the actual PR diff against its base,
  including additions, deletions, and renames. A compact table is suitable;
  identical explanations may group files only if every path remains visible.
  Explain why each change belongs, not merely its diff statistics.
- Report the checks actually run, their commands and outcomes, and distinguish
  passed, failed, pending, and not run. Explain omissions or inapplicability;
  do not turn absent evidence into success. Preserve test obligations already
  imposed by the selected workflow. Broader test-policy redesign, mandatory
  full-suite execution for every PR, merge automation, and repository-wide
  GitHub branch-protection changes are outside this ticket.
  Tie test and review evidence to the published change; later edits must not
  inherit an unsupported claim that the current diff passed tests or review.
- Start with `open_pr._pr_body` and `open_pr.open_pr` in
  `src/coga/open_pr.py`, plus `tests/test_open_pr.py`. Currently the command
  uses the ticket title directly and prefers an agent-authored `## PR` body,
  then falls back to Description/title and appends the ticket closure marker.
  Keep deterministic extraction/formatting in the existing publication path;
  review-depth judgment and explanatory prose belong to the agent's preparation
  step. Missing evidence must remain legible in fallback output, too.
- Read the body-authoring instructions in `coga/skills/code/implement/SKILL.md`,
  `coga/skills/code/self-qa/SKILL.md`, `coga/skills/code/open-pr/SKILL.md`, and
  the bundled workflows under
  `src/coga/resources/templates/coga/bootstrap/workflows/code/`. Update the
  applicable instructions together so different code workflows produce the
  same presentation. Account for a rerun that finds an existing PR: the
  presentation must not silently remain stale after the prepared title/body
  changes, and intentional human edits must not be silently lost. Define how
  generated content is distinguished from human edits and verify both cases.
  General shortening of the shared implementation, publication, and review
  skills is separate maintenance and outside this ticket.
- `coga/internals/pr-publication`, at
  `docs/contexts/coga/internals/pr-publication/SKILL.md`, is cited rather than
  attached because it is an editing target. Read its introduction and
  "Checks, in order": publication already owns branch checks, push, PR reuse,
  and recording `pr:`; preserve those guarantees and the URL-only stdout
  contract while changing presentation. Update this owning topic and any
  affected skills/workflows together with their packaged twins. Use focused
  publication tests and the packaging twin check to verify the changes.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
