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
step: 2 (peer-review)
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
peer-review rebased it to `b91664896`. The user publication topic absorbs
recipe/recovery and authoring facts; the two leaves are removed; internals and
dated decisions move to the existing development owners; sync becomes a map.
Audit disagreement: none. The existing state-publication internals topic is
already listed in the internals index; no new development page was introduced.

## Peer review

**Completed direct Codex review** of final head `a460ae2b99dd4b04e1507111d36fa41b3da36165` against base
`46b146443b29368a1808a7af04d6d7a02052506b`. All 34 changed paths and the relevant publication implementations
(`cli`, `git`, `authoring`, `publish_state`) were inspected. Original
implementation identity is established by the implement handoff and commit
attribution, not by peer configuration. Codex independently reviewed Claude's
implementation, then self-reviewed its own corrections; the final receipt
conservatively uses `kind: self`.

Findings fixed and pushed:

- The migration table still prescribed the removed authoring and sweep refs.
  Its destinations now name the surviving topic; old refs appear only as
  explicitly historical migration sources.
- The finalize skill duplicated the detailed authoring contract. It now names
  the user owner as required reading and keeps development navigation optional.
- The consolidated wording overstated which committed changes the strict
  recipe publishes. It now preserves committed-change selection, the review
  boundary, and local-control behavior without requiring developer knowledge.
- Removing the internal helper name exposed an existing documentation test
  that required it. That assertion now checks the required user-topic reference;
  the executable-entrypoint prohibition and authoring behavior tests remain.

Corrections are `af460483c` and `a460ae2b9`. A final fetch/rebase left the head
unchanged; the branch is pushed with `--force-with-lease` and this primary
checkout has returned cleanly to `main` before this handoff.

Reference/anchor audit found no surviving navigation to the deleted leaves;
only old tickets and explicit historical migration spellings remain. The changed
publication/finalize twins match. No terminal loop, pager, prompt interaction, or
rendered notification changed, so no interactive surface exercise applies.

