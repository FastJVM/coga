---
title: Let Dream Retro handle period tickets that were never committed
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: open-branch
    skills: []
    assignee: agent
    requires: branch
    run: git/open-branch
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
  - name: push-and-open-pr
    skills: []
    assignee: agent
    requires: pr
    run: git/push-and-open-pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 4 (push-and-open-pr)
agent: claude
---

## Description

Filed by Dream recurring/dream, period 2026-W48 (run 20261125T175534Z), Phase 4 observation by the Dream agent.

The recurring sweep creates period tickets under coga/tasks/recurring/<name>/ and does not commit them. In this run all 8 done period tickets were untracked: address-pr-comments, blackboard-size, blocker-reminders, phone-home, resolve-conflicts, skill-update, trim-log and usage-report. Only coga/tasks/recurring/dream/ticket.md was tracked. The Dream template's Phase 4 requires Retro in an isolated checkout based on the fetched remote base. It says period tickets are 'normally' direct-deleted with coga delete there and that each direct delete is verified on the remote base. A ticket that never reached the remote is absent from that checkout, so Retro can neither delete it nor verify the delete. Running Retro in Dream's own checkout is forbidden. Dream therefore left all eight for the scanner's prior-period fallback, which contradicts 'Retro never leaves a processed done ticket on disk'.

Decide one of: (a) Phase 4 classifies untracked period tickets from the snapshot and deletes them locally in Dream's checkout as an explicit exception, since nothing needs to land; (b) Phase 4 excludes untracked period tickets and relies on the scanner fallback, stated as such; (c) the sweep commits period tickets. Update src/coga/resources/templates/coga/recurring/dream/ticket.md (Phase 4) and retro/done-ticket to match. Acceptance: the template states the untracked case, and the next Dream run handles it without improvising.

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
        - name: open-branch
          run: git/open-branch               # Local-first skill directory containing run.py.
          assignee: agent
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (open-branch)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
A workflow run: selects a script for its step. A sibling ticket.py supplies the default script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

The recurring runner writes delegate on materialized period tickets. It
names the parent template's frozen bootstrap/<name> target.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev records branch:, base:, remote:, reviewed: (the commit OID),
and pr: (the full /pull/ URL). Write one field per line and omit unknown
values. coga/git owns the fields and the workflow that writes them.

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

branch: coga/let-dream-retro-handbacks-main
base: main
remote: origin
reviewed: 194f25638b0c7ed6afd14423ac5a031103d3e30b


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Decision

Option (a), with Retro still classifying. Reasons:
- (b) keeps the contradiction with "Retro never leaves a processed done ticket
  on disk" and silently skips any gotcha a period blackboard holds.
- (c) would make the recurring sweep write Git history every firing, which is a
  much larger behavior change. Nothing about an untracked ticket needs to land.
- Deleting an untracked file in Dream's checkout touches no Git state. It is
  the narrowest exception to "no Retro in Dream's checkout".

Dream snapshots on-base sources and wholly untracked period tickets, then
passes the latter with a `local-only:` list. Retro classifies them from the
snapshot and records a `local` handback. Extracted facts go into a theme PR
with snapshot evidence. Dream verifies durable results and rechecks the exact
artifact against the base, HEAD, index, and snapshot before calling
`coga delete recurring/<name>`. Changed artifacts are deferred. An incomplete
delete preserves the recovery copy.

## Handoff (peer-review → publication)

Claude implemented the local-only handback in `d4b4c97a6`. Codex
reviewed and corrected it in `68a5cd74c`. The owner selected this copy
for the step-script migration. Codex retargeted those changes to `main`
and resolved the Retro skill conflict so `coga retire` still handles its
single canceled ticket. Both former branch tips remain in Git history.

The reviewed code is `194f25638b0c7ed6afd14423ac5a031103d3e30b`. The
migration removes the obsolete branch-opening step and leaves the ticket at
PR publication. The next live Dream run is the behavioral acceptance check.

## PR

```yaml
title: Let Dream Retro handle period tickets that were never committed
author: claude
author_evidence: Claude (claude-opus-5-5, launch e7cd2941) implemented the route. Codex wrote
  corrections during peer review and resolved the later conflict against main.
head: 194f25638b0c7ed6afd14423ac5a031103d3e30b
base: 9f88e7ef0d21f74f86e0df595883fae3c18f2fa5
depth: skim
rationale: The prompt change directs Dream to delete untracked period artifacts after Retro
  classifies them in isolation. The previously reviewed implementation was retargeted to main
  and verified again.
implementation: Dream partitions eligible done tickets by presence on the fetched remote base.
  Untracked, base-absent recurring period tickets go to Retro as local-only slugs. Retro classifies
  them from the snapshot and extracts any knowledge into a theme PR. It hands them back with
  a new `local` progress receipt. Dream then deletes them with coga delete in its own checkout
  after verification and a fresh comparison of the exact artifact against the base, HEAD,
  index, and snapshot. Failed prechecks defer the ticket, while a partial deletion preserves
  the snapshot for recovery.
deviations: The original stacked branch was replaced with a branch based on main. The resolution
  preserves the existing canceled-ticket route and the new local-only handback.
limitations: The next live Dream run remains the end-to-end acceptance check. The Linux suite
  used Python 3.12.12. Python 3.11 is installed without pytest in this environment. Native
  macOS and Windows checks are deferred to release.
files:
  src/coga/resources/templates/coga/recurring/dream/ticket.md: Select local-only periods and
    verify handbacks before local deletion and snapshot cleanup.
  src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md: Define classification,
    PR evidence and recovery receipts for snapshot-only sources.
  tests/test_dream_worker_templates.py: Check the probes, receipt requirements and ordering
    of verification, deletion and cleanup.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: 194f25638b0c7ed6afd14423ac5a031103d3e30b
  base: 9f88e7ef0d21f74f86e0df595883fae3c18f2fa5
  detail: Codex reviewed the full code diff against main, preserved the canceled-ticket preflight
    and behavior during conflict resolution, and verified the Git and prompt contracts. Codex
    also authored the peer-review fixes and the retargeting commit.
checks:
- command: PYTHONPATH=$PWD/src python -m pytest -q -p no:cacheprovider tests/test_dream_worker_templates.py
    tests/test_retro_skill_template.py
  status: passed
  head: 194f25638b0c7ed6afd14423ac5a031103d3e30b
  base: 9f88e7ef0d21f74f86e0df595883fae3c18f2fa5
  detail: Pop!_OS 24.04 LTS, Python 3.12.12, exported commit with isolated TMPDIR. 26 passed
    in 0.54s.
- command: git diff --check 9f88e7ef0d21f74f86e0df595883fae3c18f2fa5..194f25638b0c7ed6afd14423ac5a031103d3e30b
  status: passed
  head: 194f25638b0c7ed6afd14423ac5a031103d3e30b
  base: 9f88e7ef0d21f74f86e0df595883fae3c18f2fa5
  detail: No whitespace errors.
- command: TERM=dumb PYTHONPATH=$PWD/src python -m pytest -q -p no:cacheprovider
  status: passed
  head: 194f25638b0c7ed6afd14423ac5a031103d3e30b
  base: 9f88e7ef0d21f74f86e0df595883fae3c18f2fa5
  detail: Pop!_OS 24.04 LTS, Python 3.12.12, exported commit with isolated TMPDIR. 3242 passed,
    29 skipped in 295.71s.
```
