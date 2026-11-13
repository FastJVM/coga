## Rollout 0

I’ll check how this task selects its step instructions, using at most four file reads and making no changes.

---

1. The effective source is [coga/skills/trial/write/SKILL.md](/tmp/coga-prompt-trial-667707cc/coga/skills/trial/write/SKILL.md). The ticket’s current step is `1 (write)`, whose `skills` list selects `trial/write`. That selects the skill’s instructions; the workflow’s inline `write` prose is dormant.

2. Edit that same `SKILL.md` to customize how the step writes its result, because it owns the active writing instructions. Editing the inline prose in `coga/workflows/trial/skilled.md` would have no effect while the step selects a skill.

Read three files; changed none.