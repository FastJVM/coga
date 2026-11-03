---
title: 01 Runtime compatibility for package-owned definitions
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
step: 3 (open-pr)
agent: claude
launch_generation: pending:33e27d72-6aea-493b-8b62-1a2616827f8b
---

## Description

Stage A of the package-owned definitions split (see the group README for
the goal and full design). Land runtime compatibility so `src/coga/resources/`
can become the single committed source of shipped definitions, while this
repo keeps every existing live definition. Stage B
(`v1/package-definitions/02-repo-cutover-to-package-owned-definitions`)
performs the removals and depends on this ticket being merged and in use.

### Stage A scope

**A — runtime compatibility and deletion-tolerant checks.** Land the catalog,
selection/carrier support, dependency fallbacks, init changes and reader/writer
updates first. Keep this repo's existing live definitions during this stage.
Move package seed refs as in README section 1 while keeping their live resolutions valid.
Update owning topics and links to their eventual package owners now. Commit
topic, skill and workflow changes that belong to A with its source before
any sweeping command, following the existing checkout contract.

**Pre-A publication boundary (evaluator P1 disposition):** keep this repo's
live recurring definitions and every definition sibling unchanged throughout
A, including scripts and runbooks. Ordinary mutable blackboard/worklist
updates remain ordinary published state. Committing a live recurring edit
does not protect it from the sweep. Author required instruction/link changes
only in the packaged recurring files during A; enumerate each resulting
legacy-definition difference, its old bytes and reason in A's transitional
checks. Phone-home's separate comparison must distinguish these reviewed
definition differences from its preserved complete mutable state. Do not
use a blanket recurring-directory exemption. B removes or converts these
legacy files only after A is merged and installed; it does not backport A's
new instructions into live parents before that boundary.

Update Dream's scans and hard-coded live-path consumers before deleting their
inputs. For any change inside a live recurring definition or attachment,
the packaged update takes effect after cutover; A's compatibility must still
support the unchanged live version. No source-root, provenance or publication
guard changes are part of this boundary.

A's packaging policy is deliberately transitional: package resources are
required; legacy counterparts are optional and, when present as definitions,
still checked for approved equality/divergence. Recognized state carriers are
validated as state. Remove the twin-count floor, mandatory canonical-context
existence, and phone-home's mandatory live-definition assertion; retain
required resources, seed-zero checks and the local-only audience prohibition.
Record the exact legacy removal inventory so this temporary allowance cannot
silently grow. Navigation resolves actual package paths and remains valid
with any removable counterpart absent. Tests/harnesses that open live skills,
workflows or parents must also tolerate removal. These checks must actually
be on control, not merely in the later branch.

### Acceptance criteria

- [ ] Shipped contexts, skills and their attachments, workflows, bootstrap
  tickets, recurring definitions/scripts/runbooks, and prompt resources each
  have one committed package owner, with only one packaged definition per
  logical ref. Required-resource checks prevent deleting both copies from
  becoming a vacuous pass. All `coga-dev/` files remain local-only. (Stage B
  enforces that this repo has no undeclared live counterparts.)
- [ ] Every removed live definition resolves through the installed package in
  both editable and fresh-wheel installations. Local overrides win by ref;
  malformed/unreadable overrides fail visibly without selecting stock text.
  Agent skill discovery and workflow freezing use the same effective refs.
- [ ] All nine currently bundled parents (`autoclose-merged`, `branch-sweep`,
  `blocker-reminders`, `dream`, `phone-home`, `skill-update`,
  `address-pr-comments`, `resolve-conflicts`, `trim-log`) work without local definition
  tickets. Listing/status, validation, due scans, clone scans and named launch
  agree on selection, definition source and dependencies.
- [ ] Package-backed recurring runs read/write only repo-owned parent state,
  worklists, period tasks and shared log, or clone-local ledgers/logs. Repeated
  and interleaved updates preserve unrelated blackboard keys, phone-home's
  complete `period_state`, snapshots, retirement records and CAS safeguards.
  A state-only local directory/file never shadows a package definition.
- [ ] Override boundaries include scripts and supporting files: no silent
  mixture of a local job body with a packaged `ticket.py`. Repo-specific jobs
  and attachments survive. Existing frozen workflows, period bodies,
  delegates and copied scripts are not regenerated during upgrade/migration;
  old state snapshots and legitimate unfinished periods remain usable.
