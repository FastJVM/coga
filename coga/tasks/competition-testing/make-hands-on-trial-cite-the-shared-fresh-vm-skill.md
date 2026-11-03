---
title: Make hands-on-trial cite the shared fresh-vm skill
status: active
owner: nicktoper
workflow:
  name: docs/with-review
  steps:
  - name: implement
    skills: []
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills: []
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
agent: claude
---

## Description

`coga/skills/competition-testing/hands-on-trial/SKILL.md` (proposed in PR
#1145) carries its own VM preparation steps. `coga/skills/coga/testing/fresh-vm/SKILL.md`
(proposed in PR #1153) is meant to be the single owner of VM preparation,
baseline capture, reuse, and cleanup for attended install walks and competitor
trials. Once both have merged to main, replace hands-on-trial's duplicated
VM-hygiene instructions with a citation of `coga/testing/fresh-vm`, so the
procedure has one owner per `coga/knowledge`.

Done when hands-on-trial points to fresh-vm for VM choice, preparation, baseline,
reuse, and cleanup, and restates no competing VM procedure. The trial-specific
guidance that fresh-vm does not own stays in hands-on-trial.

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

### Route: fold into #1145, then retire this ticket

Owner decision (2026-11-02): do this edit inside PR #1145
(`codex/retro-competition-testing-knowledge`, "New skill: hands-on competitor
trial method"), not as a separate follow-up PR. Order: merge PR #1153 ("Add
attended install-walk guidance with shared VM preparation", which adds
`coga/skills/coga/testing/fresh-vm/SKILL.md`) first. Then rebase #1145 onto
main and apply the change below on #1145's branch, before #1145 merges. Once
#1145 merges with the citation, cancel this ticket.

This draft tracks that work. Use it as a launched ticket only if #1145 merges
without the citation. In that case, branch from main after both PRs are in.
If #1153 is abandoned, this ticket is moot: cancel it.

### What to change

- Replace the VM-procedure parts of hands-on-trial with a link to fresh-vm.
  That covers the **Fresh VM.** bullet in `## Setup` ("Use a spare bare
  `cogatest` UTM machine, and have the human confirm which one at launch") and
  any VM reuse/cleanup steps. Use the same link form that
  `clean-install/human-walk` uses for fresh-vm.
- Remove restatements of facts that fresh-vm owns. Two are known now:
  separating steps the human installed from habit (fresh-vm `## Reusing a
  spare`), and the human being unable to copy from the agent session into the
  VM (fresh-vm `### Moving commands and evidence`) in the command-relay text.
  The relay artifact itself is trial-specific and stays.
- Keep the trial rules that fresh-vm does not own: install coverage starts at
  the bare machine's prerequisites, demands are recorded in order, earlier
  trials' write-ups are read first, and all laps run in the same VM and
  project directory (a `## Laps` rule, not VM hygiene). Read fresh-vm's final
  text to draw the line; the lists above are examples, not the boundary.
- Don't hard-code UTM/macOS in hands-on-trial. Let fresh-vm's "Choose the
  starting environment" pick the platform.
- Rule applied: `coga/knowledge` (`docs/contexts/coga/knowledge/SKILL.md`),
  cited, not attached. Read its one-owner rule ("one owner per fact; other
  surfaces summarize and link") and `## Attach or cite`. Neither skill file is
  attached either: one is edited, the other read once.
- No packaged twin: both skills are repo-local (nothing under
  `src/coga/resources/templates/coga/bootstrap/skills/competition-testing/` or
  `.../coga/testing/fresh-vm`), so `tests/test_packaging.py` does not pair them.
- Do not touch the competitor findings. `FastJVM/coga` is public, and
  hands-on-trial keeps findings out of the repo.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

---

## Blockers

- [ ] [2026-11-02 21:51] [agent:claude] id=20261102T215124 Waiting on PR #1153 (fresh-vm) to merge, then the fresh-vm citation folded into PR #1145; cancel this ticket once #1145 merges with it

---

## Blocker reminders

- 7891d747a9e1 last_reminded: 2026-11-03 10:44
