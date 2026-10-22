---
title: 03 Trim the checkouts and checkout-cleanup family
status: blocked
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

## Peer review

Completed direct Codex review of final head `244bf2661750d594e4bdc169e4eb9290158e502f` against
base `1539b07cc5a8ef33b38e8f9ded39735283b76b21`. The implement handoff identifies Claude as the
implementer, so this was independent review of that implementation. Codex
applied and self-reviewed the two corrections below; no nested review CLI ran.

Fixed findings:
- The new `coga-dev/internals/branch-sweep` text made mutual tip containment
  mandatory, losing the PR-ref exception for divergent tips. Commit
  `7e224f303` restores the actual `_publish_retirement_tag` decision and links
  the user archive rule.
- Source-pinned validation found the deleted proofs leaf still attached to
  `microkernel/move-retire-to-a-command-ticket`. Although that ticket is
  `done`, validation resolves its contexts. Commit `244bf2661` removes the
  redundant attachment (the parent was already attached); lifecycle and
  historical prose are unchanged.

Review coverage: retained the entry/work/handoff, manual recovery, chat retry,
claim, dirty-state, local-before-remote deletion and archive rules; compared
moved internals with their source; checked the remaining leaves and inbound
references. All nine affected live/package pairs are byte-identical, and no
checkout-family link or anchor is broken. Remaining proofs mentions are this
audit's history or completed-ticket prose. The new developer page is indexed.
No terminal or rendered Slack exercise applies because this diff changes
neither UI code nor message formats. No unresolved change-specific finding.

Verification on the head/base above:
- `PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest`:
  **3952 passed, 7 skipped, 3 failed** (Python 3.12.12, 367.64s). The failures
  are the existing packaging twin, distribution and navigation failures on
  main. Direct comparison verified all 12 remaining mismatched pairs are
  unchanged by this branch; the other failures are the removed `coga/code`
  topic's leftover packaged copy/registration and three links.
- `PYTHONPATH=/home/n/Code/claude/coga/src coga validate --json`: **151 OK,
  0 errors, 0 fixes, 47 warnings**, exit 0.
- `git diff --check origin/main...HEAD`: passed.

Rebased onto current main before review and force-pushed with lease. The final
fetch still had main at the base above. Returned this manual checkout to clean
`main` before writing this handoff. The branch has three commits ahead of main.

The required green suite is blocked on **blocks/02-delete-the-code-topic-and-remove-coga-repo-only**,
whose [PR #1081](https://github.com/FastJVM/coga/pull/1081) was still open at
handoff. After it merges, rebase this branch, preserve the canonical and
packaged checkout edits through overlap, re-run the full suite and validation,
and refresh the review/PR receipts before bumping. No PR for this branch has
been opened. Ticket 08 still owns the launch-topic pointer update; the
implement handoff records the topic-size follow-up.

## PR

```yaml
title: Trim the checkouts and checkout-cleanup topic families
author: claude
author_evidence: The implement handoff records a Claude Code session (claude-opus-5-5). This Codex peer-review
  session authored the two small corrections in 7e224f303 and 244bf2661; Git publisher identity is not
  the implementing-agent identity.
head: 244bf2661750d594e4bdc169e4eb9290158e502f
base: 1539b07cc5a8ef33b38e8f9ded39735283b76b21
depth: deep
rationale: 'The documentation change is bounded and the direct review completed, but the required full
  suite still fails three pre-existing packaging checks. PR #1081 must land and this branch must be rebased
  and checked again before advancing.'
implementation: Trims the checkout topic families while retaining agent procedures; merges checkout-cleanup/proofs
  into its parent; makes chat and the launch boundary their respective owners; moves mechanics and dated
  decisions into coga-dev. Peer review preserves the divergent-tip archive exception in the moved internals
  and removes an obsolete proofs attachment from a completed ticket that validation still reads.
deviations: None from the audit verdicts. Historical prose mentions in completed tickets and the dated
  rename table remain; the obsolete machine-resolved context attachment was removed.
limitations: 'The three failing packaging checks are existing main drift covered by open PR #1081 (blocks/02-delete-the-code-topic-and-remove-coga-repo-only).
  The launch-topic ownership pointer remains ticket 08 scope. git-refresh is 223 lines and exceeds the
  topic-size review threshold. No rendered terminal or Slack check was needed: no UI code or message format
  changed. Verification used Python 3.12.12; no Python 3.11 run was performed.'
files:
  coga/recurring/autoclose-merged/ticket.md: Repoint proofs links to coga/checkout-cleanup.
  coga/recurring/branch-sweep/ticket.md: Repoint proofs links to coga/checkout-cleanup.
  coga/skills/coga/autoclose/sweep/SKILL.md: Repoint the Ignored state link to coga/checkout-cleanup.
  coga/tasks/microkernel/move-retire-to-a-command-ticket.md: Remove the obsolete proofs context attachment;
    the completed ticket already attaches checkout-cleanup, and validation resolves attached contexts
    even for completed tickets.
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
  src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.md: Packaged twin of the link repoint.
  src/coga/resources/templates/coga/recurring/branch-sweep/ticket.md: Packaged twin of the link repoint.
  tests/test_packaging.py: Drop checkout-cleanup/proofs from REQUIRED_BOOTSTRAP_CONTEXT_REFS.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: 244bf2661750d594e4bdc169e4eb9290158e502f
  base: 1539b07cc5a8ef33b38e8f9ded39735283b76b21
  detail: Completed direct Codex review of the entire final branch diff against main, including procedures,
    moved mechanics, references and package twins. Independent review of the Claude implementation; Codex
    authored and self-reviewed the two corrections. Fixed the lost divergent-tip archive exception and
    the obsolete proofs context attachment. No unresolved change-specific finding. No nested review CLI
    was run.
checks:
- command: PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest
  status: failed
  head: 244bf2661750d594e4bdc169e4eb9290158e502f
  base: 1539b07cc5a8ef33b38e8f9ded39735283b76b21
  detail: 'Python 3.12.12: 3952 passed, 7 skipped, 3 failed in 367.64s. Failures: test_live_and_packaged_copies_stay_identical,
    test_context_distribution_is_complete, test_context_navigation_has_no_broken_links. All are existing
    main drift: 12 unrelated unsynced topic twins, the packaged coga/code topic and required registration
    left after canonical deletion, and three coga/code links. PR #1081 covers these paths. This completed
    run supersedes the two attempts interrupted while applying review findings.'
- command: PYTHONPATH=/home/n/Code/claude/coga/src coga validate --json
  status: passed
  head: 244bf2661750d594e4bdc169e4eb9290158e502f
  base: 1539b07cc5a8ef33b38e8f9ded39735283b76b21
  detail: 'Exit 0: 151 OK, 0 fixes, 0 errors, 47 warnings. Source-pinned validation passes after removing
    the redundant deleted-leaf attachment from microkernel/move-retire-to-a-command-ticket.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: 244bf2661750d594e4bdc169e4eb9290158e502f
  base: 1539b07cc5a8ef33b38e8f9ded39735283b76b21
  detail: No whitespace errors.
```

---

## Blockers

- [ ] [2026-10-21 17:14] [agent:codex] id=20261021T171440 Merge PR #1081 for blocks/02-delete-the-code-topic-and-remove-coga-repo-only before advancing this peer review: the required suite still has three pre-existing packaging failures covered by that PR. Then rebase the pushed branch, rerun pytest and validation, and refresh the final review receipts. Both change-specific review findings are fixed; validation passes.
