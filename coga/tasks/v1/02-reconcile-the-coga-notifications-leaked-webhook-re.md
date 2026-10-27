---
title: Reconcile the coga notifications leaked-webhook response with the append-only
  log
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

Filed by Dream 2026-W44 (Phase 6; knowledge-scan ks-20). Target: docs/contexts/coga/notifications/SKILL.md lines ~64-71 and its packaged twin.

The topic says a webhook URL seen in a diagnostic must be revoked or rotated, the tracked coga/log.md redacted, and every reachable commit inspected. The live incident v1/01-webhook-for-slack-is-public (in_progress) leaves 24 leaked lines in coga/log.md and its owner-authored Description lists redacting them as out of scope (append-only; the URL is dead once revoked). coga/architecture and coga-dev/internals/spool-merge define log.md as append-only union-merged state, and a redaction commit leaves the secret in history anyway. The owner approved optional, explicitly owner-directed cleanup after confirmed revocation on 2026-10-26. Edit both twins to preserve the append-only log during ordinary incident response and require an explicit owner-approved exception for redacting it. Revocation/rotation stays the remedy that matters; preserve the existing exposure-inspection and coordinated history-rewrite requirements.

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

Previous ref: `reconcile-the-coga-notifications-leaked-webhook-re` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

## Investigation (2026-10-26)

- Operator: Codex (GPT-6). On resume, fetched `origin/main` and confirmed
  `main` current at `e106878b3ad3b7294829809e2234e0f0874448f8`. The only
  tracked entry dirt was this session's preserved ticket notes. Relevant
  governing instructions and the notification topic did not change since
  the first investigation at `71cb300954ba67e3239cb9716a83ddca9feefc05`.
