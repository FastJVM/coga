---
title: 08 Trim launch, prompt and workflow topics
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
---

## Description

Apply the audit verdicts to launch, prompt-composition (absorbing session-conduct), lifecycle, megalaunch, human-assist, pr-publication (absorbing existing-pr), script-tickets and workflows. See `coga/tasks/blocks/README.md`.

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

Done when: the rows in the README table for launch, prompt-composition, session-conduct, lifecycle, megalaunch, human-assist, pr-publication, pr-publication/existing-pr, script-tickets and workflows are applied, `session-conduct` is merged into `prompt-composition`, `existing-pr` into `pr-publication`, and `launch` and `workflows` are under 160 lines; both copies of every touched topic are byte-identical;
no link in `docs/`, `src/`, `tests/`, `coga/` (outside old tickets and the
log), `README.md` or `AGENTS.md` points at a removed topic or anchor; any new
coga-dev page is listed in `docs/contexts/coga-dev/internals/SKILL.md`;
`.venv/bin/python -m pytest` and `coga validate --json` pass.

### Specifics

- New coga-dev page: `internals/compose` (prompt-composition internals).
  Existing: `agent-spawn`, `activity-capture`, `launch-claims`,
  `assist-publication`, `git-refresh`.
- Repoint `bootstrap/skills/code/open-pr/SKILL.md` (existing-pr link) and
  every link to `session-conduct`; drop it from
  `REQUIRED_BOOTSTRAP_CONTEXT_REFS` in `tests/test_packaging.py`; and the `commands/owner.py` comment citing lifecycle.
- One owner for the assist attribution exception (`human-assist`).
- `launch`'s checkout boundary becomes a summary + link to
  `checkouts/launch-boundary` (ticket 03 owns that topic).


<!-- coga:blackboard -->

## Handoff (implement, 2026-10-21)

Done on `coga/blocks-08-trim-launch-prompt-workflow` (commits `f245d49a7`
+ `2a5c0f6c3`, pushed; based on main `64c008fc2`). Every README row for this ticket applied:

- `session-conduct` merged into `prompt-composition` ("Session conduct":
  selection table + override note; postures stay in the `prompt-*.md`
  resources, which already state them). `existing-pr` merged into
  `pr-publication` ("Updating an existing PR"). Both copies of both removed
  topics deleted; dropped from `REQUIRED_BOOTSTRAP_CONTEXT_REFS`; links
  repointed in `architecture`, `recurring/scheduling`, `docs/README.md`,
  `code/open-pr` skill (live + bootstrap), coga-dev `agent-spawn`.
- `launch` 192 -> 144 lines: API/phases -> coga-dev `internals/agent-spawn`;
  checkout boundary is a summary + link to `checkouts/launch-boundary`;
  assist attribution now owned only by `human-assist`.
- `workflows` 200 -> 159 lines: branch-gate and code-review decisions, Dream
  W43 case, reading rules -> coga-dev `current-direction`; function names dropped.
- `prompt-composition` internals -> new coga-dev `internals/compose` (listed
  in `internals/SKILL.md`); `activity-capture`'s `#launch-marker` link repointed.
- `lifecycle` "Writer validation timing" -> coga-dev `codebase/gotchas`;
  `commands/owner.py` comment repointed. Lifecycle twin re-synced.
- `megalaunch` flag prose/function names -> `launch-claims` source notes.
- `human-assist` names/alignment loop/`COGA_ASSIST_*` -> `assist-publication`.
- `pr-publication` function names, retired-layout clauses, record parsing ->
  `git-refresh` "`coga open-pr` source notes".
- `script-tickets` "Why this shape" + source map -> coga-dev `microkernel`.
- Known defect (`--prompt-report` still sweeps) filed as draft
  `stop-launch-prompt-report-from-sweeping-coga-state` and removed from launch.

Not changed: `docs/release-notes/context-audiences.md` names `existing-pr` in
a dated rename table (text, not a link).

### Rebase after blocks/02 landed (2026-10-22)