- [ ] Existing repos with no new selection file retain local-only recurring
  activation. Deleted or `_name`-parked jobs do not reappear. Explicitly
  disabled jobs stay disabled under sweeps, `--force` and named recurring
  launch. Adding a bundled job in a package upgrade does not enable it in an
  existing repo. Fresh-init defaults follow the owner decision at review.
- [ ] Fresh init copies only approved scaffolds and real initial state. It
  creates no reusable shipped definitions in live roots. Clone setup and
  package upgrades never overwrite customization, reseed state, or recreate
  removed definitions. A documented operator migration and rollback runbook
  (rehearsed on this repo by stage B) preserves old seeds, customized
  overrides, parked jobs and saved state.
- [ ] Before compatibility merges, its ordinary handoff sweep leaves live
  recurring definitions and their supporting files unchanged on pre-A
  control while publishing ordinary ticket/state updates. Run pre-A
  control's own packaging, navigation and representative runtime checks;
  stage A's imports or relaxed checks cannot stand in for this evidence.
- [ ] Build the verification wheel from a pristine disposable clone and run
  installed-artifact smoke tests outside the editable source path. Cover all
  resource types and all nine parents with outward effects stubbed; compare
  package-resource bytes before/after and exercise read-only resources.
- [ ] The owning topics, `AGENTS.md`, indexes, shipped instructions and local
  development links describe the new ownership and navigation. Context-link
  validation reads the actual package tree. The relevant tests, seeded-repo
  validation and full suite pass after reconciliation with current main.
- [ ] This repo's live recurring definitions, their siblings and all other
  live counterparts remain present and valid on control after merge; the
  exact legacy removal inventory and every enumerated legacy-definition
  difference are recorded in the transitional checks for stage B.

## Context

### Read first

The shared design contract and verified source context live in
[the group README](README.md) (`coga/tasks/v1/package-definitions/README.md`):
"Shared design" sections 1–4 and 6, "Out of scope", and "Context". Read it
in full before planning; it is not composed into this prompt. Update the
README's design in the same PR when this stage changes the contract.

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

branch: coga/package-definitions-01-runtime-compat

## PR

