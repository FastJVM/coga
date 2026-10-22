---
title: 02 Delete the code topic and remove Coga-repo-only text from shipped topics
status: done
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
agent: claude
---

## Description

Delete the coga/code topic, fix links and statements that are only true inside the Coga repo, and turn 'Known gap' bug notes in shipped topics into tickets. See `coga/tasks/blocks/README.md`.

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

Done when: `coga/code` is deleted, no shipped topic states something true only inside the Coga repo, and no shipped topic carries a "Known gap" bug note; both copies of every touched topic are byte-identical;
no link in `docs/`, `src/`, `tests/`, `coga/` (outside old tickets and the
log), `README.md` or `AGENTS.md` points at a removed topic or anchor; any new
coga-dev page is listed in `docs/contexts/coga-dev/internals/SKILL.md`;
`.venv/bin/python -m pytest` and `coga validate --json` pass.

### Specifics

- `coga/code`: repoint `architecture:76` (drop the map entry) and
  `lifecycle:165` (→ `../blackboard/SKILL.md#superseded-designs`); move the
  "record is explicit, not inferred from the slug" rationale into
  `coga/checkouts` if it is not already there.
- Coga-repo-only text to remove or generalize: `checkout-cleanup:81` link to
  `../../../archive/evidence/...` (broken in the packaged copy);
  `recurring/scheduling:76` "This repo's `upstream-coga`"; `context-layout`
  "This repo overrides `coga/bootstrap/resolve-conflicts`"; `important`
  lines 10–15 (usage-report routing); `knowledge` `docs/archive/*` rows;
  `skill-management` google-agents-cli/anthropic pack examples;
  `tickets/discovery` `relay-os/tasks` pathspecs; `usage` "team runs on a
  subscription" and `docs/archive/evidence` links. Search for more
  (`grep -rn 'archive/\|This repo\|relay-os' docs/contexts/coga`).
- Known gaps: `checkout-cleanup` (foreign linked branch),
  `checkout-cleanup/branch-sweep` (`_local_branches` return code),
  `recurring/scheduling/failures` (`_record_unlaunched_creates`,
  `run_recurring_named` sync sink), and any other
  `grep -rn 'Known gap' docs/contexts/coga`. Create one draft ticket per gap
  at the top level (not in `blocks/`), then delete the paragraph.
- Also fix `sandboxes:41` ("When `git worktree add` cannot write…" is stale:
  sandbox-clone now triggers on branch creation failing) and add
  `prepare-checkout` to the recipe list in `coga/cli`.
- Leave tickets 03–09's structural trims to them; this ticket only removes
  the text named here, so later tickets start clean.


<!-- coga:blackboard -->
## Dev

pr: https://github.com/FastJVM/coga/pull/1081
branch: coga/blocks-02-delete-the-code-topic-and-remove-coga--23a0ec


## Implement handoff (2026-10-21)

Done on the branch (commit `d487710bb`), all twins byte-identical:

- Deleted `coga/code` (both copies; dropped from `REQUIRED_BOOTSTRAP_CONTEXT_REFS`).
  Repointed `architecture` map, `lifecycle` (→ `blackboard#superseded-designs`),
  `docs/README.md`, `coga-dev/codebase`. The "record is explicit, not inferred
  from the slug" rationale is now a paragraph in `coga/checkouts` intro.
- Coga-repo-only text: `checkout-cleanup` archive link dropped;
  `recurring/scheduling` upstream-coga sentence dropped (its own ticket states
  `scope: clone`); `context-layout` override sentence → `coga-dev/packaging`;
  `important` usage-report example generalized (usage-report ticket owns its
  routing); `knowledge` three archive rows → one generic row, Coga's paths →
  `coga-dev/archive-access`; `skill-management` google/anthropic examples
  generalized, pack decision → `coga-dev/current-direction`; `tickets/discovery`
  relay-os pathspecs → `coga-dev/codebase/gotchas`; `usage` subscription clause
  and archive links dropped, links → `coga-dev/internals/activity-capture`.
- Known gaps → drafts (top level): `guard-foreign-linked-worktree-branch-cleanup`,
  `fail-the-branch-sweep-when-local-branch-enumeratio`,
  `name-unlaunched-created-periods-when-the-recurring`,
  `report-failed-create-syncs-from-named-recurring-la`. Paragraphs deleted;
  `checkout-cleanup` "known gap below" pointer rewritten as a behavior fact.
- `sandboxes`: trigger is now "creating the feature branch fails because the
  primary `.git` is read-only". `cli`: `prepare-checkout` added to recipes.
