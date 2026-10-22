---
title: 03 Trim the checkouts and checkout-cleanup family
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
step: 3 (open-pr)
agent: claude
---

## Description

Apply the audit verdicts to coga/checkouts and its leaves and to coga/checkout-cleanup and its leaves, including merging checkout-cleanup/proofs into its parent. See `coga/tasks/blocks/README.md`.

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

Done when: the checkouts and checkout-cleanup rows in the README table are applied, `checkout-cleanup/proofs` is merged into `checkout-cleanup`, and each checkout fact (direct chat, the launch boundary) has one owner; both copies of every touched topic are byte-identical;
no link in `docs/`, `src/`, `tests/`, `coga/` (outside old tickets and the
log), `README.md` or `AGENTS.md` points at a removed topic or anchor; any new
coga-dev page is listed in `docs/contexts/coga-dev/internals/SKILL.md`;
`.venv/bin/python -m pytest` and `coga validate --json` pass.

### Specifics

- `coga/checkouts` is the most-cited topic (base prompt, ~10 skills and
  workflows). Keep every procedure an agent follows; move only history and
  mechanics. Target well under 200 lines (now 245).
- Single owners: direct chat → `checkouts/chat`; checkout boundary →
  `checkouts/launch-boundary` (`launch` and `checkouts` summarize + link; the
  `launch` side is ticket 08's, coordinate via main).
- `proofs` merge: repoint `bootstrap/retire/ticket.md`,
  `recurring/autoclose-merged/ticket.md`, `recurring/branch-sweep/ticket.md`,
  `bootstrap/skills/coga/autoclose/sweep/SKILL.md` (live and packaged copies).
- New coga-dev page: `internals/branch-sweep`. Existing: `git-refresh`,
  `launch-claims`.


<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/1083
branch: coga/blocks-03-trim-the-checkouts-and-checkout-cleanup-fcd4a4

## Handoff (implement, manual session)

Committed `e022f9ba5` on the branch, rebased onto `origin/main` `1a8f19511`, and pushed. The session went back to clean `main`.

What changed:
- `coga/checkouts`: 252 → 193 lines. Every agent procedure is kept (table, entry/work/hand-off, sweep rules, stranded-write repair). Removed: the dated linked-worktree decision, `select_checkout_policy`/`sync_coga_state`/`coga_root_paths` names, re-preflight mechanics, the reservation/provenance detail, template-adoption history, `os.chdir` evidence, and the 2026-10-06 decision. "Direct chat" is now a two-line summary linking to `checkouts/chat`. Kept headings: "Start, work, end" (compose.py notice), "Stranded ticket writes" (checkouts.py, open-pr skill), "Which checkout a step starts in" (workflows anchor).
- `checkouts/chat` (owns direct chat): lock-file location and receipt/reservation pinning moved to `coga-dev/internals/launch-claims` ("Direct chat occupancy guard and receipt"). It keeps a one-paragraph retry rule.
- `checkouts/launch-boundary` (owns the boundary): the re-pin loop, `read-tree`/`update-ref`, and contexts-root capture moved to `coga-dev/internals/git-refresh` ("Launch preparation details"). The chat paragraph now links to `chat`.
- `checkout-cleanup`: `proofs` merged in as "## The checkout proofs". Function names, `-d`→`-D` escalation, and `discover_coga_repos` moved to the new `coga-dev/internals/branch-sweep`, which is listed in the internals index. The date was dropped from the disappearance-policy text; it is recorded in internals/branch-sweep.
- `branch-sweep`: the patch-id/submodule algorithm and tag-collision mechanics moved to internals/branch-sweep. User rules, the restore commands, and the `@<sha12>` fallback stay. The `#branch-sweep-protection-and-archive` anchor is kept.
- `terminal-owners`: function names and the dated header were removed. The worklist backfill and union-merge rules moved to internals/branch-sweep.
- `proofs` links were repointed to `context:coga/checkout-cleanup` in retire, autoclose-merged, branch-sweep, and the autoclose/sweep skill (live and packaged copies). `docs/README.md` was updated, and the topic was dropped from `REQUIRED_BOOTSTRAP_CONTEXT_REFS`.
- The 2026-10-14 linked-worktree exceptions decision moved to `coga-dev/current-direction`.

Owner notes and follow-ups:
- I did not depart from the audit. I left the "Known gap" paragraphs alone because ticket 02 had already removed them from canonical main.
- `coga-dev/internals/git-refresh` is now 223 lines, over the 200-line review threshold. Possible split: move "Launch preparation details" into its own page.
- For ticket 08: `coga/launch` "Checkout boundary" says the chat occupancy guard's "scope and lifetime are owned by coga/checkouts/launch-boundary". The owner is `coga/checkouts/chat`; repoint it there.
- `docs/release-notes/context-audiences.md` still names `coga/checkout-cleanup/proofs` in a dated rename table. This is history, not a link, so I left it.
- PR #1081 (ticket 02) syncs the packaged copies of checkouts, checkout-cleanup, and branch-sweep. This branch already makes those twins byte-identical with more edits, so whichever PR merges second takes this branch's version of those three packaged files.

## Follow-ups (filed before open-pr)

Obligations the merge does not discharge, filed as drafts:
- `split-launch-preparation-out-of-the-git-refresh-in` — git-refresh is 223 lines; split its launch-preparation section.
- `repoint-the-launch-topic-chat-occupancy-guard-owne` — coga/launch still names launch-boundary as chat guard owner (ticket 08 scope; fold in if 08 is open).

## Peer review

Completed direct Codex review of final head `30c5534abb1c51f0e9e97c9d66d3b8cd66cdd830` against
base `ee50b4ba4cd8ffd4e41f4f329bf2be6ca91ee440` after PR #1081 merged. The human confirmed the
blocker resolution, recorded by `coga unblock`; no open blocker remains.
Claude authored the implementation. This is independent review of that work;
Codex authored and self-reviewed the small corrections. No nested review CLI ran.

Findings and reconciliation:
- The earlier divergent-tip archive correction survives as `789a6205c`.
- The obsolete proofs attachment fix (`244bf2661`) is already on main;
  rebase dropped that duplicate commit. The two live recurring-template link
  migrations are also already on main.
- Resolved the two packaged checkout-cleanup conflicts against the unchanged
  canonical owners. The otherwise clean merge duplicated the `## Dev` paragraph
  in the packaged checkouts topic; `30c5534ab` removes it.
- Reviewed all 26 final diff paths, retained checkout/recovery/deletion
  procedures, and compared moved mechanics with source. All nine touched
  live/package pairs match; both proofs copies are deleted; no active link
  targets the removed topic or a removed anchor. Historical mentions are confined to completed-ticket
  prose and audit/rename tables. The new developer page is indexed.

No unresolved review finding. No terminal or rendered Slack exercise applies:
this diff changes no UI code or message format. Ticket 08 still owns the
launch-topic chat pointer; the git-refresh size follow-up remains as noted in
the implement handoff.

Verification at the head/base above (Python 3.12.12):
- `PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest`:
  **3987 passed, 7 skipped**, exit 0, 383.31s. All 30 packaging tests passed.
- `PYTHONPATH=/home/n/Code/claude/coga/src coga validate --json`:
  **154 OK, 0 fixes, 0 errors, 48 warnings**, exit 0.
- `git diff --check origin/main...HEAD`: passed.
- Fresh-clone wheel build: passed. Verified the removed proofs leaf and
  development topics do not ship, no duplicate member exists, and all six
  changed context files match their canonical bytes. Exact build command below.

These completed checks replace the earlier failed receipts. The final fetch
still had main at the base above. Pushed `30c5534ab` with an explicit
force-with-lease; the branch is three commits ahead of main. The prepared PR
renders as `[skim · A:claude R:codex]` with all 26 paths covered and no evidence
gaps. This launched session leaves the branch for launch to return; it must
not switch to main itself.

## PR

```yaml
title: Trim the checkouts and checkout-cleanup topic families
author: claude
author_evidence: The implement handoff identifies Claude Code (claude-opus-5-5), also recorded in the
  implementation commit a9e7fa653. The earlier Codex peer session authored the archive correction (now
  789a6205c) and obsolete attachment fix (244bf2661, already on main). This resumed Codex peer session
  removed a duplicate paragraph introduced by rebase (30c5534ab). Git publisher identity is not implementing-agent
  identity.
head: 30c5534abb1c51f0e9e97c9d66d3b8cd66cdd830
base: ee50b4ba4cd8ffd4e41f4f329bf2be6ca91ee440
depth: skim
rationale: The documentation reorganization preserves operating procedures and changes no runtime code.
  Direct review completed and the required full suite, validation, and pristine wheel check passed. Skim
  the ownership moves and disclosed follow-up scope; Codex reviewed its own small corrections.
implementation: Merges checkout-cleanup/proofs into its parent, repoints its consumers, and trims the
  checkout topic families while retaining agent procedures. Direct chat belongs to checkouts/chat; the
  boundary belongs to checkouts/launch-boundary. Mechanics and dated decisions move into coga-dev, including
  the indexed branch-sweep topic. Reconciliation preserves the divergent-tip archive exception and keeps
  every touched live/package pair identical.
deviations: None from the audit verdicts. Historical prose in completed tickets and the dated rename table
  remains. The live recurring-template link migrations and obsolete completed-ticket attachment fix are
  already on main, so they are absent from this final branch diff.
limitations: The pre-existing launch-topic pointer for chat occupancy remains ticket 08 scope. git-refresh
  is 223 lines; splitting its launch-preparation section remains a follow-up. Verification used Python
  3.12.12; no Python 3.11 run was performed. No terminal or rendered Slack exercise applies because no
  UI code or message format changed.
files:
  coga/skills/coga/autoclose/sweep/SKILL.md: Repoint the Ignored state link to coga/checkout-cleanup.
  docs/README.md: Drop the removed proofs leaf from the library index.
  docs/contexts/coga-dev/current-direction/SKILL.md: Record the 2026-10-14 linked-worktree exceptions
    decision moved out of checkouts.
  docs/contexts/coga-dev/internals/SKILL.md: List the new branch-sweep page and the widened launch-claims
    and git-refresh scope.
  docs/contexts/coga-dev/internals/branch-sweep/SKILL.md: Own the moved checkout-disposal and branch-sweep
    mechanics; preserve the PR-ref exception when divergent tips cannot share one retirement tag.
  docs/contexts/coga-dev/internals/git-refresh/SKILL.md: Receive launch-preparation mechanics, the chdir
    evidence, template-adoption history, and the 2026-10-06 decision.
  docs/contexts/coga-dev/internals/launch-claims/SKILL.md: Receive the chat guard lock and receipt mechanics.
  docs/contexts/coga/checkout-cleanup/SKILL.md: Absorb the checkout proofs and drop private names.
  docs/contexts/coga/checkout-cleanup/branch-sweep/SKILL.md: Trim to user rules and repoint the proofs
    link.
  docs/contexts/coga/checkout-cleanup/proofs/SKILL.md: Deleted; merged into checkout-cleanup.
  docs/contexts/coga/checkout-cleanup/terminal-owners/SKILL.md: Drop function names, the dated header,
    and worklist internals.
  docs/contexts/coga/checkouts/SKILL.md: Trim history and mechanics; direct chat becomes a summary plus
    link.
  docs/contexts/coga/checkouts/chat/SKILL.md: Move lock and receipt internals to coga-dev.
  docs/contexts/coga/checkouts/launch-boundary/SKILL.md: Move the re-pin loop, realignment plumbing, and
    contexts-root capture to coga-dev.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/SKILL.md: Packaged twin,
    byte-identical.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/branch-sweep/SKILL.md: Packaged
    twin, byte-identical.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/proofs/SKILL.md: Packaged
    twin deleted.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/terminal-owners/SKILL.md: Packaged
    twin, byte-identical.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md: Packaged twin, byte-identical.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/chat/SKILL.md: Packaged twin, byte-identical.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/launch-boundary/SKILL.md: Packaged
    twin, byte-identical.
  src/coga/resources/templates/coga/bootstrap/retire/ticket.md: Repoint the proofs link to coga/checkout-cleanup.
  src/coga/resources/templates/coga/bootstrap/skills/coga/autoclose/sweep/SKILL.md: Packaged twin of the
    skill link repoint.
  src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.md: Align the packaged proofs links
    with the live recurring template, whose migration is already on main.
  src/coga/resources/templates/coga/recurring/branch-sweep/ticket.md: Align the packaged proofs links
    with the live recurring template, whose migration is already on main.
  tests/test_packaging.py: Drop checkout-cleanup/proofs from REQUIRED_BOOTSTRAP_CONTEXT_REFS.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: 30c5534abb1c51f0e9e97c9d66d3b8cd66cdd830
  base: ee50b4ba4cd8ffd4e41f4f329bf2be6ca91ee440
  detail: Completed direct Codex review of the entire final diff, including checkout procedures, moved
    mechanics against source, links and anchors, all nine live/package pairs, and preservation of current-main
    changes through the rebase. Independent review of the Claude implementation; Codex corrections were
    self-reviewed. The earlier divergent-tip archive fix is retained, the obsolete attachment fix is now
    on main, and the rebase-created duplicate paragraph in the packaged checkouts topic is removed. No
    unresolved finding. No nested review CLI ran.
checks:
- command: PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest
  status: passed
  head: 30c5534abb1c51f0e9e97c9d66d3b8cd66cdd830
  base: ee50b4ba4cd8ffd4e41f4f329bf2be6ca91ee440
  detail: 'Python 3.12.12: 3987 passed, 7 skipped in 383.31s (0:06:23), exit 0. All 30 packaging tests
    passed, including the three checks that blocked the prior review.'
- command: PYTHONPATH=/home/n/Code/claude/coga/src coga validate --json
  status: passed
  head: 30c5534abb1c51f0e9e97c9d66d3b8cd66cdd830
  base: ee50b4ba4cd8ffd4e41f4f329bf2be6ca91ee440
  detail: 'Exit 0: 154 OK, 0 fixes, 0 errors, 48 warnings (21 stuck-in-progress, 19 unfrozen-workflow,
    7 empty-description, 1 large-blackboard).'
- command: git diff --check origin/main...HEAD
  status: passed
  head: 30c5534abb1c51f0e9e97c9d66d3b8cd66cdd830
  base: ee50b4ba4cd8ffd4e41f4f329bf2be6ca91ee440
  detail: No whitespace errors.
- command: /home/n/Code/claude/coga/.venv/bin/python -m pip wheel --no-deps --no-build-isolation --no-cache-dir
    --wheel-dir /tmp/coga-blocks03-peer-review-jo11i4in/wheels /tmp/coga-blocks03-peer-review-jo11i4in/pristine
  status: passed
  head: 30c5534abb1c51f0e9e97c9d66d3b8cd66cdd830
  base: ee50b4ba4cd8ffd4e41f4f329bf2be6ca91ee440
  detail: Built coga-0.4.1-py3-none-any.whl from a fresh local clone at this head, exit 0. ZIP inspection
    confirmed no duplicate members, no removed proofs leaf or coga-dev contexts, and byte-identical canonical
    content for all six changed shipped context files.
```

## Blockers

- [x] [2026-10-21 17:14] [agent:codex] id=20261021T171440 Merge PR #1081 for blocks/02-delete-the-code-topic-and-remove-coga-repo-only before advancing this peer review: the required suite still has three pre-existing packaging failures covered by that PR. Then rebase the pushed branch, rerun pytest and validation, and refresh the final review receipts. Both change-specific review findings are fixed; validation passes.
  resolved: [2026-10-21 21:17] [human:nicktoper] PR #1081 has merged (a1a3f5049b5dd2457f531a4d81b79b6a6425bb9f). The attending human confirmed clearing this blocker and continuing: rebase the pushed branch onto current main, rerun the full suite and validation, and refresh the final peer-review and PR receipts before advancing.