```yaml
title: Resolve shipped definitions from the package with recurring selection and state carriers (stage A)
author: claude/codex
author_evidence: Claude Code (claude-opus-5-5) implemented the feature. The prior Codex peer-review independently
  reviewed Claude's implementation and authored four review-fix commits. This resumed Codex session reviewed the
  reconciled diff directly and made no implementation changes; review remains conservatively labeled self because
  Codex authored the fixes.
head: 13da855da42dcf27bb29527875ce7ab956b96eb7
base: 876f8b00453449cb748d5fd38e05b1963ddffd7c
depth: deep
rationale: 'Review the diff: this changes definition resolution, initialization, recurring admission and shared-state
  publication across 162 paths. Tests cover compatibility and removal, but these contracts and the proposed fresh-init
  defaults warrant owner review.'
implementation: Resolve reusable definitions from one package location, preserving deliberate local overrides. Use
  an explicit jobs.toml recurring selection and validated repo-owned state carriers; atomically publish first-use
  state with the period/ledger. Keep discovery, launch, validation, worklists and state writers consistent. Initialize
  only approved scaffolds. Pin package resources and the exact legacy-removal inventory, tolerate valid carriers,
  audit package navigation, and document migration/rollback. Retention validates carrier siblings and rechecks package
  script bytes during publication retries.
deviations: Stage A retains all live counterparts and preserves live recurring instructions/siblings byte-for-byte.
  The existing seeded fixture continues to exercise pre-upgrade local-only activation; new catalog/init/wheel tests
  exercise selection. The group README contract is unchanged. Stage B owns the actual repository cutover.
limitations: Fresh init selects all nine bundled jobs as proposed in the group README; the owner must decide that
  default at review. Codex authored and reviewed the fixes; no separate reviewer identity is claimed. Live external
  services and native Windows/macOS were not exercised; outward effects were stubbed. Verification uses Python 3.12.12;
  the available Python 3.11 interpreter lacks the test dependencies. Repository-wide validation has existing ticket-state
  findings and an expected webhook warning with notification variables removed, disclosed below. Stage B owns the
  real control migration and rollback rehearsal.
files:
  AGENTS.md: Describe single package ownership and the stage A transitional checks.
  CONTRIBUTING.md: Links point at package owners instead of removable legacy copies.
  README.md: Links point at package owners instead of removable legacy copies.
  coga/skills/code/implement/SKILL.md: Link package owners; match packaged copy.
  coga/skills/code/open-pr/SKILL.md: Link package owners; match packaged copy.
  coga/skills/code/peer-review/SKILL.md: Link package owners; match packaged copy.
  coga/skills/code/self-qa/SKILL.md: Link package owners; match packaged copy.
  coga/skills/coga/releasing/SKILL.md: Link package owners; match packaged copy.
  coga/skills/coga/show/SKILL.md: Link package owners; match packaged copy.
  coga/skills/coga/testing/clean-install/SKILL.md: Link package owners; match packaged copy.
  coga/skills/coga/testing/clean-install/macos-aws/SKILL.md: Link package owners; match packaged copy.
  coga/skills/coga/testing/clean-install/windows-aws/SKILL.md: Link package owners; match packaged copy.
  coga/skills/coga/ticket/finalize/SKILL.md: Link package owners; match packaged copy.
  docs/README.md: Link package owners; index the package-definitions release note.
  docs/contexts/coga-dev/archive-access/SKILL.md: Link package owners.
  docs/contexts/coga-dev/codebase/SKILL.md: Update development guidance and owner links.
  docs/contexts/coga-dev/codebase/gotchas/SKILL.md: Link package owners.
  docs/contexts/coga-dev/current-direction/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/activity-capture/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/agent-config/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/agent-spawn/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/assist-publication/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/blackboard-io/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/branch-sweep/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/claim-recovery/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/compose/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/git-refresh/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/git-regressions/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/launch-claims/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/notifications/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/recurring-admission/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/recurring-autofix/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/recurring-clone/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/recurring-control/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/spool-merge/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/state-publication/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/state-publication/log-writers/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/state-publication/publish/SKILL.md: Link package owners.
  docs/contexts/coga-dev/internals/usage-pricing/SKILL.md: Link package owners.
  docs/contexts/coga-dev/microkernel/SKILL.md: Link package owners.
  docs/contexts/coga-dev/packaging/SKILL.md: Update development guidance and owner links.
  docs/contexts/coga-dev/testing/SKILL.md: Update development guidance and owner links.
  docs/contexts/coga/architecture/SKILL.md: Document package ownership and state.
  docs/contexts/coga/blackboard/SKILL.md: Document package ownership and state.
  docs/contexts/coga/cli/SKILL.md: Document package ownership and state.
  docs/contexts/coga/configuration/SKILL.md: Document package ownership and state.
  docs/contexts/coga/context-layout/SKILL.md: Document package ownership and state.
  docs/contexts/coga/edge-code/SKILL.md: Document package ownership and state.
  docs/contexts/coga/edge-code/edge-code-upgrades.md: Upgrade carriers by selecting the package; keep full local
    overrides explicit.
  docs/contexts/coga/init/SKILL.md: Document package ownership and state.
  docs/contexts/coga/install/SKILL.md: Document package ownership and state.
  docs/contexts/coga/knowledge/SKILL.md: Document package ownership and state.
  docs/contexts/coga/notifications/producers/SKILL.md: Document package ownership and state.
  docs/contexts/coga/period-task/SKILL.md: Document package ownership and state.
  docs/contexts/coga/prompt-composition/SKILL.md: Document package ownership and state.
  docs/contexts/coga/recurring/SKILL.md: Document package ownership and state.
  docs/contexts/coga/recurring/scheduling/SKILL.md: Document package ownership and state.
  docs/contexts/coga/recurring/templates/SKILL.md: Document package ownership and state.
  docs/contexts/coga/script-tickets/SKILL.md: Document package ownership and state.
  docs/contexts/coga/skill-management/SKILL.md: Document package ownership and state.
  docs/contexts/coga/state-publication/SKILL.md: Document package ownership and state.
  docs/contexts/coga/usage/SKILL.md: Document package ownership and state.
  docs/release-notes/audit-retention.md: Describe selection-based adoption and link the packaged runbook.
  docs/release-notes/package-definitions.md: 'Release note: package ownership, selection, carriers, migration.'
  src/coga/agent_skills.py: Reject incomplete local overrides before exposing bundled agent skills.
  src/coga/checkout_policy.py: An invalid override makes the step manual instead of raising.
  src/coga/commands/init.py: Report invalid skill overrides cleanly during clone setup.
  src/coga/commands/recurring.py: Show effective origin/selection, wrap rows and print complete refusals/errors
    below the table.
  src/coga/commands/update.py: Fresh init copies only the reviewed scaffold allowlist and writes the one-time jobs.toml
    selection.
  src/coga/compose.py: Report an invalid local skill override as an unresolved skill with its reason.
  src/coga/create.py: Skill checks treat invalid overrides as unresolved.
  src/coga/launch.py: Refuse a launch when agent discovery finds an invalid local override.
  src/coga/log_publication.py: Pin recurring/jobs.toml with the retention decision inputs.
  src/coga/paths.py: Add LocalOverrideError/local_definition_entry and skill_unresolved; an unusable local skill
    override fails instead of selecting the package copy.
  src/coga/recurring.py: Resolve effective recurring sources, explicit selection, parked/disabled jobs and repo
    state; fail on broken selection links.
  src/coga/recurring_runner.py: Use selected definitions and repo state; publish a new carrier atomically with its
    first period and ledger.
  src/coga/recurring_state.py: Classify state carriers and overrides; initialize state under the shared lock without
    reseeding.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md: Document package ownership and
    state.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md: Document package ownership and
    state.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: Document package ownership and state.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md: Document package ownership and
    state.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/context-layout/SKILL.md: Document package ownership
    and state.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/SKILL.md: Document package ownership and state.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/edge-code-upgrades.md: Ship the carrier-aware
    upgrade procedure.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: Document package ownership and state.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md: Document package ownership and state.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/knowledge/SKILL.md: Document package ownership and state.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/producers/SKILL.md: Document package ownership
    and state.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/period-task/SKILL.md: Document package ownership and
    state.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md: Document package ownership
    and state.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md: Document package ownership and state.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: Document package ownership
    and state.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/SKILL.md: Document package ownership
    and state.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/package-definitions-migration.md: Document
    package ownership and state.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md: Document package ownership
    and state.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/skill-management/SKILL.md: Document package ownership
    and state.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md: Document package ownership
    and state.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/usage/SKILL.md: Document package ownership and state.
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/contract-audit/SKILL.md: Dream audits
    package source in the source repo and replaces the twin-divergence shard with the single-source check.
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/knowledge-scan/SKILL.md: Dream audits
    package source in the source repo and replaces the twin-divergence shard with the single-source check.
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/scan-protocol/SKILL.md: Dream audits package
    source in the source repo and replaces the twin-divergence shard with the single-source check.
  src/coga/resources/templates/coga/bootstrap/skills/code/implement/SKILL.md: Link package owners.
  src/coga/resources/templates/coga/bootstrap/skills/code/open-pr/SKILL.md: Link package owners.
  src/coga/resources/templates/coga/bootstrap/skills/code/peer-review/SKILL.md: Link package owners.
  src/coga/resources/templates/coga/bootstrap/skills/code/self-qa/SKILL.md: Link package owners.
  src/coga/resources/templates/coga/bootstrap/skills/coga/releasing/SKILL.md: Link package owners.
  src/coga/resources/templates/coga/bootstrap/skills/coga/show/SKILL.md: Link package owners.
  src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/SKILL.md: Link package owners.
  src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/macos-aws/SKILL.md: Link package
    owners.
  src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/windows-aws/SKILL.md: Link package
    owners.
  src/coga/resources/templates/coga/bootstrap/skills/coga/ticket/finalize/SKILL.md: Link package owners.
  src/coga/resources/templates/coga/bootstrap/skills/direct/body/SKILL.md: Move the definition to its unique bootstrap
    owner.
  src/coga/resources/templates/coga/bootstrap/workflows/autoclose-merged/sweep.md: Move the definition to its unique
    bootstrap owner.
  src/coga/resources/templates/coga/bootstrap/workflows/blocker-reminders/run.md: Move the definition to its unique
    bootstrap owner.
  src/coga/resources/templates/coga/bootstrap/workflows/branch-sweep/sweep.md: Move the definition to its unique
    bootstrap owner.
  src/coga/resources/templates/coga/bootstrap/workflows/build/onboarding.md: Move the definition to its unique bootstrap
    owner.
  src/coga/resources/templates/coga/bootstrap/workflows/code/with-self-review.md: Links point at package owners
    instead of removable legacy copies (package copy and live twin kept identical).
  src/coga/resources/templates/coga/bootstrap/workflows/direct/body.md: Move the definition to its unique bootstrap
    owner.
  src/coga/resources/templates/coga/bootstrap/workflows/docs/with-review.md: Links point at package owners instead
    of removable legacy copies (package copy and live twin kept identical).
  src/coga/resources/templates/coga/bootstrap/workflows/phone-home/run.md: Move the definition to its unique bootstrap
    owner.
  src/coga/resources/templates/coga/bootstrap/workflows/skill-update/run.md: Move the definition to its unique bootstrap
    owner.
  src/coga/resources/templates/coga/bootstrap/workflows/trim-log/run.md: Move the definition to its unique bootstrap
    owner.
  src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.md: Packaged recurring definition links point
    at package owners (live definition unchanged; difference pinned).
  src/coga/resources/templates/coga/recurring/blocker-reminders/ticket.md: Packaged recurring definition links point
    at package owners (live definition unchanged; difference pinned).
  src/coga/resources/templates/coga/recurring/dream/ticket.md: Packaged recurring definition links point at package
    owners (live definition unchanged; difference pinned).
  src/coga/resources/templates/coga/recurring/phone-home/operations.md: Packaged recurring definition links point
    at package owners (live definition unchanged; difference pinned).
  src/coga/resources/templates/coga/recurring/phone-home/ticket.md: Packaged recurring definition links point at
    package owners (live definition unchanged; difference pinned).
  src/coga/resources/templates/coga/recurring/trim-log/operations.md: Packaged recurring definition links point
    at package owners (live definition unchanged; difference pinned).
  src/coga/resources/templates/coga/recurring/trim-log/ticket.md: Packaged recurring definition links point at package
    owners (live definition unchanged; difference pinned).
  src/coga/resources/templates/coga/skills/direct/body/SKILL.md: Move the definition to its unique bootstrap owner.
  src/coga/resources/templates/coga/workflows/autoclose-merged/sweep.md: Move the definition to its unique bootstrap
    owner.
  src/coga/resources/templates/coga/workflows/blocker-reminders/run.md: Move the definition to its unique bootstrap
    owner.
  src/coga/resources/templates/coga/workflows/branch-sweep/sweep.md: Move the definition to its unique bootstrap
    owner.
  src/coga/resources/templates/coga/workflows/build/onboarding.md: Move the definition to its unique bootstrap owner.
  src/coga/resources/templates/coga/workflows/direct/body.md: Move the definition to its unique bootstrap owner.
  src/coga/resources/templates/coga/workflows/phone-home/run.md: Move the definition to its unique bootstrap owner.
  src/coga/resources/templates/coga/workflows/skill-update/run.md: Move the definition to its unique bootstrap owner.
  src/coga/resources/templates/coga/workflows/trim-log/run.md: Move the definition to its unique bootstrap owner.
  src/coga/retire_worklist.py: A selected package-backed parent without a local ticket still owns its repo worklist.
  src/coga/tasks.py: Bootstrap ticket resolution reports an unusable local override (BootstrapOverrideError) instead
    of falling back.
  src/coga/validate.py: Recurring validation walks the effective catalog (selection errors, carriers, enabled package
    definitions); skill checks treat invalid overrides as unresolved.
  src/coga/views.py: Status footer counts only enabled (or errored) recurring jobs.
  src/coga_edge/phone_home.py: Obtain repo state through the shared resolver (parked parent, first-use carrier)
    and CAS its first publication.
  src/coga_edge/trim_log.py: Select jobs during adoption, validate carrier siblings and pin effective package script
    bytes during retention.
  tests/conftest.py: Seed direct/body from its bootstrap package path.
  tests/legacy_removal_inventory.txt: Pinned stage A legacy removal inventory (live copy -> package owner) for stage
    B.
  tests/test_address_pr_comments_skill.py: Read the required packaged skill after legacy removal.
  tests/test_autoclose_sweep.py: Use package fixtures and compare legacy definitions only while present.
  tests/test_compose.py: Packaged direct/body paths moved to bootstrap/.
  tests/test_dream_worker_templates.py: Read packaged topics and require package-aware Dream scans.
  tests/test_edge_distribution.py: Exercise package-backed fresh installs, explicit legacy installs and the packaged
    operations runbook.
  tests/test_git.py: 'Regression: the stage A handoff sweep publishes ordinary state but never definitions on real
    control/feature checkouts.'
  tests/test_init.py: 'Fresh init expectations: scaffolds plus jobs.toml, no definitions; package-backed Dream and
    phone-home seed.'
  tests/test_open_pr.py: Require the package owner and compare the live skill only while present.
  tests/test_packaging.py: Pin resource inventory, validate carriers, audit package navigation and smoke read-only
    installed wheels.
  tests/test_paths.py: Cover incomplete nested, dangling and unreadable local overrides.
  tests/test_recurring.py: Package paths moved to bootstrap/; incomplete-override expectation for a directory without
    ticket.md.
  tests/test_recurring_shims.py: Phone-home runs package-backed via selection; local install uses the moved workflow
    path.
  tests/test_recurring_state.py: Cover selection/refusal, first-use CAS publication/adoption races, direct state
    writes and narrow-terminal listing.
  tests/test_skill_update.py: Packaged workflow path moved to bootstrap/.
  tests/test_trim_log.py: Exercise carrier interleaving/parking/cursor races, package changes and idempotent adoption.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 13da855da42dcf27bb29527875ce7ab956b96eb7
  base: 876f8b00453449cb748d5fd38e05b1963ddffd7c
  detail: Direct review completed against the final head/base. Reviewed selection/override boundaries, carrier publication
    and retention guards, init, transitional packaging/navigation, and the subsequent README-only main changes.
    All nine feature patches remain unchanged across the rebases; no unresolved code findings or new implementation
    changes. Initial review was independent of Claude; Codex authored the fixes, so the overall receipt remains
    self-review. No nested reviewer or subagent ran.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q --basetemp=/tmp/coga-package-review-reconciled-full
    -p no:cacheprovider
  status: passed
  head: 13da855da42dcf27bb29527875ce7ab956b96eb7
  base: 876f8b00453449cb748d5fd38e05b1963ddffd7c
  detail: 4350 passed, 10 skipped in 571.65s on Python 3.12.12. Completed against this exact reconciled head in
    the ordinary-layout primary checkout; checkout identity stayed stable throughout.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q --basetemp=/home/n/Code/.coga-package-review-final-full
    -p no:cacheprovider
  status: passed
  detail: 4350 passed, 10 skipped in 623.35s on Python 3.12.12; stable ordinary-layout primary checkout.
  head: cfbb75410bf276ab4fe810c069912ffb55ecf710
  base: 53758fe388a1be3cc428f194843892ce175fea52
- command: PYTHONPATH=/tmp/coga-package-review-reconciled-artifact/src /home/n/Code/coga/.venv/bin/python -m pytest
    -q tests/test_packaging.py::test_wheel_includes_bootstrap_batteries tests/test_packaging.py::test_installed_wheel_init_and_phone_home_are_isolated
    -p no:cacheprovider --basetemp=/home/n/Code/.coga-package-review-reconciled-wheel
  status: passed
  detail: 2 passed in 5.05s. Built from a clean disposable Git clone at this exact head; wheel imports outside source,
    all resource types and nine parents, outward effects stubbed, read-only package resources unchanged.
  head: 13da855da42dcf27bb29527875ce7ab956b96eb7
  base: 876f8b00453449cb748d5fd38e05b1963ddffd7c
- command: .venv/bin/python /tmp/coga-package-review-reconciled-pre-a.py
  status: passed
  detail: 'Pre-A control 876f8b00453449cb748d5fd38e05b1963ddffd7c used its own publisher/imports/tests against this
    feature head. Ordinary ticket and complete phone-home state published; all 170 checked recurring definition/sibling,
    rollout and package-resource files unchanged. Control packaging/navigation, recurring shim, init, trim-log and
    autoclose suites: 249 passed in 30.09s.'
  head: 13da855da42dcf27bb29527875ce7ab956b96eb7
  base: 876f8b00453449cb748d5fd38e05b1963ddffd7c
- command: .venv/bin/python /tmp/coga-package-review-resumed-pty.py > /tmp/coga-package-review-reconciled-pty-output.txt
  status: passed
  detail: 'Reran on this head in actual 80x24 and 120x40 PTYs: enabled package jobs, disabled job and parked carrier;
    invalid selection at 80x24. Names, schedules, firing times and full remedies are visible. Long reasons follow
    the table. Listing wrote no state.'
  head: 13da855da42dcf27bb29527875ce7ab956b96eb7
  base: 876f8b00453449cb748d5fd38e05b1963ddffd7c
- command: git diff --check origin/main...HEAD; git diff --name-only origin/main...HEAD -- coga/recurring rollout
    coga/workflows coga/bootstrap
  status: passed
  detail: Whitespace clean. No branch diff in live recurring definitions/siblings, rollout, live workflows or bootstrap
    tickets. All 162 diff paths are explained. The last rebase changed only README wording from main; every source,
    test and protected resource byte is unchanged.
  head: 13da855da42dcf27bb29527875ce7ab956b96eb7
  base: 876f8b00453449cb748d5fd38e05b1963ddffd7c
- command: 'env -u SLACK_WEBHOOK_URL -u COGA_IMPORTANT_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/python
    -m coga.cli validate --json (cwd: tests/fixtures/seeded-repo/coga)'
  status: passed
  detail: ok_count 5; no issues, exit 0.
  head: 13da855da42dcf27bb29527875ce7ab956b96eb7
  base: 876f8b00453449cb748d5fd38e05b1963ddffd7c
- command: env -u SLACK_WEBHOOK_URL -u COGA_IMPORTANT_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src .venv/bin/python
    -m coga.cli validate --json
  status: failed
  detail: 'Exit 1; ok_count 95; 27 existing ticket findings: 6 stuck-in-progress, 14 unfrozen-workflow, 5 unsynthesized-draft-blackboard
    and 2 large-blackboard, plus 1 expected missing-important-webhook warning with notification variables removed.
    Pre-A control code produced identical findings on the same checkout state. No recurring/resource findings. This
    ticket is below the size warning threshold.'
  head: 13da855da42dcf27bb29527875ce7ab956b96eb7
  base: 876f8b00453449cb748d5fd38e05b1963ddffd7c
- command: env -u SLACK_WEBHOOK_URL -u COGA_IMPORTANT_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src .venv/bin/python
    -m coga.cli validate --task v1/package-definitions/01-runtime-compatibility-for-package-owned-definit --json
  status: passed
  head: 13da855da42dcf27bb29527875ce7ab956b96eb7
  base: 876f8b00453449cb748d5fd38e05b1963ddffd7c
  detail: Exit 0; ok_count 1; only the expected missing-important-webhook warning with notification variables removed.
    No task findings.
- command: PYTHONPATH=/tmp/coga-package-review-rer1uw26/cutover-complete/src /home/n/Code/coga/.venv/bin/python
    -m pytest -q -p no:cacheprovider --basetemp=/home/n/Code/.coga-package-review-cutover-full
  status: passed
  head: 5ce1c8a853a4a70915008e33e8b61e08881631ba
  base: bdffb5555d5757d766ebd1941e8bff313126ef2a
  detail: '4341 passed, 10 skipped in 774.46s. Full suite completed against this exact source head. Disposable clone:
    all 103 inventory entries removed or converted (95 removals; 8 carriers preserving complete blackboards); selection
    preserves prior activation. Historical receipt from the preceding session; retained on its actual head/base.
    All resumed rebases preserved the nine feature patches.'
```

