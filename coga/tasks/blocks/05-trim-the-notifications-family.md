---
title: 05 Trim the notifications family
status: in_progress
owner: nicktoper
contexts:
- coga/knowledge
- coga-dev/packaging
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
step: 4 (review)
agent: claude
---

## Description

Apply the audit verdicts to coga/notifications, notifications/producers and important; split notifications/failures into a user summary and a coga-dev internals page. See `coga/tasks/blocks/README.md`.

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

### Scope and acceptance

Read `coga/tasks/blocks/README.md` first: it holds the test, the rules every
ticket in this group follows, and the audit rows for these topics. The audit
verdicts are recommendations; re-check each against current main and record
any disagreement on the blackboard for the owner before departing from it.

Done when: the notifications rows in the README table are applied, `notifications/failures` is split and deleted, and Slack configuration is documented once (the shipped `coga.toml`); both copies of every touched topic are byte-identical;
no link in `docs/`, `src/`, `tests/`, `coga/` (outside old tickets and the
log), `README.md` or `AGENTS.md` points at a removed topic or anchor; any new
coga-dev page is listed in `docs/contexts/coga-dev/internals/SKILL.md`;
`.venv/bin/python -m pytest` and `coga validate --json` pass.

### Specifics

- `notifications/producers` stays a user topic: `workflows/blocker-reminders/run.md`
  and `bootstrap/skills/coga/blockers/remind/SKILL.md` cite it.
- New coga-dev page: `internals/notifications` (failures internals, caller
  columns, message format, accounting rule, "Adding a notifying command").
- Repoint links to `notifications/failures` from `sync`, `important`,
  `notifications`, `producers`.


<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/1085
branch: coga/blocks-05-trim-the-notifications-family

## Implementation

Claude Code / Claude Opus 5.5 implemented the audit in `db0ef105b`, now
rebased as `7ef1c3a2d`. Notification topics are trimmed; the failures topic is
split between the user summary and local internals; Slack configuration lives
in shipped TOML comments. The new internals page is indexed and removed-topic
links and registration are repaired. No audit disagreement. Codex's earlier
review corrections are `d817f2ac3`; the packaged-template sync is `c18575a28`.

## Peer review

**Direct review completed** by Codex on final head `c18575a282a151b8d83c41d8a36b82fd8f7d5a05`
against base `293ea3f29abd1b9d9678a426132a7e0d47a3554b`. No unresolved findings.
Codex independently reviewed Claude's original implementation and self-reviewed
its own corrections, rebase resolutions and the two template syncs. The
combined receipt is therefore self-review. No nested reviewer CLI or subagent ran.

The owner cleared the blocker after PR #1081 merged as `a1a3f5049`;
`coga unblock` recorded the resolution. Rebased onto current main, preserving
main's usage-pricing index entry and this family's canonical important-topic
cleanup. The projected ticket was backed up and restored byte-for-byte; the
unblock audit entry was already published before rebase.

Earlier review corrections remain: distinguish explicit-send failure from
best-effort post-transition announcements and name the actual pre-write gates;
move sync's developer procedure into coga-dev/patterns so shipped guidance
requires only user knowledge; remove duplicate owner-map setup while preserving
its anchor and the usage-report decision's rationale.

The first resumed suite at `d817f2ac3` completed with **2 failed, 3985 passed,
7 skipped in 373.93s**. Only `test_autoclose_live_and_packaged_copies_stay_in_sync`
and `test_live_and_packaged_copies_stay_identical` failed. Main's `ee50b4ba4`
had published live autoclose/branch-sweep template links without their packaged
twins. Commit `c18575a28` carries the exact two-template sync already approved
for PR #1084. Both corrected templates now match their live copies.

Reviewed all 19 final diff paths and the user/developer split against dispatch,
redaction, preflight callers, configuration parsing, validation and producers.
Four surviving topic pairs match, both failures copies are absent, the new
internals page is indexed, and live navigation has no removed topic/anchor
references. Old tickets and audit prose remain under the group's exclusion.
No Slack-rendering or terminal exercise applies: executable UI and message
formats are unchanged.

Verification on the final head/base above (Python 3.12.12):

- `PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest -q`:
  **3987 passed, 7 skipped in 365.12s (0:06:05)**.
- `PYTHONPATH=/home/n/Code/claude/coga/src coga validate --json`:
  **156 OK, 0 errors, 48 warnings, 0 fixes**, exit 0.
- `.venv/bin/python /tmp/coga-blocks05-resumed-review-rbw6mdpi/doc_audit.py`:
  passed; no enforced twin drift, navigation/distribution errors or prohibited
  shipped developer references; parsed TOML unchanged; 360 Markdown sources checked.
