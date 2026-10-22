---
title: 09 Trim setup and extension topics
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
launch_generation: d9c4ea26-ae29-47f9-ab2f-28315f358ce0
---

## Description

Apply the audit verdicts to configuration, context-layout, edge-code, extension-model, first-task, init, install, knowledge, skill-management, sandboxes, usage and cli. See `coga/tasks/blocks/README.md`.

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

Done when: the rows in the README table for configuration, context-layout, edge-code, extension-model, first-task, init, install, knowledge, skill-management, sandboxes, usage, cli and uninstall are applied, `install` is under 160 lines, and the recipe/alias lists have one owner (`coga/cli`); both copies of every touched topic are byte-identical;
no link in `docs/`, `src/`, `tests/`, `coga/` (outside old tickets and the
log), `README.md` or `AGENTS.md` points at a removed topic or anchor; any new
coga-dev page is listed in `docs/contexts/coga-dev/internals/SKILL.md`;
`.venv/bin/python -m pytest` and `coga validate --json` pass.

### Specifics

- These are mostly HUMAN reference topics; keep the operator-facing content
  and move only developer material and repo-specific text (ticket 02 handles
  the repo-specific lines named there).
- Destinations: `coga-dev/codebase`, `packaging`, `microkernel`,
  `current-direction`, `archive-access`, `activity-capture`.
- `init` gains "Instruction files and skill discovery" in ticket 01; do not
  duplicate it.


<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/1082
branch: coga/blocks-09-trim-setup-extension

## Handoff (implement snapshot)

These notes describe the implementation phase. The peer-review result below
supersedes its packaging limitation.

Applied every row for this ticket's topics. Re-checked against main first:
01 (PR #1080, unmerged) owns the `coga/agents` links in configuration,
first-task, init, sandboxes and init's "Instruction files and skill
discovery"; I left those lines alone. 02's repo-only edits (cli recipe list
with `prepare-checkout`, context-layout "This repo overrides", knowledge
archive rows, skill-management pack examples, usage subscription/archive
links, sandboxes stale `git worktree add`) were already on main — a state
sweep published 02's docs half (001aad66f) without twins.

Per topic:
- configuration: private names and "adding a key means…" → coga-dev/codebase.
- context-layout: distribution states + bundled-launcher rule →
  coga-dev/packaging; one user paragraph kept (local-then-package, init-seeded
  scaffolds are repo-owned); private names dropped; `resources/` row added to
  the layout tree (the override fact used to live in init's deleted section;
  prompt-composition owns it).
- edge-code: packaging invariants and phone-home refactor constraints →
  microkernel "Edge packaging invariants".
- extension-model: kernel tier, No inversion, prepare-checkout justification,
  unbuilt provenance hook, bad-alias escape-hatch note → microkernel "The
  kernel tier and its edges". Recipe and default-alias lists removed.
- cli: now the one owner of the recipe list (full names) and default aliases
  (table rows); seeded-coga.toml examples → pointer to coga.toml.
  AGENTS.md recipe list → pointer to `coga/cli`.