- Left alone on purpose: `workflows` "known gaps in PRs #1058…" (W43 history,
  ticket 08); `tests/test_init.py` synthetic `coga/code` fixture strings;
  `docs/release-notes/context-audiences.md` rename table (history, not a link);
  `sandbox-clone` "this repo's checkout root" (means the adopting repo).
- Audit disagreement: none.

**Incident — main is red until this PR lands.** Running `coga create` with the
docs edits uncommitted made its exit sweep publish the whole `docs/contexts/`
half to main as `001aad66f` "Sync coga state" (the contexts root is Coga state).
Main therefore has the canonical edits and the `coga/code` deletion but not the
packaged twins or the `test_packaging.py` line: on `origin/main` (a0982d68c)
`tests/test_packaging.py` has 3 failures. After rebase this branch's diff is
only the twins + test (18 files). Lesson: commit before any mutating `coga`
command when contexts-root files are dirty.

At implement time, `coga validate --json` exited 1 on
`marketing/fix-installer/find-out-what-macos-actually-ships`
(`unsynthesized-draft-blackboard`); same 48 issues on main. Fixed during
peer-review below.

## Peer review

**Completed — direct, independent Codex review**, covering head
`bd3fbc017b6a093145ce0e3670cda667fda5c3af` against base
`cf58f4aea2ea31f7e0a2cf1d3592a39ed7096a6c`. Claude Opus 5.5 implemented the
branch (handoff plus commit co-author evidence); this fresh Codex session
reviewed it directly. No nested reviewer ran.

Findings and resolution:

- Fixed two unresolved `contexts: coga/code` attachments in completed tickets:
  `fix-parser-bugs-documented-in-pr-1055` now attaches `coga/checkouts`, and
  `match-concurrent-codex-sessions-to-their-launch-so` drops the obsolete
  attachment while retaining its existing `coga/checkouts`. Published on
  control as `717ffdd37`. Historical prose mentions remain historical.
- At the attending human's request to fix the remaining validation problem,
  synthesized `marketing/fix-installer/find-out-what-macos-actually-ships`'s
  evaluator findings into its Description/Context. Its body now asks the
  machine-state, pip-to-uv, PATH and externally-managed questions, names the
  primary sources and findings attachment, and distinguishes the blocked
  test proposal from evidence. Preserved its frontmatter, guide, original
  body and complete evaluator review; the latter two live under Superseded
  designs. Published as `cf58f4aea`; no validation exception remains.
- Replaced the incompatible inherited PR preparation (mapping-valued author,
  old field names, globbed file coverage and missing review receipts) with
  the supported preparation format below.

The review includes the canonical edits swept to main as `001aad66f`, all
18 current diff paths, the four new draft bug tickets, and current source
for the corrected sandbox trigger and recipe index. All 15 changed topic
pairs are byte-identical; `coga/code` is absent from both trees, and live
navigation resolves to surviving topics/anchors. The remaining Coga-specific
structural/history trims belong to blocks 03–09 as directed by this ticket.
No new development page was added. No unresolved must-fix findings remain.

Rebased at entry and again after publishing the state repairs. The final
range-diff proves the implementation patch unchanged, the touched twins were
rechecked, and the final fetch found no commits ahead of the reviewed base.
The branch was pushed with an explicit force-with-lease and has one
implementation commit ahead of main. The current ticket stays unstaged.

Final verification: full suite **3955 passed, 7 skipped**; pristine-clone
packaging **30 passed**; repository validation **exit 0, zero errors**
(47 existing warnings). Exact commands and head/base receipts are below.
The read-only PR formatter accepted the prepared `skim` title, all 18 paths,
and every current receipt with no publication evidence gaps. Scoped ticket
validation also passes with no issues.
Interactive terminal/notification checks are inapplicable to this prose and
package-inventory diff. All tests used Python 3.12.12; no Python 3.11 run is
claimed. The next step is the mechanical open-pr handoff.

## PR

