---
name: coga/project-stage
description: Posture for coga's current stage — pre-product, no real users, high volatility. Tells the agent how aggressive to be. Temporary context; delete when coga has actual users.
---

# Coga — project stage

**Pre-product. Testers only (nick + small crew). No real users.**

This context governs *posture*, not principles. The principles
(fail loud, legibility, classical mode) are forever. The posture
below has an expiry date — when coga has paying or even
non-tester users, this context gets deleted, not edited.

## Move fast, break things

- Any spec, command name, file format, frontmatter field, or
  directory layout can change on a whim if the new design is
  better. No RFC, no migration window. Just change it and update
  affected tickets/configs in place.
- Moving `contexts/` to live next to tasks would be fine if the
  design were better. (We already shipped a rename — `coga step` →
  `coga bump` — and a primitive removal — `task.lock` — without
  ceremony.)

## Compatibility is migration-only

- Do not add open-ended deprecation shims or preserve old behavior as a second
  supported product surface.
- Superseded config spellings fail loud instead of remaining as upgrade aids.
  Use the current surface explicitly; do not keep a second path that warns only
  when an operator remembers to validate it.
- No `_legacy` fields kept around "in case."
- No migration scripts for ticket frontmatter — edit the few
  existing tickets by hand.
- No "rename but keep the old name working." If we rename, we
  rename.
- No feature flags gating the new behavior. Just ship the new
  behavior.

## No premature generality

- Three similar lines beats an abstraction. We don't yet know what
  the right shape is, so abstractions calcify the wrong shape.
- Inline the second use; extract only on the third real caller.
- "What if someone wanted X?" — they don't. There is no someone.
  When a real person hits a real wall, then build it.

## Bias toward deletion

- When in doubt, remove the feature, the flag, the option, the
  config field, the command.
- The precedent list, kept so a later cleanup does not delete a survivor a
  second time. Watchers were removed, reintroduced for mapped Slack cc
  mentions, and removed again in the ticket-format simplification (PR #784)
  once it was clear no ticket ever populated the field. `coga build` was
  removed with `coga project` (PR #691) and deliberately restored three days
  later (PR #701, "we want the build back with the skills; it was useful"),
  while `coga project` stayed gone — so the removal ticket's "no references
  remain" is true for only half of what it removed. Apply the same
  evidence-first standard elsewhere: delete freely, and record the reversal
  when one happens.
- Restoring half of a removal is a **partial revert, not `git revert`**: a
  whole-commit revert resurrects the half that should stay dead. Bring back
  the scoped files verbatim from the pre-removal parent (`git show
  <removal>^:<path>`) and verify them byte-identical; for files that drifted
  since the removal, re-add the mentions on top of current text rather than
  restoring old prose wholesale — current text wins on conflict. Re-check any
  restored template against conventions that changed in between, and restore
  the tests the removal deleted alongside the code.
- "Small surface, sharp behavior" beats "big surface, fuzzy
  behavior."

## What this means for code review

If a PR adds a deprecation, a backwards-compat path, a feature flag, or an
abstraction "for future use" — push back unless it is a bounded migration for
a surface Coga itself shipped or there is a concrete user-blocking reason.
Default answer is still "rip it out."

## Expiry

Delete this context when:

- Coga has 1+ real (non-tester) user, OR
- A breaking change actually breaks someone's workflow such that
  we genuinely need a migration story.

Until then: ship the right design, edit the few tickets that exist,
move on.

## What this context does NOT cover

- Timeless principles — see `coga/principles`.
- What's currently being worked on — see `coga/current-direction`.
