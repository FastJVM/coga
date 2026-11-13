---
title: 02 Compare current and candidate prompt assembly
status: in_progress
owner: nicktoper
contexts:
- coga-dev/microkernel/objectives
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: report-to-coga
    skills: []
    assignee: agent
step: 1 (agent-produces)
agent: claude
---

## Description

Test whether a candidate prompt assembler is actually better than the current one before replacing production assembly. Execute the paired, bounded protocol approved in ticket 01, retain complete input/output evidence, and let the owner judge the results. This ticket is done when the approved trials have been run or their limitations explicitly recorded, the report is reproducible and inspectable, and the owner's decision is recorded as a selected candidate, no demonstrated gain, or inconclusive. Completion of this ticket alone is not permission to implement a replacement.

### Prerequisite and execution

Do not begin trials until `v1/microkernel/03-prompt-assembly/01-define-prompt-candidates-and-trial-protocol` has produced its owner-approved protocol, complete candidates, fixtures and bounded budget. Copy the needed approved inputs into this ticket's attachments so their later retirement cannot invalidate the evidence. Record the source revisions and approval provenance.

Run baseline and candidate with the same task inputs, starting state and agent settings, using the protocol's pairing, repetitions and observations. Preserve the actual rendered prompt for each run and its block/source manifest, outcomes, failures, deviations and limits. Use isolated fixture repositories with local publication targets and notifications disabled so a trial's lifecycle or checkout actions cannot alter live work. Never recursively invoke `coga launch` inside an agent launch; use bounded independent agent sessions or the approved subprocess/test seam.

The noninteractive recurring autofix prompt is included, with its output parsing and exit behavior checked as such. The deterministic-only control must still run code without prompt composition or an agent. Assess skilled and inline workflow cases and the representative invocation cases selected in the protocol; do not silently drop failing cases or change criteria after seeing results.

### Decision before replacement

Apply the approved correctness gates first. A candidate that loses completion, checkout, authority, required-input or deterministic-execution guarantees cannot win. For candidates that pass, compare demonstrated improvements and costs using the pre-agreed measures. Distinguish static composition regressions from observed agent behavior; neither substitutes for the other. Prompt-size estimates do not establish task-success improvements.

The report must support an explicit owner decision. If the candidate is not better or the evidence is inconclusive, record that result and leave ticket 03 unlaunched; do not force a rewrite to justify the experiment. If one wins, retain the exact selected prompt form, explicit applicability facts, required additions, block provenance and known limits as the implementation input. Any materially revised candidate needs a new comparison before it can replace production.

Distinguish observed results from an enduring product decision. Transfer any
enduring ruling, including a deliberate refusal to replace the assembler and
its reopening conditions, to the owner `coga/prompt-composition`. A positive
selection is carried by ticket 03's documentation change. Otherwise, create
a narrow `docs/with-review` follow-up with the complete decision before
finishing `report-to-coga`; do not leave its only copy in a temporary report.
This experiment workflow does not itself edit the packaged topic.

No production prompt or launcher changes belong here. Executing the experiment is separate from implementing the winning form.

## Context

Owns the comparison evidence and result; ticket 01 owns protocol preparation and ticket 03 owns any production implementation. Ticket 02 may finish successfully with a negative result. Its `done` status must not be treated as proof that ticket 03 is eligible.

Read the copied approved protocol first, then the actual resolved source for baseline and candidates. The source inventory must include `src/coga/recurring_autofix.py` (`build_prompt`, `analyze_record`) as well as `src/coga/compose.py` and the shared-session callers. Neither the paused launch-decomposition scope nor a previous suite receipt proves a candidate improves behavior.

Cited rather than attached: `coga-dev/testing`, `docs/contexts/coga-dev/testing/SKILL.md`, "Verification tiers and receipts". Record the exact revision, working-tree differences, platform, agent CLI/version and model settings when available, actual commands, counts and runtime for every run. Mark unavailable information and native-platform limits explicitly. Do not claim that mocked transport tests establish native Windows behavior.

Workflow `draft-for-human` is for conducting bounded experiments and preparing a decision report, followed by the owner's judgment and recording of that decision. The deliverables are trial inputs, prompt specimens, transcripts and results, not product code or a permanent harness. A new reusable code artifact requires a separately reviewed code scope rather than silently extending this experiment.

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

The blackboard is a notepad to be written to often as the human and agent works through a task.
