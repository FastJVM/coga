---
title: Correct migration claims the fix-stale branch's files still make
status: blocked
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
step: 3 (peer-review)
agent: claude
---

## Description

Filed by Dream recurring/dream, period 2026-W48 (run 20261125T175534Z), Phase 6 disposition of Phase 2 knowledge-scan / Phase 3 contract-audit findings.

These living docs still describe machinery removed by the plain-Git migration (#1279). Every target is a file that the unpushed branch coga/fix-stale-doc-references-left-by-the-plain-git-m-bc5100 (ticket fix-stale-doc-references-left-by-the-plain-git-mig, B1-B24) already edits, but that branch does not carry these fixes. A separate main-based PR would conflict, so land them on top of that branch or after it merges. Verified not fixed on that branch, and still stale against origin/main.

- G13 (ca-08, ks-01) src/coga/resources/templates/coga/recurring/resolve-conflicts/ticket.md l.31-46: replace the lease/generation/control/strict-publication paragraph with a pointer to coga/recurring/delegation.
- G20 (ks-01, ca-04) src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/autofix/SKILL.md l.83: delete 'temp-control scans copy it back to the durable workspace'.
- G23 (ks-01, ca-04) src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/SKILL.md l.87-88 and l.204: drop 'first carrier publishes ... pinned to control's absence' and 'publish the operating root's state as the CLI's exit sweep would' (runner.run_entry only reports and bumps).
- G41 (ks-11) src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md l.57: say a repo-wide validate --fix also removes orphan launch tmp areas (link coga/launch#run-state).
- G56 (ks-11) src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md l.65: 'confirmed on the base branch' -> 'once you approve the vision and the batch' (link build/onboarding).
- G43 (ks-15) docs/contexts/coga-dev/codebase/gotchas/SKILL.md l.67-69: recurring shims are edge shims running coga_edge.<mod>.main through runner.run_entry, not run_recipe registry shims; fix the test claim.
- G64 (ca-01) same file l.27: mark_active validates the prospective ticket before writing; drop 'post-write' from the TaskValidationError sentence.
- G46 (ks-16) src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md l.325-326: drop 'same shape as the bootstrap/dream skill uses' for Proposals, or point to coga/blackboard.
- G76 (ca-05) same file l.218: drop 'which also searches the pre-rename relay-os/tasks/ tree'.
- G48 (ks-17) docs/contexts/coga-dev/current-direction/SKILL.md l.27 (+ l.8 Last updated): 'Until implemented, the current topics still describe today's behavior' is false; the decision landed in #1279.
- G67 (ca-03) src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md l.38: the ## Dev example names branch:/worktree:/pr:; use the coga/git record (branch, base, remote, reviewed, pr) or defer to coga/git.

Also seen while authoring PR #1290 (comments/docstrings only, left out of that PR's scope): src/coga/compose.py ~l.403 still mentions a 'checkout notice' and a checkout parameter; recurring_state.ensure_parent_state mentions a receipt; several 'publish' comments remain in recurring.py, launch.py, repl_supervisor.py and megalaunch.py. Check each against the fix-stale branch before editing.

Evidence: .coga/dream-scans is not kept; each line names its shard. Acceptance: each claim matches code (grep per named symbol), tests/test_packaging.py passes, coga validate --json shows no new issues.

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

branch: coga/correct-migration-claims-the-fix-stale-branch-s--4128cc
base: coga/sweep-orphan-tmp-trees-that-contain-read-only-di-c1cc7a
remote: origin

## Peer review handoff

Codex reviewed the documented claims against their code and examined all 15 paths from the recorded base `0aaa67fb` to `e649a9ce3`. Claude Code authored `718a44a36`. Codex, in a separate session, committed `e649a9ce3` to correct remaining launch and recurring comments, streamline the delegation pointer, and clarify which recurring shims use `run_entry`. The Python ASTs match after stripping docstrings. The compose checkout notice and launch `_commit_auto_activate` comments are already corrected on `fix-stale`.

The ticket requires `fix-stale-doc-references-left-by-the-plain-git-mig` to land first or serve as the PR base. After `git fetch origin`, neither that branch nor the recorded `sweep-orphan` base had a remote head. The fix-stale ticket is itself blocked on publication of its base. A merge-tree preview with the recorded base as the explicit ancestor isolates this ticket's diff and finds one content conflict, `coga-dev/current-direction`. When reconciling, keep the latest product decisions and this ticket's #1279 landing sentence. The ordinary merge of fix-stale with `origin/main` already conflicts in current-direction, autofix and spool-merge.

Refresh onto the reconciled fix-stale branch or onto main after it lands. Repeat verification and record `reviewed:` for that head before bumping. The shared checkout has pending log and unrelated ticket changes from the queue.

## PR

```yaml
title: Correct plain-Git migration claims the fix-stale branch leaves behind
author: claude
author_evidence: >-
  Claude Code authored 718a44a36 in launch aa07f7fc. Codex authored the
  review corrections in e649a9ce3 in the independent peer-review session.
head: e649a9ce3b02dcc5dc67b14b7fbb2428a03c1ee3
base: 0aaa67fbbc54037ebf50d7c341df7fabf228a067
depth: deep
rationale: >-
  The ticket diff is limited to documentation, comments and docstrings.
  The intended fix-stale integration base is unavailable. This evidence
  covers the local recorded base and will need refreshing after reconciliation.
implementation: >-
  Corrects the eleven Dream findings and stale source comments about the
  removed publication machinery. The recurring delegation topic owns the
  lifecycle details.
deviations: >-
  Implementation used the local sweep-orphan base while fix-stale was
  blocked. Review kept that base and clarified the launch and recurring
  comments and the coverage of the recurring-shim tests.
limitations: >-
  Publication is blocked on the fix-stale dependency. Native Windows and
  macOS verification is deferred to release.
files:
  docs/contexts/coga-dev/codebase/gotchas/SKILL.md: >-
    Describe prospective activation validation and how the five edge shims report and bump.
  docs/contexts/coga-dev/current-direction/SKILL.md: >-
    Record the landing of #1279 and update the date.
  src/coga/launch.py: >-
    Explain delegation's start callback, readiness checks, and prompt rendering.
  src/coga/recurring.py: >-
    Describe local ledger snapshots, completed-period replacement and scan refusals.
  src/coga/recurring_state.py: >-
    Explain how parent state is initialized with exclusive creation.
  src/coga/repl_supervisor.py: >-
    Explain assist audit attribution and deferred done markers.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md: >-
    Point to coga/git for the current Dev record fields.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md: >-
    Document repo-wide orphan tmp cleanup and the onboarding approval gates.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/autofix/SKILL.md: >-
    Document how run records are saved locally.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/SKILL.md: >-
    Document exclusive carrier creation, failure reporting and the scheduled bump.
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md: >-
    Point to the current ticket discovery recipe and blackboard Proposals convention.
  src/coga/resources/templates/coga/recurring/resolve-conflicts/ticket.md: >-
    Point to the recurring delegation lifecycle contract.
  src/coga/runner.py: >-
    Explain which local root owns the failure report.
  src/coga_edge/megalaunch.py: >-
    Describe the local dependency-drain ticket writes and validation.
  tests/test_recurring_shims.py: >-
    Correct the docstring describing run_entry and the behavior under test.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: e649a9ce3b02dcc5dc67b14b7fbb2428a03c1ee3
  base: 0aaa67fbbc54037ebf50d7c341df7fabf228a067
  detail: >-
    Codex independently reviewed the Claude implementation and then reviewed
    its own documentation corrections. All 15 paths were checked against
    the recorded base. The claims match the current code. Publication
    approval is pending reconciliation with the fix-stale branch.
checks:
  - command: >-
      TMPDIR="$review_tmp" PYTHONPATH="$PWD/src" TERM=dumb .venv/bin/python -m pytest -q -p no:cacheprovider
    status: passed
    head: e649a9ce3b02dcc5dc67b14b7fbb2428a03c1ee3
    base: 0aaa67fbbc54037ebf50d7c341df7fabf228a067
    detail: >-
      Pop!_OS 24.04 LTS, Python 3.12.12. 3257 passed, 30 skipped in 215.91s.
      The run used a dedicated temporary directory under /tmp.
  - command: >-
      TMPDIR="$packaging_tmp" PYTHONPATH="$PWD/src" TERM=dumb .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_packaging.py
    status: passed
    head: e649a9ce3b02dcc5dc67b14b7fbb2428a03c1ee3
    base: 0aaa67fbbc54037ebf50d7c341df7fabf228a067
    detail: >-
      Pop!_OS 24.04 LTS, Python 3.12.12. 43 passed in 11.03s. The run used a
      dedicated temporary directory under /tmp.
  - command: >-
      PYTHONPATH=<reviewed-or-base-src> TERM=dumb .venv/bin/python -m coga.cli validate --json
    status: passed
    head: e649a9ce3b02dcc5dc67b14b7fbb2428a03c1ee3
    base: 0aaa67fbbc54037ebf50d7c341df7fabf228a067
    detail: >-
      Pop!_OS 24.04 LTS, Python 3.12.12. Ran against the same checkout using
      each revision's source. Both exited zero with the same 82 issue
      records, with zero added and zero removed.
  - command: git diff --check 0aaa67fbbc54037ebf50d7c341df7fabf228a067...HEAD
    status: passed
    head: e649a9ce3b02dcc5dc67b14b7fbb2428a03c1ee3
    base: 0aaa67fbbc54037ebf50d7c341df7fabf228a067
    detail: >-
      No whitespace errors. An AST comparison confirmed all seven Python
      changes are comments or docstrings. Changed Markdown frontmatter,
      period template blackboard and new relative link targets also checked.
```

---

## Blockers

- [ ] [2026-11-25 18:00] [agent:codex] id=20261125T180053 Land fix-stale-doc-references-left-by-the-plain-git-mig first, or publish its reconciled branch as this ticket's PR base. The recorded sweep-orphan base is local-only and does not contain fix-stale. Reconcile this branch and refresh peer review once the intended base is available.
