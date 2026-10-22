---
title: 06 Collapse state publication into one user topic
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

Make coga/state-publication the single user owner (absorbing sweep's strict recipe and recovery), move sweep and authoring internals to coga-dev, and shorten coga/sync to a map. See `coga/tasks/blocks/README.md`.

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

Done when: `coga/state-publication` is the single user topic for Coga-state publication (roots, eligibility, the pre-review hazard, the strict `coga run publish-state` recipe, recovery), `state-publication/authoring` and `state-publication/sweep` are deleted, and `coga/sync` is a short map; both copies of every touched topic are byte-identical;
no link in `docs/`, `src/`, `tests/`, `coga/` (outside old tickets and the
log), `README.md` or `AGENTS.md` points at a removed topic or anchor; any new
coga-dev page is listed in `docs/contexts/coga-dev/internals/SKILL.md`;
`.venv/bin/python -m pytest` and `coga validate --json` pass.

### Specifics

- `authoring`'s three user facts (one guarded publish; a Git-destination
  change refuses; edits are kept on failure) go into
  `bootstrap/skills/coga/ticket/finalize/SKILL.md` (live + packaged) or
  `state-publication`.
- Internals → existing `coga-dev/internals/state-publication`.
- Repoint links from `sandboxes`, `checkouts`, `checkouts/manual`,
  `extension-model`, `sync`, `architecture`, and the comments in
  `src/coga/cli.py` and `src/coga/publish_state.py`.
- `sync`'s "Design rule for new features" and the 2026-10-01 decision →
  `coga-dev/patterns`.


<!-- coga:blackboard -->

## Dev

branch: blocks-06-collapse-state-publication

## Handoff (implement)

Claude Opus 5.5 implemented the consolidation in original commit `042e0d10b`;
peer-review rebased it to final implementation commit `4a2eab359`. The user publication topic absorbs
recipe/recovery and authoring facts; the two leaves are removed; internals and
dated decisions move to the existing development owners; sync becomes a map.
Audit disagreement: none. The existing state-publication internals topic is
already listed in the internals index; no new development page was introduced.

## Peer review

**Completed direct Codex review** of final head `2861f388d01188d735b2d24ad9560fc9d97675d7`
against base `abe8aa7cf7fafa145137089fe876ef5321060cba`. All 36 changed paths, the
publication implementations (`cli`, `git`, `authoring`, `publish_state`), the
rebase range-diff, twins, and links/anchors were reviewed. No unresolved
finding. Claude's original implementation received independent Codex review;
Codex corrections and conflict resolutions were self-reviewed, so the combined
receipt conservatively records `kind: self`.

PR #1081 merged and the owner confirmed resolving the original blocker;
`coga unblock` recorded the answer. The owner subsequently answered **"ok to
expand"** on 2026-10-22: the two packaged recurring-template link corrections
now match their live copies already on main. This approved expansion overlaps
PR https://github.com/FastJVM/coga/pull/1083 and fixes both remaining baseline
failures. No executable behavior changed. Prior review corrections for
migration destinations, duplicate finalize ownership, publication selection
wording, and the documentation assertion remain in the branch.

All 11 surviving touched canonical/package pairs are byte-identical; both
removed publication leaves are absent from both trees. Every repository twin
matches. Navigation has no link to a removed publication topic or anchor;
old spellings remain only as historical migration sources and in old tickets.
The existing development internals topic remains indexed. Audit disagreement:
none. No terminal or rendered Slack surface changed, so no interactive
exercise applies.

Final verification on this head/base:

- `.venv/bin/python -m pytest -q`: **3987 passed, 7 skipped**, exit 0, 343.09s.
- `.venv/bin/coga validate --json`: **156 OK, zero errors, 48 warnings**, exit 0.
- Fresh-clone `tests/test_packaging.py`: **30 passed**, exit 0, 11.20s; wheel
  and installed-wheel checks included.
- `git diff --check origin/main...HEAD`: passed.

Verification used Python 3.12.12; Python 3.11 was not tested. An earlier green
run at `b3622968d` was followed by main's routine task/log updates. Rebase onto
`abe8aa7cf` preserved all four patches unchanged; the full suite, validation,
and pristine packaging checks were then rerun on the final revision above.
The final fetch found no further main movement. The projected ticket and
CLI-written log entry were preserved throughout checkout reconciliation;
this ticket remains unstaged and outside the branch commits.

The exact verified head `2861f388d` is pushed with force-with-lease; the
remote-tracking branch matches it. Ready to bump once to the mechanical
`open-pr` step. Advisory review depth is **skim**; the owner decides whether to
merge. Historical failed receipts are superseded by the executed final checks
below, not re-stamped as current results.

## PR

