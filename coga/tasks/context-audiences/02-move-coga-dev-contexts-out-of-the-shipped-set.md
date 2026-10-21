---
title: 02 Move Coga-dev contexts out of the shipped set
status: done
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
agent: claude
---

## Description

Carry out the decision record in `coga/tasks/context-audiences/README.md`,
which sibling `01` writes and the owner approves. It defines two context
audiences, for repos that use Coga and for developing Coga. Make the split real
in the tree, the package, the tests and the guidance docs. Do not reopen the
README's product decisions. If the README is missing, unapproved, or doesn't
cover something you hit, ask the owner.

1. **Move and split topics** as the README's classification table says, in
   `docs/contexts/` and in the packaged twins under
   `src/coga/resources/templates/coga/bootstrap/contexts/`.
2. **Stop shipping Coga-dev topics.** Delete their packaged copies and make
   `tests/test_packaging.py` enforce the split: `REQUIRED_BOOTSTRAP_CONTEXT_REFS`
   holds only user topics. `LOCAL_ONLY_CONTEXT_REFS` previously demanded a reason
   per topic, so change how it expresses a whole local-only audience (e.g. by
   namespace) rather than listing about 30 identical reasons.
3. **Update every ref and link** to a moved topic: ticket `contexts:` in
   `coga/tasks/`, skills, workflows, source strings, tests, fixtures
   (`tests/fixtures/seeded-repo/`), `README.md`, `AGENTS.md`, and GitHub-URL
   links in packaged templates.
4. **Update the guidance docs** so they name both sets and the criterion:
   `docs/README.md`, `coga/knowledge`, `coga-dev/packaging`,
   `coga/context-layout`, the `bootstrap/ticket` skill's "Context and skill
   selection contract", and `AGENTS.md`'s canonical-topics list.
5. **Release note** naming the renamed and de-packaged refs, per the README's
   compatibility decision.

Done when every topic under `docs/contexts/` matches its README row, the
packaged bootstrap set contains only `user` topics and the packaging test
enforces it, no reference to an old ref or URL remains outside
`docs/archive/`, `docs/README.md` and `bootstrap/ticket`'s selection contract
each name both sets and the criterion, and `python -m pytest` and
`coga validate --json` pass.

## Context

### Depends on 01

Don't start until `context-audiences/01-classify-contexts-by-audience-and-decide-the-la`
is done and the README decision record is approved. Read the README first. It
is not composed into this prompt.

### Topics this ticket edits (cited, not attached)

These are read and edited, so they are left off `contexts:`:

- `coga-dev/packaging` (`docs/contexts/coga-dev/packaging/SKILL.md`): twin mapping,
  the "Local-only" definition, and the bootstrap/init-seeded/local-only
  categories. Read it whole before touching twins.
- `coga/knowledge` (`docs/contexts/coga/knowledge/SKILL.md`): "Attach or
  cite".
- `coga/context-layout` (`docs/contexts/coga/context-layout/SKILL.md`). This
  repo sets `[layout] contexts = "docs/contexts"` in `coga/coga.toml`, and
  `config.contexts_root` resolves it.
- `docs/README.md`, whose Start / Understand / Operate / Internals grouping is
  a rough precursor of the split.
- The `bootstrap/ticket` skill
  (`src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/`). It
  has no live twin under `coga/skills/`.
- `AGENTS.md`.

### Mechanics

- Packaged twins must stay byte-identical with their canonical copies, which
  `tests/test_packaging.py` derives and enforces. A moved user topic moves in
  both trees. A de-packaged topic loses its packaged copy and becomes
  local-only.
- Composition fails loud on an unknown ref, so a missed `contexts:` entry in
  `coga/tasks/` breaks that ticket's next launch. Grep refs, `docs/contexts/<ref>`
  paths, and `github.com/FastJVM/coga/blob/main/docs/contexts/` URLs.
- Exclude `docs/archive/**` from the rewrite. It is dated history.

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

pr: https://github.com/FastJVM/coga/pull/1077
branch: context-audiences-split

## Implement handoff

