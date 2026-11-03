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
step: 2 (peer-review)
agent: claude
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
author: claude
author_evidence: This implement session ran as Claude Code (claude-opus-5-5) under the megalaunch queue; no agent override.
head: 5fd175871afade4ff877aa9d7958f73179faf409
base: b8edf445fabb324e68433e1ceb5c1d37b9005325
depth: deep
rationale: Broad runtime change (recurring catalog, selection, state carriers, init, trim-log/phone-home state paths, packaging policy) across about 150 files; inspect the diff. Peer review has not run yet.
implementation: Package bootstrap roots own every reusable ref; resolvers fail on unusable local overrides; recurring.py adds an effective catalog with jobs.toml selection; recurring_state.py owns state-only carriers created once on first admitted run; scans, named launch, listing, validation, runner, worklists, phone-home and trim-log use it; fresh init copies only a scaffold allowlist plus a one-time jobs.toml; packaging tests apply the transitional inventory policy; owner docs, runbook and release note updated.
deviations: The group README (coga/tasks) is not edited on the branch to avoid a stranded ticket write; its contract still matches. The fresh-init default selects all nine jobs, pending the owner decision the README calls for.
limitations: No runner-level git test of package-backed create/sync/adoption races; interleaved phone-home/trim-log with a carrier is covered only by existing local-definition tests; trim-log retry guards pin jobs.toml but not a hash of the packaged script; seeded fixture has no jobs.toml.
files:
  AGENTS.md: "Describe single package ownership and the stage A transitional checks."
  CONTRIBUTING.md: "Links point at package owners instead of removable legacy copies."
  README.md: "Links point at package owners instead of removable legacy copies."
  coga/skills/code/implement/SKILL.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  coga/skills/code/open-pr/SKILL.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  coga/skills/code/peer-review/SKILL.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  coga/skills/code/self-qa/SKILL.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  coga/skills/coga/releasing/SKILL.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  coga/skills/coga/show/SKILL.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  coga/skills/coga/testing/clean-install/SKILL.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  coga/skills/coga/testing/clean-install/macos-aws/SKILL.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  coga/skills/coga/testing/clean-install/windows-aws/SKILL.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  coga/skills/coga/ticket/finalize/SKILL.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  docs/README.md: "Link package owners; index the package-definitions release note."
  docs/contexts/coga-dev/archive-access/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/codebase/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/codebase/gotchas/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/current-direction/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/activity-capture/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/agent-config/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/agent-spawn/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/assist-publication/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/blackboard-io/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/branch-sweep/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/claim-recovery/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/compose/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/git-refresh/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/git-regressions/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/launch-claims/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/notifications/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/recurring-admission/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/recurring-autofix/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/recurring-clone/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/recurring-control/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/spool-merge/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/state-publication/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/state-publication/log-writers/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/state-publication/publish/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/internals/usage-pricing/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/microkernel/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/packaging/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga-dev/testing/SKILL.md: "Local development guidance updated for package ownership, or links pointed at package owners."
  docs/contexts/coga/architecture/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  docs/contexts/coga/blackboard/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  docs/contexts/coga/cli/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  docs/contexts/coga/configuration/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  docs/contexts/coga/context-layout/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  docs/contexts/coga/edge-code/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  docs/contexts/coga/init/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  docs/contexts/coga/install/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  docs/contexts/coga/knowledge/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  docs/contexts/coga/notifications/producers/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  docs/contexts/coga/period-task/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  docs/contexts/coga/prompt-composition/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  docs/contexts/coga/recurring/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  docs/contexts/coga/recurring/scheduling/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  docs/contexts/coga/recurring/templates/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  docs/contexts/coga/script-tickets/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  docs/contexts/coga/skill-management/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  docs/contexts/coga/state-publication/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  docs/contexts/coga/usage/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  docs/release-notes/package-definitions.md: "Release note: package ownership, selection, carriers, migration."
  src/coga/checkout_policy.py: "An invalid override makes the step manual instead of raising."
  src/coga/commands/recurring.py: "recurring list shows origin/selection and summarizes unselected bundled jobs."
  src/coga/commands/update.py: "Fresh init copies only the reviewed scaffold allowlist and writes the one-time jobs.toml selection."
  src/coga/compose.py: "Report an invalid local skill override as an unresolved skill with its reason."
  src/coga/create.py: "Skill checks treat invalid overrides as unresolved."
  src/coga/log_publication.py: "Pin recurring/jobs.toml with the retention decision inputs."
  src/coga/paths.py: "Add LocalOverrideError/local_definition_entry and skill_unresolved; an unusable local skill override fails instead of selecting the package copy."
  src/coga/recurring.py: "Effective recurring catalog (TemplateSource, jobs.toml selection, parked/disabled/unselected), definition vs state paths on Template, first-use carrier initialization, scans/create/list on the catalog."
  src/coga/recurring_runner.py: "Named launch clone-scope probe, forced snapshots and template-damage checks use the selected definition; state stays repo-local."
  src/coga/recurring_state.py: "New shared module: state-only carrier shape, parent directory classification, parent_state_path and ensure_parent_state."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/context-layout/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/knowledge/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/producers/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/period-task/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/package-definitions-migration.md: "New operator migration and rollback procedure for existing repos."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/skill-management/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/usage/SKILL.md: "Owner topic (package copy and canonical twin) updated for package ownership, selection and carriers, or links pointed at package owners."
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/contract-audit/SKILL.md: "Dream audits package source in the source repo and replaces the twin-divergence shard with the single-source check."
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/knowledge-scan/SKILL.md: "Dream audits package source in the source repo and replaces the twin-divergence shard with the single-source check."
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/scan-protocol/SKILL.md: "Dream audits package source in the source repo and replaces the twin-divergence shard with the single-source check."
  src/coga/resources/templates/coga/bootstrap/skills/code/implement/SKILL.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  src/coga/resources/templates/coga/bootstrap/skills/code/open-pr/SKILL.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  src/coga/resources/templates/coga/bootstrap/skills/code/peer-review/SKILL.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  src/coga/resources/templates/coga/bootstrap/skills/code/self-qa/SKILL.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  src/coga/resources/templates/coga/bootstrap/skills/coga/releasing/SKILL.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  src/coga/resources/templates/coga/bootstrap/skills/coga/show/SKILL.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/SKILL.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/macos-aws/SKILL.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/windows-aws/SKILL.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  src/coga/resources/templates/coga/bootstrap/skills/coga/ticket/finalize/SKILL.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  src/coga/resources/templates/coga/skills/direct/body/SKILL.md: "Moved to the package bootstrap root so each reusable ref has one packaged definition (README section 1)."
  src/coga/resources/templates/coga/bootstrap/skills/direct/body/SKILL.md: "Moved to the package bootstrap root so each reusable ref has one packaged definition (README section 1)."
  src/coga/resources/templates/coga/workflows/autoclose-merged/sweep.md: "Moved to the package bootstrap root so each reusable ref has one packaged definition (README section 1)."
  src/coga/resources/templates/coga/bootstrap/workflows/autoclose-merged/sweep.md: "Moved to the package bootstrap root so each reusable ref has one packaged definition (README section 1)."
  src/coga/resources/templates/coga/workflows/blocker-reminders/run.md: "Moved to the package bootstrap root so each reusable ref has one packaged definition (README section 1)."
  src/coga/resources/templates/coga/bootstrap/workflows/blocker-reminders/run.md: "Moved to the package bootstrap root so each reusable ref has one packaged definition (README section 1)."
  src/coga/resources/templates/coga/workflows/branch-sweep/sweep.md: "Moved to the package bootstrap root so each reusable ref has one packaged definition (README section 1)."
  src/coga/resources/templates/coga/bootstrap/workflows/branch-sweep/sweep.md: "Moved to the package bootstrap root so each reusable ref has one packaged definition (README section 1)."
  src/coga/resources/templates/coga/workflows/build/onboarding.md: "Moved to the package bootstrap root so each reusable ref has one packaged definition (README section 1)."
  src/coga/resources/templates/coga/bootstrap/workflows/build/onboarding.md: "Moved to the package bootstrap root so each reusable ref has one packaged definition (README section 1)."
  src/coga/resources/templates/coga/bootstrap/workflows/code/with-self-review.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  src/coga/resources/templates/coga/workflows/direct/body.md: "Moved to the package bootstrap root so each reusable ref has one packaged definition (README section 1)."
  src/coga/resources/templates/coga/bootstrap/workflows/direct/body.md: "Moved to the package bootstrap root so each reusable ref has one packaged definition (README section 1)."
  src/coga/resources/templates/coga/bootstrap/workflows/docs/with-review.md: "Links point at package owners instead of removable legacy copies (package copy and live twin kept identical)."
  src/coga/resources/templates/coga/workflows/phone-home/run.md: "Moved to the package bootstrap root so each reusable ref has one packaged definition (README section 1)."
  src/coga/resources/templates/coga/bootstrap/workflows/phone-home/run.md: "Moved to the package bootstrap root so each reusable ref has one packaged definition (README section 1)."
  src/coga/resources/templates/coga/workflows/skill-update/run.md: "Moved to the package bootstrap root so each reusable ref has one packaged definition (README section 1)."
  src/coga/resources/templates/coga/bootstrap/workflows/skill-update/run.md: "Moved to the package bootstrap root so each reusable ref has one packaged definition (README section 1)."
  src/coga/resources/templates/coga/workflows/trim-log/run.md: "Moved to the package bootstrap root so each reusable ref has one packaged definition (README section 1)."
  src/coga/resources/templates/coga/bootstrap/workflows/trim-log/run.md: "Moved to the package bootstrap root so each reusable ref has one packaged definition (README section 1)."
  src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.md: "Packaged recurring definition links point at package owners (live definition unchanged; difference pinned)."
  src/coga/resources/templates/coga/recurring/blocker-reminders/ticket.md: "Packaged recurring definition links point at package owners (live definition unchanged; difference pinned)."
  src/coga/resources/templates/coga/recurring/dream/ticket.md: "Packaged recurring definition links point at package owners (live definition unchanged; difference pinned)."
  src/coga/resources/templates/coga/recurring/phone-home/operations.md: "Packaged recurring definition links point at package owners (live definition unchanged; difference pinned)."
  src/coga/resources/templates/coga/recurring/phone-home/ticket.md: "Packaged recurring definition links point at package owners (live definition unchanged; difference pinned)."
  src/coga/resources/templates/coga/recurring/trim-log/operations.md: "Packaged recurring definition links point at package owners (live definition unchanged; difference pinned)."
  src/coga/resources/templates/coga/recurring/trim-log/ticket.md: "Packaged recurring definition links point at package owners (live definition unchanged; difference pinned)."
  src/coga/retire_worklist.py: "A selected package-backed parent without a local ticket still owns its repo worklist."
  src/coga/tasks.py: "Bootstrap ticket resolution reports an unusable local override (BootstrapOverrideError) instead of falling back."
  src/coga/validate.py: "Recurring validation walks the effective catalog (selection errors, carriers, enabled package definitions); skill checks treat invalid overrides as unresolved."
  src/coga/views.py: "Status footer counts only enabled (or errored) recurring jobs."
  src/coga_edge/phone_home.py: "Obtain repo state through the shared resolver (parked parent, first-use carrier) and CAS its first publication."
  src/coga_edge/trim_log.py: "Accept a phone-home carrier with the packaged shim; adoption records selection plus attribute instead of copying definitions."
  tests/conftest.py: "Seed direct/body from its bootstrap package path."
  tests/legacy_removal_inventory.txt: "Pinned stage A legacy removal inventory (live copy -> package owner) for stage B."
  tests/test_autoclose_sweep.py: "Skip absent or pinned legacy copies; packaged workflow path moved."
  tests/test_compose.py: "Packaged direct/body paths moved to bootstrap/."
  tests/test_dream_worker_templates.py: "Contract-audit now documents the single-source ownership shard."
  tests/test_edge_distribution.py: "Installed-wheel tests start from a package-backed init; legacy full installs are modeled explicitly."
  tests/test_git.py: "Regression: the stage A handoff sweep publishes ordinary state but never definitions on real control/feature checkouts."
  tests/test_init.py: "Fresh init expectations: scaffolds plus jobs.toml, no definitions; package-backed Dream and phone-home seed."
  tests/test_packaging.py: "Transitional ownership checks: inventory, required owners, pinned legacy differences, package-relative navigation, pristine wheel build and read-only installed smoke for all nine parents."
  tests/test_recurring.py: "Package paths moved to bootstrap/; incomplete-override expectation for a directory without ticket.md."
  tests/test_recurring_shims.py: "Phone-home runs package-backed via selection; local install uses the moved workflow path."
  tests/test_recurring_state.py: "New coverage for selection, parking, carriers, incomplete forks, worklist/cache-only directories and invalid overrides."
  tests/test_skill_update.py: "Packaged workflow path moved to bootstrap/."
  tests/test_trim_log.py: "Adoption selects the job and preserves other selections; disabled selection is refused."
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Implement step; the workflow's peer-review step runs next with the other agent.
checks:
  - command: .venv/bin/python -m pytest -q --basetemp=/home/n/.cache/coga-pd-bt -p no:cacheprovider
    status: passed
    head: 5fd175871afade4ff877aa9d7958f73179faf409
    base: b8edf445fabb324e68433e1ceb5c1d37b9005325
    detail: 4329 passed, 10 skipped in 528.55s on the committed HEAD (clean tree apart from the projected ticket).
  - command: PYTHONPATH=<pre-A clone>/src python -m pytest tests/test_packaging.py tests/test_recurring_shims.py tests/test_init.py tests/test_trim_log.py tests/test_autoclose_sweep.py
    status: passed
    head: b8edf445fabb324e68433e1ceb5c1d37b9005325
    base: b8edf445fabb324e68433e1ceb5c1d37b9005325
    detail: Pre-A control b8edf445f in a disposable clone with its own imports; 249 passed.
  - command: coga validate --json
    status: passed
    head: 5fd175871afade4ff877aa9d7958f73179faf409
    base: b8edf445fabb324e68433e1ceb5c1d37b9005325
    detail: 25 pre-existing ticket-level findings (unfrozen-workflow 13, stuck-in-progress 6, unsynthesized-draft-blackboard 4, large-blackboard 2); none on recurring jobs or definitions.
  - command: env -u SLACK_WEBHOOK_URL -u COGA_IMPORTANT_WEBHOOK_URL coga validate --json (tests/fixtures/seeded-repo/coga)
    status: passed
    head: 5fd175871afade4ff877aa9d7958f73179faf409
    base: b8edf445fabb324e68433e1ceb5c1d37b9005325
    detail: ok_count 5, no issues.
