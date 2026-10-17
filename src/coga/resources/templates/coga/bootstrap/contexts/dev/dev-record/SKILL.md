---
name: dev/dev-record
description: Compatibility context for existing tickets that attach the former Dev-record guide, pointing to the current contract owners.
---

# Dev record compatibility

This context remains bundled so existing tickets with `dev/dev-record` in
`contexts:` continue to validate and launch after an upgrade. New tickets
carry their writing guidance in the annotated ticket template; see
[ticket authoring](../../coga/tickets/authoring/SKILL.md).

The ticket's `## Dev` record links its branch, PR, and optional sandbox clone.
Current contracts live in [PR publication](../../coga/internals/pr-publication/SKILL.md)
(record parsing and publication), [workflows](../../coga/workflows/SKILL.md)
(completion gates), and [checkouts](../checkouts/SKILL.md)
(where to write and reconcile the record). Follow those owners when changing
behavior; this compatibility topic does not duplicate their specifications.
