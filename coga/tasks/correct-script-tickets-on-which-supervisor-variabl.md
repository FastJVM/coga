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
step: 4 (review)
agent: claude
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

pr: https://github.com/FastJVM/coga/pull/1275
branch: coga/correct-script-tickets-on-which-supervisor-variabl

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
- Env note: the system `python` lacks `tomlkit`; use `.venv/bin/python`.

## Peer review

Codex completed an independent direct review of `b25ad3f5e609ee5661b5008af3af1bd7d2785d98` against
`a4d06e84e0fe006109bc0afe0fa1117c3688ab80`. No findings. Step 4 matches the launcher environment block and the
linked inactivity topic. Both overlapping PRs (#1244 and #1247) merged on
November 19, 2026. The branch rebased cleanly across both and was pushed
with an explicit lease. The Linux suite passed with 5179 passed, 33 skipped in 1113.51s.
Native Windows and macOS checks are deferred to release.

## PR

```yaml
title: Correct script-tickets on which supervisor variables a ticket.py child loses
author: claude
author_evidence: >-
  The implementation session used Claude Opus 5.5 under megalaunch.
  The implementation commit carries the Claude Opus 5.5 co-author trailer.
head: b25ad3f5e609ee5661b5008af3af1bd7d2785d98
base: a4d06e84e0fe006109bc0afe0fa1117c3688ab80
depth: merge
rationale: >-
  The diff changes one documentation paragraph. Direct independent review
  matched it against the launcher and inactivity topic. Both overlapping
  PRs are in the base, and the full Linux suite passed.
implementation: >-
  Step 4 documents the explicitly empty COGA_DONE_SENTINEL and the
  task, step, and assist variables that strict human assist re-mints.
deviations: "None."
limitations: >-
  Documentation-only change. Native Windows and macOS checks are
  deferred to release. The Linux suite used Python 3.12.12.
files:
  src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md: >-
    Align step 4 with the script child's environment and link the
    canonical sentinel explanation.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: b25ad3f5e609ee5661b5008af3af1bd7d2785d98
  base: a4d06e84e0fe006109bc0afe0fa1117c3688ab80
  detail: >-
    Direct Codex review completed with no findings on the rebased diff.
    Checked the launcher environment block and linked inactivity topic.
checks:
  - command: .venv/bin/python -m pytest -q -p no:cacheprovider
    status: passed
    head: b25ad3f5e609ee5661b5008af3af1bd7d2785d98
    base: a4d06e84e0fe006109bc0afe0fa1117c3688ab80
    detail: >-
      Pop!_OS 24.04 LTS (Linux), Python 3.12.12. 5179 passed, 33 skipped in 1113.51s.
  - command: git diff --check origin/main...HEAD
    status: passed
    head: b25ad3f5e609ee5661b5008af3af1bd7d2785d98
    base: a4d06e84e0fe006109bc0afe0fa1117c3688ab80
    detail: "No whitespace errors."
```

## Blockers

- [x] [2026-11-18 21:38] [agent:codex] id=20261118T213802 Before opening this PR, wait for #1244 (v1/microkernel/09-work-orchestration-commands-to-tickets) and #1247 (v1/microkernel/move-slack-fyis-to-a-command-ticket) to land or be rebased, as required by the ticket. Then unblock and refresh the peer-review handoff against current main.
  resolved: [2026-11-20 16:13] [human:nicktoper] GitHub confirms #1244 and #1247 both merged on November 19, 2026, at 20:32:56 UTC and 20:33:18 UTC respectively. Both publication prerequisites are satisfied. Refresh the peer review and handoff against current main.

- [x] [2026-11-19 11:20] [agent:codex] id=20261119T112015 Wait for both overlapping PRs #1244 (v1/microkernel/09-work-orchestration-commands-to-tickets) and #1247 (v1/microkernel/move-slack-fyis-to-a-command-ticket) to land or be rebased, or explicitly waive that publication condition. Both PRs remain open with no new commits since the original blocker. Then unblock and refresh the peer-review handoff against current main.
  resolved: [2026-11-20 16:13] [human:nicktoper] GitHub confirms #1244 and #1247 both merged on November 19, 2026, at 20:32:56 UTC and 20:33:18 UTC respectively. Both publication prerequisites are satisfied. Refresh the peer review and handoff against current main.


---

## Blocker reminders

- e7ff8d2aff56 last_reminded: 2026-11-19 09:03

- 31bca67a2c7a last_reminded: 2026-11-20 12:11
