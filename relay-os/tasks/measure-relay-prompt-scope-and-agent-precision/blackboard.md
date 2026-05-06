## Dev

branch: codex/relay-prompt-scope-report
worktree: /home/n/Code/relay
pr:

## Notes

Prepared from a bootstrap/orient discussion on 2026-05-06.

Question being captured: Relay is new, but does it reduce token/cost and
increase precision versus a normal agent? The working answer is that precision
should improve from explicit task/workflow/context state, while cost needs
measurement because scoped context may spend more tokens up front to avoid
rediscovery and rework.

User correction to preserve: Relay should not rely on dumping every context into
every run. The ticket should compose the relevant contexts, and the workflow
step should compose the relevant skill. Current broad/all-context inclusion is a
temporary baseline to measure, not the target design.

## Suggested first pass

Start by inspecting `src/relay/compose.py` and existing prompt-size warning
helpers. Add the smallest report surface that can show prompt contribution by
layer without changing the normal launch behavior.

Useful outputs:

- approximate token count per layer
- included context refs
- included skill ref for the current step
- blackboard size warning if it crosses the existing threshold
- total approximate prompt tokens

Then document a small comparison protocol for real tasks rather than trying to
invent a synthetic benchmark.

## Implementation

Implemented the instrumentation slice directly from the bootstrap/orient
session.

Changes made:

- `src/relay/compose.py` now builds a `PromptComposition` with per-layer
  `PromptLayer` metadata while keeping `compose_prompt()` compatible.
- `relay launch --prompt-report` prints a read-only prompt report and exits
  without activating drafts, acquiring locks, checking for a TTY, checking the
  agent binary, writing logs, posting to Slack, or spawning an agent.
- The report includes layer name, exact context/skill ref, bytes, approximate
  token count, and total composed prompt size.
- Approximate token counting is dependency-light: `characters / 4`.
- README, `docs/spec.md`, and `relay/cli` context now document the report and
  the scoped-context direction.

Real-ticket check:

`PYTHONPATH=src .venv/bin/python -m relay.cli launch measure-relay-prompt-scope-and-agent-precision --prompt-report`

Result: current composed prompt is 35.8 KiB, approximately 9,095 tokens. The
largest included layers are `relay/current-direction`, `prompt.md`, and
`relay/architecture`, which makes the current broad-context cost visible.

Verification:

- `.venv/bin/python -m pytest tests/test_compose.py tests/test_launch.py` ->
  30 passed
- `.venv/bin/python -m pytest` -> 249 passed
- `PYTHONPATH=src .venv/bin/python -m relay.cli validate --json` -> ok_count
  33, no issues

## Follow-up: ticket context selection bug

User clarified the real bug: ticket creation should not attach broad contexts as
labels. It should select exact context payload that must be included, and
process knowledge should stay in workflow step `skill:` refs.

Follow-up changes:

- Tightened `bootstrap/ticket` instructions in both the live Relay skill and
  upstream template source.
- The creation contract now says `contexts:` are prompt payload, not tags.
- Broad orientation contexts are not defaults; if only one fact is needed, copy
  the fact into ticket `## Context`.
- Existing skills should be selected through workflow step `skill:` refs. If a
  skill exists but no workflow uses it, the ticket should mention/propose that
  workflow change instead of copying skill text into context.
- Added a template test for this contract.
- Trimmed this ticket's contexts from six refs to three:
  `relay/principles`, `relay/codebase`, and `dev/code`.

After trimming, the same prompt report is about 25 KiB / 6.4k estimated tokens
instead of 35.8 KiB / approximately 9,095 tokens. The final number includes
these blackboard notes, so the delta also demonstrates blackboard growth.

Verification for the follow-up:

- `.venv/bin/python -m pytest tests/test_bootstrap_ticket_skill_template.py tests/test_compose.py tests/test_launch.py`
  -> 31 passed
- `PYTHONPATH=src .venv/bin/python -m relay.cli validate --json` -> ok_count
  33, no issues
