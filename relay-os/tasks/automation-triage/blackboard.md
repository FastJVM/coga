The blackboard is a notepad to be written to often as the human and agent works through a task.

## Notes for the implementer

The ticket is fully specced — read it; this is just orientation.

- **Source method:** the post cited in the ticket *is* the rubric. Don't re-derive.
- **This ticket = rubric + tiers only.** Ships the `autonomy/triage` context + the
  four `autonomy/` tier workflows (3 moved from `browser/`, 1 new `assist-only`),
  and repoints `build-automation`'s moved tier paths. It does **not** wire the
  test into any flow — that's the follow-up. So nothing consumes `autonomy/triage`
  yet; that's intended.
- **build-automation triage is a separate concern** — leave its logic untouched;
  only update the moved tier paths.
- **Move is path-safe** (verified at authoring): no `workflow:` field binds a
  moved tier, no tests reference tier names, `validate.py` has no tier whitelist.
  `name:` is display-only, not used for resolution.
- **Done check** is in the ticket: `relay validate --json`, grep for stale
  `browser/<tier>` refs, single-token assignees, follow-up filed as draft.

(Full bootstrap/eval history was trimmed once the ticket stabilized — it's in git
history if needed.)
