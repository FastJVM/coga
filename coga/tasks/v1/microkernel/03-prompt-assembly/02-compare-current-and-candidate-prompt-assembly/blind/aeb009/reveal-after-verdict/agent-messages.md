## Rollout 0

You’re editing `author-paused` (status: `paused`). I’m using the supplied `bootstrap/ticket` skill to refine the ticket while preserving its paused state.

---

What would you like to change in `author-paused`? I’ll preserve its paused status, current workflow step, and existing owner note.

---

I’ll add the sentence to `## Description`, preserving the paused status, current step, frozen workflow, and owner note. I’ll only check the ticket edit; I won’t run the work.

---

Added “Verify the output before handoff.” to the Description in [ticket.md](/tmp/coga-prompt-trial-667707cc/coga/tasks/author-paused/ticket.md).

Verified that paused status, current step, frozen workflow, and owner note are unchanged. No work was run.

---

Confirmed. `author-paused` remains paused at its current step. Nothing was advanced.
## Rollout 1

Approved for the authorized scope. The diff adds exactly “Verify the output before handoff.” to Description.

Paused status, step `1 (write)`, frozen workflow, contexts, skills, and unrelated owner note are preserved. Verification fits the existing write-then-owner-judge workflow without expanding scope. The agreed result remains unspecified, an existing limitation rather than one introduced by this edit. Prompt-size review was unavailable.