- `docs/contexts/coga/notifications/SKILL.md`, "When a post fails", and its
  packaged twin at
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/SKILL.md`
  were byte-identical and required tracked-log redaction at entry. This ticket
  needed an implementation change.
- `coga/tasks/webhook-for-slack-is-public.md` remains `in_progress` at the
  owner-held `approve` step. Its Context excludes historical-log redaction
  and history rewriting, and its inventory preserves those copies. It
  records no completed revocation or general policy choice among optional,
  prohibited, and required redaction. Its incident-specific scope is evidence
  for the recommendation, not an answer to this ticket's explicit owner ask.
- A count-only scan for complete Slack service credential paths found 24
  affected lines in both the working `coga/log.md` and `origin/main`'s copy.
  No credential was printed or probed. Full-URL-only matching is insufficient:
  legacy error text can expose the `/services/` path separately from the host.
- `coga/architecture`, "Durable files", defines the CLI-written log as
  append-only. `coga-dev/internals/spool-merge`, "merge=union files" and
  "Legacy lines stay", explains preservation and the risk of resurrecting
  deleted lines across writers. A redaction commit also leaves prior Git
  versions intact. Dream's live report labels this finding D18, "owner
  decision"; no resolution was found in the referenced live records.

## Owner decision and configuration recovery (2026-10-26)

The owner approved the proposed optional-cleanup policy in this conversation
("ok for me") and explicitly authorized configuring their local Coga user.
Historical-copy redaction is optional after confirmed revocation; routine
response preserves `coga/log.md`, and redacting it needs an explicit
owner-approved exception. Revocation remains required. Exposure inspection
and the coordinated-approval requirement for history rewriting stay intact.
The notification topic and packaged twin own the durable rule in the
implementation branch.

The earlier `coga block` exited 2 before any transition because the local
`user` was unset. The connected GitHub profile identifies the owner as
`nicktoper`, matching this ticket. Created the gitignored
`coga/coga.local.toml` with only `user = "nicktoper"` under the owner's new
authorization, and verified `config.load_config` resolves that actor. No open
blocker was recorded, so no `coga unblock` transition is needed.

## Dev

pr: https://github.com/FastJVM/coga/pull/1120
branch: coga/reconcile-webhook-log-policy

## Implement handoff (2026-10-27)

Implemented and pushed `3c8f43f44da139d05a4be0a330f52344861c1666` on the
recorded branch. Both notification copies now require confirming revocation,
make historical-copy redaction optional at the owner's direction, and
preserve the append-only log during routine response unless the owner
explicitly approves a redaction exception. Exposure inspection and the
coordinated-approval requirement for published-history rewriting remain.
Only those two documents are in the implementation diff. No new regression
test or fixture was needed for this prose change; existing packaging tests
cover twin equality.

The first full-suite attempt exhausted `/tmp`'s inode capacity: 1,413 passed,
10 skipped, 2,708 errors. Inspection found only 36 free inodes despite ample
free bytes. Removed only that completed run's temporary fixtures and reran
the entire suite with `TMPDIR` on the main disk: 4,121 passed, 10 skipped in
361.16 seconds on Linux/Python 3.12.12. Temporary fixtures from that run were
also removed. Logs remain at `/tmp/coga-webhook-policy-pytest.log` and
`/tmp/coga-webhook-policy-pytest-retry.log`.

Tests ran before commit against staged tree
`63c8a53cd7c6fda621bd3cc43f9c2366f0087c03`. Before committing, verified the
working tree matched the index with no untracked files; the resulting
commit's tree has that identical OID. Fresh fetch/rebase left the commit
unchanged; its merge base with `origin/main` is
`478bfe5e72ba4e00081bb5a021d94444467f9491`. Pushed the branch, fetched main
again with no intervening commits, and returned this checkout to `main`
before writing this handoff.

Ticket validation reported no issues, the notification twins compare
byte-identically, and the diff whitespace check passed. No implementation
findings remained at handoff, and no PR was opened. Actual webhook
rotation/revocation remains with the separate incident
ticket and was not performed or verified here.

## Peer review

Completed direct review on 2026-10-27 in a fresh Codex (GPT-6) session,
covering head `0d56035fd86c1f118a363f3d66e206d71319136a` against base
`0c672984a9e2497e69102d7acf885ab252df57a7`. The recorded implementer was
also Codex, so this is **self-review**, not independent review under the
PR-presentation identity rule. The configured `claude` assignment is not
authorship evidence. No child agent or nested review CLI was used.

Started on clean, current `main`; verified the control ticket remained
`in_progress` at peer-review and GitHub had no PR for its recorded branch.
Followed the manual checkout procedure and rebased that branch onto current
main. Intervening changes were only ticket/log state; `git range-diff`
confirmed the implementation patch was unchanged. Reviewed both complete
notification copies against the owner decision, architecture's append-only
contract, and spool-merge's union/legacy-line rules. A cross-surface search
found no other standing historical-log-redaction requirement.

No must-fix findings or implementation edits. The wording requires confirmed
revocation, preserves the log during routine response, makes later cleanup
owner-directed with an explicit log-redaction exception, and retains exposure
inspection and coordinated approval for published-history rewriting. No
interactive surface changed; direct reading covered the Markdown wording.

The full suite on the rebased head passed: **4,121 passed, 10 skipped** in
407.92 seconds on Linux/Python 3.12.12. Used a fresh temporary directory on
the main disk because `/tmp` still had limited free inodes; removed only this
completed run's fixtures. Output remains at
`/tmp/coga-webhook-policy-peer-pytest.log`. Task validation, twin equality,
and whitespace checks also passed. The implementation-run results above are
historical; the `## PR` check receipts below were run on this rebased head.

A final fetch/rebase left head and base unchanged. Pushed with an explicit
lease against the previously published head, fetched main again, and returned
to clean `main` before writing this handoff. No PR was opened. The mechanical
open-pr step can proceed with a `skim` recommendation and disclosed
self-review. Live webhook remediation remains with the incident ticket.

## PR