## Implement handoff (Claude, 2026-11-03; summarized after review)

Claude implemented the catalog, selection, carriers, scaffold-only init, transitional
packaging policy and owner documentation. Original handoff: head `5fd175871afade4ff877aa9d7958f73179faf409`
on base `b8edf445fabb324e68433e1ceb5c1d37b9005325`; its full suite passed
4329 tests with 10 skipped. Those receipts are historical. The final PR record above
supersedes its coverage gaps: review added publication/adoption race, carrier writer,
package-script retry, invalid override and complete removal coverage. The proposed
all-nine fresh-init default still belongs to the owner review.

## Peer review

**Direct review completed (resumed Codex session, 2026-11-03).** Final head
`13da855da42dcf27bb29527875ce7ab956b96eb7`, base
`876f8b00453449cb748d5fd38e05b1963ddffd7c`. No unresolved code findings or new
implementation changes. Claude implemented the feature; the prior Codex session
independently reviewed it and then authored/self-reviewed the four fixes below.
This fresh Codex session reviewed the final reconciled diff; the record retains
`self` rather than inventing a distinct reviewer identity. No nested review or
subagent ran. Recommendation remains **deep**: definition resolution and shared-state
publication warrant inspection, and the owner must decide the all-nine init default.

Must-fix findings resolved:
- The first package-backed period omitted its new carrier from control publication.
  It now publishes carrier/period/ledger together with the absence CAS; tests cover
  feature/control creation, competing complete parent state and stale-period adoption.