```

## Implement handoff (claude, 2026-11-03)

Stage A has been implemented on `coga/package-definitions-01-runtime-compat` and pushed, in 6 commits on main b8edf445f.
This repo's live recurring definitions, their siblings, and `rollout/trim-log/` are byte-unchanged
(`git diff origin/main...HEAD -- coga/recurring rollout coga/workflows coga/bootstrap` is empty).

What landed:
- **One packaged definition per ref.** The seeded reusable workflows (`direct/body`, `build/onboarding`, the recurring
  workflows) and `skills/direct/body` moved into package `bootstrap/`. The old seed paths now hold only `_template` starters.
- **Resolvers.** `paths.local_definition_entry` / `LocalOverrideError`. An unusable local skill or bootstrap override
  (a non-file, a dangling link, or supporting files with no definition) fails instead of selecting stock text.
  `skill_unresolved` and `missing_skill_message` report the reason.
- **Recurring catalog** (`recurring.py`). `TemplateSource`, `iter_template_sources`, `resolve_template_source`,
  `read_job_selection` and `planned_job_selection` (tomlkit) read `coga/recurring/jobs.toml` (`[jobs] name = bool`).
  Selection semantics follow README section 2. `Template.path` is the definition; `Template.state_path` is the repo state.
  Scans, clone scans, `create_named`, `list_templates`, validation, the runner (named clone probe, forced snapshots,
  damage check), retire worklists, phone-home and trim-log all use the catalog.
- **Carriers** (`recurring_state.py`). Exact shape `---\n{}\n---\n<!-- coga:recurring-state -->\n\n<fence>`.
  - Classification: definition / carrier / state-only (`retires.md`) / incomplete. Empty or `__pycache__`-only
    directories count as absent.
  - `parent_state_path` handles parked parents and errors when both active and parked exist.
  - `ensure_parent_state` creates the carrier exclusively and once, on the first admitted repo-scoped run, behind
    `log_transaction.ensure_clear`. It never reseeds.
- **phone-home.** Gets its state through the resolver. It CASes the first publish with `expect=None`.
- **trim-log.** A carrier counts as compatible with the packaged shim, and a stray `ticket.py` beside it is refused.
  `jobs.toml` is pinned in `log_publication.read_inputs`. `install()` writes the selection plus the attribute rule, with
  no definition copies. It keeps the parked, fork and attribute refusals and refuses a `false` selection.
- **Init.** `FRESH_SCAFFOLDS` allowlist plus a one-time `jobs.toml` with all nine jobs set to `true`. Clone setup is unchanged.
- **Transitional packaging checks** (`tests/test_packaging.py`).
  - `tests/legacy_removal_inventory.txt` pins 103 removable live copies (98 derived plus the 5 staged trim-log files) to
    their package owners. `SCAFFOLD_COUNTERPARTS` holds the 6 physical files.
  - Removed: the twin-count floor, mandatory canonical contexts, and the mandatory live phone-home check.
  - Parent tickets compare only the text above the fence.
  - `LEGACY_DEFINITION_DIFFERENCES` pins 6 live definitions (sha256 of the text above the fence) whose packaged copies
    now link package owners.
  - Navigation is package-relative. Surviving sources may not link removable copies.
  - Wheels are built from a pristine copy of the tracked files (no duplicate archive paths). A read-only installed smoke
    test covers every resource type and all nine parents.
- **Docs.** Owner topics (init, recurring/templates with a new "Selection and state" section, scheduling, period-task,
  context-layout, knowledge, edge-code, skill-management) are updated in the package and mirrored to their twins.
  Also: the new package-only `recurring/templates/package-definitions-migration.md` runbook (migration plus rollback),
  `docs/release-notes/package-definitions.md`, AGENTS.md, `coga-dev/{packaging,testing,codebase}`, docs/README, and
  Dream's contract-audit/knowledge-scan/scan-protocol (single-source shard, package source scanned in this repo).
  About 90 links were repointed to package owners.
- **Tests.** `tests/test_recurring_state.py` (new) and the `test_git.py` stage A boundary regression, plus adapted
  init/trim-log/edge-distribution/recurring/shim/autoclose tests.

Pre-A control evidence: control b8edf445f was cloned to a disposable directory and run with its own `src`
(`PYTHONPATH`; it imported its own `coga`). `tests/test_packaging.py`, `test_recurring_shims.py`, `test_init.py`,
`test_trim_log.py` and `test_autoclose_sweep.py`: 249 passed.

For review / owner decision:
- **Fresh-init default.** It selects all nine bundled jobs, as the README proposes ("subject to owner approval").
  This is `FRESH_RECURRING_SELECTION` in `commands/update.py`.
- **Not done in A, left for B or follow-ups.** The seeded fixture has no `jobs.toml`; the catalog coverage lives in
  `test_recurring_state.py` instead. There are no runner-level git tests of package-backed create, sync and adoption
  races. Interleaved phone-home/trim-log runs with a carrier are covered only by the existing local-definition tests.
  The package script identity used by trim-log is not hashed into retry guards; only `jobs.toml` is pinned.
- `_parent_state` in phone-home reports `created=True` even if a concurrent writer won the exclusive create in the
  same instant. The publish CAS then refuses visibly, so this is not silent.
- The group README was not edited: it lives under `coga/tasks` and would strand on the branch.
  Its contract still matches, apart from the fresh-init default, which is pending owner approval.
- `coga validate --json` on this repo shows 25 pre-existing ticket-level findings (unfrozen-workflow 13,
  stuck-in-progress 6, unsynthesized-draft-blackboard 4, large-blackboard 2) and none on recurring jobs.
  The seeded fixture validates clean (Slack env unset).
- Peer review has not run. That is the next workflow step.

The blackboard is a notepad to be written to often as the human and agent works through a task.
