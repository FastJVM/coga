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

## No backwards-compat hacks

- No deprecation shims (e.g. an old command name calling into the
  new one).
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
- Watchers were removed without ceremony. Same energy applies
  elsewhere.
- "Small surface, sharp behavior" beats "big surface, fuzzy
  behavior."

## What this means for code review

If a PR adds a deprecation, a backwards-compat path, a feature
flag, or an abstraction "for future use" — push back unless there's
a concrete user-blocking reason. Default answer is "rip it out."

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
