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
step: 1 (implement)
agent: claude
launch_generation: 18462d61-3b9c-4e5a-9b55-1702776fea34
---

## Description

Filed by Dream 2026-W44 (Phase 6; knowledge-scan ks-20). Target: docs/contexts/coga/notifications/SKILL.md lines ~64-71 and its packaged twin.

The topic says a webhook URL seen in a diagnostic must be revoked or rotated, the tracked coga/log.md redacted, and every reachable commit inspected. The live incident webhook-for-slack-is-public (in_progress) leaves 24 leaked lines in coga/log.md and its owner-authored Description lists redacting them as out of scope (append-only; the URL is dead once revoked). coga/architecture and coga-dev/internals/spool-merge define log.md as append-only union-merged state, and a redaction commit leaves the secret in history anyway. The owner approved optional, explicitly owner-directed cleanup after confirmed revocation on 2026-10-26. Edit both twins to preserve the append-only log during ordinary incident response and require an explicit owner-approved exception for redacting it. Revocation/rotation stays the remedy that matters; preserve the existing exposure-inspection and coordinated history-rewrite requirements.

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

## Investigation (2026-10-26)

- Operator: Codex (GPT-6). On resume, fetched `origin/main` and confirmed
  `main` current at `e106878b3ad3b7294829809e2234e0f0874448f8`. The only
  tracked entry dirt was this session's preserved ticket notes. Relevant
  governing instructions and the notification topic did not change since
  the first investigation at `71cb300954ba67e3239cb9716a83ddca9feefc05`.
- `docs/contexts/coga/notifications/SKILL.md`, "When a post fails", and its
  packaged twin at
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/SKILL.md`
  are byte-identical and still require tracked-log redaction. This ticket is
  not already satisfied.
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
The notification topic and packaged twin will own the durable rule.

The earlier `coga block` exited 2 before any transition because the local
`user` was unset. The connected GitHub profile identifies the owner as
`nicktoper`, matching this ticket. Created the gitignored
`coga/coga.local.toml` with only `user = "nicktoper"` under the owner's new
authorization, and verified `config.load_config` resolves that actor. No open
blocker was recorded, so no `coga unblock` transition is needed. The task
continues at implement.

## Dev

branch: coga/reconcile-webhook-log-policy

## Implementation plan

Publish this decision and branch linkage from `main`, then edit both
notification copies on the feature branch. Run the full pytest suite,
reconcile with current main, push, return to main, write the PR preparation
and handoff, and bump once. No runtime code, fixture, credential, or historical
log changes are needed.