- first-task: step 2 activation/preflight detail → one sentence + launch link.
- init: "Ticket-writing template" deleted; private function names dropped.
- install: 195 → 147 lines (04's PR adds ~12, still < 160). fcntl analysis and
  the 2026-09-30/10-01 owner decisions → current-direction; private names,
  clean-install runbook pointer, contributor install line dropped.
- knowledge: nothing left (archive rows already generic on main; archive-access
  names the paths).
- skill-management: "Known PR checkout failure" → draft ticket
  `preflight-dirty-tracked-files-before-skill-update`; command list →
  `--help`; legacy-digest detail shortened in place (operator-relevant: a
  metadata-only change shows in the `--pr` flow); internals → codebase.
- sandboxes: 2026-10-14 launch-preflight rationale → internals/agent-spawn.
- usage: "Facts a future price table needs" → new coga-dev
  `internals/usage-pricing` (listed in internals index; moving it into
  activity-capture pushed that page past 10,000 bytes).
- uninstall: private names dropped.
- architecture: no topic deleted or merged here, so map unchanged.
- current-direction: alias entry repointed from configuration to
  extension-model.

Disagreement with audit, for the owner: skill-management's legacy-digest
paragraph was kept (shortened) rather than moved, because it explains a
visible `--pr` change to operators.

## Verification

Final feature head: `3d7db0a6140854224b846fad7ad8ba8bd67fd48c`.
Reviewed/tested diff base: `b52fac95c38d51b5a33f4c7cf166b2ad9ce953df`.

- `.venv/bin/python -m pytest`: **3955 passed, 7 skipped** in 348.95s
  on Python 3.12.12, after the reconciliation commit.
- Fresh clone `/tmp/coga-blocks09-pristine-3d7db0a61`:
  `PYTHONPATH=/tmp/coga-blocks09-pristine-3d7db0a61/src /home/n/Code/claude/coga/.venv/bin/python -m pytest tests/test_packaging.py`:
  **30 passed** in 11.46s, including wheel construction.
- `coga validate --json`: exit 0, 154 OK, no errors; warnings on unrelated
  tickets. `git diff --check origin/main...HEAD`: exit 0.
- All 107 enforced pairs are byte-identical; distribution and context
  navigation checks pass. Searches across live docs/src/tests/coga and the
  root guides found no links to the removed topic or anchors (archives,
  old tickets, and the log excluded). `install` is 147 lines.

## Follow-ups filed

- `preflight-dirty-tracked-files-before-skill-update` (draft).
- `stop-the-contexts-root-sweep-from-publishing-canon` (draft): sweeps publish
  canonical `docs/contexts/coga/*` edits from feature branches without their
  packaged twins, breaking main's packaging tests. This branch's own docs
  edits reached main in e9a88b970 the same way; the PR carries the twins.

A `publish-state` recipe failure (exit 2) was recorded when I passed a
mistyped path for the second draft; the retry with the real slug path
published it. No residue.

## Merge notes

The feature branch is committed and pushed at `3d7db0a6140854224b846fad7ad8ba8bd67fd48c`.
No PR exists yet. The final fetch/rebase check found main unchanged at
`b52fac95c38d51b5a33f4c7cf166b2ad9ce953df`; the invoking checkout was returned cleanly to main
before writing this handoff.

PR #1081 (blocks/02) remains open, but this branch now carries the remaining
packaged reconciliation of its canonical edits already on main. No sibling
branch was merged. Later blocks PRs still overlap shared topics; reconcile
canonical content first and copy it to the packaged twins after merging.
The original topic edits mostly reached main through state sweeps, so this
PR necessarily contains more packaged paths than canonical paths.

## Peer review

**Completed** a direct Codex review of final head
`3d7db0a6140854224b846fad7ad8ba8bd67fd48c` against base
`b52fac95c38d51b5a33f4c7cf166b2ad9ce953df`. Read the complete branch diff and commits,
the audit rows, affected operator topics and developer destinations, and the
alias/recipe registry. No nested reviewer CLI or subagent was used.

Finding fixed: the inherited partial blocks/02 publication left ten packaged
topics divergent, an orphaned packaged `coga/code`, and stale navigation and
required-topic entries. The first rebased suite at `e2eeaccde` reproduced
3952 passed, 7 skipped, and the three packaging failures. Commit `3d7db0a61`
synchronizes the ten topics with the canonical files already on main,
removes the orphan, and repairs the index and required set. The final suite
above passes without an unmerged dependency. Re-read the final combined diff
and confirmed that the repair adds no runtime behavior change.

No unresolved must-fix findings. The skill-management digest paragraph is
appropriately retained for its operator-visible effect; the usage-pricing
leaf is indexed and keeps developer material local. No interactive terminal
or Slack check was applicable: only prose, packaged copies, and the required
context expectation changed.

Actual authorship: Claude implemented the original trim; Codex performed this
review and the mechanical reconciliation. The original trim was independently
reviewed, while the Codex correction was self-reviewed. The combined PR is
conservatively marked `self` with advisory depth `skim`; no claim of a wholly
independent final review is made. The preparation record was rendered read-only
and has current receipts and explanations for all 30 diff paths.

## PR

```yaml
title: Trim setup and extension topics and reconcile packaged contexts
author: claude/codex
author_evidence: Claude Code (Opus 5.5) implemented the topic trim, as recorded in the implement handoff.
  This Codex peer-review session applied the mechanical reconciliation of canonical cleanup already on
  main.
head: 3d7db0a6140854224b846fad7ad8ba8bd67fd48c
base: b52fac95c38d51b5a33f4c7cf166b2ad9ce953df
depth: skim
rationale: Documentation and packaging alignment with unchanged runtime behavior. The full suite and fresh-clone
  packaging checks pass. Read the deliberate legacy-digest retention and the reconciliation of partially
  published blocks/02 work. Codex independently reviewed the Claude implementation and self-reviewed its
  own mechanical repair, so skim is recommended rather than an automatic merge recommendation.
implementation: Keeps setup and extension topics focused on operator knowledge, moves developer details
  to local coga-dev owners, centralizes recipe/default-alias lists in coga/cli, reduces install to 147
  lines, and indexes the new usage-pricing leaf. Canonical edits already published to main are carried
  into their packaged twins. The review also completes the remaining blocks/02 packaging reconciliation,
  removing the orphaned coga/code copy and its stale navigation and required-topic expectation.
deviations: 'The legacy-digest paragraph remains shortened in skill-management because it explains a visible
  --pr change. Price-table facts use a new usage-pricing leaf to keep activity-capture below its size-review
  threshold. The skill-update checkout bug became a draft ticket. Many canonical edits reached main through
  state sweeps before this PR; the final diff includes the remaining blocks/02 twin cleanup so it does
  not depend on PR #1081 merging first.'
limitations: 'The final diff is not wholly independently reviewed: Codex self-reviewed its own mechanical
  packaging correction. Tests use Python 3.12.12; no Python 3.11 or native Windows claim is made. No terminal
  or Slack interaction was exercised because no rendered interactive surface or runtime behavior changed.
  Validation reports warnings on unrelated tickets.'
files:
  AGENTS.md: Replace the restated recipe list with a pointer to coga/cli.
  docs/README.md: Replace the link to the already removed coga/code topic with its checkout owner.
  docs/contexts/coga-dev/internals/SKILL.md: List the new usage-pricing page.
  docs/contexts/coga-dev/internals/activity-capture/SKILL.md: Remove the interim copy of the price-table
    facts a sweep published.
  docs/contexts/coga-dev/internals/usage-pricing/SKILL.md: New home for the price-table facts moved out
    of coga/usage.
  docs/contexts/coga/usage/SKILL.md: Point the deferred price table at usage-pricing.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md: Match main's canonical
    topic map, which points directly to the owners formerly summarized by coga/code.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/SKILL.md: Match main's canonical
    removal of the known-gap history and repository archive link.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/branch-sweep/SKILL.md: Match
    main's canonical removal of the known-gap implementation note.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md: Carry main's canonical
    ownership of the explicit ticket-to-branch/PR record into the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: Packaged twin of the trimmed
    topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/code/SKILL.md: Remove the orphaned packaged
    copy after its canonical topic was deleted on main; retained owners preserve its contracts.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md: Packaged twin of the
    trimmed topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/context-layout/SKILL.md: Packaged twin of
    the trimmed topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/SKILL.md: Packaged twin of the trimmed
    topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md: Packaged twin of
    the trimmed topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md: Packaged twin of the
    trimmed topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/important/SKILL.md: Match main's generic operator
    policy without the source-repository usage-report example.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: Packaged twin of the trimmed
    topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md: Packaged twin of the trimmed
    topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/knowledge/SKILL.md: Match the canonical generic
    archive ownership rule required by this ticket's audit row.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md: Point superseded designs
    at blackboard, replacing the removed coga/code link.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: Match main's
    removal of the source-repository upstream-coga example.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/failures/SKILL.md: Match
    main's removal of known-gap implementation notes.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/sandboxes/SKILL.md: Packaged twin of the trimmed
    topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/skill-management/SKILL.md: Packaged twin of
    the trimmed topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/discovery/SKILL.md: Match main's generic
    retirement-history instructions without the relay-os source-repository path.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/uninstall/SKILL.md: Packaged twin of the trimmed
    topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/usage/SKILL.md: Packaged twin of the trimmed
    topic.
  tests/test_packaging.py: Remove coga/code from the required set to match its canonical deletion already
    on main.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 3d7db0a6140854224b846fad7ad8ba8bd67fd48c
  base: b52fac95c38d51b5a33f4c7cf166b2ad9ce953df
  detail: Direct review completed on the final head/base, including the complete diff, audit rows, moved-content
    owners, alias/recipe registry, and removal/link checks. No unresolved must-fix findings. Independent
    of Claude's original trim; self-review of Codex's mechanical reconciliation, so the combined result
    is conservatively labeled self-review. All 107 enforced twins match; install is 147 lines.
checks:
- command: .venv/bin/python -m pytest
  status: passed
  head: 3d7db0a6140854224b846fad7ad8ba8bd67fd48c
  base: b52fac95c38d51b5a33f4c7cf166b2ad9ce953df
  detail: 3955 passed, 7 skipped in 348.95s on Python 3.12.12 after the reconciliation commit; no failures.
- command: PYTHONPATH=/tmp/coga-blocks09-pristine-3d7db0a61/src /home/n/Code/claude/coga/.venv/bin/python
    -m pytest tests/test_packaging.py
  status: passed
  head: 3d7db0a6140854224b846fad7ad8ba8bd67fd48c
  base: b52fac95c38d51b5a33f4c7cf166b2ad9ce953df
  detail: 30 passed in 11.46s, run from /tmp/coga-blocks09-pristine-3d7db0a61, a fresh local clone of
    this head. Includes pristine-tree wheel construction, distribution, twin identity, and navigation
    checks.
- command: coga validate --json
  status: passed
  head: 3d7db0a6140854224b846fad7ad8ba8bd67fd48c
  base: b52fac95c38d51b5a33f4c7cf166b2ad9ce953df
  detail: Exit 0, 154 OK, no errors; warnings on unrelated tickets.
- command: git diff --check origin/main...HEAD
  status: passed
  head: 3d7db0a6140854224b846fad7ad8ba8bd67fd48c
  base: b52fac95c38d51b5a33f4c7cf166b2ad9ce953df
  detail: Exit 0; no whitespace errors.
```
