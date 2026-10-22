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
step: 2 (peer-review)
agent: claude
launch_generation: pending:8bb04620-41d9-4dd9-b402-a7454e5da0c1
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

branch: coga/blocks-05-trim-the-notifications-family

## Handoff (implement)

Done on the branch (commit `db0ef105b`, pushed). Every README row for this family is applied:

- `coga/notifications`: the Configuration section is gone. Slack keys are now documented once, in the shipped `coga.toml`, which gained the facts only the topic had: Slack inferred when `channels` is absent, unknown channel fails load, `channels = []` gives one stderr line, three keys overridable locally, the `--check-slack` empty payload, opt-out behaviour and its cost, GIF kinds with the `panic` fallback, member IDs not secret. The fail-loud sentence was also corrected, because `fatal=False` posts report rather than crash. Message format, the snapshot test, #56 history, `OUTCOME_EVENT_KINDS`/`ValueError`, "outbound only" and "Adding a notifying command" moved to coga-dev. The new user section "When a post fails" holds the failures summary: best-effort vs refuse-before-write, never rerouted, rotate a leaked webhook. Kept the `#pinging-the-owner` anchor, which `coga/recurring/usage-report/ticket.md` and `coga/skills/coga/usage-report/post` link.
- `notifications/producers`: dropped the Caller column, the "grep for the real call" note and the Accounting rule. Kept the phone-home "miss stays off log" fact as user-visible.
- `notifications/failures`: deleted (both copies, and its entry in `test_packaging.py`). Links repointed in `sync` (row merged; design-rule step 1 now links coga-dev internals), `important` (→ `notifications#when-a-post-fails`), `producers`, `notifications`, `docs/README.md`, and the coga-dev `testing` page.
- `important`: removed the repo-specific usage-report carve-out sentence. This follows the audit: the decision is this repo's, and it is now recorded on the coga-dev page. "Not covered here" now points webhook config at `coga.toml`.
- New coga-dev page `internals/notifications` (157 lines, listed in the `internals` index), holding failure internals, preflight callers, log gaps, redaction, the caller list, the accounting rule, the usage-report exception, message format, and "Adding a notifying command".

Decisions / disagreement for owner: none against the audit. One judgment call: the generic "a repo may route a low-volume report to important" sentence was dropped rather than kept generic. If this conflicts with PR #1081 (ticket 02), which rewrites the same packaged `important` lines, take this version.

Verification:
- `.venv/bin/python -m pytest -q`: 3952 passed, 7 skipped, 3 failed. All 3 are `tests/test_packaging.py` failures already present on main (`identical`, `distribution_is_complete`, `navigation_has_no_broken_links`). They come from ticket 02's canonical half reaching main via sweep commit `001aad66f` (`coga/code` deletion plus 14 drifted twins), and PR #1081 carries the fix. No problem involves a file this branch touches, and the touched twins are verified by `cmp`.
- `coga validate --json`: 0 errors, 47 pre-existing warnings.
- After the rebase onto `aa64b7b7f` (only this ticket changed), `tests/test_packaging.py` and `tests/test_validate.py` were re-run with the same 3 failures.

Review has not run yet; peer-review is the next step.

## PR

```yaml
title: Trim the notifications family and split notifications/failures
author: claude (Claude Code, claude-opus-5-5)
head: db0ef105b61a501676a73158799cdf5bc4f87444
base: aa64b7b7fa61a8a7f8eab9eb1fdbd0df361f7972
review_depth: skim
review_depth_rationale: docs-only reorganization plus coga.toml comments and one test-list entry; no runtime code changes
files:
  docs/contexts/coga/notifications/SKILL.md: user contract trimmed; failure summary added; config pointed at coga.toml
  docs/contexts/coga/notifications/producers/SKILL.md: caller column and accounting rule removed
  docs/contexts/coga/notifications/failures/SKILL.md: deleted (split)
  docs/contexts/coga/important/SKILL.md: repo-specific exception removed; failures link repointed
  docs/contexts/coga/sync/SKILL.md: failures row merged; design rule links coga-dev internals
  src/coga/resources/templates/coga/bootstrap/contexts/coga/{notifications,notifications/producers,important,sync}/SKILL.md: byte-identical twins
  src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/failures/SKILL.md: deleted twin
  src/coga/resources/templates/coga/coga.toml: notification comments absorb topic-only config facts
  docs/contexts/coga-dev/internals/notifications/SKILL.md: new internals page
  docs/contexts/coga-dev/internals/SKILL.md: index entry
  docs/contexts/coga-dev/testing/SKILL.md: link repointed to coga.toml comments
  docs/README.md: failures link removed
  tests/test_packaging.py: drop coga/notifications/failures from the bootstrap context set
checks:
  - command: .venv/bin/python -m pytest -q
    head: de36a7b89 (same tree as db0ef105b minus rebase of ticket-only main commit)
    result: 3 failed, 3952 passed, 7 skipped; failures pre-exist on main (ticket 02 sweep)
  - command: .venv/bin/python -m pytest -q tests/test_packaging.py tests/test_validate.py
    head: db0ef105b
    result: 3 failed (same pre-existing), 180 passed
  - command: coga validate --json
    result: rc 0, 47 warnings, no errors
review: not run (peer-review step follows)
```

The blackboard is a notepad to be written to often as the human and agent works through a task.
