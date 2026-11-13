## Rollout 0

I’ll check the ticket and skill locations to identify what selected the current instructions, without changing any files.

---

1. The effective source is [coga/skills/trial/write/SKILL.md](/tmp/coga-prompt-trial-667707cc/coga/skills/trial/write/SKILL.md). The ticket’s current step is `write`, whose `skills` list selects `trial/write`; that makes the workflow’s inline `write` prose dormant.

2. Edit that same skill file to customize how the result is written. It owns the active instructions to write `ready` to the sibling `result.txt` and verify it.

No files changed; four files read.