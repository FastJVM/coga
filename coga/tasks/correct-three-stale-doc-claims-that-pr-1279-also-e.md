---
title: Correct three stale doc claims that PR 1279 also edits
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

Filed by Dream 2026-W48 (run 20261123T224856Z), Phase 2 knowledge scan (shards ks-09, ks-06, ks-14). All three claims are wrong on main today, but open PR https://github.com/FastJVM/coga/pull/1279 (owner ticket v1/03-use-git-like-everyone-remove-coga-s-publication-ab) edits the same three files without carrying these fixes, so a separate main-based PR would collide. Land after or on top of #1279.

- F1 src/coga/resources/templates/coga/bootstrap/contexts/coga/knowledge/SKILL.md (~l.46-49): "Retro and `coga delete` remove a ticket without repairing inbound references". Since make-retro-check-inbound-doc-links-before-deleting, retro/done-ticket's Inbound references section repoints each live-tree reference to a full-OID permalink before deleting (knowledge PR or reference-pin PR; e.g. PR #1282). Only `coga delete` and the deterministic `coga retire` path skip it (open ticket warn-when-coga-delete-or-coga-retire-leaves-a-live adds a warning, not a repair). Reword; keep the advice to point durable surfaces at standing owners.
- F2 docs/contexts/coga-dev/microkernel/SKILL.md "Open command placements" table: the `owner` head's cleanup ticket is named `lifecycle-verbs-to-ticket-operations`; the ticket is v1/microkernel/15-lifecycle-verbs-to-ticket-operations (sibling rows already use numbered slugs).
- F3 docs/contexts/coga-dev/current-direction/SKILL.md: the "No branch freshness guard at bump (2026-10-06)" entry ends "Contract: coga/workflows", but coga/workflows says nothing about a bump-time freshness guard. Repoint to the topic that owns it (coga/git) or drop the link. (The scan's companion claim about the thin-ticket entry is false on main: coga/workflows l.144 names design-then-implement.)

Acceptance: each statement matches current behavior; links resolve; tests/test_packaging.py passes.

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

branch: coga/correct-three-stale-doc-claims-that-pr-1279-also-abb6b6
base: coga/v1-no-weird-state-in-personal-dir-d9bd4b
remote: origin
reviewed: 5edf21b45b76c636aa90c7cbace2824b3f90e5e5


## Implement handoff (2026-11-23)

Base `coga/v1-no-weird-state-in-personal-dir-d9bd4b` is PR #1280, stacked on
#1279's branch. Claude implemented the three corrections in dc473f331.

### Peer-review findings

Codex compared all three changes with the deletion and retire entry points,
the Retro skill, the numbered ticket and the bump and PR workflow gates.
The first correction generalized `coga retire` across both statuses. Review
commit 5edf21b45 limits direct deletion to the done-ticket path and links
the Retro procedure and ticket Git record sections directly. The canceled
path delegates to Retro. GitHub and the fetched base confirm the stack.
GitHub reports #1279 conflicts with `main`. Its versions of the three changed
docs match the recorded #1280 base at review time.

The Python 3.11 full suite failed only on `test_layout_context_artifact_symlink_rejected`.
`python -m pytest -q tests/test_config.py -k layout` reproduced it on the
recorded base (1 failed, 20 passed in 0.56s) and reviewed head (same counts in
0.52s) with the same CPython 3.11.15 environment and each tree's PYTHONPATH.
Python 3.11's `Path.rglob("SKILL.md")` omits the dangling symlink in the fixture.
Python 3.12 includes it. Packaging and link checks passed on Python 3.11.

### Incident: full suite run inside the launch damaged the checkout

The first `pytest` runs inherited the launch's `COGA_*` env and a `TMPDIR`
inside the repo (`coga/.coga/tmp/...`). They deleted 35 tracked files (coga.toml,
log.md, docs/contexts/coga-dev/*, coga/.gitignore, ...). I restored them from
HEAD with `git restore`. **Lost:** ~40 uncommitted lines in `coga/log.md`
(audit entries appended before this session), which are now back at the HEAD
version. The other uncommitted ticket edits survived. Reliable receipt
recipe: `env -u COGA_* ... TMPDIR=$(mktemp -d /tmp/...) .venv/bin/python -m pytest`.
Leftover `pytest-of-n` dirs in the launch TMPDIR also break
`test_packaged_workflow_scripts_have_their_canonical_paths`; I removed them.
This may deserve its own ticket: tests are not hermetic against a launch env.

The same runs also deleted **ignored** machine-local state, which Git cannot
restore: `coga/coga.local.toml` and `coga/.coga/data/` (durable agent state).
Repo-root `.coga/megalaunch-selection.json` (saved by the 15:56 `--pick`) was
lost too.

Recovery (owner grant in this session: "recreate ... + fix all that"):
`coga/coga.local.toml` recreated from the identical init-generated copy in
`../fastci` (`user = "nicktoper"`; Slack resolves through coga.toml's `env:`).
This task's data dir was recreated with `run_state.ensure_task_data_dir`, and
other tasks' dirs are recreated on their next launch. Not recoverable: the ~40
uncommitted `coga/log.md` lines (no Git blob holds them, and audit entries are
not invented) and the megalaunch selection (`--relaunch` needs a fresh
`--pick`). `coga validate` shows only pre-existing ticket drift.

### Push-step note

Unrelated uncommitted ticket edits from the shared checkout (other tickets'
`M`/`??` files) will trip push-and-open-pr's "Commit your work first" check.
They are not this ticket's to commit.

## PR

```yaml
title: Correct three stale doc claims that PR 1279 also edits
author: claude
author_evidence: >-
  Claude Code (claude-opus-5-5) wrote dc473f331 in the implementation session.
  Codex wrote 5edf21b45 during peer review.
head: 5edf21b45b76c636aa90c7cbace2824b3f90e5e5
base: c306d14d1aeee73ed065042cf3aa0a151aa73ae1
depth: deep
rationale: >-
  The three docs-only corrections are verified against their sources. The
  Python 3.11 suite has a symlink-validation failure also present on the base.
implementation: >-
  Clarifies which retirement paths repair durable references, corrects the
  owner cleanup ticket slug, and links the bump-freshness entry to the Git
  record while documenting the PR step's current-branch check.
deviations: >-
  F3 also replaces the stale claim that the PR step checks commits ahead of
  the base. The review adds direct links to the Retro and Git sections.
limitations: >-
  Stacked on PR 1280 and PR 1279. GitHub reports conflicts between PR 1279 and
  main. Native Windows and macOS verification is deferred to release per
  coga-dev/testing.
files:
  docs/contexts/coga-dev/current-direction/SKILL.md: "F3 links the Git record and describes the PR step's current-branch check."
  docs/contexts/coga-dev/microkernel/SKILL.md: "F2 corrects the numbered cleanup ticket for the owner head."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/knowledge/SKILL.md: "F1 describes Retro reference repair and the direct deletion path for done tickets."
review:
  reviewer: codex
  kind: independent
  status: passed
  head: 5edf21b45b76c636aa90c7cbace2824b3f90e5e5
  base: c306d14d1aeee73ed065042cf3aa0a151aa73ae1
  detail: >-
    Codex independently reviewed Claude's full three-file diff against its
    documented procedures, ticket path and command entry points. Claude and
    Codex worked in separate sessions. Codex authored the review correction,
    then reread and verified the resulting head. All three claims and links
    are accurate. The diff changes documentation only.
checks:
  - command: /tmp/coga-peer-review-_9q82i27/venv/bin/python -m pytest -q tests/test_packaging.py
    status: passed
    head: 5edf21b45b76c636aa90c7cbace2824b3f90e5e5
    base: c306d14d1aeee73ed065042cf3aa0a151aa73ae1
    detail: >-
      Pop!_OS 24.04 LTS (Linux), CPython 3.11.15, 41 passed in 14.25s,
      including link validation. Disposable clone, absolute PYTHONPATH,
      launch variables stripped and temporary paths outside both checkouts.
  - command: /tmp/coga-peer-review-_9q82i27/venv/bin/python -m pytest -q
    status: failed
    head: 5edf21b45b76c636aa90c7cbace2824b3f90e5e5
    base: c306d14d1aeee73ed065042cf3aa0a151aa73ae1
    detail: >-
      Pop!_OS 24.04 LTS (Linux), CPython 3.11.15, 1 failed, 3189 passed,
      29 skipped in 222.66s. Layout symlink test also failed on the base
      in a focused comparison. Same isolated environment as packaging.
  - command: /home/n/Code/coga/.venv/bin/python -m pytest -q
    status: passed
    head: 5edf21b45b76c636aa90c7cbace2824b3f90e5e5
    base: c306d14d1aeee73ed065042cf3aa0a151aa73ae1
    detail: >-
      Pop!_OS 24.04 LTS (Linux), CPython 3.12.12, 3190 passed, 29 skipped
      in 188.30s. Disposable clone, absolute PYTHONPATH, launch variables
      stripped and temporary paths outside both checkouts.
```
