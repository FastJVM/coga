---
title: Make Retro check inbound doc links before deleting a done ticket
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
launch_generation: 7fff4fd0-f9c4-4ef5-be1c-91b9e3e57589
---

## Description

Filed by Dream run recurring/dream, period 2026-W46 (run 20261112T051938Z), Phase 6 — a gap found in the run itself, not by a scan shard.

Dream Phase 4 Retro direct-deleted the done ticket document-the-remedy-for-a-bloated-blackboard-sibli (no unextracted durable knowledge), but the root README.md cites it by a blob/main link as its worked example. tests/test_packaging.py::test_context_navigation_has_no_broken_links then failed on main. Fixed for now by PR #1214, which repoints the link to the last commit containing the ticket (dc6832e0b).

Root cause: retro/done-ticket (src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md) and the Dream template's Phase 4 eligibility check open PRs and live checkouts, but not durable inbound references (README.md, docs/*.md, contexts, skills) to coga/tasks/<slug> on blob/main. Decide the rule: e.g. before deleting, grep tracked docs for the task path and either rewrite the link to a commit permalink in the same change (knowledge PR or a small PR next to the direct delete) or skip the ticket and report it. Also consider whether coga delete itself should warn on inbound blob/main links.

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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/1223
branch: make-retro-check-inbound-doc-links-before-deleting

## Decision

- Rule owner: `retro/done-ticket`, new `### Inbound references`. Before
  choosing a source's deletion path, Retro runs
  `git grep -n -F -e '<tasks-root>/<slug>' -e '<task-leaf>' -- . ':!<tasks-root>' ':!<coga-os>/log.md'` (plus repository-required exclusions)
  in the isolated checkout and inspects each hit. Prefix-sharing slugs,
  same-path fixture trees, and links from other live tickets are not
  references. It repoints each real reference to a permalink at the full OID of
  the fresh control tip (that tip still contains the task).
  - Knowledge-bearing source: the repoint goes in its knowledge PR. Repointed
    files do not count toward the 3-knowledge-file limit, and the PR body lists
    them under `Repointed references`.
  - No-knowledge source with references: no direct delete, because
    `coga delete` publishes only the task and the log, and doc edits need
    review. It goes into one run-level reference-pin PR
    (`codex/retro-pin-references-<run-id>`, "Pin links to deleted tickets"), with no
    marker. Progress receipt: `pr pin-references — <url> — <slugs>`.
  - Self-review re-runs the search on each branch, and on the tree before each
    direct delete.
- Rejected: "skip the ticket and report it". That breaks Retro's invariant that
  no processed done ticket stays on disk, and Dream would re-pick the ticket
  every run.
- `coga delete`/`coga retire` warning: not in this change, because it grows
  the shared core path and retire's deterministic delete needs its own
  decision. Filed as draft `warn-when-coga-delete-or-coga-retire-leaves-a-live`.

## Handoff (implement → peer-review)

- Changed: the Retro skill (new section, plus the contract, Scope, steps
  5/9/10/11, progress line, PR body, and intro); Dream Phase 4 (a summary
  paragraph that links to the skill); `retire.md` (an exception clause); tests
  in `tests/test_retro_skill_template.py` (new test, plus one assertion that
  followed the reworded "Do not" line) and `tests/test_dream_worker_templates.py`
  (new test). No fixture change: these are prompt templates only.
- Known red on main, not caused by this change: README.md still links the
  deleted `document-the-remedy-for-a-bloated-blackboard-sibli` on blob/main.
  This fails `test_packaging.py::test_context_navigation_has_no_broken_links`,
  plus two `test_git.py::test_final_package_edits_never_escape_a_mutating_cli_sweep`
  cases that run that test in a subprocess. PR #1214 (OPEN) fixes it.

## Peer review

- **Completed direct Codex review** of final head `36d2a660490ee8eedb116f9efcbb9887223e218f` against base
  `2881e54d72a4a3e1acbd885e5e63b7c253fefaba`. Original implementation is Claude Opus 5.5
  (implement receipt and commit coauthor); Codex independently reviewed it,
  applied must-fix repairs, and self-reviewed those repairs. The final record
  is labeled self-review to disclose that overlap. No unresolved must-fix
  findings, no nested review process, and no subagent.
- Fixed: full-path grep missed relative links; unconditional direct-delete
  instructions contradicted the new route; the reference-pin body inherited a
  nonexistent-marker claim; a fixed branch name collided across runs. The
  search now also uses the final slug component, resolves relative targets,
  honors search restrictions, and leaves existing permalinks alone. Contracts,
  marker instructions, result reporting and retire's summary match the rule.
- Rebased onto fresh `origin/main` before review. Final fetch/rebase was a
  no-op, preserving the head/base above. Both feature commits are pushed;
  manual checkout returned cleanly to `main` before this handoff.
- Verification: `.venv/bin/python -m pytest -q` finished with **3 failed, 4766 passed, 33 skipped in 703.56s (0:11:43)**.
  Inspected all three failures: the README navigation failure and two
  `test_git.py::test_final_package_edits_never_escape_a_mutating_cli_sweep`
  subprocess failures share the pre-existing broken README link on main.
  Confirmed main still has that link and lacks the task; PR #1214 is open.
  Output: `/tmp/coga-inbound-peer-review-pytest.log`.
