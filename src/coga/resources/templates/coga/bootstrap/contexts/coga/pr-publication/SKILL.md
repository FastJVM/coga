---
name: coga/pr-publication
description: Open a reviewable PR using the declared Git workflow script and the ticket's evidence.
---

# Open the ticket's PR

Use `run: git/push-and-open-pr` in a code workflow. It reads the ticket's
`## Dev` record and commits, pushes, and opens the PR from the current branch.
The human and agent responsibilities are in [coga/git](../git/SKILL.md).

The script requires committed implementation changes. It pushes state and
checks GitHub for a PR on the recorded branch. It reuses an open PR on the
recorded base and readies a draft. A closed PR, wrong base, or failed Git or
GitHub operation stops the step. An already pushed branch or open PR can be
reused when retrying a partial run. Configure push access and authenticate
`gh` beforehand.

For a new PR the script renders the ticket's request, actual files changed,
and recorded evidence. Review and checks apply to their recorded revisions.
Follow [PR preparation](preparation/SKILL.md) for the evidence schema and
review recommendations.
