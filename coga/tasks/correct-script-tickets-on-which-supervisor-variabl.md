---
title: Correct script-tickets on which supervisor variables a ticket.py child loses
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 2 (peer-review)
agent: claude
launch_generation: pending:ae6ba8d5-e3ac-47b5-b9fb-8967abfc273b
---

## Description

Filed by Dream recurring/dream, period 2026-W47 (run 20261118T170921Z), Phase 6 disposition. Target src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md is also edited by open PRs #1244 and #1247, which reword the neighbouring vanished-entry paragraph but do not carry this fix. Phase 3 shard ca-05.

Route: open a PR against the target once the overlapping PR(s) have landed or been rebased; the fix is pr-required (human review).

Finding: script-tickets overstates which supervisor variables a ticket.py child "loses"

- shard: ca-05
- class: drift
- target: src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md
- area: coga/script-tickets

`script-tickets/SKILL.md:54-58` says the script child's environment "loses `COGA_SUPERVISED`, `COGA_DONE_SENTINEL`, `COGA_EXPECTED_TASK`, `COGA_EXPECTED_STEP`, and `COGA_EXPECTED_AGENT`" unconditionally. Code reality (`src/coga/launch_script.py:272-283`): `COGA_DONE_SENTINEL` is not removed but set to the explicit empty string (the "no supervisor polls here" signal that `coga/recurring/scheduling/inactivity/SKILL.md:92-94` correctly describes for ticket scripts), and under a strict human assist (`if strict_assist:`) launch re-mints `COGA_EXPECTED_TASK` and `COGA_EXPECTED_STEP` (plus the `COGA_ASSIST_*` values) for the child. Reword step 4 to say the sentinel is exported empty and that only a strict assist re-mints the task/step witness, so the topic agrees with `launch_script.py` and the inactivity leaf.

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
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
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
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

## Dev

branch: coga/correct-script-tickets-on-which-supervisor-variabl

## Plan

Docs-only fix to step 4 of `coga/script-tickets` (package copy). Overlapping
PRs #1244/#1247 (still open) only touch the classification paragraph and add a
new help section; neither touches step 4, so no textual conflict expected.

## Handoff (implement)

- Commit `7dafd8f` on the branch (pushed). It rewords step 4 of
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md`.
  The child loses `COGA_SUPERVISED` and `COGA_EXPECTED_{TASK,STEP,AGENT}`.
  `COGA_DONE_SENTINEL` is exported as the explicit empty string, with a link
  to the inactivity leaf. Only a strict human assist re-mints
  `COGA_EXPECTED_TASK` (the target path), `COGA_EXPECTED_STEP` and
  `COGA_ASSIST_*`. Verified against `launch_script.run_script_phase` (the env
  block after `apply_task_env`).
- No code or test change. No existing test pins the old wording (grep).
- Peer review: check the new wording against `launch_script.py`. The
  open-pr step should note that #1244/#1247 touch other paragraphs of the same
  file, so rebasing after either one lands should be clean.
- Env note: the system `python` lacks `tomlkit`; use `.venv/bin/python`.

## PR

```yaml
title: Correct script-tickets on which supervisor variables a ticket.py child loses
author: claude
author_evidence: >-
  Implement session ran as Claude Opus 5.5 (claude-opus-5-5) under megalaunch.
head: 7dafd8fe439daa022a5dbc0b9d7e9322a995fd78
base: 59d917fa206a31ee55fab476996539e16e989d2f
depth: skim
rationale: >-
  One-paragraph docs correction in a shipped topic; compare it with the env
  block in launch_script.run_script_phase.
implementation: >-
  Step 4 now says COGA_DONE_SENTINEL is exported empty rather than removed,
  and that only a strict human assist re-mints COGA_EXPECTED_TASK,
  COGA_EXPECTED_STEP and COGA_ASSIST_* for the child.
deviations: "None."
limitations: >-
  Docs only. The overlapping open PRs #1244/#1247 edit other paragraphs of
  the same file, and those edits were not merged here.
files:
  src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md: >-
    Align the step-4 child-environment description with launch_script.py and
    the inactivity leaf.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: "Code review has not run yet; the peer-review step follows."
checks:
  - command: .venv/bin/python -m pytest -q -p no:cacheprovider
    status: passed
    head: 7dafd8fe439daa022a5dbc0b9d7e9322a995fd78
    base: 59d917fa206a31ee55fab476996539e16e989d2f
    detail: "5004 passed, 33 skipped in 808s, on a clean committed tree."
```
