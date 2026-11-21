---
name: code/self-qa
description: Review and verify your implementation before the PR step.
---

Switch to the recorded `branch:` if needed and stop on Git errors. Read
`coga/git` and `coga/pr-publication/preparation`. Review the whole diff
against the base, fix and commit substantive findings, and run the
repository's required checks on the resulting head.

Record the review method, findings and final verification under
`## Self-QA` and update the structured `## PR` receipts. Attribute the
review as self-review and report any check you omitted. Bump once the
handoff is ready.