Implemented the approved audience decisions: all 80 classification rows
(78 original plus PR #1068's two checkout topics) yield 61 shipped user topics
and 24 local Coga-dev topics. Mixed topics are split as specified. Namespace,
wheel, resolver, twin, shipped-dependency and Markdown target/anchor checks
enforce the boundary. Updated consumers, ticket refs, skills/workflows,
fixtures, README/AGENTS, guidance and release notes. The empty manifesto
directory is gone. Two pre-existing broken navigation links were also repaired.

Reconciliation preserved main's checkout/chat/manual guidance and newer task
lifecycle state. Historical PR records retain their recorded paths and receipts;
they are evidence about past commits, not live context dependencies. Runtime
Python changes are limited to six source comments/docstrings.

## Peer review

Direct review **completed** on `aa422de4da092149ae0925f69ee96c21b26ec43a` against
`94fad92944fe829f4c233fa3cb0f56d883748097` (`origin/main`). Reviewer: Codex.
The implementer was also Codex, so this is recorded as self-review; no independent
reviewer, nested CLI reviewer or subagent ran. The final rebase preserved newer pin-control lifecycle state, checked criteria
and complete PR receipts; only context references and the approved audience
wording changed relative to its control copy. Runtime/resources and tests
remain identical to the previous full-suite revision.
The final publication-freshness probe passed against control
`94fad92944fe829f4c233fa3cb0f56d883748097`: HEAD contains latest origin/main.

The owner approved all three finding groups on 2026-10-21. Fixed and re-reviewed:

1. Microkernel rule/placement citations now name `coga-dev/microkernel`;
   recipe/alias facts keep their user owner, and development links are explicit.
2. The release checklist now uses the existing `coga/edge-code/edge-code-upgrades.md` runbook.
3. Live tasks/designs keep development contracts local and require twins only
   for user topics. New lock implementation topics use `coga-dev/internals/`;
   operator facts stay in shipped launch/checkouts/tickets/megalaunch topics.

No unresolved must-fix finding remains. No terminal/pager/TTY/Slack rendering
behavior changed, so the interactive-surface exercise is inapplicable.

Final-head checks: 3945 passed, 7 skipped in 351.77s (0:05:51); pristine-clone wheel 1 passed;
root and seeded-fixture validation 0 errors. Audit: 61 user/24 development
topics, 89 protected ticket headers unchanged except contexts, 9 historical PR
records unchanged, and 6 unchanged executable runtime ASTs. Exact receipts
and platform omissions are below. Advisory PR recommendation remains `deep`
for the broad migration, coordinated state conversion and self-review.
The PR presentation rendered with all 295 diff paths covered, current receipts
and no publication evidence gaps.

## Coordinated conversion and next step

The branch is committed and pushed; no PR is open. The current ticket is
published separately and is excluded from the implementation diff.

Before the lifecycle handoff, all 95 changed `coga/tasks/` and
`coga/recurring/` working copies were restored from fresh `origin/main` and
verified byte-identical to control. Their conversion remains in committed/pushed
head `aa422de4da092149ae0925f69ee96c21b26ec43a`. This prevents a sweep from
publishing new refs before their topics land. The launcher returns the checkout.
Repeat this protection if a later step checks out the conversion branch and
needs a lifecycle command; preserve the committed conversion.

Before merge, follow `coga-dev/internals/git-regressions`, “Shipping a
stored-ticket schema conversion”: open the writer quiet window, rebuild the
conversion on the exact control tip while preserving newer state, merge topics
and consumers together, and verify updated installations before resuming writers.
The next workflow step is the mechanical PR publication step.

## PR

```yaml
title: Separate shipped user contexts from Coga development guidance
author: codex
author_evidence: The implementation handoff records Codex (GPT-6) as the actual implementer, overriding
  the configured Claude agent. The approved peer-review fixes were also applied by Codex.
head: aa422de4da092149ae0925f69ee96c21b26ec43a
base: 94fad92944fe829f4c233fa3cb0f56d883748097
depth: deep
rationale: Broad clean-break context/package migration with coordinated stored-ticket changes. Direct
  self-review completed with all three finding groups resolved; independent review and native Windows/Python
  3.11 verification have not run.
implementation: 'Implements all 78 original approved rows plus two user topics added by current main:
  61 shipped user topics and 24 local Coga-dev topics. Splits mixed contracts, migrates consumers and
  ticket contexts, enforces namespace, wheel, twin and link boundaries, and documents the clean break.
  Review fixes correct split-topic ownership citations, the release upgrade-runbook path, and live task/design
  requirements for local-only topics.'
deviations: 'No audience decisions changed; PR #1068 added dev/checkouts/chat and dev/checkouts/manual,
  both user topics under the approved shipped-consumer criterion. Stored-ticket ref conversion travels
  with the topics under the coordinated-conversion procedure; lifecycle fields and titles are preserved.
  Two already-broken links were repaired during the requested audit. The owner approved all three review
  finding groups and targeted corrections on 2026-10-21.'
limitations: Python 3.12.12 verified; Python 3.11 and native Windows were not verified. No terminal, pager,
  TTY-prompt or Slack-rendering behavior changed, so an interactive-surface exercise is inapplicable.
  Old spellings remain as mapping/history in the approved decision and release note, historical task descriptions
  and PR receipts, immutable audit history, one human-owned parked-ticket title, and the legacy gitignore-cleanup
  literal; these are not live dependencies. Archives were not read or edited. Before merge, refresh the
  conversion on the exact control tip and coordinate the writer quiet window and installation update required
  by coga-dev/internals/git-regressions.
files:
  AGENTS.md: Update audience guidance and links to the correct topic owners.
  CONTRIBUTING.md: Update audience guidance and links to the correct topic owners.
  README.md: Update audience guidance and links to the correct topic owners.
  coga/context.md: Refresh the generated principles owner and links.
  coga/recurring/dream/ticket.md: Point recurring instructions at the owning user topics.
  coga/recurring/phone-home/operations.md: Point recurring instructions at the owning user topics.
  coga/recurring/phone-home/ticket.md: Point recurring instructions at the owning user topics.
  coga/skills/code/implement/SKILL.md: Update audience guidance and links to the correct topic owners.
  coga/skills/code/open-pr/SKILL.md: Update audience guidance and links to the correct topic owners.
  coga/skills/code/self-qa/SKILL.md: Update audience guidance and links to the correct topic owners.
  coga/skills/coga/releasing/SKILL.md: Update audience guidance and links to the correct topic owners.
  coga/skills/coga/ticket/finalize/SKILL.md: Update audience guidance and links to the correct topic owners.
  coga/skills/marketing/write-post/SKILL.md: Update audience guidance and links to the correct topic owners.
  coga/tasks/_v2/README.md: Migrate live context refs; preserve lifecycle and historical PR receipts.
  coga/tasks/_v2/absorb-compound-engineering-leaf-skills-as-a-coga.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/_v2/add-dev-testing-setup-skill.md: Migrate live context refs; preserve lifecycle and historical
    PR receipts.
  coga/tasks/_v2/add-relay-skill-search-with-candidate-eval.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/_v2/auto-persist-dirty-launch-worktrees-to-pushed-bran.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/_v2/automerge-ticket.md: Migrate live context refs; preserve lifecycle and historical PR
    receipts.
  coga/tasks/_v2/autotrigger-ticket-type.md: Migrate live context refs; preserve lifecycle and historical
    PR receipts.
  coga/tasks/_v2/dream-recurring-persist-done-stop-inline-delete.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/_v2/fail-validation-when-local-user-is-required-for-ex.md: Correct split-topic ownership
    and audience/twin requirements while preserving lifecycle and historical receipts.
  coga/tasks/_v2/implement-accepted-ticket-interview-improvements.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/_v2/install-smoke-ci-matrix.md: Migrate live context refs; preserve lifecycle and historical
    PR receipts.
  coga/tasks/_v2/measure-relay-prompt-scope-and-agent-precision.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/_v2/move-some-alerts-to-coga-important-instead-of-coga.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/_v2/propagate-local-coga-config-into-worktrees.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/_v2/remove-the-twin-check-and-the-twin-concept.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/_v2/rename-workflow-primitive-to-playbook.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/_v2/ship-a-shared-recurring-reminder-engine-battery.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/_v2/split-context-to-doc-user-accessible-and-editable.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/_v2/use-worktree-when-starting-a-dev-task.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/_v2/validate-tickets-on-hand-edit-gap-outside-relay-co.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/a-slack-repo-without-important-webhook-can-abort-t.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/add-a-failed-terminal-status.md: Migrate live context refs; preserve lifecycle and historical
    PR receipts.
  coga/tasks/add-an-applying-a-batch-of-verdicts-section-to-the.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/adjudicate-the-eight-premise-dead-v2-drafts.md: Correct split-topic ownership and audience/twin
    requirements while preserving lifecycle and historical receipts.
  coga/tasks/autofix-dedupe-ignores-closed-autofix-tickets.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/autofix-write-ups-lose-their-body-to-h2-headings.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/autofix/name-cross-repo-retire-follow-ups-with-the-repo-th/ticket.md: Migrate live context
    refs; preserve lifecycle and historical PR receipts.
  coga/tasks/automate-checkout-setup-and-deduplicate-instructio.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/cleanup/handle-a-bare-slack-webhook-url-during-empty-repo.md: Migrate live context refs;
    preserve lifecycle and historical PR receipts.
  coga/tasks/confirm-why-branch-sweep-ran-as-a-shared-period-ta.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/context-audiences/README.md: Migrate live context refs; preserve lifecycle and historical
    PR receipts.
  coga/tasks/dedupe-claude-transcript-usage-by-message-id.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/define-the-api-equivalent-cost-proxy-and-price-tab.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/digest-can-clobber-recurring-last-serviced-period.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/document-the-remedy-for-a-bloated-blackboard-sibli.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/dream-s-own-blackboard-trips-large-blackboard-ever.md: Correct split-topic ownership and
    audience/twin requirements while preserving lifecycle and historical receipts.
  coga/tasks/exclude-superseded-designs-from-launch-prompts.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/file-post-merge-obligations-before-open-pr-because.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/fix-coga-git-sync-failures-that-leave-main-diverge.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/fix-git-sync-failure.md: Migrate live context refs; preserve lifecycle and historical PR
    receipts.
  coga/tasks/fix-parser-bugs-documented-in-pr-1055.md: Migrate live context refs; preserve lifecycle and
    historical PR receipts.
  coga/tasks/gigantic-refactor-move-recurring-recipes-out-of-co.md: Correct split-topic ownership and
    audience/twin requirements while preserving lifecycle and historical receipts.
  coga/tasks/implement-the-include-allowlist-that-url-skill-upd.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/interview-the-owner-on-the-17-title-only-v2-stubs.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/keep-multiline-audit-messages-on-one-log-line.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/launch-locks/checkout-exclusivity-lock/design.md: Keep new lock implementation contracts
    local under coga-dev; put operator facts in shipped topics.
  coga/tasks/launch-locks/checkout-exclusivity-lock/ticket.md: Keep new lock implementation contracts
    local under coga-dev; put operator facts in shipped topics.
  coga/tasks/launch-locks/ticket-ownership-lock/design.md: Keep new lock implementation contracts local
    under coga-dev; put operator facts in shipped topics.
  coga/tasks/launch-locks/ticket-ownership-lock/ticket.md: Keep new lock implementation contracts local
    under coga-dev; put operator facts in shipped topics.
  coga/tasks/launch-moves-the-checkout-to-main-before-and-after.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/let-the-autofix-generator-attach-repo-default-contexts.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/lifecycle-writes-read-control-s-ticket-before-modi.md: Correct split-topic ownership and
    audience/twin requirements while preserving lifecycle and historical receipts.
  coga/tasks/make-coga-status-an-interactive-control-center.md: Correct split-topic ownership and audience/twin
    requirements while preserving lifecycle and historical receipts.
  coga/tasks/marketing/demo-hackability-ask-claude-to-add-a-command-live.md: Migrate live context refs;
    preserve lifecycle and historical PR receipts.
  coga/tasks/marketing/fix-installer/affordable-macos-testing-on-owned-macs-and-per-min.md: Migrate live
    context refs; preserve lifecycle and historical PR receipts.
  coga/tasks/marketing/fix-installer/test-install-on-windows.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/marketing/publish-coga-1-0-as-the-final-v1-step.md: Correct the edge-code upgrade-runbook
    path and migrated context refs.
  coga/tasks/marketing/readme-top.md: Migrate live context refs; preserve lifecycle and historical PR
    receipts.
  coga/tasks/marketing/state-the-hatchling-prerequisite-in-the-clean-whee.md: Migrate live context refs;
    preserve lifecycle and historical PR receipts.
  coga/tasks/match-concurrent-codex-sessions-to-their-launch-so.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/microkernel/README.md: Correct split-topic ownership and audience/twin requirements while
    preserving lifecycle and historical receipts.
  coga/tasks/microkernel/launch-decomposition.md: Migrate live context refs; preserve lifecycle and historical
    PR receipts.
  coga/tasks/microkernel/lifecycle-verbs-to-ticket-operations.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/microkernel/move-retire-to-a-command-ticket.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/microkernel/read-report-commands-as-ticket-workflows.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/microkernel/residual-command-surfaces.md: Correct split-topic ownership and audience/twin
    requirements while preserving lifecycle and historical receipts.
  coga/tasks/microkernel/support-commands-boundary.md: Migrate live context refs; preserve lifecycle and
    historical PR receipts.
  coga/tasks/microkernel/work-orchestration-commands-to-tickets.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/name-the-current-script-assist-preflight-post-call.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/no-durable-runbook-covers-running-coga-headless.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/nothing-exercises-python-3-11-the-declared-floor.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/parse-agents-rejects-cogalocaltoml.md: Migrate live context refs; preserve lifecycle and
    historical PR receipts.
  coga/tasks/pin-control-inside-the-state-lock-during-checkout.md: Correct split-topic ownership and audience/twin
    requirements while preserving lifecycle and historical receipts.
  coga/tasks/premise-check-2026-w39-25-parked-drafts-need-a-ver.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/premise-check-2026-w40-8-parked-drafts-need-a-verd.md: Correct split-topic ownership and
    audience/twin requirements while preserving lifecycle and historical receipts.
  coga/tasks/prevent-duplicate-session-usage-records-from-infla.md: Correct split-topic ownership and
    audience/twin requirements while preserving lifecycle and historical receipts.
  coga/tasks/publish-coga-0-4-1-to-pypi-which-main-already-decl.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/recheck-codex-usage-completeness-after-the-session.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/recurring/dream/ticket.md: Migrate live context refs; preserve lifecycle and historical PR
    receipts.
  coga/tasks/repair-ticket-referents-when-a-referent-is-renamed.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/reuse-the-existing-control-worktree-for-recurring.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/run-recurring-agent-templates-off-the-control-bran.md: Correct split-topic ownership and
    audience/twin requirements while preserving lifecycle and historical receipts.
  coga/tasks/scrub-the-service-account-token-from-the-launch-ch.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/slim-the-40-9-kib-blackboard-of-the-macos-and-wind.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/state-sync-published-unmerged-recurring-templates.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/stop-creating-linked-worktrees-for-coga-retire.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/triage-the-v2-parking-area-empty-descriptions-prem.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/validate-that-committed-skill-scripts-with-a-sheba.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/verify-dream-under-codex-on-the-real-repo-w40.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/windows-native/core-port-cli-and-test-suite-pass-on-native-window.md: Correct split-topic
    ownership and audience/twin requirements while preserving lifecycle and historical receipts.
  coga/tasks/windows-native/interactive-coga-launch-on-native-windows.md: Correct split-topic ownership
    and audience/twin requirements while preserving lifecycle and historical receipts.
  coga/tasks/windows-native/pr-ci-with-linux-and-windows-test-jobs.md: Correct split-topic ownership and
    audience/twin requirements while preserving lifecycle and historical receipts.
  docs/README.md: Update audience guidance and links to the correct topic owners.
  docs/contexts/coga-dev/archive-access/SKILL.md: Keep Coga development knowledge in the local-only audience.
  docs/contexts/coga-dev/codebase/SKILL.md: Keep Coga development knowledge in the local-only audience.
  docs/contexts/coga-dev/codebase/gotchas/SKILL.md: Correct split-topic ownership and audience/twin requirements
    while preserving lifecycle and historical receipts.
  docs/contexts/coga-dev/current-direction/SKILL.md: Correct split-topic ownership and audience/twin requirements
    while preserving lifecycle and historical receipts.
  docs/contexts/coga-dev/internals/SKILL.md: Keep Coga development knowledge in the local-only audience.
  docs/contexts/coga-dev/internals/activity-capture/SKILL.md: Keep Coga development knowledge in the local-only
    audience.
  docs/contexts/coga-dev/internals/agent-spawn/SKILL.md: Keep Coga development knowledge in the local-only
    audience.
  docs/contexts/coga-dev/internals/assist-publication/SKILL.md: Keep Coga development knowledge in the
    local-only audience.
  docs/contexts/coga-dev/internals/claim-recovery/SKILL.md: Keep Coga development knowledge in the local-only
    audience.
  docs/contexts/coga-dev/internals/git-refresh/SKILL.md: Keep Coga development knowledge in the local-only
    audience.
  docs/contexts/coga-dev/internals/git-regressions/SKILL.md: Keep Coga development knowledge in the local-only
    audience.
  docs/contexts/coga-dev/internals/launch-claims/SKILL.md: Keep Coga development knowledge in the local-only
    audience.
  docs/contexts/coga-dev/internals/recurring-admission/SKILL.md: Keep Coga development knowledge in the
    local-only audience.
  docs/contexts/coga-dev/internals/recurring-control/SKILL.md: Keep Coga development knowledge in the
    local-only audience.
  docs/contexts/coga-dev/internals/recurring-temp-worktrees/SKILL.md: Keep Coga development knowledge
    in the local-only audience.
  docs/contexts/coga-dev/internals/spool-merge/SKILL.md: Keep Coga development knowledge in the local-only
    audience.
  docs/contexts/coga-dev/internals/state-publication/SKILL.md: Keep Coga development knowledge in the
    local-only audience.
  docs/contexts/coga-dev/internals/state-publication/publish/SKILL.md: Keep Coga development knowledge
    in the local-only audience.
  docs/contexts/coga-dev/microkernel/SKILL.md: Keep Coga development knowledge in the local-only audience.
  docs/contexts/coga-dev/packaging/SKILL.md: Keep Coga development knowledge in the local-only audience.
  docs/contexts/coga-dev/patterns/SKILL.md: Keep Coga development knowledge in the local-only audience.
  docs/contexts/coga-dev/principles/SKILL.md: Keep Coga development knowledge in the local-only audience.
  docs/contexts/coga-dev/principles/reading-list.md: Keep Coga development knowledge in the local-only
    audience.
  docs/contexts/coga-dev/project-stage/SKILL.md: Keep Coga development knowledge in the local-only audience.
  docs/contexts/coga-dev/testing/SKILL.md: Keep Coga development knowledge in the local-only audience.
  docs/contexts/coga/agents/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/architecture/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/blackboard/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/cli/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/codebase/SKILL.md: Move or split this topic into its approved audience.
  docs/contexts/coga/codebase/gotchas/SKILL.md: Move or split this topic into its approved audience.
  docs/contexts/coga/context-layout/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/current-direction/SKILL.md: Move or split this topic into its approved audience.
  docs/contexts/coga/edge-code/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/edge-code/edge-code-upgrades.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/extension-model/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/human-assist/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/install/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/internals/activity-capture/SKILL.md: Move or split this topic into its approved audience.
  docs/contexts/coga/internals/agent-spawn/SKILL.md: Move or split this topic into its approved audience.
  docs/contexts/coga/internals/assist-publication/SKILL.md: Move or split this topic into its approved
    audience.
  docs/contexts/coga/internals/claim-recovery/SKILL.md: Move or split this topic into its approved audience.
  docs/contexts/coga/internals/git-refresh/SKILL.md: Move or split this topic into its approved audience.
  docs/contexts/coga/internals/git-regressions/SKILL.md: Move or split this topic into its approved audience.
  docs/contexts/coga/internals/human-assist/SKILL.md: Move or split this topic into its approved audience.
  docs/contexts/coga/internals/launch-claims/SKILL.md: Move or split this topic into its approved audience.
  docs/contexts/coga/internals/pr-publication/SKILL.md: Move or split this topic into its approved audience.
  docs/contexts/coga/internals/pr-publication/existing-pr/SKILL.md: Move or split this topic into its
    approved audience.
  docs/contexts/coga/internals/pr-publication/preparation/SKILL.md: Move or split this topic into its
    approved audience.
  docs/contexts/coga/internals/recurring-admission/SKILL.md: Move or split this topic into its approved
    audience.
  docs/contexts/coga/internals/recurring-control/SKILL.md: Move or split this topic into its approved
    audience.
  docs/contexts/coga/internals/recurring-temp-worktrees/SKILL.md: Move or split this topic into its approved
    audience.
  docs/contexts/coga/internals/spool-merge/SKILL.md: Move or split this topic into its approved audience.
  docs/contexts/coga/internals/state-publication/SKILL.md: Move or split this topic into its approved
    audience.
  docs/contexts/coga/internals/state-publication/authoring/SKILL.md: Move or split this topic into its
    approved audience.
  docs/contexts/coga/internals/state-publication/publish/SKILL.md: Move or split this topic into its approved
    audience.
  docs/contexts/coga/internals/state-publication/sweep/SKILL.md: Move or split this topic into its approved
    audience.
  docs/contexts/coga/knowledge/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/launch-internals/SKILL.md: Move or split this topic into its approved audience.
  docs/contexts/coga/launch/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/megalaunch/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/packaging/SKILL.md: Move or split this topic into its approved audience.
  docs/contexts/coga/packaging/edge-code-upgrades.md: Move or split this topic into its approved audience.
  docs/contexts/coga/patterns/SKILL.md: Move or split this topic into its approved audience.
  docs/contexts/coga/period-task/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/pr-publication/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/pr-publication/existing-pr/SKILL.md: Keep user facts and navigation at the approved
    ref.
  docs/contexts/coga/pr-publication/preparation/SKILL.md: Keep user facts and navigation at the approved
    ref.
  docs/contexts/coga/principles/SKILL.md: Move or split this topic into its approved audience.
  docs/contexts/coga/principles/reading-list.md: Move or split this topic into its approved audience.
  docs/contexts/coga/project-stage/SKILL.md: Move or split this topic into its approved audience.
  docs/contexts/coga/prompt-composition/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/recurring/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/recurring/delegation/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/recurring/scheduling/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/recurring/scheduling/failures/SKILL.md: Keep user facts and navigation at the approved
    ref.
  docs/contexts/coga/recurring/scheduling/ledger/SKILL.md: Keep user facts and navigation at the approved
    ref.
  docs/contexts/coga/recurring/templates/SKILL.md: Use the correct optional development packaging link;
    preserve canonical/package byte identity.
  docs/contexts/coga/sandboxes/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/script-tickets/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/skill-management/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/state-publication/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/state-publication/authoring/SKILL.md: Keep user facts and navigation at the approved
    ref.
  docs/contexts/coga/state-publication/sweep/SKILL.md: Keep user facts and navigation at the approved
    ref.
  docs/contexts/coga/sync/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/testing/SKILL.md: Move or split this topic into its approved audience.
  docs/contexts/coga/tickets/ownership/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/usage/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/coga/workflows/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/dev/checkouts/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/dev/checkouts/launch-boundary/SKILL.md: Keep user facts and navigation at the approved
    ref.
  docs/contexts/dev/checkouts/manual/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/dev/code/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/contexts/dev/dev-record/SKILL.md: Keep user facts and navigation at the approved ref.
  docs/release-notes/context-audiences.md: Document all renamed and de-packaged refs for the clean break.
  src/coga/cli.py: Update the source comment or docstring owning-topic citation.
  src/coga/git.py: Update the source comment or docstring owning-topic citation.
  src/coga/launch.py: Update the source comment or docstring owning-topic citation.
  src/coga/logfile.py: Update the source comment or docstring owning-topic citation.
  src/coga/publish_state.py: Update the source comment or docstring owning-topic citation.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/agents/SKILL.md: Ship the canonical user topic
    byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md: Ship the canonical
    user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md: Ship the canonical user
    topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: Ship the canonical user topic
    byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md: Remove the old or development
    context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/gotchas/SKILL.md: Remove the old
    or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/context-layout/SKILL.md: Ship the canonical
    user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/SKILL.md: Ship the canonical user
    topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/edge-code-upgrades.md: Ship the
    canonical user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md: Ship the canonical
    user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/human-assist/SKILL.md: Ship the canonical
    user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md: Ship the canonical user
    topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/activity-capture/SKILL.md: Remove
    the old or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/agent-spawn/SKILL.md: Remove the
    old or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/assist-publication/SKILL.md: Remove
    the old or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/claim-recovery/SKILL.md: Remove
    the old or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/git-refresh/SKILL.md: Remove the
    old or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/git-regressions/SKILL.md: Remove
    the old or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/human-assist/SKILL.md: Remove the
    old or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/launch-claims/SKILL.md: Remove the
    old or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/pr-publication/SKILL.md: Remove
    the old or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/pr-publication/existing-pr/SKILL.md: Remove
    the old or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/pr-publication/preparation/SKILL.md: Remove
    the old or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/recurring-admission/SKILL.md: Remove
    the old or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/recurring-control/SKILL.md: Remove
    the old or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/recurring-temp-worktrees/SKILL.md: Remove
    the old or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/spool-merge/SKILL.md: Remove the
    old or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/state-publication/SKILL.md: Remove
    the old or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/state-publication/authoring/SKILL.md: Remove
    the old or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/state-publication/publish/SKILL.md: Remove
    the old or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/state-publication/sweep/SKILL.md: Remove
    the old or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/knowledge/SKILL.md: Ship the canonical user
    topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/launch-internals/SKILL.md: Remove the old
    or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md: Ship the canonical user topic
    byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/megalaunch/SKILL.md: Ship the canonical user
    topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/packaging/SKILL.md: Remove the old or development
    context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/packaging/edge-code-upgrades.md: Remove the
    old or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/patterns/SKILL.md: Remove the old or development
    context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/period-task/SKILL.md: Ship the canonical user
    topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/pr-publication/SKILL.md: Ship the canonical
    user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/pr-publication/existing-pr/SKILL.md: Ship
    the canonical user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/pr-publication/preparation/SKILL.md: Ship
    the canonical user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/principles/SKILL.md: Remove the old or development
    context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/principles/reading-list.md: Remove the old
    or development context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md: Ship the canonical
    user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md: Ship the canonical user
    topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/delegation/SKILL.md: Ship the canonical
    user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: Ship the canonical
    user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/failures/SKILL.md: Ship
    the canonical user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/ledger/SKILL.md: Ship
    the canonical user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/SKILL.md: Use the correct
    optional development packaging link; preserve canonical/package byte identity.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/sandboxes/SKILL.md: Ship the canonical user
    topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md: Ship the canonical
    user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/skill-management/SKILL.md: Ship the canonical
    user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md: Ship the canonical
    user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/authoring/SKILL.md: Ship
    the canonical user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/sweep/SKILL.md: Ship the
    canonical user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md: Ship the canonical user topic
    byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/testing/SKILL.md: Remove the old or development
    context from the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/ownership/SKILL.md: Ship the canonical
    user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/usage/SKILL.md: Ship the canonical user topic
    byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md: Ship the canonical user
    topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/dev/checkouts/SKILL.md: Ship the canonical user
    topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/dev/checkouts/launch-boundary/SKILL.md: Ship the
    canonical user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/dev/checkouts/manual/SKILL.md: Ship the canonical
    user topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/dev/code/SKILL.md: Ship the canonical user topic
    byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/contexts/dev/dev-record/SKILL.md: Ship the canonical user
    topic byte-for-byte.
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/scan-protocol/SKILL.md: Update
    audience guidance and links to the correct topic owners.
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md: Update audience guidance
    and links to the correct topic owners.
  src/coga/resources/templates/coga/bootstrap/skills/code/implement/SKILL.md: Update audience guidance
    and links to the correct topic owners.
  src/coga/resources/templates/coga/bootstrap/skills/code/open-pr/SKILL.md: Update audience guidance and
    links to the correct topic owners.
  src/coga/resources/templates/coga/bootstrap/skills/code/self-qa/SKILL.md: Update audience guidance and
    links to the correct topic owners.
  src/coga/resources/templates/coga/bootstrap/skills/coga/releasing/SKILL.md: Update audience guidance
    and links to the correct topic owners.
  src/coga/resources/templates/coga/bootstrap/skills/coga/ticket/finalize/SKILL.md: Update audience guidance
    and links to the correct topic owners.
  src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md: Update audience guidance
    and links to the correct topic owners.
  src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md: Update audience
    guidance and links to the correct topic owners.
  src/coga/resources/templates/coga/bootstrap/workflows/code/with-review.md: Update audience guidance
    and links to the correct topic owners.
  src/coga/resources/templates/coga/bootstrap/workflows/code/with-self-review.md: Update audience guidance
    and links to the correct topic owners.
  src/coga/resources/templates/coga/bootstrap/workflows/docs/with-review.md: Update audience guidance
    and links to the correct topic owners.
  src/coga/resources/templates/coga/recurring/dream/ticket.md: Update audience guidance and links to the
    correct topic owners.
  src/coga/resources/templates/coga/recurring/phone-home/operations.md: Update audience guidance and links
    to the correct topic owners.
  src/coga/resources/templates/coga/recurring/phone-home/ticket.md: Update audience guidance and links
    to the correct topic owners.
  src/coga/resources/ticket.md: Update audience guidance and links to the correct topic owners.
  src/coga/retire_worklist.py: Update the source comment or docstring owning-topic citation.
  tests/fixtures/seeded-repo/coga/workflows/code/with-review.md: Verify audience isolation, relocated
    refs, or representative fixtures.
  tests/test_compose.py: Verify audience isolation, relocated refs, or representative fixtures.
  tests/test_dream_worker_templates.py: Verify audience isolation, relocated refs, or representative fixtures.
  tests/test_edge_distribution.py: Verify audience isolation, relocated refs, or representative fixtures.
  tests/test_packaging.py: Verify audience isolation, relocated refs, or representative fixtures.
review:
  reviewer: codex
  kind: self
  status: passed
  head: aa422de4da092149ae0925f69ee96c21b26ec43a
  base: 94fad92944fe829f4c233fa3cb0f56d883748097
  detail: Direct review completed on the final rebased and fixed revision. All three documentation finding
    groups were corrected with the attending owner's approval; no unresolved must-fix findings remain.
    Implementation and reviewer identities are both Codex, so this is self-review. No independent reviewer,
    nested CLI reviewer, or subagent ran. Final rebase preserved newer pin-control lifecycle state and
    PR receipts; runtime/resources and tests remain identical to the previous full-suite revision.
checks:
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest > /tmp/coga-context-audiences-peer-reconciled-pytest.log
    2>&1
  status: passed
  head: aa422de4da092149ae0925f69ee96c21b26ec43a
  base: 94fad92944fe829f4c233fa3cb0f56d883748097
  detail: 3945 passed, 7 skipped in 351.77s (0:05:51) on Python 3.12.12 after the final rebase. Seven
    skips require native Windows (2 job-object and 5 PowerShell checks).
- command: PYTHONPATH=/tmp/coga-context-peer-reconciled-9i5tskhj/repo/src /home/n/Code/codex/coga/.venv/bin/python
    -m pytest tests/test_packaging.py::test_wheel_includes_bootstrap_batteries -q --tb=short > /tmp/coga-context-peer-reconciled-wheel.log
  status: passed
  head: aa422de4da092149ae0925f69ee96c21b26ec43a
  base: 94fad92944fe829f4c233fa3cb0f56d883748097
  detail: 1 passed in 19.07s from a pristine independent clone of the final head at /tmp/coga-context-peer-reconciled-9i5tskhj/repo.
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m coga.validate --json > /tmp/coga-context-audiences-peer-reconciled-validate.json
  status: passed
  head: aa422de4da092149ae0925f69ee96c21b26ec43a
  base: 94fad92944fe829f4c233fa3cb0f56d883748097
  detail: 'Repository: 123 OK, 46 warnings (20 stuck in progress, 18 unfrozen workflows, 7 empty descriptions,
    1 large blackboard), 0 errors. Read-only validation module avoids publishing converted routine state
    before merge.'
- command: env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python
    -m coga.validate --json > /tmp/coga-context-audiences-peer-reconciled-fixture-validate.json
  status: passed
  head: aa422de4da092149ae0925f69ee96c21b26ec43a
  base: 94fad92944fe829f4c233fa3cb0f56d883748097
  detail: 'Seeded fixture: 4 OK, no issues. Ran from tests/fixtures/seeded-repo/coga.'
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python /tmp/coga-context-audiences-peer-audit.py
  status: passed
  head: aa422de4da092149ae0925f69ee96c21b26ec43a
  base: 94fad92944fe829f4c233fa3cb0f56d883748097
  detail: 80 classification rows yield 61 shipped user and 24 local development topics. All topic names,
    user twins and changed-ticket context attachments resolve; 89 protected headers differ only in contexts,
    9 historical PR records remain identical to control, and 6 runtime modules have unchanged executable
    ASTs. All 295 diff paths are accounted for.
- command: git diff --check origin/main...HEAD
  status: passed
  head: aa422de4da092149ae0925f69ee96c21b26ec43a
  base: 94fad92944fe829f4c233fa3cb0f56d883748097
  detail: Passed on the final committed diff.
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python /tmp/coga-context-peer-freshness.py
  status: passed
  head: aa422de4da092149ae0925f69ee96c21b26ec43a
  base: 94fad92944fe829f4c233fa3cb0f56d883748097
  detail: 'Publication freshness probe passed against control 94fad92944fe829f4c233fa3cb0f56d883748097:
    HEAD contains latest origin/main'
- command: python3.11 -m pytest
  status: not-run
  detail: The implementation handoff reports that the available Python 3.11 interpreter lacks the test
    dependencies. Executed checks used Python 3.12.12; no Python 3.11 verification is claimed.
```