```yaml
title: Make revoked-webhook log redaction optional
author: codex
author_evidence: >-
  Implemented by the actual Codex (GPT-6) session, including the owner-approved
  policy and local identity recovery. The ticket's configured claude agent was
  not used as authorship evidence. No subagents were used.
head: 0d56035fd86c1f118a363f3d66e206d71319136a
base: 0c672984a9e2497e69102d7acf885ab252df57a7
depth: skim
rationale: >-
  Bounded two-document policy clarification matching the owner's approved
  tradeoff. Direct Codex self-review completed with no findings, and the full
  suite and focused checks passed on the rebased head. Read the description
  for the owner-directed cleanup exception and the self-review limitation.
implementation: >-
  Require confirming the leaked webhook is revoked. Make historical-copy
  redaction optional afterward at the owner's direction, preserving the
  append-only log during ordinary response and requiring explicit owner
  approval for a redaction exception. Preserve exposure inspection and
  coordinated approval for rewriting published history. Update both twins.
deviations: >-
  No scope deviations. The owner separately authorized setting the missing
  local Coga user to nicktoper; that gitignored setting is outside the diff.
limitations: >-
  No live webhook action or probe was performed; operational remediation
  remains with the incident ticket. Verification ran on Linux/Python 3.12.12;
  no separate Python 3.11 or Windows run. This fresh Codex session performed
  direct self-review because the actual implementer was also Codex; no
  independent review was performed. The earlier implementation suite's
  temporary-inode failure and successful retry remain in the implement
  handoff; the current suite also passed using temporary space on the main disk.
files:
  docs/contexts/coga/notifications/SKILL.md: State the approved leaked-webhook policy in its canonical owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/SKILL.md: Ship the byte-identical fallback policy for adopting repositories.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 0d56035fd86c1f118a363f3d66e206d71319136a
  base: 0c672984a9e2497e69102d7acf885ab252df57a7
  detail: >-
    Direct review completed in this fresh Codex (GPT-6) peer-review session;
    no must-fix findings. Reviewed both notification copies against the
    approved policy and append-only/union-merge contracts, and checked other
    standing surfaces for conflicting redaction instructions. Actual author
    and reviewer are both Codex, so this is self-review. No nested reviewer
    or subagent was invoked, and no review remains in flight.
checks:
  - command: >-
      TMPDIR=/home/n/Code/.coga-webhook-peer-tests-VUNKKmXY
      PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest
      > /tmp/coga-webhook-policy-peer-pytest.log 2>&1
    status: passed
    head: 0d56035fd86c1f118a363f3d66e206d71319136a
    base: 0c672984a9e2497e69102d7acf885ab252df57a7
    detail: >-
      4121 passed, 10 skipped in 407.92 seconds, Linux/Python 3.12.12.
      Executed after rebase on clean committed tree
      73c9a435cdd6ce30b3b4dd89500daa9e71a65e6b. Used a fresh temporary
      directory on the main disk; removed its fixtures after completion.
      Final fetch/rebase left the tested commit unchanged.
  - command: >-
      PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate
      --task reconcile-the-coga-notifications-leaked-webhook-re --json
    status: passed
    head: 0d56035fd86c1f118a363f3d66e206d71319136a
    base: 0c672984a9e2497e69102d7acf885ab252df57a7
    detail: Exit 0; ok_count 1, no issues or fixes. Executed on the rebased branch.
  - command: >-
      cmp docs/contexts/coga/notifications/SKILL.md
      src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/SKILL.md
    status: passed
    head: 0d56035fd86c1f118a363f3d66e206d71319136a
    base: 0c672984a9e2497e69102d7acf885ab252df57a7
    detail: Exit 0; the canonical and packaged copies are byte-identical.
  - command: git diff --check origin/main...HEAD
    status: passed
    head: 0d56035fd86c1f118a363f3d66e206d71319136a
    base: 0c672984a9e2497e69102d7acf885ab252df57a7
    detail: Exit 0; no whitespace errors.
  - command: >-
      git range-diff
      478bfe5e72ba4e00081bb5a021d94444467f9491..3c8f43f44da139d05a4be0a330f52344861c1666
      origin/main..HEAD
    status: passed
    head: 0d56035fd86c1f118a363f3d66e206d71319136a
    base: 0c672984a9e2497e69102d7acf885ab252df57a7
    detail: Exit 0; the single implementation commit maps with =, preserving its patch through rebase.
```
