---
title: Correct README claims about prompt report output
status: in_progress
owner: nicktoper
workflow:
  name: docs/with-review
  steps:
  - name: implement
    skills: []
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills: []
    assignee: agent
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
agent: claude
launch_generation: 16f4620f-d064-4e83-a7f4-114471a8382c
---

## Description

The README says `coga launch --prompt-report` "shows the exact prompt before anything runs." That is false: the flag prints a table of composed prompt layers with byte sizes and approximate token counts, then exits without launching. It does not print prompt text.

Correct that README sentence so it describes what `--prompt-report` actually shows, with a runnable, target-specific example (e.g. `coga launch <slug> --prompt-report`). Scope is the factual documentation correction only, decided with the owner on 2026-10-08: do not add a full-prompt output option. If no existing command prints full prompt text, say nothing that implies one exists. Done when the README wording matches the output of a representative invocation and claims no unavailable functionality.

## Context

### Report relayed by the owner — 2026-10-07

Another AI reports that --prompt-report lists layers and token estimates, and found no full-text output option. Intake confirms README.md claims it “shows the exact prompt before anything runs.” Verify the current command surface before deciding whether any existing way to inspect full text can be documented.

Read coga/prompt-composition (`docs/contexts/coga/prompt-composition/SKILL.md`) and coga/launch (`docs/contexts/coga/launch/SKILL.md`), cited rather than attached; inspect the report contract. Start with README.md, `src/coga/commands/launch.py`, `src/coga/compose.py`, and CLI help. This ticket does not fix body-section omission, which belongs to autofix-write-ups-lose-their-body-to-h2-headings.

### Verified at authoring — 2026-10-08

- The claim is the `--prompt-report` sentence in README.md's "Everything is inspectable and hackable" bullet (near line 34 as of this writing).
- `coga launch --help` describes the flag as "Print composed prompt layers and approximate token counts, then exit without launching." Match that contract; the option is defined in `commands/launch.py` and rendered by `_format_prompt_report` over `compose.compose_prompt_report`.
- No other `launch` flag or top-level command prints the full composed prompt text.
- `--prompt-report` is not write-free. On 2026-10-08 it swept state, committed "Sync coga state", and pushed to origin/main from a draft ticket (`dev/checkouts` documents the sweep and the `.agent-skills/` regeneration). Do not run it in the shared checkout. To get a representative invocation, use an isolated fixture repo or call `compose.compose_prompt_report` directly, which `dev/checkouts` names as the write-free view.
- `--prompt-report` refuses script targets (`ticket.py`). The replacement wording must not imply it works on every target.
- Already-correct wording to stay consistent with: `docs/contexts/coga/first-task/SKILL.md` and the `--prompt-report` passage in `docs/contexts/coga/launch/SKILL.md`.
- Re-verify these facts against the tree you work from before editing.
- Out of scope: adding a full-prompt output option; editing contexts or the packaged templates unless they repeat the same false claim (grep for "exact prompt" to check).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
