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
step: 4 (review)
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

pr: https://github.com/FastJVM/coga/pull/1181
branch: coga/v1-human-review-pr-for-ambiguous-lifecycle-statu-a4ef81

## Decisions — 2026-11-06 (owner, attended)

- **Windows waiver for this ticket:** owner explicitly selected “Waive Windows
  verification for this ticket” during peer review on 2026-11-06. No Windows
  instance was provisioned. This is a ticket-specific verification exception.
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

## Implementation origin

Claude implemented this ticket in `9e542eadad4e63fe1acdc2321e250275e096884f`,
stacked on the owner-approved cherry-pick of PR #1180. The original handoff
and check receipts remain in that ticket's control history. The peer-review
record and `## PR` below supersede the initial verification and presentation.

## Peer review

**Completed — direct Codex review**, covering final head
`7db1cdf0349d71f6d81a04249fa6610c308529fb` against diff base
`1ab16cd484844e97ca621dd43ad1891c51248ae4`. Codex independently reviewed
Claude's implementation, applied the findings, and self-reviewed the final
corrections. No second independent reviewer of those corrections is claimed.
No unresolved code findings. Recommendation: **deep** for lifecycle/GitHub
publication and provenance behavior, the stacked prerequisite, mixed review
independence, and the disclosed verification limits.

Fixes in `c634bad38`:

- Shared non-exiting review preparation covers batch/post-prompt unblock
  and autoclose.
- Owner recovery retires a merged review only after confirmed publication,
  keeps its record on rollback, and preserves the newer published provenance.
- Unavailable GitHub execution and review preparation keep the exit-75 refusal.
- GitHub explicitly selects the configured repository; mismatched/multiple
  push destinations refuse. URL parsing is shared with PR-assist verification.
- The machine-local review record never publishes, even without an ignore rule.
- Both maintenance tickets fetch titles before skipping human-review PRs.
- Lifecycle progress cannot cross a replaced frozen workflow (the prerequisite
  could otherwise merge step 4 into a two-step workflow).

Final documentation fix in `7db1cdf03`: point three lifecycle-contract links
at their package owners. The full-run trace exposed these new broken links
inside a test that already failed on base; they are now fixed.

Validation: the full Linux suite at `c634bad38` had **4556 passed, 10 skipped,
2 failed in 974.25s**. Its navigation failure included three new links in
addition to the two baseline anchor errors. After the link fix, the final-head
focused run had **46 passed, 2 failed in 18.04s**; the remaining failures are
exactly the baseline launch-boundary twin drift and two broken anchors.
Both failing tests were reproduced on exact base `1ab16cd48` (2 failed in
1.03s), and direct comparison of navigation diagnostics confirms the final
branch matches that baseline. Source and tests are byte-identical between
`c634bad38` and final head; the full suite was not repeated after the three
link-only corrections. Scoped ticket validation: 1 task, 0 issues; seeded
fixture: 5 tasks, 0 issues. Linux Pop!_OS 24.04 LTS, Python 3.12.12; native
Windows waived by the owner for this ticket, and no Python 3.11 run. Exact
commands and revision scopes are in `## PR`.

Human-visible check: drove the actual refusal in real 80x24 and 120x30 PTYs;
the conflict, remedy, and PR URL remained readable. Inspected the generated
PR body's field list and fenced base/local/control versions. Tests used real
Git repositories with the GitHub boundary stubbed; no live test PR was created.

Rebased before final review/tests and pushed with an explicit lease. The
projected ticket was backed up/restored byte-for-byte and never committed.
Final fetch saw `origin/main` at
`28982d66c6eee700713e18a890afac968260dc97`: only `coga/log.md` advanced since
the reviewed base, with no feature overlap. This is the generated-state drift
allowed by `coga/pr-publication`; tested head/base receipts remain exact.

**Next step:** mechanically open the PR using the preparation below. PR
#1180 is still open/unmerged; this branch includes its cherry-picked commit
`22a1a4985ee685be87595b978c8c1a54bd4e9f66` and must merge after #1180. Do not
claim an independent final-patch review or a green full suite. Bump only once.

