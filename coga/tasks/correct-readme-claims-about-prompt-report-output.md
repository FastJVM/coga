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
step: 3 (open-pr)
agent: claude
launch_generation: 7c2008d2-c33c-4e5a-9398-605ac66c5a73
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

## Dev

branch: docs/correct-prompt-report-readme (pushed; commit "Correct README description of --prompt-report output")

## Findings (implement)

- Docs-only. The sole false claim was README.md:34. The other "exact prompt" grep hit (`coga/internals/launch-claims`, both twins) describes the real launch preflight materializing the prompt, which is accurate, so it stays untouched. README has no packaged twin.
- New wording: "`coga launch <slug> --prompt-report` lists the prompt layers a ticket launch would compose, with each layer's size and approximate token count, then exits without launching an agent." It says "a ticket launch" so it doesn't claim script (`ticket.py`) targets, and it mentions no full-text output.
- Verified write-free against `compose.compose_prompt_report` + `launch._format_prompt_report` on this ticket (no CLI run in the shared checkout). The output is a "Prompt report for <slug>" header, a table of layer/ref/bytes/approx_tokens (characters / 4), and a total line. No prompt text appears. This matches the `--help` text.
- Process note: the auto-mode classifier denied the pre-branch `sync_coga_state` publish because it pushes to origin/main. The tree was clean, so I switched without it and recorded `branch:` here after returning to main. This entry is published by `coga bump`.

## Peer review

- Reviewed `2263875d6` on `docs/correct-prompt-report-readme` from clean `main`, without switching. No must-fix findings; the one-sentence README correction satisfies the ticket and makes no full-prompt-output or write-free claim.
- Checked `git diff main...docs/correct-prompt-report-readme -- '*.md'` and `--stat`: README prose only. No links changed, no context/template twins affected. `git diff main...docs/correct-prompt-report-readme --check` passed. No pytest run, as required for this prose-only step.
- Verified `coga launch --help`, the report return and script-target refusal in `src/coga/commands/launch.py`, `_format_prompt_report`, and byte/token calculations in `src/coga/compose.py` against the prompt-composition and launch topics. The example supplies the required target and promises layer metadata, not prompt text.
- Independently rendered this ticket through `compose_prompt_report` and `_format_prompt_report`, using `PYTHONPATH=/home/n/Code/coga/src /home/n/.local/share/uv/tools/coga/bin/python` with `load_config`, `resolve_task`, and `read_ticket`. Output contained layer/ref/bytes/approx_tokens columns and a total, with no prompt text. The ambient `python` lacked Coga; the CLI interpreter succeeded. No report-mode CLI launch was run in the shared checkout.
- Ready for the open-pr step; no branch edits needed.