- `python /tmp/coga-inbound-search-exercise.py` passed using the actual prompt
  command in a temporary Git repo: root and relative bare-file links,
  directory-ticket link and existing permalink were found; task/log/restricted
  paths were excluded. Existing permalink is already safe after inspection.
  No real Retro deletion was performed. No interactive terminal surface or
  executable/runtime template changed. `git diff --check origin/main...HEAD`
  passed on the feature branch.
- Next: the mechanical `open-pr` step. Recommendation **deep** because the
  known inherited test failures remain; `coga delete` / deterministic done
  retirement guard is deferred to the already-filed draft.

## PR

```yaml
title: Repoint inbound task links before Retro deletes a ticket
author: claude/codex
author_evidence: Implement handoff and commit coauthor record Claude Opus 5.5 as original
  implementer. This Codex peer-review session authored commit 36d2a6604 with the review fixes.
head: 36d2a660490ee8eedb116f9efcbb9887223e218f
base: 2881e54d72a4a3e1acbd885e5e63b7c253fefaba
depth: deep
rationale: 'Bounded prompt/template change, but the full suite inherits the broken README
  navigation on main (PR #1214 is still open). Codex independently reviewed the Claude implementation
  and self-reviewed its own repairs; inspect the deletion-routing and link-search wording.'
implementation: Retro searches tracked files for root-relative task paths and final slug components,
  inspects relative targets, and pins durable live-tree references to a full-OID commit permalink
  before deletion. Knowledge-bearing sources carry repoints in their knowledge PR; referenced
  sources without new knowledge leave in one run-level reference-pin PR with a unique branch
  and no markers. Dream and retire defer to this rule.
deviations: No design deviation. Peer review repaired missed relative links, contradictory
  unconditional direct-delete instructions, the marker assertion in the reference-pin PR body,
  and the branch name collision across runs. The search honors repository access restrictions
  and preserves existing commit permalinks.
limitations: coga delete and deterministic done-ticket coga retire remain unguarded; follow-up
  draft warn-when-coga-delete-or-coga-retire-leaves-a-live owns that decision. Search hits
  require agent interpretation. No live Retro deletion was performed. Native Windows and interactive-terminal
  checks were omitted because this changes prompt text and string assertions, with no runtime
  code or executable template change.
files:
  src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md: Own the inbound-reference
    search, permalink routing, progress and PR-body rules; keep deletion contracts consistent.
  src/coga/resources/templates/coga/recurring/dream/ticket.md: Point Phase 4 at the Retro
    rule and explain why eligibility gates are insufficient.
  src/coga/resources/retire.md: Keep the canceled-ticket Retro caller consistent with the
    reference-pin exception.
  tests/test_retro_skill_template.py: Cover the prompt contract, relative-link search, marker-free
    route and unique per-run branch.
  tests/test_dream_worker_templates.py: Check that Dream defers the rule to Retro.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 36d2a660490ee8eedb116f9efcbb9887223e218f
  base: 2881e54d72a4a3e1acbd885e5e63b7c253fefaba
  detail: Direct review completed on the final diff with no unresolved must-fix findings.
    The initial review was independent of Claude authorship; the final review also includes
    self-review of Codex repairs. No nested review tool or child agent was used.
checks:
- command: .venv/bin/python -m pytest -q
  status: failed
  head: 36d2a660490ee8eedb116f9efcbb9887223e218f
  base: 2881e54d72a4a3e1acbd885e5e63b7c253fefaba
  detail: '3 failed, 4766 passed, 33 skipped in 703.56s (0:11:43). All three failures inherit
    the README blob/main link to the deleted document-the-remedy-for-a-bloated-blackboard-sibli
    ticket: the packaging navigation check and both test_git final-package sweep subprocess
    cases. Captured at /tmp/coga-inbound-peer-review-pytest.log. No new failure relative to
    the implement receipt.'
- command: .venv/bin/python -m pytest -q tests/test_packaging.py::test_context_navigation_has_no_broken_links
  status: failed
  head: 36d2a660490ee8eedb116f9efcbb9887223e218f
  base: 2881e54d72a4a3e1acbd885e5e63b7c253fefaba
  detail: '1 failed: README.md links the deleted document-the-remedy-for-a-bloated-blackboard-sibli
    ticket on blob/main. Confirmed same README and absent target on origin/main; PR #1214
    remains open.'
- command: python /tmp/coga-inbound-search-exercise.py
  status: passed
  head: 36d2a660490ee8eedb116f9efcbb9887223e218f
  base: 2881e54d72a4a3e1acbd885e5e63b7c253fefaba
  detail: 'Executed the template git-grep command in a temporary Git repo: root and relative
    bare-file links, directory ticket link and existing permalink found; task/log/restricted-tree
    hits excluded. Existing permalink was classified as already safe. No real tickets deleted.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: 36d2a660490ee8eedb116f9efcbb9887223e218f
  base: 2881e54d72a4a3e1acbd885e5e63b7c253fefaba
  detail: No whitespace errors in the final diff.
```

## Plan

- Rule lives in `retro/done-ticket` (owner of deletion): before choosing a
  source's deletion path, `git grep` tracked files (outside the task root and
  `coga/log.md`) for the task path and final slug component; repoint every live reference to a
  full-OID commit permalink in a PR. Knowledge-bearing → same knowledge PR;
  no-durable-knowledge with references → not direct-deleted, leaves in one
  run-level reference-pin PR. Dream Phase 4 summarizes and links.
- `coga delete`/`coga retire` warning: not in this change (core growth);
  file a follow-up draft.
