---
title: 02 Move Coga-dev contexts out of the shipped set
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
step: 2 (peer-review)
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

branch: context-audiences-split

## Implement handoff

Implemented the owner-approved classification without changing its decisions.
All 78 original rows and both user topics added by main are accounted for:
61 user topics ship, 24 Coga-dev topics stay local. The decision table records
the two additions from PR #1068 under its existing shipped-consumer rule. Mixed topics are cut as specified; local-only topics have
no package copies. Namespace, wheel, local-first resolution, twin, shipped
dependency, and Markdown target/anchor checks enforce the boundary.

The owner requested checking and fixing broken refs. Updated source citations,
skills, workflows, recurring instructions, ticket attachments and contexts,
fixtures, README/AGENTS, and the docs index. Also repaired the blocker-reminder
contract link and the parked-ticket index's retired-task anchor. The release
note lists all renamed/de-packaged refs. The empty manifesto directory is gone.
All 11 structured historical PR records match control exactly: their diff
paths and receipts describe recorded commits, not live context dependencies.
Protected ticket frontmatter is unchanged except contexts; the rebase preserved
the concurrent pin-control ticket's new status and agent assignment.
Reconciliation also preserved PR #1068's checkout preparation, chat/manual
topics, source-map additions, and publication provenance instructions. This
session began under the earlier launch protocol without a Checkout (runtime)
notice; it created and published its branch record before switching.

### Coordinated conversion and next step

This branch includes mechanical stored-ticket reference migration under
`coga-dev/internals/git-regressions`, “Shipping a stored-ticket schema
conversion”: merge the topics and their consumers together. The current
ticket's own state is published separately and is not implementation diff.
Refresh the conversion from current main before merge, preserve newer task
state, and follow that procedure's writer/installation coordination.

Do not run a sweeping Coga command with the converted routine-state working
copies: it would publish the refs before the topics land. For this handoff,
after committing, testing and pushing, all changed `coga/tasks/` and
`coga/recurring/` working copies were restored from fresh `origin/main` and
verified byte-identical to it; the converted versions remain in commit
`15fa204c9a78aab65ce10eb6ca39f15719572e8a`. The current ticket was then loaded from control and this handoff
written. The launcher can discard the already-published routine-state dirt
and return to main. Repeat that protection if a later step checks out the
conversion branch and needs a lifecycle command; never drop the committed
conversion or publish it early to silence a gate.

The full suite passed 3,945 tests with 7 Windows-only skips at
`217f0028488f5c7d3fa3e232c7d57b6cdbd77b9d`. The final rebase only
updated routine state; later edits corrected two local development link
labels and preserved historical PR records. Runtime/resources and test
trees remain byte-identical. Fresh focused tests, validation, and the reference audit cover the final
head. A pristine-clone wheel check verified the identical package/resource
tree before the last routine-ticket-only rebase. The receipts
below retain their actual tested OIDs; the full-suite receipt is historical.

Independent code review has not run and no PR is open. The next workflow
step owns peer review. No unresolved implementation blocker was found.

## PR

