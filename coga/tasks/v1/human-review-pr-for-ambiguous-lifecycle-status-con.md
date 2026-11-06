---
title: Human-review PR for ambiguous lifecycle status conflicts
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
  - name: peer-review
    skills:
    - code/peer-review
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

Split from v1/07-lifecycle-writes-read-control-s-ticket-before-modi (owner decision 2026-11-05). That ticket landed preparation: lifecycle commands reconcile the ticket with fresh control and refuse an unreconcilable ticket with exit 75. An ambiguous status conflict (paused/blocked against another status, or done versus canceled; git.TicketConflictError with status_conflict=True) currently refuses like any other conflict. This ticket adds the owner-requested escalation (owner decision 2026-09-28): leave the lifecycle operation unapplied and open a PR titled `Human Review needed: <ticket slug> — lifecycle merge conflict`. The PR's base is configured control. Its head preserves the local ticket on a branch rooted at the proven provenance commit, built in an isolated index, so the PR shows the real Git conflict. The description carries the base, local, and control versions and the conflicting fields. Identify a conflict by ticket path plus the base/local/control ticket-blob fingerprints. An open matching PR is reused without force-pushing over human edits. Return path (owner-approved): if the PR merged, adopt control's copy as the resolution, record it as provenance, and three-way merge any local edits made after the PR was created; if it closed unmerged, refuse without opening a new PR; if it is open, reuse it. When GitHub, auth, network, or Git writes are unavailable, keep the local refusal and report that no PR was created. Never use open_pr's implementation path, its `Closes ticket:` footer, or `## Dev` branch:/pr:. Update coga/bootstrap/resolve-conflicts and address-pr-comments (live and packaged) to leave `Human Review needed` PRs for humans. Document the narrow exception in coga/state-publication and coga-dev/internals/git-regressions. Test with real-Git fixtures for each ambiguous pair, stubbing only the gh boundary.

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

<!-- coga:blackboard -->

## Dev

branch: coga/v1-human-review-pr-for-ambiguous-lifecycle-statu-a4ef81


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Decisions — 2026-11-06 (owner, attended)

- **Stacked on PR #1180** (owner choice): its commit `5de611c6b` is
  cherry-picked onto this branch because preparation/`TicketConflictError`
  are not on main yet. This PR must merge after #1180; rebase drops the copy.
- **Design approved as proposed:** conflict key = sha256(rel, base, local,
  control blob oids) → deterministic branch `coga/human-review/<slug>-<fp12>`
  (any checkout finds the PR via `gh pr list --head`). Head commit = provenance
  commit's tree with the local ticket, built in an isolated index and pushed
  as `<oid>:refs/heads/<branch>` only when the remote branch is absent (never
  force). Per-worktree `.coga/human-review.json` records created PRs for the
  merged return path (base := PR's local blob; record control's blob as
  provenance once the resolved ticket is written). Single `_gh()` boundary
  stubbed in tests. Accepted tradeoffs: merged return path is per-checkout;
  control churn while a PR is open opens another PR (4-part key per ticket);
  PR body versions truncated to fit GitHub's body limit.

## Implementation handoff — 2026-11-06 (claude, attended)

Branch pushed at `9e542eadad4e63fe1acdc2321e250275e096884f`: two commits on
origin/main `25091f7e7` — `d86a864c9` (PR #1180's commit, cherry-picked, see
Decisions) and `9e542eada` (this ticket). No PR yet. **The open-pr step must
make this PR depend on #1180** (merge after it, or rebase once #1180 lands so
its copy drops out).

- `src/coga/git.py`: `StatusConflict` attached as `TicketConflictError.review`
  for unrankable status pairs (`status_conflict_fields`, `_introducing_commit`
  for the provenance root). `prepare_ticket(..., review_base=, on_resolved=)`
  → `_prepare_reviewed` (merged-PR return path). `PreparedTicket.resolved`
  runs on the first prepared write and records control's blob in
  `PUBLISHED_REF` (deferred on purpose; see git-regressions).
- `src/coga/review_conflict.py` (new): key/branch naming, `_gh` boundary,
  `escalate` (lookup → isolated-index commit → push only if remote branch
  absent → `gh pr create`), `.coga/human-review.json` records,
  `merged_record`, `report`.
- `src/coga/commands/common.py`: `prepare_lifecycle_ticket` checks merged
  records first (only when the record file exists, so no extra Git calls
  otherwise), escalates on a status conflict, adopts a merged same-key PR,
  and always exits 75 on refusal.
- Bootstrap `resolve-conflicts` / `address-pr-comments` (live + packaged):
  new `skipped-human-review` status for `Human Review needed` PRs.