- Agent discovery could expose stock instructions for an incomplete local override.
  It now shares override validation; unreadable/dangling/nested incomplete overrides fail.
- Carrier creation and direct state lookup needed shared locking and validation.
  Direct/parked writers preserve unrelated keys and complete phone-home state; alternating
  phone-home/trim-log and cursor-race coverage now runs with carriers too.
- Retention needed carrier-sibling checks and package-script identity in retry guards;
  adoption also remains idempotent after first state creation.
- Transitional checks rejected valid carriers and some tests/navigation still opened
  removable live definitions. They now validate state and use package owners; the full
  inventory removal rehearsal preserves all eight existing parent blackboards.
- A broken jobs.toml link silently restored local-only activation. Scans, force and
  named launch now refuse it visibly.
- The recurring table truncated names/times when reasons were long. Real 80x24 and
  120x40 PTYs now show readable rows plus full reasons below; invalid selections are
  also legible at 80x24. Listing remains read-only.

Verification receipts are in `## PR`. The final ordinary-layout suite passed
**4350 tests, 10 skipped in 571.65s** on Python 3.12.12. Earlier completed runs are
historical; the current receipt covers the exact reconciled head above. Pre-A control's
own publisher preserved 170 checked definition/resource files while publishing ordinary
ticket and complete phone-home state; its own suites passed 249 tests. The pristine-clone
wheel smoke passed for all resource types and nine parents with outward effects stubbed
and read-only resources unchanged. Actual 80x24 and 120x40 PTYs showed readable names,
schedules, times and full remedies, including invalid selection at 80x24; listing wrote
no state. Seeded validation passed; ticket-scoped validation has no task findings.
Repository-wide findings match pre-A control and are disclosed in the receipts.