- Pristine-clone wheel build and `.venv/bin/python /tmp/coga-blocks05-resumed-review-rbw6mdpi/verify_wheel.py`:
  passed; changed resources match and removed/local-only topics do not ship.
- `git diff --check origin/main...HEAD`: passed.

The branch is committed and pushed with `--force-with-lease` at `c18575a28`,
three commits ahead of main. The final freshness fetch still names the reviewed
base. Coga's read-only PR formatter accepts the 19-path preparation without
evidence gaps. Only this projected ticket remains unstaged; no PR was opened
in this step.

Recommendation: **skim** for the pulled-forward blocks/06 sync procedure and
the two previously approved packaged-template syncs. No Python 3.11 run was
performed. The required review and verification are complete; open-pr is next,
and launch owns returning the checkout after the transition.

## PR

```yaml
title: Trim notification topics and separate user guidance from internals
author: claude/codex
author_evidence: The implement handoff identifies Claude Code / Claude Opus 5.5 as author of db0ef105b,
  now rebased as 7ef1c3a2d. Codex independently reviewed that implementation and authored the earlier
  corrections b5668d59a, now d817f2ac3. This resumed Codex session resolved the rebase and authored the
  two packaged-template syncs in c18575a28.
head: c18575a282a151b8d83c41d8a36b82fd8f7d5a05
base: 293ea3f29abd1b9d9678a426132a7e0d47a3554b
depth: skim
rationale: 'Bounded documentation reorganization with no runtime behavior change. Direct review completed
  and the full suite, validation, twin/link audit and pristine wheel checks passed on this head. Read
  the pulled-forward sync procedure and the two packaged-template syncs already approved for PR #1084.
  Codex corrections and reconciliation are disclosed as self-review.'
implementation: Trim notifications, producers and important; replace notifications/failures with an accurate
  user failure summary and indexed local developer internals. Centralize Slack configuration in shipped
  TOML comments, repair navigation and keep twins identical. Clarify explicit-send versus post-transition
  failure behavior and move the sync implementation procedure to coga-dev/patterns. Synchronize two packaged
  recurring templates with their existing live copies.
deviations: 'No audit disagreement or runtime behavior change. The sync design procedure planned for blocks/06
  was pulled forward so shipped guidance does not require local-only developer reading. Two recurring-template
  link syncs already approved for PR #1084 are included to repair main’s pre-existing twin failures; they
  are byte-identical to that PR’s fixes. Old ticket prose and audit history remain under the group’s exclusion.'
limitations: 'Python 3.12.12 was tested; no Python 3.11 run is claimed. No live Slack or TTY exercise
  applies because executable UI and rendered messages are unchanged. Codex independently reviewed the
  original Claude implementation and self-reviewed Codex corrections, rebase resolutions and template
  syncs; no separate reviewer covered those corrections. PR #1081 is merged and included.'
files:
  docs/README.md: Remove the deleted notifications/failures navigation entry.
  docs/contexts/coga-dev/internals/SKILL.md: Index the new notification internals owner.
  docs/contexts/coga-dev/internals/notifications/SKILL.md: Own failure internals, producer callers, accounting,
    message format, and the repo-specific usage-report decision.
  docs/contexts/coga-dev/patterns/SKILL.md: Receive the developer-only sync design procedure so shipped
    guidance does not require an unshipped topic.
  docs/contexts/coga-dev/testing/SKILL.md: Point notification setup guidance at the shipped configuration
    comments.
  docs/contexts/coga/important/SKILL.md: Remove the repo-specific report exception and repoint failure
    and configuration guidance.
  docs/contexts/coga/notifications/SKILL.md: Retain the user contract and accurate failure summary; move
    setup and developer details to their owners.
  docs/contexts/coga/notifications/failures/SKILL.md: Delete the split topic after moving user guidance
    and internals.
  docs/contexts/coga/notifications/producers/SKILL.md: Keep the user-visible event/destination inventory
    and move caller/accounting detail to developer guidance.
  docs/contexts/coga/sync/SKILL.md: Repoint failures navigation and replace the developer procedure with
    optional navigation.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/important/SKILL.md: Keep the packaged important
    topic byte-identical to its canonical owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/SKILL.md: Keep the packaged
    notification topic byte-identical to its canonical owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/failures/SKILL.md: Delete the
    packaged twin of the split failures topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/producers/SKILL.md: Keep the
    packaged producer inventory byte-identical to its canonical owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md: Keep the packaged sync overview
    byte-identical to its canonical owner.
  src/coga/resources/templates/coga/coga.toml: Own the moved Slack configuration comments without changing
    parsed settings.
  tests/test_packaging.py: Remove the retired failures topic from required bootstrap contexts.
  src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.md: 'Synchronize checkout-cleanup
    links with the live template already on main, using the exact fix previously approved for PR #1084.'
  src/coga/resources/templates/coga/recurring/branch-sweep/ticket.md: 'Synchronize checkout-cleanup links
    with the live template already on main, using the exact fix previously approved for PR #1084.'
review:
  reviewer: codex
  kind: self
  status: passed
  head: c18575a282a151b8d83c41d8a36b82fd8f7d5a05
  base: 293ea3f29abd1b9d9678a426132a7e0d47a3554b
  detail: Direct review completed on the final head/base with no unresolved findings. Independent review
    of the Claude implementation, plus self-review of Codex corrections, rebase resolutions and the template
    syncs. Checked the audit verdicts and moved contracts against notification dispatch, redaction, preflight
    callers, config parsing, validation and producers; reviewed all 19 diff paths, navigation and twins.
    No nested reviewer CLI or subagent ran.
checks:
- command: PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest -q
  status: passed
  head: c18575a282a151b8d83c41d8a36b82fd8f7d5a05
  base: 293ea3f29abd1b9d9678a426132a7e0d47a3554b
  detail: 'Python 3.12.12: 3987 passed, 7 skipped in 365.12s (0:06:05). Completed after the final sync
    commit. Log: /tmp/coga-blocks05-resumed-review-rbw6mdpi/pytest-final.log.'
- command: PYTHONPATH=/home/n/Code/claude/coga/src coga validate --json
  status: passed
  head: c18575a282a151b8d83c41d8a36b82fd8f7d5a05
  base: 293ea3f29abd1b9d9678a426132a7e0d47a3554b
  detail: 'Exit 0: 156 OK, 0 errors, 48 warnings, 0 fixes; warnings concern existing ticket state.'
- command: .venv/bin/python /tmp/coga-blocks05-resumed-review-rbw6mdpi/doc_audit.py
  status: passed
  head: c18575a282a151b8d83c41d8a36b82fd8f7d5a05
  base: 293ea3f29abd1b9d9678a426132a7e0d47a3554b
  detail: Four surviving topic pairs and both recurring-template pairs are byte-identical; both failures-topic
    copies are absent. Across 360 Markdown sources outside archives/tasks/log, no notification link errors;
    no global context navigation or distribution errors, no enforced twin drift, and no prohibited shipped
    developer references. Parsed TOML settings are unchanged. The new developer topic is indexed. Old
    task references were inspected and retained under the group’s exception.
- command: git diff --check origin/main...HEAD
  status: passed
  head: c18575a282a151b8d83c41d8a36b82fd8f7d5a05
  base: 293ea3f29abd1b9d9678a426132a7e0d47a3554b
  detail: No whitespace errors on the final branch diff.
- command: /home/n/Code/claude/coga/.venv/bin/python -m pip wheel --no-build-isolation --no-deps . -w
    /tmp/coga-blocks05-resumed-review-rbw6mdpi/wheels
  status: passed
  head: c18575a282a151b8d83c41d8a36b82fd8f7d5a05
  base: 293ea3f29abd1b9d9678a426132a7e0d47a3554b
  detail: Built coga-0.4.1-py3-none-any.whl successfully in a pristine clone at /tmp/coga-blocks05-resumed-review-rbw6mdpi/clean
    of this exact head. The clone was created with git clone --quiet --no-hardlinks --single-branch --branch
    coga/blocks-05-trim-the-notifications-family /home/n/Code/claude/coga /tmp/coga-blocks05-resumed-review-rbw6mdpi/clean.
- command: .venv/bin/python /tmp/coga-blocks05-resumed-review-rbw6mdpi/verify_wheel.py
  status: passed
  head: c18575a282a151b8d83c41d8a36b82fd8f7d5a05
  base: 293ea3f29abd1b9d9678a426132a7e0d47a3554b
  detail: Pristine clone remains clean. Wheel contains byte-identical copies of the four changed user
    topics, the two corrected recurring templates and the shipped TOML. The retired failures topic, all
    local-only developer contexts and build-state directories are absent.
```

## Blockers

- [x] [2026-10-21 18:01] [agent:codex] id=20261021T180105 Merge PR #1081 for blocks/02-delete-the-code-topic-and-remove-coga-repo-only to repair the three required packaging-test failures reproduced on main. Then rebase the pushed branch, rerun pytest and validation, and refresh the final review receipts before bumping. Direct review and documentation fixes are complete at b5668d59a; validation passes.
  resolved: [2026-10-21 21:55] [human:nicktoper] The owner confirmed clearing this dependency blocker and resuming review. PR #1081 merged as a1a3f5049b5dd2457f531a4d81b79b6a6425bb9f and is present on fetched origin/main. Rebase the branch, preserve notification cleanup through overlaps, rerun the full suite and validation, and refresh final review receipts before bumping.