- Docs: `coga/state-publication` "Human review of status conflicts" (live +
  packaged), `coga-dev/internals/git-regressions`, `coga-dev/codebase`.
- Tests: `tests/test_review_conflict.py` (13): each ambiguous pair end to end
  through `coga bump`, reuse of an open PR without pushing over a human edit,
  existing branch with no PR reused not force-pushed, closed unmerged, gh
  unavailable, push refused, merged adopt + provenance, local edits after the
  PR merged onto its resolution, `-s ours` merge recognized without a record,
  non-status conflict never calls gh. `tests/conftest.py` stub accepts kwargs.
- Fixed during verification: the record lookup initially ran `git toplevel`
  before every preparation and broke 5 `test_launch` tests that fake
  `subprocess.run`; now gated on the record file existing.
- Pre-existing failures (not caused here, same as #1180 recorded):
  `test_packaging.py::test_live_and_packaged_copies_stay_identical`
  (launch-boundary drift) and `::test_context_navigation_has_no_broken_links`
  (current-direction anchors).
- Not done: no independent code review; peer-review step owns it.

## PR

```yaml
title: Open a human-review PR for ambiguous lifecycle status conflicts
author: claude
author_evidence: Attended implement session run by Claude (claude-opus-5-5); this handoff.
head: 9e542eadad4e63fe1acdc2321e250275e096884f
base: 25091f7e727c1f0c9939e1fe5d8d96208f3b5d87
depth: deep
rationale: Adds GitHub writes and a pushed branch to every lifecycle command's refusal path, a new preparation mode that adopts a human resolution, and deferred provenance recording; stacked on unreviewed PR #1180.
implementation: On an unrankable status conflict, lifecycle commands still exit 75 unapplied and additionally find or open a `Human Review needed` PR keyed by path plus base/local/control blob ids, whose head is the local ticket committed onto the commit that introduced the shared base (isolated index, push only when the remote branch is absent). Merged PRs are adopted on the next preparation (later local edits merge onto the resolution), closed ones refuse without a new PR, open ones are reused; unavailable GitHub/Git reports that no PR was created.
deviations: Stacked on PR #1180 (owner choice) because the preparation API it extends is not on main; the branch carries #1180's commit d86a864c9.
limitations: The merged return path relies on the refusing checkout's local .coga/human-review.json record (except when the merge kept control's blob). A changed control or local copy is a new conflict key and opens another PR. PR body ticket versions are truncated past 18,000 characters each.
files:
  src/coga/git.py: StatusConflict payload, review_base preparation mode, deferred provenance hook (plus #1180's commit).
  src/coga/review_conflict.py: Escalation, review branch construction, gh boundary, return-path records.
  src/coga/commands/common.py: Escalate on status conflicts and adopt merged review PRs before lifecycle preparation.
  tests/test_review_conflict.py: Real-git coverage of every escalation and return-path outcome with only gh faked.
  tests/conftest.py: Preparation stub accepts the new keyword arguments.
  coga/bootstrap/resolve-conflicts/ticket.md: Skip Human Review needed PRs (live twin).
  coga/bootstrap/address-pr-comments/ticket.md: Skip Human Review needed PRs (live twin).
  src/coga/resources/templates/coga/bootstrap/resolve-conflicts/ticket.md: Skip Human Review needed PRs.
  src/coga/resources/templates/coga/bootstrap/address-pr-comments/ticket.md: Skip Human Review needed PRs.
  docs/contexts/coga/state-publication/SKILL.md: Own the human-review contract (live twin).
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md: Own the human-review contract.
  docs/contexts/coga-dev/internals/git-regressions/SKILL.md: Internals of escalation and the deferred provenance record.
  docs/contexts/coga-dev/codebase/SKILL.md: Source-map entry for review_conflict.py.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Implement step; the workflow's peer-review step owns code review.
checks:
  - command: PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q -p no:cacheprovider -rf
    status: failed
    head: 9e542eadad4e63fe1acdc2321e250275e096884f
    base: 25091f7e727c1f0c9939e1fe5d8d96208f3b5d87
    detail: 4523 passed, 10 skipped, 2 failed; both are pre-existing test_packaging failures (launch-boundary twin drift, current-direction anchors) that #1180 also recorded on its base. Run on the committed tree with only the projected ticket dirty.
  - command: PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_review_conflict.py
    status: passed
    head: 9e542eadad4e63fe1acdc2321e250275e096884f
    base: 25091f7e727c1f0c9939e1fe5d8d96208f3b5d87
    detail: 13 passed (also included in the full run). Seeded-fixture validate omitted because validation behavior did not change.
```
