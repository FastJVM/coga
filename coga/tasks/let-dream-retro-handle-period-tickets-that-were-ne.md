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

branch: coga/let-dream-retro-handle-period-tickets-that-were--72379e
base: main
remote: origin
reviewed: 8323da1ba7e6977b187828205b8b6655c0f24d9d

## Decision

Owner chose option (a) on 2026-11-27 (attended implement session). (b)
would lose `## Gotchas`, because the scanner deletes without Retro. (c) would
make every sweep a Git writer on the operator's branch. There was also a
pre-existing problem: Retro's stop-and-ask on "source absent from isolated
base" meant an untracked slug would have halted the whole pass.

Dream delegates a done period ticket from its snapshot when the exact task
artifact is absent from the index, local HEAD, and fetched base. Retro
publishes any knowledge in its theme's PR and appends a handoff receipt.
Dream verifies the required receipts, rechecks the exact live artifact and
firing evidence, verifies the local delete, and then removes the snapshot.
Locally tracked period tickets missing from the base stay for the scanner.
Ordinary tickets missing from the base are reported as human-needed.

## Peer-review findings

Codex independently reviewed Claude's original implementation at
`589de88d4d959c4b1eb4cfdfdcb6c95efb762d77`. The owner approved corrections.
`3ba79b249` moves local cleanup ahead of snapshot teardown, requires a matching
verified knowledge PR for each extract handoff, and routes the untracked
exception before Retro's marker and delete steps. It also requires a matching
live artifact and firing. `8323da1ba` adds the local HEAD check after a probe
showed that the index is empty for a locally committed, staged removal.

A disposable Git repo confirmed that a changed status, hidden attachment,
new firing audit for an identical artifact, staged attachment, and staged
removal each fail the applicable guard. The CLI removed only the eligible
artifact and preserved the neighbor and the serviced-period ledger.

## PR

```yaml
title: Let Dream Retro handle period tickets that were never committed
author: claude
author_evidence: >-
  Claude Code (claude-opus-5-5) implemented the feature in the attended session.
  Codex independently reviewed that implementation, then authored the two
  correction commits in the review step with owner approval.
head: 8323da1ba7e6977b187828205b8b6655c0f24d9d
base: 9460fd8aa33f9f8a2fc2d25658ed86f909c6f27c
depth: deep
rationale: >-
  Dream can permanently delete untracked period tickets. The handoff, Git,
  and snapshot checks determine whether the local artifact can be removed.
implementation: >-
  Dream snapshots eligible period tickets absent from the index, local HEAD
  and fetched base. Retro classifies them, opens any knowledge PRs, and hands
  the slugs back through progress receipts. Dream verifies the receipts and
  the live artifact and firing before deleting locally, then verifies deletion
  before discarding the evidence.
deviations: >-
  None from option (a). Locally tracked period tickets absent from the base
  stay for the scanner. Ordinary tickets missing from the base are surfaced
  as human-needed.
limitations: >-
  A live Dream run has yet to exercise the new path. A disposable Git repo
  exercised the pre-delete guards and real CLI deletion. Native Windows and
  macOS verification is deferred to release. The earlier Python 3.11
  review run reproduced one config symlink failure on both the original
  implementation and its base.
files:
  src/coga/resources/templates/coga/recurring/dream/ticket.md: >-
    Select eligible untracked periods, verify handoffs and live state, and
    retain recovery evidence until cleanup is verified.
  src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md: >-
    Route untracked periods around source mutations and emit handoff receipts
    after knowledge PR evidence.
  tests/test_dream_worker_templates.py: >-
    Guard the selection, verification, deletion and teardown instructions.
  tests/test_retro_skill_template.py: >-
    Guard the untracked workflow route and receipt ordering.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 8323da1ba7e6977b187828205b8b6655c0f24d9d
  base: 9460fd8aa33f9f8a2fc2d25658ed86f909c6f27c
  detail: >-
    Codex independently reviewed Claude's full diff, then corrected and reviewed
    the resulting diff against the recorded base. The final head includes Codex's
    own corrections. The review traced normal Dream and retire paths, the delete
    CLI, the recurring scanner fallback, and receipt and cleanup failures. No
    must-fix findings remain.
checks:
  - command: PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/test_dream_worker_templates.py tests/test_retro_skill_template.py
    status: passed
    head: 8323da1ba7e6977b187828205b8b6655c0f24d9d
    base: 9460fd8aa33f9f8a2fc2d25658ed86f909c6f27c
    detail: >-
      26 passed in 0.26s on Pop!_OS 24.04 LTS, Python 3.12.12.
  - command: PYTHONPATH=$PWD/src .venv/bin/python -m coga.cli validate --task let-dream-retro-handle-period-tickets-that-were-ne
    status: passed
    head: 8323da1ba7e6977b187828205b8b6655c0f24d9d
    base: 9460fd8aa33f9f8a2fc2d25658ed86f909c6f27c
    detail: One task checked, no errors.
  - command: env -u SLACK_WEBHOOK_URL PYTHONPATH="$PWD/src" .venv/bin/python -
    status: passed
    head: 8323da1ba7e6977b187828205b8b6655c0f24d9d
    base: 9460fd8aa33f9f8a2fc2d25658ed86f909c6f27c
    detail: >-
      Inline disposable-checkout probe checked missing ref, changed status,
      hidden attachment, new audit for identical bytes, staged attachment,
      and staged removal. Exact CLI deletion preserved the neighboring ticket
      and ledger. Pop!_OS 24.04 LTS, Python 3.12.12.
  - command: TMPDIR=/tmp/coga-retro-review.aibWZv PYTHONPATH="$PWD/src" PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m pytest -q --tb=short
    status: passed
    head: 8323da1ba7e6977b187828205b8b6655c0f24d9d
    base: 9460fd8aa33f9f8a2fc2d25658ed86f909c6f27c
    detail: >-
      3242 passed, 29 skipped in 167.42s on Pop!_OS 24.04 LTS, Python 3.12.12.
      Native Windows and macOS verification is deferred to release.
```