**Unresolved acceptance dependency:**
`blocks/02-delete-the-code-topic-and-remove-coga-repo-only` (PR
https://github.com/FastJVM/coga/pull/1081) is still at its owner review gate and
unmerged. Its canonical changes already reached main; its outstanding packaged
changes account for the 15 mismatched context pairs and missing canonical
`coga/code` on both main and this branch. In particular, this ticket's touched
`architecture`, `checkouts`, and `sandboxes` pairs cannot yet satisfy byte identity.
The earlier implement handoff grouped PRs #1080/#1081 together; the observed
packaging failures specifically trace to #1081's changed paths.

Final suite: **3 failed, 3952 passed, 7 skipped**. The failures are:

- `test_packaging.py::test_live_and_packaged_copies_stay_identical`
- `test_packaging.py::test_context_distribution_is_complete`
- `test_packaging.py::test_context_navigation_has_no_broken_links`

All three reproduce on main `46b146443b29368a1808a7af04d6d7a02052506b` in an independent test clone. The pristine
feature-clone packaging run also passed its wheel check. Final validation exits
0 with 151 OK, zero errors, and 47 warnings. Detailed commands and revision-specific
receipts are below. No remaining change-specific review finding was found, but
the ticket's passing-suite and touched-twin acceptance remain unmet, so this
step must block rather than bump to the mechanical publication step.

After task 02 lands: rebase this branch, resolve ordinary documentation drift,
recheck every touched twin, rerun the full suite and validation, complete a
review of the resulting head/base, refresh this preparation, and then bump once.

Entry recovery: the sole dirty file on main was the stale-context removal in
`state-sync-published-unmerged-recurring-templates` already documented by the
implement step. Its ownership and exact diff were verified, then
`coga run publish-state` published it as `46b146443` before the branch switch.

## PR

```yaml
title: Collapse state publication into one user topic
author: claude/codex
author_evidence: Claude Opus 5.5 performed the implement step (original commit 042e0d10b, rebased to b91664896).
  Codex performed this direct review and authored the corrections in af460483c and a460ae2b9.
head: a460ae2b99dd4b04e1507111d36fa41b3da36165
base: 46b146443b29368a1808a7af04d6d7a02052506b
depth: deep
rationale: 'Documentation consolidation with no executable behavior change, but the required suite and
  twin-identity acceptance remain blocked by pre-existing packaging drift from task blocks/02-delete-the-code-topic-and-remove-coga-repo-only
  (PR #1081). The final fixes were self-reviewed. Resume peer-review after that dependency lands; do not
  publish yet.'
implementation: Make coga/state-publication the user owner for roots, eligibility, publication timing
  and checkout behavior, the pre-review hazard, strict publish-state, and recovery. Delete the authoring
  and sweep leaves, retain their implementation details in the existing coga-dev internals page, and reduce
  sync to a map. Move the developer design rule and dated decisions to coga-dev. Update navigation, migration
  targets, packaged counterparts, and resource assertions. The finalize skill now requires the user owner
  instead of restating its contract.
deviations: The active draft state-sync-published-unmerged-recurring-templates had a stale context attachment;
  its implement-step repair was still dirty on entry and was strictly published on main as 46b146443 before
  branch work. Peer review also corrected overbroad committed-publication wording and aligned an existing
  authoring test with the user reference. No runtime behavior changes or new development topics.
limitations: 'Main and this branch both have 15 mismatched context pairs and a missing canonical coga/code
  topic. Three touched pairs (architecture, checkouts, sandboxes) consequently remain non-identical. PR
  #1081 contains the outstanding packaged changes. No interactive terminal or rendered Slack surface changed,
  so those manual checks are inapplicable. Tests used Python 3.12.12. Historical receipts below retain
  their original revisions.'
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
review:
  reviewer: codex
  kind: self
  status: passed
  head: a460ae2b99dd4b04e1507111d36fa41b3da36165
  base: 46b146443b29368a1808a7af04d6d7a02052506b
  detail: 'Completed direct review of all 34 paths at this head/base, including re-review after both correction
    commits. The original Claude implementation received an independent Codex review; Codex self-reviewed
    its own fixes, so the combined final review is conservatively classified as self. Fixed stale migration
    destinations, duplicate authoring ownership, overbroad publication selection wording, and the obsolete
    internal-helper assertion. No unresolved change-specific findings. Packaging acceptance is still blocked
    by PR #1081; this is not merge approval.'
checks:
- command: .venv/bin/python -m pytest -q
  status: failed
  head: a460ae2b99dd4b04e1507111d36fa41b3da36165
  base: 46b146443b29368a1808a7af04d6d7a02052506b
  detail: 'Final commit: 3 failed, 3952 passed, 7 skipped in 343.11s. Only the three packaging failures
    listed in Peer review remain; all reproduce on main.'
- command: .venv/bin/coga validate --json
  status: passed
  head: a460ae2b99dd4b04e1507111d36fa41b3da36165
  base: 46b146443b29368a1808a7af04d6d7a02052506b
  detail: 'Final commit: exit 0; ok_count 151, zero errors, 47 warnings.'
- command: git diff --check main...HEAD
  status: passed
  head: a460ae2b99dd4b04e1507111d36fa41b3da36165
  base: 46b146443b29368a1808a7af04d6d7a02052506b
  detail: 'Final commit: no whitespace errors.'
- command: PYTHONPATH=/tmp/coga-blocks06-peer-review-check/src /home/n/Code/claude/coga/.venv/bin/python
    -m pytest -q tests/test_packaging.py
  status: failed
  head: af460483c97ab0c0af017093c16e3356a5a6e0b9
  base: 46b146443b29368a1808a7af04d6d7a02052506b
  detail: 'Historical pristine-clone verification, cwd /tmp/coga-blocks06-peer-review-check: 3 failed,
    27 passed in 3.83s. The clean-tree wheel test passed; only the same baseline packaging failures remained.
    The later commit changes only tests/test_authoring.py.'
- command: PYTHONPATH=/tmp/coga-blocks06-peer-review-check/src /home/n/Code/claude/coga/.venv/bin/python
    -m pytest -q tests/test_packaging.py::test_live_and_packaged_copies_stay_identical tests/test_packaging.py::test_context_distribution_is_complete
    tests/test_packaging.py::test_context_navigation_has_no_broken_links
  status: failed
  head: 46b146443b29368a1808a7af04d6d7a02052506b
  base: 46b146443b29368a1808a7af04d6d7a02052506b
  detail: 'Baseline reproduction, cwd /tmp/coga-blocks06-peer-review-check at main: all 3 failed in 8.40s
    with the same causes. This receipt verifies the baseline, not the feature head.'
- command: .venv/bin/python -m pytest -q tests/test_authoring.py
  status: passed
  head: af460483c97ab0c0af017093c16e3356a5a6e0b9
  base: 46b146443b29368a1808a7af04d6d7a02052506b
  detail: 28 passed in 8.08s. Run at af460483c with the one-line test correction unstaged; that exact
    correction was then committed as a460ae2b9. The full final suite independently verifies the committed
    tree.
- command: .venv/bin/python -m pytest -q
  status: failed
  head: af460483c97ab0c0af017093c16e3356a5a6e0b9
  base: 46b146443b29368a1808a7af04d6d7a02052506b
  detail: 'Historical intermediate run: 4 failed, 3951 passed, 7 skipped in 346.78s. The additional internal-helper-name
    assertion was corrected in a460ae2b9 and passes in the final full run.'
- command: .venv/bin/python -m pytest -q
  status: failed
  head: b91664896a22db9c0d47e7c2d9b8e2c2a7d8ca39
  base: 46b146443b29368a1808a7af04d6d7a02052506b
  detail: 'Historical initial review run after rebase: 3 failed, 3952 passed, 7 skipped in 346.49s; the
    same pre-existing packaging failures.'
```

---

## Blockers

- [x] [2026-10-21 18:38] [agent:codex] id=20261021T183800 Land the owner-reviewed packaged changes from blocks/02-delete-the-code-topic-and-remove-coga-repo-only (PR #1081), then resume this peer-review for rebase and verification. Three packaging failures reproduce on main; architecture, checkouts, and sandboxes twins touched here remain non-identical. Final branch a460ae2b9 is pushed; direct review completed and validation passed, but the required passing-suite and twin-identity acceptance are unmet.
  resolved: [2026-10-21 22:21] [human:nicktoper] The attending owner confirmed that merged PR #1081 resolves the dependency blocker. Resume peer-review, rebase onto current origin/main, verify touched twins, rerun the full suite and validation, and refresh the final review receipts before bumping.