## PR

```yaml
title: Open human-review PRs for ambiguous lifecycle status conflicts
author: claude/codex
author_evidence: Claude implemented the prerequisite and this ticket (implement handoff); Codex applied
  peer-review corrections in c634bad38 and documentation fixes in 7db1cdf03 after owner approval.
head: 7db1cdf0349d71f6d81a04249fa6610c308529fb
base: 1ab16cd484844e97ca621dd43ad1891c51248ae4
depth: deep
rationale: 'Changes lifecycle reconciliation, external GitHub writes, and provenance/rollback behavior.
  Includes the still-open #1180 prerequisite, and final corrections were self-reviewed. Two baseline packaging
  failures remain; the full suite predates a three-link documentation fix, and Windows verification was
  explicitly waived by the owner.'
implementation: Unrankable status conflicts leave the operation unapplied and find or create a Human Review
  needed PR on configured control. The head preserves the local ticket above proven provenance using an
  isolated index; open PRs are reused without overwriting human edits, closed PRs remain refused, and
  merged PRs reconcile later local edits onto control. Shared handling covers batch/post-prompt unblock
  and autoclose. Owner recovery retires records only after confirmed publication, private records never
  publish, and progress across replaced workflows refuses.
deviations: Depends on FastJVM/coga#1180 and must merge after it; the branch carries its cherry-picked
  implementation (22a1a4985ee685be87595b978c8c1a54bd4e9f66). Peer review also fixed the prerequisite workflow-replacement
  merge defect. Owner explicitly waived native Windows verification for this ticket on 2026-11-06.
limitations: Merged resolution normally relies on this checkout’s .coga/human-review.json record; unchanged-control
  resolutions can be recognized by the conflict key. Control/local blob changes generate another key.
  PR body versions truncate past 18,000 characters. The configured remote must have one matching fetch/push
  repository. Real Git fixtures exercise local bare remotes with the GitHub boundary stubbed; no live
  GitHub test PR was created. Native Windows and Python 3.11 were not run (Linux used Python 3.12.12).
  The inherited Windows-description divergence between the live/package launch topics also exists on the
  base; this branch adds identical teardown text to both. The full suite ran at c634bad38; final head
  differs only by three documentation links, checked with focused tests and verified source/test equivalence.
  Two baseline packaging failures remain.
files:
  coga/bootstrap/address-pr-comments/ticket.md: 'Live counterpart: fetch titles and leave human-review
    PRs for the human.'
  coga/bootstrap/resolve-conflicts/ticket.md: 'Live counterpart: fetch titles and skip human-review PRs
    before reconciliation.'
  docs/contexts/coga-dev/codebase/SKILL.md: Source map for shared lifecycle review handling.
  docs/contexts/coga-dev/internals/agent-spawn/SKILL.md: 'Prerequisite: session-teardown ticket and log
    publication boundary.'
  docs/contexts/coga-dev/internals/assist-publication/SKILL.md: 'Prerequisite: prepared lifecycle writes
    and session teardown publication.'
  docs/contexts/coga-dev/internals/git-refresh/SKILL.md: 'Prerequisite: per-ticket preparation exception
    to whole-checkout refresh; link to the owning package contract.'
  docs/contexts/coga-dev/internals/git-regressions/SKILL.md: Preparation/refusal internals, escalation,
    configured remote, deferred resolution and owner rollback. Link to the owning package contracts.
  docs/contexts/coga/launch/SKILL.md: 'Live counterpart: prerequisite session-teardown publication.'
  docs/contexts/coga/lifecycle/SKILL.md: 'Live counterpart: eligibility and bump checks use the prepared
    ticket.'
  docs/contexts/coga/state-publication/SKILL.md: Live counterpart of the preparation and human-review
    publication contract.
  docs/contexts/coga/sync/SKILL.md: 'Live counterpart: overview links to prepared lifecycle transactions.'
  src/coga/autoclose.py: Prepare from fresh control, recheck implementation PR linkage, and use shared
    review handling.
  src/coga/blackboard.py: 'Prerequisite: pure blocker transforms for a single prepared ticket write.'
  src/coga/bump.py: 'Prerequisite: advance and publish the prepared snapshot with an exact control expectation.'
  src/coga/commands/block.py: 'Prerequisite: derive status and append the blocker in one prepared write.'
  src/coga/commands/bump.py: 'Prerequisite: eligibility, workflow and artifact gates use fresh control
    before advancing.'
  src/coga/commands/common.py: Shared preparation, human-review escalation/recovery, and non-exiting boundary
    for loops.
  src/coga/commands/mark.py: 'Prerequisite: every mark command checks and writes the prepared ticket.'
  src/coga/commands/owner.py: Prepare owner changes and retire a merged review only after confirmed strict
    publication.
  src/coga/commands/unblock.py: Prepare answers atomically; batch and post-prompt writes share review
    escalation/recovery.
  src/coga/git.py: Prepared snapshots, exact pending publication expectations, status-conflict payloads,
    merged-review provenance, machine-local exclusions, and refusal across replaced workflows.
  src/coga/github_source.py: Shared remote repository identity parser used by escalation and PR-assist
    verification.
  src/coga/launch.py: 'Prerequisite: retry the started session ticket with its usage log before chaining.'
  src/coga/mark.py: 'Prerequisite: shared lifecycle writers accept prepared snapshots and preserve publication
    expectations.'
  src/coga/pr_assist.py: Use the extracted shared remote identity parser with unchanged assist verification
    behavior.
  src/coga/resources/templates/coga/bootstrap/address-pr-comments/ticket.md: Fetch titles and leave human-review
    PR comments and resolution for humans.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md: Own the prerequisite session-teardown
    publication description.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md: Own prepared lifecycle
    eligibility and stale supervised-step checks.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md: Own preparation,
    workflow conflicts, the human-review exception, return path, and private records.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md: Summarize and link the prerequisite
    transaction and retry behavior.
  src/coga/resources/templates/coga/bootstrap/resolve-conflicts/ticket.md: Fetch titles and skip human-review
    PRs before automatic reconciliation.
  src/coga/review_conflict.py: Conflict identity, isolated review branch, configured GitHub boundary,
    refusal reporting, and merged-review records.
  src/coga/taskfile.py: 'Prerequisite: in-memory blackboard replacement used by prepared blocker updates.'
  tests/conftest.py: 'Prerequisite: stub new preparation/retry boundaries outside real-Git fixtures.'
  tests/test_checkouts.py: 'Prerequisite: verify session-teardown publication without an unnecessary commit.'
  tests/test_git.py: Real-Git preparation/provenance/race/retry coverage plus workflow replacement refusal
    regressions.
  tests/test_launch.py: Prerequisite teardown coverage and assist-publication expectations.
  tests/test_mark.py: Prerequisite terminal-control eligibility refusal and prepared write forwarding.
  tests/test_owner.py: Prerequisite owner decisions use fresh control and preserve newer notes.
  tests/test_review_conflict.py: Real-Git coverage for all 24 ordered ambiguous pairs, PR reuse and recovery,
    owner rollback, unblock variants, private records, unavailable tools, and configured remotes; gh boundary
    tests.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 7db1cdf0349d71f6d81a04249fa6610c308529fb
  base: 1ab16cd484844e97ca621dd43ad1891c51248ae4
  detail: 'Direct review completed on the final head/base: independently reviewed Claude’s original diff,
    applied the findings, and self-reviewed the corrections. No unresolved code findings; no claim of
    a second independent reviewer of the final corrections. Reviewed configured-remote selection, the
    isolated index, merged/closed/open recovery, strict owner rollback and provenance, loop callers, and
    workflow compatibility. Drove refusal output in real PTYs at 80x24 and 120x30; messages and PR URL
    remained readable. Inspected the generated PR body and its fenced base/local/control copies. Re-reviewed
    the final documentation fixes; no new navigation errors remain compared with the base.'
checks:
- command: PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest -q -p no:cacheprovider
    -rf
  status: failed
  head: c634bad380eeb25d914235131bf493f211967307
  base: 1ab16cd484844e97ca621dd43ad1891c51248ae4
  detail: 'Historical full-suite receipt: 4556 passed, 10 skipped, 2 failed in 974.25s on Linux (Pop!_OS
    24.04 LTS), Python 3.12.12. test_live_and_packaged_copies_stay_identical failed on baseline launch-boundary
    drift; test_context_navigation_has_no_broken_links included two baseline anchors plus three new legacy-copy
    links. The three new links were fixed in 7db1cdf03. Source/tests are unchanged at final head; the
    full suite was not repeated after those documentation-only corrections.'
- command: PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest -q -p no:cacheprovider
    tests/test_review_conflict.py tests/test_git.py::test_prepare_refuses_progress_across_a_replaced_workflow
    tests/test_packaging.py::test_live_and_packaged_copies_stay_identical tests/test_packaging.py::test_context_navigation_has_no_broken_links
    -rf
  status: failed
  head: 7db1cdf0349d71f6d81a04249fa6610c308529fb
  base: 1ab16cd484844e97ca621dd43ad1891c51248ae4
  detail: '46 passed, 2 failed in 18.04s at final head, Linux/Python 3.12.12. All focused behavior tests
    pass. Remaining failures match exact base: launch-boundary twin drift and two existing navigation
    anchors (install#windows-baseline and macos-aws#full-suite-at-a-commit). Direct comparison confirms
    final navigation diagnostics equal the baseline; all three added link errors are fixed.'
- command: git diff --exit-code c634bad380eeb25d914235131bf493f211967307 HEAD -- src tests
  status: passed
  head: 7db1cdf0349d71f6d81a04249fa6610c308529fb
  base: 1ab16cd484844e97ca621dd43ad1891c51248ae4
  detail: 'Exit 0: source and tests at final head exactly match the full-suite revision; only three links
    in two development topics changed afterward.'
- command: PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest -q -p no:cacheprovider
    tests/test_git.py::test_prepare_refuses_progress_across_a_replaced_workflow tests/test_review_conflict.py
    -rf
  status: passed
  head: c634bad380eeb25d914235131bf493f211967307
  base: 1ab16cd484844e97ca621dd43ad1891c51248ae4
  detail: 46 passed in 13.02s on Linux (Pop!_OS 24.04 LTS), Python 3.12.12; tested working source tree
    equals this commit.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task v1/human-review-pr-for-ambiguous-lifecycle-status-con
    --json
  status: passed
  head: 7db1cdf0349d71f6d81a04249fa6610c308529fb
  base: 1ab16cd484844e97ca621dd43ad1891c51248ae4
  detail: 1 task checked, 0 issues, 0 fixes.
- command: env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/python
    -m coga.cli validate --json
  status: passed
  head: 7db1cdf0349d71f6d81a04249fa6610c308529fb
  base: 1ab16cd484844e97ca621dd43ad1891c51248ae4
  detail: 'Run from tests/fixtures/seeded-repo: 5 tasks checked, 0 issues, 0 fixes.'
- command: PYTHONPATH=/tmp/coga-human-review-peer-1b4195q4/baseline/src TERM=dumb /home/n/Code/coga/.venv/bin/python
    -m pytest -q -p no:cacheprovider tests/test_packaging.py::test_live_and_packaged_copies_stay_identical
    tests/test_packaging.py::test_context_navigation_has_no_broken_links -rf
  status: failed
  head: 1ab16cd484844e97ca621dd43ad1891c51248ae4
  base: 1ab16cd484844e97ca621dd43ad1891c51248ae4
  detail: 'Baseline comparison only: both tests fail in 1.03s on an isolated snapshot of exact base 1ab16cd484844e97ca621dd43ad1891c51248ae4;
    docs/archive excluded. Confirms these failures predate the branch. Linux, Python 3.12.12.'
- command: Native Windows full suite
  status: not-run
  detail: Explicitly waived by the attending owner for this ticket on 2026-11-06; no Windows resources
    provisioned.
```
