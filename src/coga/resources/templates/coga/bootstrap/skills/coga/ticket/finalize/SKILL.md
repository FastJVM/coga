---
name: coga/ticket/finalize
description: Validate local changes at the end of guided ticket authoring.
---

# Ticket Authoring Finalize

After a successful authoring interview, `coga ticket` validates the affected
local tickets and checks that a draft has a workflow. If validation fails,
keep the edits and resolve the reported issue before activating the draft.

Use [coga/git](../../../../contexts/coga/git/SKILL.md) to share the changes.
The command runs finalization directly.