Stage A changes no live recurring definition/sibling or rollout file. All 103 inventory
entries remain present; the 20 inventoried recurring/rollout files match control bytes.
Stage B owns the actual control migration and rollback rehearsal after A is merged and
installed. No code or review findings remain open; the all-nine init default remains an
explicit owner decision during PR review.

## Resumed verification and handoff

The human released this checkout from `v1/25-position-op-as-optional`; `coga unblock`
recorded the resolution before review resumed. Its draft edits were already published.
Rebased onto current main, then incorporated two subsequent README-only updates.
`git range-diff` confirms all nine feature patches unchanged across the three rebases.
The ticket projection was backed up and byte-verified around each rebase. No other task's
edits were changed; the CLI-maintained blocker history below preserves the interruption.

Review and verification are complete. Final branch head is `13da855da42dcf27bb29527875ce7ab956b96eb7`
on base `876f8b00453449cb748d5fd38e05b1963ddffd7c`, pushed with an explicit lease against
`5ce1c8a85`. The review handoff is published and the primary checkout has returned to
clean, current main. Ready for the single peer-review bump and the mechanical open-pr
step; no PR has been opened in this session.

---

## Blockers

- [x] [2026-11-03 13:31] [agent:codex] id=20261103T133150 Release /home/n/Code/coga from v1/25-position-op-as-optional, or relaunch this peer-review in an explicitly prepared clone. That launch switched the primary to main during verification and its draft edits remain unpublished. Review fixes are pushed at 5ce1c8a85; isolated cutover full suite passed 4341 tests with 10 skipped. Reconcile the preserved branch with current main and rerun the ordinary-layout full suite before bumping.
  resolved: [2026-11-03 14:40] [human:nicktoper] Human confirmed this checkout is released from v1/25-position-op-as-optional and authorized resuming peer review here. Verified a clean main checkout, the other ticket remains draft with edits published at c7417bb7f, no feature PR exists, and the preserved branch matches its remote at 5ce1c8a853a4a70915008e33e8b61e08881631ba. Reconcile with current main and rerun ordinary-layout full verification before advancing.
