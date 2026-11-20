---
title: Maintain ticket blackboards
status: done
owner: nicktoper
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
    checkout: reuse-required
  - name: pr
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
agent: claude
---

## Description

Filed by Dream in 2026-W46 (run 20261112T051938Z) as `validate-drift: large-blackboard`. The initial report identified a 36.8 KiB blackboard on `v1/20-ask-which-agents-to-enable-during-coga-init`. That ticket is now done. It is the example that exposed the missing maintenance process.

### Detect oversized blackboards

Add a dedicated recurring task, independent of Dream. Use the existing `large-blackboard` findings from `coga validate --json` to report the affected tickets, their sizes, and the current 32 KiB threshold. The alert is informational. Oversized blackboards can be exceptional, and an alert does not create a mandatory review or block work.

### Remove stale notes during normal ticket work

Add a blackboard cleanup instruction to the agent workflow. Whenever the agent loads or resumes a ticket, it checks the blackboard as part of reading it and removes notes that clearly no longer help the work. This is a light pass during normal ticket work and requires no separate review step. Age is a cue to check usefulness. Keep current decisions and rationale, active blockers, the worklist, and verification evidence still needed for handoff. Obsolete notes can be deleted directly. Update the owning `coga/blackboard` topic and the agent instructions that apply the policy.

### Completion

Deliver both behaviors in this ticket.

- Run the dedicated recurring task against a fixture with a blackboard above the threshold and one below it. Verify that only the oversized blackboard is reported, with its ticket ref, measured size, and threshold.
- Verify that the normal agent prompt includes the cleanup instruction when loading or resuming a ticket. Walk through a sample blackboard containing obsolete notes and information still needed for handoff, and confirm the instruction supports removing the former and retaining the latter. Update the owning blackboard topic alongside the prompt.
- Use fixtures for verification and leave the completed agent-selection ticket as the original example.

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

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/1271
branch: coga/maintain-ticket-blackboards

## Handoff (self-qa, 2026-11-19)

Branch `coga/maintain-ticket-blackboards` at `f1d68b6` (pushed; rebased on `bb26656`). No PR yet.

- **Detection.** Bundled recurring job `blackboard-size` (Mondays 08:00, workflow `blackboard-size/run`). The packaged `ticket.py` is a shim; the logic lives in `src/coga_edge/blackboard_size.py`, so frozen periods follow wheel upgrades. It subprocesses `python -m coga.validate --json`, keeps the `large-blackboard` findings and writes `## Oversized blackboards` (ref, size, threshold) to the period blackboard. When something is flagged it posts one non-fatal FYI. It always bumps.
- **Decision: size is parsed from the finding message.** The validate JSON has no structured size field, and the ticket asks for the validate findings. `test_reads_size_from_the_validator_warning` pins the format in the same wheel. An unreadable finding raises and goes to `## Recipe Failure`. The owner may prefer a structured `Issue` field or an in-process measure; 3 of 4 `/simplify` angles and `/code-review` raised this.
- **Selection.** In `FRESH_RECURRING_SELECTION` (owner review decides that default list) and this repo's `jobs.toml`. Lazy carrier approved.
- **Cleanup.** Ticket-loop step 1 in `prompt-ticket.md`; `coga/blackboard` "Stale-note cleanup" owns the policy. The protected list now covers runner- and gate-written sections. The prompt inlines the policy because the topic is not attached to every ticket.
- **Walkthrough (completion criterion 2).** Sample blackboard: (a) a superseded plan with no live rationale, (b) a "tests running…" status, (c) a ruled-out dead end, (d) a decision with its reason, (e) an open `## Blockers` ask, (f) the worklist, (g) the suite receipt the PR needs. The instruction deletes (a)-(c) and keeps (d)-(g). Self-QA applied it here: the implement handoff was folded into this one.
- **Follow-up for owner / retro.** Dream's validate-drift still classifies `large-blackboard` as human-needed, so oversized tickets can be reported twice. Filed as parked draft `_v2/stop-dream-double-reporting-large-blackboards` (pr step). Use `.venv/bin/python` for tests (the uv-tool `python` lacks `tomlkit`).

## Self-QA

