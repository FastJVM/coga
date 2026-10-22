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
step: 2 (peer-review)
agent: claude
launch_generation: 5ad97f0e-e3ab-486f-b337-1a925a0451c2
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

branch: coga/blocks-09-trim-setup-extension

## Handoff (implement)

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

- `.venv/bin/python -m pytest` on head 1b4a8c1: 3952 passed, 7 skipped,
  3 failed. 3 failures in
  `tests/test_packaging.py` are inherited from main (02's half-published
  `coga/code` deletion and architecture edit; twins only in PR #1081). In a
  scratch worktree, this branch merged with 02's branch (cli/usage twin
  conflicts resolved to the canonical copy) passes all 30 packaging tests.
- `coga validate --json`: exit 0, warnings only.

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

Expect conflicts with 01, 02, 04, 06, 07, 08 on shared files (packaged twins
of cli/usage/sandboxes/skill-management/configuration/init, microkernel,
current-direction, codebase, internals index). Resolve twins by copying the
canonical docs file after merging docs.

Most canonical `docs/` edits reached main through sweeps (e9a88b970 and
later), so the PR diff against main is mostly packaged twins plus AGENTS.md,
the usage-pricing split, and the internals index.

## PR

```yaml
title: Trim setup and extension topics to operator knowledge
author: claude
author_evidence: Implement session ran as Claude Code (Opus 5.5) under megalaunch; this handoff.
head: 1b4a8c1bbd4830c58a6fb469c31683ac05414e61
base: 51f430c10465cb816b1531ecb17828f8f2946655
depth: deep
rationale: Documentation-only, but main's packaging tests fail until blocks/02 (PR #1081) merges, and twins will conflict with sibling blocks PRs; review the twin resolution and the moved-content placement.
implementation: Applies the blocks/09 audit rows to configuration, context-layout, edge-code, extension-model, first-task, init, install, skill-management, sandboxes, usage, cli and uninstall; developer material moves to coga-dev codebase, packaging, microkernel, current-direction, internals/agent-spawn and new internals/usage-pricing; coga/cli owns the recipe and default-alias lists; AGENTS.md points there.
deviations: skill-management's legacy-digest paragraph was shortened in place rather than moved (operator-visible --pr effect). The Known PR checkout failure became draft ticket preflight-dirty-tracked-files-before-skill-update. Canonical docs edits mostly reached main through state sweeps, not this diff.
limitations: Three tests/test_packaging.py failures are inherited from main (blocks/02's coga/code deletion and architecture edit published without twins); they pass in a scratch merge with the 02 branch.
files:
  AGENTS.md: Replace the restated recipe list with a pointer to coga/cli.
  docs/contexts/coga-dev/internals/SKILL.md: List the new usage-pricing page.
  docs/contexts/coga-dev/internals/activity-capture/SKILL.md: Remove the interim copy of the price-table facts a sweep published.
  docs/contexts/coga-dev/internals/usage-pricing/SKILL.md: New home for the price-table facts moved out of coga/usage.
  docs/contexts/coga/usage/SKILL.md: Point the deferred price table at usage-pricing.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: Packaged twin of the trimmed topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md: Packaged twin of the trimmed topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/context-layout/SKILL.md: Packaged twin of the trimmed topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/SKILL.md: Packaged twin of the trimmed topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md: Packaged twin of the trimmed topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md: Packaged twin of the trimmed topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: Packaged twin of the trimmed topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md: Packaged twin of the trimmed topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/sandboxes/SKILL.md: Packaged twin of the trimmed topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/skill-management/SKILL.md: Packaged twin of the trimmed topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/uninstall/SKILL.md: Packaged twin of the trimmed topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/usage/SKILL.md: Packaged twin of the trimmed topic.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Peer review is the next workflow step.
checks:
  - command: .venv/bin/python -m pytest
    status: failed
    head: 1b4a8c1bbd4830c58a6fb469c31683ac05414e61
    base: 51f430c10465cb816b1531ecb17828f8f2946655
    detail: 3952 passed, 7 skipped, 3 failed (test_live_and_packaged_copies_stay_identical, test_context_distribution_is_complete, test_context_navigation_has_no_broken_links), all on architecture/code from blocks/02's half-published state on main.
  - command: git merge origin/coga/blocks-02-delete-the-code-topic-and-remove-coga--23a0ec (scratch worktree, cli/usage twins resolved to canonical) && .venv/bin/python -m pytest tests/test_packaging.py
    status: passed
    head: 346693ed717d1af0c102021fa9591a8b0980a9fd
    base: 3a50057a91b426c6109a39b035d81c568595a9df
    detail: 30 passed; run on the pre-rebase commit, before the activity-capture cleanup commit.
  - command: coga validate --json
    status: passed
    head: 1b4a8c1bbd4830c58a6fb469c31683ac05414e61
    base: 51f430c10465cb816b1531ecb17828f8f2946655
    detail: Exit 0; warnings only (stuck-in-progress, unfrozen-workflow on unrelated tickets).
```