```yaml
title: Delete coga/code and sync shipped topics with canonical cleanup
author: claude
author_evidence: The implementation handoff and implementation commit identify Claude Opus 5.5. Codex
  performed the independent direct review and the separate control-state repairs recorded below.
head: bd3fbc017b6a093145ce0e3670cda667fda5c3af
base: cf58f4aea2ea31f7e0a2cf1d3592a39ed7096a6c
depth: skim
rationale: 'Bounded documentation and package-inventory cleanup, independently reviewed with full-suite
  and pristine-wheel checks passing. Read the publication deviation: the canonical half already reached
  main through a state sweep, and this branch restores the packaged twins.'
implementation: Removes the obsolete packaged coga/code overview and required-bootstrap entry, synchronizes
  15 packaged user topics with their canonical edits, and fixes the docs index. The topics preserve explicit
  Dev linkage, repoint superseded-design guidance, remove repository-specific examples and four draft-tracked
  bug notes, correct the sandbox fallback trigger, and list prepare-checkout.
deviations: Canonical context edits and their development destinations reached main in 001aad66f through
  the implement-session state sweep. Peer review repaired two remaining stored coga/code attachments on
  control in 717ffdd37. At the attending human's request, it also synthesized the unrelated macOS draft
  evaluator notes into its body, preserving its frontmatter and original evidence, in cf58f4aea. These
  state repairs are already in the reviewed base and are not PR diff paths.
limitations: Adopting repositories with explicit coga/code attachments must remove or repoint them because
  that fallback is intentionally deleted. The four pre-existing runtime defects are tracked in draft tickets.
  Repository validation exits 0 with 47 existing warnings about other tickets; checks ran on Python 3.12.12.
files:
  docs/README.md: Remove navigation to the deleted coga/code overview.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md: Remove the deleted
    overview link and keep direct navigation to the code-ticket topics.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/SKILL.md: Remove the repo
    archive link and draft-tracked foreign-worktree bug note while retaining the current operator-visible
    behavior.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/branch-sweep/SKILL.md: Remove
    the local-branch enumeration bug note now recorded in its own draft ticket.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md: Preserve the explicit
    Dev-record linkage rationale from the deleted overview.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: Include prepare-checkout in
    the fixed recipe index.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/code/SKILL.md: Delete the redundant packaged
    code-topic overview.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/context-layout/SKILL.md: Remove Coga-specific
    bootstrap override examples now owned by development packaging.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/important/SKILL.md: Generalize the private
    usage-report routing example for adopting repositories.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/knowledge/SKILL.md: Describe archive ownership
    without imposing Coga-specific archive paths.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md: Link superseded-design
    guidance directly to the blackboard owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: Remove the
    source repository-only upstream-coga example.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/failures/SKILL.md: Remove
    the two failure-accounting bug notes now tracked in separate drafts.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/sandboxes/SKILL.md: Correct the independent-clone
    trigger to feature-branch creation failing on read-only Git metadata.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/skill-management/SKILL.md: Remove source-repository
    skill-pack examples and installation-state claims.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/discovery/SKILL.md: Remove relay-os
    history-specific pathspecs from the user instructions.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/usage/SKILL.md: Remove the local subscription
    rationale and private archive references.
  tests/test_packaging.py: Stop requiring the intentionally removed coga/code fallback.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: bd3fbc017b6a093145ce0e3670cda667fda5c3af
  base: cf58f4aea2ea31f7e0a2cf1d3592a39ed7096a6c
  detail: Direct Codex review completed on the final head/base, including the canonical changes already
    on main. Found and fixed the two unresolved stored context attachments; repaired the PR preparation
    schema and per-path evidence. No unresolved must-fix findings. Verified all 15 changed twins, the
    topic deletion, replacement links, four draft issue records, and the unchanged implementation patch
    after final rebase. No interactive terminal or rendered notification behavior is touched.
checks:
- command: PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest -q
  status: passed
  head: bd3fbc017b6a093145ce0e3670cda667fda5c3af
  base: cf58f4aea2ea31f7e0a2cf1d3592a39ed7096a6c
  detail: 3955 passed, 7 skipped in 357.98s on Python 3.12.12; final run after both state repairs and
    final rebase.
- command: PYTHONPATH=/tmp/coga-blocks-02-peer-1weah2qn/pristine/src /home/n/Code/claude/coga/.venv/bin/python
    -m pytest -q tests/test_packaging.py
  status: passed
  head: bd3fbc017b6a093145ce0e3670cda667fda5c3af
  base: cf58f4aea2ea31f7e0a2cf1d3592a39ed7096a6c
  detail: 30 passed in 3.83s from /tmp/coga-blocks-02-peer-1weah2qn/pristine, a pristine git clone detached
    at the reviewed head. Includes wheel-content and installed-wheel checks.
- command: PYTHONPATH=/home/n/Code/claude/coga/src coga validate --json
  status: passed
  head: bd3fbc017b6a093145ce0e3670cda667fda5c3af
  base: cf58f4aea2ea31f7e0a2cf1d3592a39ed7096a6c
  detail: 'Exit 0; 151 OK, zero errors, 47 warnings: 20 stuck-in-progress, 19 unfrozen-workflow, 7 empty-description,
    1 large-blackboard. All three errors found during this review are fixed; no validation exception remains.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: bd3fbc017b6a093145ce0e3670cda667fda5c3af
  base: cf58f4aea2ea31f7e0a2cf1d3592a39ed7096a6c
  detail: Passed; no whitespace errors in the publication diff.
```