```yaml
title: Collapse state publication into one user topic
author: claude/codex
author_evidence: Claude Opus 5.5 performed the implement step (original 042e0d10b, now 4a2eab359). Codex
  authored the earlier review corrections (now 247c1b0b5 and 9e2f08cbc), resolved rebase conflicts, and
  applied the owner-approved two-template correction in 2861f388d. Authorship is established by the implement
  and peer-review handoffs; Git publisher identity and peer configuration are not the evidence.
head: 2861f388d01188d735b2d24ad9560fc9d97675d7
base: abe8aa7cf7fafa145137089fe876ef5321060cba
depth: skim
rationale: 'Bounded documentation consolidation with no runtime change. Direct review completed on the
  final head/base, the required full suite and validation pass, all touched twins match, and a fresh clone
  passes all packaging and wheel checks. Skim the ownership moves and the approved two-template synchronization
  overlapping PR #1083; Codex self-reviewed its corrections.'
implementation: Make coga/state-publication the single user owner for roots, eligibility, publication
  timing and checkout behavior, the pre-review hazard, strict publish-state, and recovery. Delete the
  authoring and sweep leaves, retain their machinery in the existing coga-dev internals topic, and reduce
  sync to a map. Move developer design rules and dated decisions to their existing owners; update navigation,
  migration targets, packaged counterparts, and resource assertions. The finalize skill requires the user
  owner instead of restating its contract. Align two packaged recurring-template links with their live
  copies already on main.
deviations: 'The owner explicitly approved expanding this diff to synchronize only the packaged autoclose-merged
  and branch-sweep template links. Their live changes had reached main before PR #1083, causing both remaining
  baseline test failures; the two-file correction overlaps that PR. Rebase preserves main''s newer extension-model
  and sandbox wording. The earlier stale draft attachment repair is already on main (46b146443). No new
  development topic or runtime behavior change.'
limitations: Verification used Python 3.12.12; Python 3.11 was not tested. No terminal loop, pager, prompt
  interaction, or rendered Slack message changed, so interactive surface checks are inapplicable. Codex
  independently reviewed the original Claude implementation and self-reviewed its own corrections; the
  combined review is conservatively classified as self. The owner retains the merge decision.
files:
  coga/skills/coga/ticket/finalize/SKILL.md: Replace the duplicate authoring contract with required reading
    of its single user owner and optional implementation navigation.
  docs/README.md: Replace authoring and sweep leaf links with the consolidated publication and recovery
    topic.
  docs/contexts/coga-dev/codebase/SKILL.md: Point the source map at the publication contract.
  docs/contexts/coga-dev/internals/SKILL.md: Point publication references at the consolidated owner; the
    existing internals page remains indexed.
  docs/contexts/coga-dev/internals/git-refresh/SKILL.md: Repoint the dirty-publication contract to its
    user owner.
  docs/contexts/coga-dev/internals/state-publication/SKILL.md: Retain sweep exclusions, strict recipe
    wiring, authoring mechanics, and the dated publication decision locally.
  docs/contexts/coga-dev/internals/state-publication/publish/SKILL.md: Repoint recovery to the consolidated
    user topic and anchor.
  docs/contexts/coga-dev/patterns/SKILL.md: Own the state-changing-command design rule and the 2026-10-01
    decision removed from the user sync map.
  docs/contexts/coga/architecture/SKILL.md: Remove links to the deleted publication leaves from the topic
    map.
  docs/contexts/coga/checkouts/SKILL.md: Repoint publication timing and recovery to the single user owner.
  docs/contexts/coga/checkouts/manual/SKILL.md: Repoint the strict-publication handoff contract.
  docs/contexts/coga/configuration/SKILL.md: Repoint the Git-publication configuration reference.
  docs/contexts/coga/extension-model/SKILL.md: Repoint the publish-state recipe contract.
  docs/contexts/coga/sandboxes/SKILL.md: Repoint failed-publication recovery.
  docs/contexts/coga/state-publication/SKILL.md: Own roots, eligibility, timing, checkout behavior, review
    hazard, strict publication, and recovery; retain committed-change limits in user language.
  docs/contexts/coga/state-publication/authoring/SKILL.md: Delete the split leaf after moving user facts
    to the parent and implementation to coga-dev.
  docs/contexts/coga/state-publication/sweep/SKILL.md: Delete the split leaf after moving the strict recipe
    and recovery to the parent and implementation to coga-dev.
  docs/contexts/coga/sync/SKILL.md: Shorten sync to an ownership map; move the publication contract and
    developer design rules to their owners.
  docs/release-notes/context-audiences.md: Make migration targets name the surviving publication topic;
    deleted refs remain only as historical source spellings.
  src/coga/cli.py: Repoint a source comment to the local owner of sweep exclusions; no runtime change.
  src/coga/publish_state.py: Repoint a module-docstring reference to the user recipe contract; no runtime
    change.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md: 'Packaged counterpart:
    Remove links to the deleted publication leaves from the topic map.'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md: 'Packaged counterpart:
    Repoint publication timing and recovery to the single user owner.'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/manual/SKILL.md: 'Packaged counterpart:
    Repoint the strict-publication handoff contract.'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md: 'Packaged counterpart:
    Repoint the Git-publication configuration reference.'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md: 'Packaged counterpart:
    Repoint the publish-state recipe contract.'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/sandboxes/SKILL.md: 'Packaged counterpart:
    Repoint failed-publication recovery.'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md: 'Packaged counterpart:
    Own roots, eligibility, timing, checkout behavior, review hazard, strict publication, and recovery;
    retain committed-change limits in user language.'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/authoring/SKILL.md: 'Packaged
    counterpart: Delete the split leaf after moving user facts to the parent and implementation to coga-dev.'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/sweep/SKILL.md: 'Packaged
    counterpart: Delete the split leaf after moving the strict recipe and recovery to the parent and implementation
    to coga-dev.'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md: 'Packaged counterpart: Shorten
    sync to an ownership map; move the publication contract and developer design rules to their owners.'
  src/coga/resources/templates/coga/bootstrap/skills/coga/ticket/finalize/SKILL.md: 'Packaged counterpart:
    Replace the duplicate authoring contract with required reading of its single user owner and optional
    implementation navigation.'
  tests/test_authoring.py: Update the documentation-only finalize skill assertion to require its user
    publication reference instead of an internal Python helper name.
  tests/test_packaging.py: Remove the two deleted context refs from the required bootstrap inventory.
  src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.md: 'Align cleanup-topic links with
    the live template already on main; owner-approved expansion overlapping PR #1083, with no execution
    change.'
  src/coga/resources/templates/coga/recurring/branch-sweep/ticket.md: 'Align cleanup-topic links with
    the live template already on main; owner-approved expansion overlapping PR #1083, with no execution
    change.'
review:
  reviewer: codex
  kind: self
  status: passed
  head: 2861f388d01188d735b2d24ad9560fc9d97675d7
  base: abe8aa7cf7fafa145137089fe876ef5321060cba
  detail: Completed direct review of all 36 final paths, the unchanged four-patch range-diff after the
    final rebase, publication implementations (cli, git, authoring, publish_state), all 11 surviving touched
    twin pairs, and removed-topic links and anchors. Both deleted leaf pairs are absent, all repository
    twins match, and the source ASTs are unchanged after excluding the module docstring. The owner-approved
    template correction fixes both baseline failures. No unresolved findings; no nested review CLI ran.
    Actual Claude implementation review was independent; Codex corrections and rebase resolutions were
    self-reviewed.
checks:
- command: .venv/bin/python -m pytest -q
  status: passed
  head: 2861f388d01188d735b2d24ad9560fc9d97675d7
  base: abe8aa7cf7fafa145137089fe876ef5321060cba
  detail: 3987 passed, 7 skipped in 343.09s (0:05:43), exit 0. Full suite after the final rebase; output
    in /tmp/coga-blocks06-refreshed-pytest.log.
- command: .venv/bin/coga validate --json
  status: passed
  head: 2861f388d01188d735b2d24ad9560fc9d97675d7
  base: abe8aa7cf7fafa145137089fe876ef5321060cba
  detail: 'Exit 0: 156 OK, zero errors, 48 warnings. Output in /tmp/coga-blocks06-refreshed-validation.json.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: 2861f388d01188d735b2d24ad9560fc9d97675d7
  base: abe8aa7cf7fafa145137089fe876ef5321060cba
  detail: No whitespace errors.
- command: PYTHONPATH=/tmp/coga-blocks06-refreshed-pristine/src /home/n/Code/claude/coga/.venv/bin/python
    -m pytest -q tests/test_packaging.py
  status: passed
  head: 2861f388d01188d735b2d24ad9560fc9d97675d7
  base: abe8aa7cf7fafa145137089fe876ef5321060cba
  detail: 'Fresh local clone at the final head, cwd /tmp/coga-blocks06-refreshed-pristine: 30 passed in
    11.20s, exit 0. Includes twin identity, context distribution/navigation, wheel contents, and installed-wheel
    isolation.'
```

---

## Blockers

- [x] [2026-10-21 18:38] [agent:codex] id=20261021T183800 Land the owner-reviewed packaged changes from blocks/02-delete-the-code-topic-and-remove-coga-repo-only (PR #1081), then resume this peer-review for rebase and verification. Three packaging failures reproduce on main; architecture, checkouts, and sandboxes twins touched here remain non-identical. Final branch a460ae2b9 is pushed; direct review completed and validation passed, but the required passing-suite and twin-identity acceptance are unmet.
  resolved: [2026-10-21 22:21] [human:nicktoper] The attending owner confirmed that merged PR #1081 resolves the dependency blocker. Resume peer-review, rebase onto current origin/main, verify touched twins, rerun the full suite and validation, and refresh the final review receipts before bumping.