```yaml
title: Separate shipped user contexts from Coga development guidance
author: codex
author_evidence: This attended implementation session used Codex (GPT-6), overriding the ticket’s configured
  Claude agent.
head: 15fa204c9a78aab65ce10eb6ca39f15719572e8a
base: bfacdea86d72007aaf5bf24f9cff54101a54adc8
depth: deep
rationale: Broad context/package migration with coordinated stored-ticket ref changes; independent peer
  review is the next step.
implementation: 'Implements all 78 original approved rows plus the two user topics added by current main:
  61 shipped user topics and 24 local Coga-dev topics. Splits mixed contracts, migrates consumers and
  ticket contexts, audits links and anchors, enforces namespace and wheel boundaries, and documents the
  clean break.'
deviations: 'No audience decisions changed; PR #1068 added dev/checkouts/chat and dev/checkouts/manual,
  both user topics by the approved shipped-consumer criterion. Stored-ticket ref conversion travels with
  the topics under the existing coordinated-conversion procedure; lifecycle fields and titles are preserved.
  Two already-broken context links were repaired during the requested audit.'
limitations: Tests use Python 3.12.12; the available Python 3.11 interpreter lacks the test dependencies
  and was not verified. Old spellings remain as migration history in the approved decision and release
  note, in historical PR receipts, in immutable audit history, in one human-owned parked-ticket title,
  and in the legacy gitignore-cleanup path literal (not a context dependency). Archives were not read
  or edited.
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
  coga/tasks/_v2/fail-validation-when-local-user-is-required-for-ex.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
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
  coga/tasks/adjudicate-the-eight-premise-dead-v2-drafts.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
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
  coga/tasks/dream-s-own-blackboard-trips-large-blackboard-ever.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
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
  coga/tasks/gigantic-refactor-move-recurring-recipes-out-of-co.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/implement-the-include-allowlist-that-url-skill-upd.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/interview-the-owner-on-the-17-title-only-v2-stubs.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/keep-multiline-audit-messages-on-one-log-line.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/launch-locks/checkout-exclusivity-lock/design.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/launch-locks/checkout-exclusivity-lock/ticket.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/launch-locks/ticket-ownership-lock/design.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/launch-locks/ticket-ownership-lock/ticket.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/launch-moves-the-checkout-to-main-before-and-after.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/let-the-autofix-generator-attach-repo-default-contexts.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/lifecycle-writes-read-control-s-ticket-before-modi.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/marketing/demo-hackability-ask-claude-to-add-a-command-live.md: Migrate live context refs;
    preserve lifecycle and historical PR receipts.
  coga/tasks/marketing/fix-installer/affordable-macos-testing-on-owned-macs-and-per-min.md: Migrate live
    context refs; preserve lifecycle and historical PR receipts.
  coga/tasks/marketing/fix-installer/test-install-on-windows.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/marketing/publish-coga-1-0-as-the-final-v1-step.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/marketing/readme-top.md: Migrate live context refs; preserve lifecycle and historical PR
    receipts.
  coga/tasks/marketing/state-the-hatchling-prerequisite-in-the-clean-whee.md: Migrate live context refs;
    preserve lifecycle and historical PR receipts.
  coga/tasks/match-concurrent-codex-sessions-to-their-launch-so.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/microkernel/README.md: Migrate live context refs; preserve lifecycle and historical PR receipts.
  coga/tasks/microkernel/launch-decomposition.md: Migrate live context refs; preserve lifecycle and historical
    PR receipts.
  coga/tasks/microkernel/lifecycle-verbs-to-ticket-operations.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/microkernel/move-retire-to-a-command-ticket.md: Migrate live context refs; preserve lifecycle
    and historical PR receipts.
  coga/tasks/microkernel/read-report-commands-as-ticket-workflows.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/microkernel/residual-command-surfaces.md: Migrate live context refs; preserve lifecycle and
    historical PR receipts.
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
  coga/tasks/pin-control-inside-the-state-lock-during-checkout.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/premise-check-2026-w39-25-parked-drafts-need-a-ver.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/premise-check-2026-w40-8-parked-drafts-need-a-verd.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/prevent-duplicate-session-usage-records-from-infla.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
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
  coga/tasks/run-recurring-agent-templates-off-the-control-bran.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
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
  coga/tasks/windows-native/core-port-cli-and-test-suite-pass-on-native-window.md: Migrate live context
    refs; preserve lifecycle and historical PR receipts.
  coga/tasks/windows-native/interactive-coga-launch-on-native-windows.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  coga/tasks/windows-native/pr-ci-with-linux-and-windows-test-jobs.md: Migrate live context refs; preserve
    lifecycle and historical PR receipts.
  docs/README.md: Update audience guidance and links to the correct topic owners.
  docs/contexts/coga-dev/archive-access/SKILL.md: Keep Coga development knowledge in the local-only audience.
  docs/contexts/coga-dev/codebase/SKILL.md: Keep Coga development knowledge in the local-only audience.
  docs/contexts/coga-dev/codebase/gotchas/SKILL.md: Keep Coga development knowledge in the local-only
    audience.
  docs/contexts/coga-dev/current-direction/SKILL.md: Keep Coga development knowledge in the local-only
    audience.
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
  docs/contexts/coga/recurring/templates/SKILL.md: Keep user facts and navigation at the approved ref.
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
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/SKILL.md: Ship the canonical
    user topic byte-for-byte.
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
  reviewer: none
  kind: none
  status: not-run
  detail: Implementation step only; independent peer-review follows this handoff. No subagents or nested
    reviewer were run.
checks:
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest
  status: passed
  head: 217f0028488f5c7d3fa3e232c7d57b6cdbd77b9d
  base: 90c7ee837ece99d77cfe255f0e4a6e9b36096d2f
  detail: 3945 passed, 7 skipped in 354.42s on Python 3.12.12. Seven skips require native Windows (2 job-object
    and 5 PowerShell checks). Historical revision before routine-state reconciliation and two local link-label
    fixes; runtime/resources and test trees are identical to the final head.
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest tests/test_packaging.py tests/test_compose.py
    tests/test_dream_worker_templates.py tests/test_edge_distribution.py -q --tb=short
  status: passed
  head: 15fa204c9a78aab65ce10eb6ca39f15719572e8a
  base: bfacdea86d72007aaf5bf24f9cff54101a54adc8
  detail: 158 passed in 19.89s after the final state-only rebase. Covers namespace isolation, resolver
    fallbacks, wheel contents, twins, navigation targets/anchors, composition, fixture contracts, and
    edge distribution.
- command: PYTHONPATH=/tmp/coga-audiences-handoff-pristine-1779cqsq/repo/src /home/n/Code/codex/coga/.venv/bin/python
    -m pytest tests/test_packaging.py::test_wheel_includes_bootstrap_batteries -q --tb=short
  status: passed
  head: 140cbeafc72c0e19f08e0bd1c3a78cdbfc73de7e
  base: 00b22b5e148a186ab98a66956f5b85302644260a
  detail: 1 passed in 1.35s from a pristine independent clone at /tmp/coga-audiences-handoff-pristine-1779cqsq/repo.
    This precedes only the last routine-ticket update; source/resources and tests are byte-identical.
- command: PYTHONPATH=/home/n/Code/codex/coga/src coga validate --json
  status: passed
  head: 15fa204c9a78aab65ce10eb6ca39f15719572e8a
  base: bfacdea86d72007aaf5bf24f9cff54101a54adc8
  detail: 'Repository: 123 OK, 45 warnings (20 stuck in progress, 18 unfrozen workflows, 7 empty descriptions),
    0 errors.'
- command: env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python
    -m coga.cli validate --json
  status: passed
  head: 15fa204c9a78aab65ce10eb6ca39f15719572e8a
  base: bfacdea86d72007aaf5bf24f9cff54101a54adc8
  detail: 'Seeded fixture: 4 OK, no issues. Ran from tests/fixtures/seeded-repo/coga; optional Slack webhook
    removed for deterministic fixture validation.'
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python /tmp/coga_audiences_audit.py
  status: passed
  head: 15fa204c9a78aab65ce10eb6ca39f15719572e8a
  base: bfacdea86d72007aaf5bf24f9cff54101a54adc8
  detail: No old live refs; 80 classification rows produce 61 user and 24 dev topics; protected fields
    unchanged in 88 tickets/templates; 11 structured historical PR records match control exactly; 27 additional
    context links resolve; runtime/resources and test tree OIDs match the full-suite revision.
- command: git diff --check
  status: passed
  head: 15fa204c9a78aab65ce10eb6ca39f15719572e8a
  base: bfacdea86d72007aaf5bf24f9cff54101a54adc8
  detail: Passed on the clean implementation tree before handoff publication.
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest
  status: not-run
  detail: 'Not repeated on the final OID: subsequent changes are routine ticket/audit state and two local
    development-topic link labels. Runtime/resources and test tree OIDs match the recorded 3945-pass run.
    Fresh focused checks, root/fixture validation and the reference audit cover the reconciliation; the
    original full-suite receipt retains its actual OID.'
- command: python3.11 -m pytest
  status: not-run
  detail: The available Python 3.11 interpreter lacks the test dependencies. Executed checks used Python
    3.12.12; no 3.11 verification is claimed.
```
