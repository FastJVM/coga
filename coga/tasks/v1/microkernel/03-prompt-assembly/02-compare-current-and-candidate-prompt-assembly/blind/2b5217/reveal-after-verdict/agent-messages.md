## Rollout 0

I’ll check the task’s step selection and instruction sources, reading no more than four files and making no changes.

---

1. The effective source is [coga/skills/trial/write/SKILL.md](/tmp/coga-prompt-trial-667707cc/coga/skills/trial/write/SKILL.md). The ticket’s current step is `1 (write)`, whose frozen workflow entry specifies `skills: [trial/write]`; that selects the skill instead of the workflow’s dormant inline prose.

2. Edit that same **SKILL.md** to customize how the result is written. It owns the active writing instructions; changing inline prose in `coga/workflows/trial/skilled.md` would have no effect on this skilled step.

No files were changed.