The blocker (main red from ticket 02's half-published twins) cleared when
PR #1081 merged; unblocked and rebased onto `64c008fc2`. Conflicts were
four coga-dev internals pages that main also extended (`internals/SKILL.md`
index, `agent-spawn` description, `git-refresh`, `launch-claims`): kept both
sides. Ticket 01's `coga/agents` -> `coga/configuration` change pushed
`workflows` to 160 lines; commit `2a5c0f6c3` rewraps that sentence (both
copies) back to 159. Suite now green. Lesson kept: commit `docs/contexts`
edits on the branch before any sweeping `coga` command.

## PR

```yaml
title: Trim launch, prompt, lifecycle, workflow and PR topics
author: claude
author_evidence: Implement session ran in Claude Code (claude-opus-5-5); see handoff above.
head: 2a5c0f6c3a9111a6cb0054a205f1638f2a3fdbf1
base: 64c008fc2fa80a9f978cfb2f47af9779d6596c37
depth: skim
rationale: Documentation-only moves plus one code comment; read the description for which facts left the shipped topics and where they went.
implementation: Applies the blocks/08 audit rows; merges session-conduct into prompt-composition and existing-pr into pr-publication; moves internals to coga-dev pages (new internals/compose).
deviations: Launch's Python API went to internals/agent-spawn (no dedicated launch page exists). Workflows' dated decisions went to coga-dev current-direction.
limitations: None known.
files:
  coga/skills/code/open-pr/SKILL.md: Repoint existing-pr link to pr-publication.
  src/coga/resources/templates/coga/bootstrap/skills/code/open-pr/SKILL.md: Packaged twin of the open-pr skill link fix.
  docs/README.md: Drop removed topics from the library index.
  docs/contexts/coga/architecture/SKILL.md: Drop links to removed topics.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md: Same link fix in the packaged copy.
  docs/contexts/coga/recurring/scheduling/SKILL.md: Repoint session-conduct link.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: Same link fix in the packaged copy.
  docs/contexts/coga/launch/SKILL.md: Trim to user contract under 160 lines.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md: Packaged twin.
  docs/contexts/coga/prompt-composition/SKILL.md: Absorb session-conduct; move internals out.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md: Packaged twin.
  docs/contexts/coga/session-conduct/SKILL.md: Deleted; merged into prompt-composition.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/session-conduct/SKILL.md: Deleted packaged twin.
  docs/contexts/coga/lifecycle/SKILL.md: Drop writer-validation internals and dated/private names.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md: Packaged twin, re-synced.
  docs/contexts/coga/megalaunch/SKILL.md: Drop flag prose and function names.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/megalaunch/SKILL.md: Packaged twin.
  docs/contexts/coga/human-assist/SKILL.md: Drop internals; single owner of assist attribution.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/human-assist/SKILL.md: Packaged twin.
  docs/contexts/coga/pr-publication/SKILL.md: Absorb existing-pr; drop function names and record parsing.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/pr-publication/SKILL.md: Packaged twin.
  docs/contexts/coga/pr-publication/existing-pr/SKILL.md: Deleted; merged into pr-publication.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/pr-publication/existing-pr/SKILL.md: Deleted packaged twin.
  docs/contexts/coga/script-tickets/SKILL.md: Drop design rationale and function names.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md: Packaged twin.
  docs/contexts/coga/workflows/SKILL.md: Drop history and names; under 160 lines.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md: Packaged twin.
  docs/contexts/coga-dev/internals/compose/SKILL.md: New page for prompt-composition internals.
  docs/contexts/coga-dev/internals/SKILL.md: List the compose page; note agent-spawn's launch API.
  docs/contexts/coga-dev/internals/agent-spawn/SKILL.md: Receive launch API/phases; repoint conduct ref.
  docs/contexts/coga-dev/internals/activity-capture/SKILL.md: Repoint launch-marker anchor to compose.
  docs/contexts/coga-dev/internals/assist-publication/SKILL.md: Receive assist alignment and identity internals.
  docs/contexts/coga-dev/internals/git-refresh/SKILL.md: Receive open-pr source notes and record parsing.
  docs/contexts/coga-dev/internals/launch-claims/SKILL.md: Receive megalaunch source notes.
  docs/contexts/coga-dev/microkernel/SKILL.md: Receive the ticket.py design rationale and source map.
  docs/contexts/coga-dev/codebase/gotchas/SKILL.md: Receive prospective-validation rule from lifecycle.
  docs/contexts/coga-dev/current-direction/SKILL.md: Receive workflows' dated decisions and W43 evidence.
  src/coga/commands/owner.py: Comment now cites coga-dev/codebase/gotchas.
  tests/test_packaging.py: Drop removed topics from REQUIRED_BOOTSTRAP_CONTEXT_REFS.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Review is the workflow's later step; not yet run.
checks:
  - command: .venv/bin/python -m pytest -q
    status: passed
    head: f245d49a77db41e7090ccdda94fef82fa720ebbc
    base: 64c008fc2fa80a9f978cfb2f47af9779d6596c37
    detail: 3987 passed, 7 skipped. Head 2a5c0f6c3a9111a6cb0054a205f1638f2a3fdbf1 adds only a one-sentence rewrap in both workflows copies, covered by the packaging run below.
  - command: .venv/bin/python -m pytest -q tests/test_packaging.py
    status: passed
    head: 2a5c0f6c3a9111a6cb0054a205f1638f2a3fdbf1
    base: 64c008fc2fa80a9f978cfb2f47af9779d6596c37
    detail: 30 passed.
  - command: .venv/bin/coga validate --json
    status: passed
    head: f245d49a77db41e7090ccdda94fef82fa720ebbc
    base: 64c008fc2fa80a9f978cfb2f47af9779d6596c37
    detail: Exit 0; 158 ok, 48 issues, none errors.
```

## Dev

branch: coga/blocks-08-trim-launch-prompt-workflow

---

## Blockers

- [x] [2026-10-21 19:17] [agent:claude] id=20261021T191736 Depends on blocks/02-delete-the-code-topic-and-remove-coga-repo-only: implement is pushed (coga/blocks-08-trim-launch-prompt-workflow) but pytest has 3 packaging failures inherited from main, where commit 001aad66f published 02's docs/contexts edits without their packaged twins. Land 02 (then a relaunch rebases, reruns tests and bumps), or answer 'bump anyway' to send this to review with the inherited red suite.
  resolved: [2026-10-22 12:15] [human:nicktoper] blocks/02 landed on main (PR #1081, a1a3f5049). Rebase onto main, rerun tests, and bump if green.

---

## Blocker reminders

- 9b9d09c67721 last_reminded: 2026-10-22 09:03