- **Review.** `/code-review` (default effort, Claude Opus 5.5 forked skill, self-review) ran against `main...HEAD` and **returned** with 7 findings. Fixed: (1, important) the cleanup's protected list missed `## Recipe Failure`, `## Evaluator review`, `## Production notes` and recurring state, now in both the prompt and the topic; (2, important) 113 lines of job logic frozen into each period, now a `coga_edge` module behind a shim; (3) the import from Dream's module was dropped; (4) init topic and packaging test said "nine" jobs; (5) the packaging topic's lazy-carrier sentence; (6) the topic now says the job reports only when selected. Skipped: (7) the prompt restating the policy. That is deliberate, because the topic is not attached to every ticket.
- **`/simplify`** ran 4 angles (reuse, simplification, efficiency, altitude). Applied: the threshold is a constant instead of a per-record field; the no-findings case is a unit test instead of a second end-to-end launch; the prompt clause is shorter. Skipped: replacing validate with an in-process measurement (it contradicts the ticket's "use validate findings"; left to the owner); a shared `conftest` seeded fixture (outside the diff); trimming the job description across the template, topic and workflow (minor).
- **Fix commit re-review.** The fixes in `f1d68b6` came after `/code-review` returned. I read that commit directly (self-review, **completed**) and found no defects.
- **Tests.** Full suite at `f1d68b6`: 5011 passed, 33 skipped. A live dry render of the moved module flags `recurring/dream` 39.5 KiB, `v1/14-…` 49.3 KiB and `v1/20-…` 36.8 KiB. No hand-swept surface: no TTY or render paths changed.

## PR

```yaml
title: Report oversized blackboards weekly and prune stale notes on read
author: claude
author_evidence: >-
  Implement and self-qa sessions ran as Claude Opus 5.5 (claude-opus-5-5) in a megalaunch queue.
head: f1d68b6ec261b9e88e3d37e38f7112d619184c3b
base: bb2665636e8954c8a6e30f7222fe53198001bfb9
depth: deep
rationale: >-
  Adds a bundled recurring job selected by default for fresh repos (owner
  review decides that list) and changes the shipped ticket-loop prompt that
  every agent session composes; review so far is self-review only.
implementation: >-
  New package-owned recurring template blackboard-size whose ticket.py shim runs
  coga_edge.blackboard_size: it reports coga validate --json large-blackboard
  findings (ref, size, threshold) to the period blackboard and as one non-fatal
  FYI, then bumps. Ticket-loop step 1 instructs a light stale-note cleanup on
  load or resume, protecting command-, runner- and gate-written sections;
  coga/blackboard owns the policy in a new Stale-note cleanup section.
deviations: >-
  None from the ticket. Size is parsed from the finding message because the
  validate JSON has no structured size field; a test pins the format in the same wheel.
limitations: >-
  Message parsing couples the job to blackboard_size_warning's wording (owner
  may prefer a structured Issue field). Dream validate-drift still files
  large-blackboard as human-needed, so a live oversized ticket can surface in
  both places. The cleanup pass is prompt guidance; its judgment was checked by
  walkthrough, not automated.
files:
  coga/recurring/jobs.toml: Select the new bundled job in this repo.
  docs/contexts/coga-dev/codebase/SKILL.md: Map the new coga_edge module.
  docs/contexts/coga-dev/packaging/SKILL.md: Name blackboard-size as a lazy state carrier.
  src/coga/commands/update.py: Add blackboard-size to the fresh-repo recurring selection.
  src/coga/resources/prompt-ticket.md: Instruct the stale-note cleanup pass when loading or resuming a ticket.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md: >-
    Own the stale-note cleanup policy and name the size report job.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: Fresh init now selects ten bundled jobs.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/producers/SKILL.md: >-
    Inventory the new job's informational FYI.
  src/coga/resources/templates/coga/bootstrap/workflows/blackboard-size/run.md: One-step workflow for the script-backed period.
  src/coga/resources/templates/coga/recurring/blackboard-size/ticket.md: Template contract and schedule for the size report.
  src/coga/resources/templates/coga/recurring/blackboard-size/ticket.py: Shim selecting the coga_edge implementation.
  src/coga_edge/blackboard_size.py: Job logic that reads validate findings and reports them.
  tests/required_package_resources.txt: Require the new package owners.
  tests/test_packaging.py: >-
    Approve the lazy state carrier and run the new job in the installed-wheel smoke.
  tests/test_recurring_state.py: Include the new job in the bundled catalog.
  tests/test_blackboard_size.py: >-
    End-to-end fixture run (one blackboard above and one below threshold),
    message-format pin, and prompt/topic cleanup-clause checks.
review:
  reviewer: claude
  kind: self
  status: passed
  head: f1d68b6ec261b9e88e3d37e38f7112d619184c3b
  base: bb2665636e8954c8a6e30f7222fe53198001bfb9
  detail: >-
    Claude Opus 5.5 /code-review (default effort) plus /simplify (4 angles)
    returned on implement head 9b139b329 (plus an uncommitted
    working tree); its fixes and /simplify's form f1d68b6, which got a completed
    direct self-review only. No independent review yet.
checks:
  - command: .venv/bin/python -m pytest -q -p no:cacheprovider -x
    status: passed
    head: f1d68b6ec261b9e88e3d37e38f7112d619184c3b
    base: bb2665636e8954c8a6e30f7222fe53198001bfb9
    detail: >-
      5011 passed, 33 skipped in 788.98s, on the working tree committed
      unchanged as head (rebase onto base was a no-op).
```

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `maintain-ticket-blackboards`
Recorded: 2026-11-19T09:41:29+00:00

    [open-pr] origin/main advanced only through non-overlapping Coga task/log state; branch is safe to publish
    PR presentation: review kind must be independent, self, or none.

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `maintain-ticket-blackboards`
Recorded: 2026-11-19T09:41:43+00:00

    [open-pr] origin/main advanced only through non-overlapping Coga task/log state; branch is safe to publish
    PR presentation: reviewer must be a compact identity.
