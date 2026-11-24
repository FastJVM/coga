---
name: code/peer-review
description: Independently review the committed change and record the reviewed head.
---

Read the ticket and its `## Dev` record. Switch to the recorded branch
if needed and stop if Git refuses. Read `coga/git` and
`coga/pr-publication/preparation`.

Review the full diff against the recorded base. Check normal entry points,
behavioral changes, data compatibility and failure paths. Run the required
verification. Discuss blockers through session conduct. Apply and commit
must-fix corrections, then review and verify the resulting head.

Record the review method, actual reviewer identity, conclusions and
verification receipts in `## PR`. Record the approved full HEAD OID as
`reviewed:` under `## Dev`, preserving the other fields. Stop when you
cannot approve that head. Otherwise bump with the handoff ready.

The step assigns a reviewer role. In the review receipt, record the actual reviewer
identity and disclose any overlap with the implementation session.
