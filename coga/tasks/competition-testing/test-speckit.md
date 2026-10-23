---
title: Test SpecKit
status: active
owner: zach
contexts:
- coga-dev/principles
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

Install GitHub Spec Kit (https://github.com/github/spec-kit) and run a real task through it end to end, then write up how it compares to Coga. As of October 2026, Spec Kit is the most-adopted tool in this space at roughly 142k stars; install is `uv tool install specify-cli` then `specify init <project> --integration <agent>`, and it needs Python 3.11+ and uv. It ships three prescribed processes: spec-driven development (constitution, specify, plan, tasks, implement, converge), bug fixing (bug-assess, bug-fix, bug-test), and idea assessment (assess-intake, research, define, shape, decide), plus a documented path for adding custom processes. Things worth paying attention to, not a checklist to work through: the installation experience end to end, how much the fixed command sequence constrains the way you work, whether the custom-process extension point genuinely lets you define your own loop or only reskins theirs, and what it does that Coga does not.

Done when the SpecKit section of the "Coga Competitor Tests" Google Doc reflects a trial Zach considers finished, and he has shared the doc with Nico.

Why now: Coga positioning is unresolved. From the outside it reads as a weaker overlap of Spec Kit, BMAD and Compound Engineering, and the claim we want to make — that Coga is a hackable substrate you shape to your own way of working rather than a fixed cycle — needs first-hand evidence. The installation angle is doubly useful because the installer is being reworked under marketing/fix-installer.

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
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

### How this runs

Zach runs Spec Kit hands-on in a VM (`cogatest@cogatests-Virtual-Machine`),
pastes screenshots into the session, and notes what he sees. The agent discusses
findings with him and drafts write-up text for the doc. The agent does not run
Spec Kit. This is information gathering, not a staged project — follow Zach's
lead on what to look at next.

### Where findings go

The doc is "Coga Competitor Tests" —
https://docs.google.com/document/d/19qnSHqN2eH5e66peQ7X-R6NPIg6IPHc0wsS3cBxUEuM/edit
(its Drive filename is still "Untitled document"). It is a numbered running log
per tool, with Zach's screenshots inline. Its SpecKit section is the deliverable.

The Drive tools can read that doc but cannot write to it: `update_file` changes
metadata only, and there is no content-edit tool for an existing Doc. So the
agent drafts markdown and Zach pastes it in — Docs converts pasted markdown to
real headings and lists. Do not create a replacement Doc; the screenshots live
in this one.

`FastJVM/coga` is public, so findings stay in the doc and the blackboard stays a
pointer. The doc itself is owner-only, so its URL here is safe; share it with
Nico by named account rather than switching on link-sharing.

### The trial task

Build `tiny-ticket`: a command-line tool that stores tasks as markdown files
with YAML frontmatter, with three commands — create a task, list tasks, and
validate the files. Validation enforces that `status` is one of a fixed set and
that any non-draft task has a workflow.

Zach picked it because he knows the correct design cold, so a bad spec or plan
is obvious on sight. The bias to name rather than hide is that it is Coga's own
problem domain.

The same task runs through BMAD and Compound Engineering in the sibling tickets
`competition-testing/test-bmad-method` and
`competition-testing/test-compound-engineering`. Keep the product name
`tiny-ticket` in all three and vary only the project directory:
`speckit-tiny-ticket`, `bmad-tiny-ticket`, `ce-tiny-ticket`. What is worth
comparing across the three gets decided once the docs exist, not up front.

### Install facts already established

From `specify check` on the VM:

- The `--integration` token for Claude Code is `claude`, per
  https://github.github.io/spec-kit/integrations/index.html. The names in
  `specify check` output are display names, not accepted values.
- Claude Code reads "not found" on the VM, so `specify init` will fail its
  agent-tools check until Claude Code is installed there. `--ignore-agent-tools`
  skips the check but leaves no agent to run the task with.

Installer findings are also input to
`marketing/fix-installer/make-the-readme-install-section-the-only-install-p`,
which owns the copy-pasteable install commands.

### Out of scope

Only the spec-driven development loop gets trialled; Spec Kit's bug-fixing and
idea-assessment processes are named in `## Description` for completeness.

Do not commit trial output, competitor notes, or the `tiny-ticket` source into
this repo. The scratch project stays in the VM. At `report-to-coga`, record the
doc link and that the section is done — not what the trial found.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
