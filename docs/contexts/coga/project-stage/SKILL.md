---
name: coga/project-stage
description: Dated posture for Coga's current stage — pre-product, testers only, high volatility — telling agents how aggressively to change things and when this posture expires.
---

# Coga — project stage

Last reviewed: 2026-09-22. **Pre-product. Testers only (the owner and a small
crew). No real users.** The owner verifies this premise; the planned V1
Show HN launch ([`marketing/plan`](../../marketing/plan/SKILL.md)) is the
expected point at which the expiry below trips.

This context governs *posture*, not principles. The principles
([`coga/principles`](../principles/SKILL.md)) are permanent; this posture
expires.

## Move fast

- Any spec, command name, file format, frontmatter field or directory layout
  may change when the new design is better. No RFC and no migration window:
  change it and update affected tickets and configuration in place.
- Precedent: `coga step` → `coga bump` and the removal of `task.lock` shipped
  without ceremony.

## Compatibility is migration-only

- No open-ended deprecation shims and no second supported surface for old
  behavior.
- Superseded config spellings fail loud rather than lingering as upgrade aids;
  do not keep a second path that warns only when someone validates.
- No `_legacy` fields, no migration scripts for ticket frontmatter (edit the few
  tickets by hand), no "rename but keep the old name working", no feature flags
  gating new behavior.
- A bounded migration for a surface Coga itself shipped is acceptable.

## No premature generality

- Three similar lines beat an abstraction; the right shape is not yet known.
- Inline the second use; extract on the third real caller.
- "What if someone wanted X?" — build it when a real person hits a real wall.

## Bias toward deletion

- When in doubt, remove the feature, flag, option, config field or command.
  "Small surface, sharp behavior" beats "big surface, fuzzy behavior".
- Delete with evidence and record reversals when they happen, so a later
  cleanup does not delete a survivor twice. Recorded reversals are in
  [`docs/archive/superseded-decisions.md`](../../../archive/superseded-decisions.md).
- Restoring half of a removal is a scoped partial revert, not `git revert`
  (which resurrects the half that should stay dead). Restore the scoped files
  verbatim from the removal's parent (`git show <removal>^:<path>`) and verify
  them byte-identical; for files that drifted since, re-add the mentions on top
  of current text, which wins on conflict. Re-check restored templates against
  conventions that changed in between, and restore the tests the removal
  deleted.

## Code review

Push back on a PR that adds a deprecation, a backwards-compatibility path, a
feature flag or an abstraction "for future use", unless it is a bounded
migration for a surface Coga shipped or there is a concrete user-blocking
reason. The default answer is still "rip it out".

## Expiry

Retire or rewrite this context when either holds:

- Coga has one or more real (non-tester) users; or
- a breaking change actually breaks someone's workflow, so a migration story
  is genuinely needed.

Until then: ship the right design, edit the few tickets that exist, move on.
Current work is in [`coga/current-direction`](../current-direction/SKILL.md)
and [`coga/roadmap`](../roadmap/SKILL.md).
