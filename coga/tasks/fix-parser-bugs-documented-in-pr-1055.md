---
title: Fix parser bugs documented in PR 1055
status: draft
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
---

## Description

Fix the three unresolved parser and diagnostic defects documented by https://github.com/FastJVM/coga/pull/1055. The owner requested actual bug fixes after reviewing that documentation-only PR. Deliver code, regression tests, and the corrected behavior contracts together.

### Defects and reproduction evidence

1. False blockers from examples and superseded designs. In `src/coga/blackboard.py`, `parse_blockers_text` scans every stored line without code-fence or archive awareness; `open_blockers` exposes these results to launch and megalaunch eligibility checks. The line `- [ ] [2026-09-18 12:00] [human:marc] id=old Historical example ask` is currently treated as an open blocker even inside a fenced example or under the exact `## Superseded designs` section. The prompt projection can omit that history while the pre-composition gate still refuses work.

2. Truncated workflow instructions. `src/coga/workflow.py::_parse_inline_sections` uses a fence-unaware heading regex. In a skill-less step's `## implement` section, put a closed fenced Markdown example containing `## Example`, then ordinary instructions after the example. The example heading ends the step's instructions prematurely, even when "Example" is not a step name. A fenced heading matching another step can also supply bogus instructions for that step.

3. Missing warning for uncomposed preamble. Put substantive prose before `## Description`, followed by otherwise valid Description and Context sections. `taskfile.body_sections` returns only headed sections, so composition omits that prose and `uncomposed_sections` reports nothing about it. Preserve the existing Description/Context composition boundary; warn about the lost prose and explain where to move it.

These code paths were inspected on main at `27e384504067548a6ea8b1b020559f5f25cfe70a` on 2026-10-20. PR #1055 was still open at head `14d6863ce33bd4aef747af26a4ccd2e7aa630050` and changed only contexts, packaged twins, and source-ticket deletion. This ticket records source-inspection evidence, not a completed runtime test.

### Acceptance criteria

- Fenced blocker examples and every exact Superseded designs section are inert for blocker reading, launch, megalaunch, and the composed blocker preamble. Preserve the documented archive boundaries and all genuine live blockers, resolved entries, and supported legacy entries. Examples must not alter a live blocker's resolution state. Exercise both direct readers and a launch/queue consumer.
- Inline workflow instructions retain fenced H2 lines and all subsequent prose through the next real section boundary. Fenced headings cannot create another step's instructions. Cover backtick and tilde fences, non-step headings, and headings matching another real step; preserve skill-backed step behavior.
- Validate and launch/prompt-report consistently warn when substantive pre-heading prose will be omitted. The warning identifies the omitted region and directs the author to Description or Context. Test a nonempty Description after the preamble, a prose-only body, and whitespace-only preambles. Preserve terminal-ticket warning policy and normal composed-section behavior. Do not silently expand the composition contract.
- Use the existing shared Markdown helpers where they fit. Confirm the handling of unmatched fences and archive boundaries explicitly; do not introduce a competing Markdown parser or accidentally change the archive projection contract.
- Add regression tests that fail on the current behavior and pass with the fixes, including negative controls proving real blockers and real workflow headings still work.
- Update the owning blackboard, tickets, and workflows contexts and their packaged twins in the same PR. Check #1055's current merge state: replace its known-gap workarounds if they have landed, otherwise document the corrected behavior against current main and identify the overlap in the implementation PR.
- Verify focused regressions, packaging twins, and the full suite using the checkout's own source, and run repository validation. Record exact commands, interpreter, and results.

### Scope

This is one parser/diagnostics bug-fix ticket. Changes to Retro's general follow-up policy, automatic composition of extra ticket text, a general Markdown redesign, and unrelated historical-ticket rewrites are outside its scope. PR #1055's documentation cleanup does not resolve these defects.

### Verification starting points

Read and extend the relevant coverage in `tests/test_blackboard.py`, `tests/test_compose.py`, `tests/test_taskfile.py`, `tests/test_validate.py`, `tests/test_launch.py`, and `tests/test_megalaunch.py`; `tests/test_packaging.py` checks the canonical/package twins. Keep the regression coverage focused on the user-visible failures above.

## Context

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/internals/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
