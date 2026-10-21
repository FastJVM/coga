---
title: Confirm why branch-sweep ran as a shared period task despite scope clone
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

Filed by Dream 2026-W43 (recurring/dream, Phase 6; Phase 2 knowledge-scan shard ks-21, drift). Target: coga/recurring/branch-sweep/ticket.md and the clone-scope runner (src/coga/recurring_clone.py, recurring_runner). Evidence: the template has carried scope: clone on main since 2026-10-16 and its body says a clone-scoped run creates no shared period task and writes its report to .coga/recurring-clone/branch-sweep.log. Yet coga/log.md 2026-10-19 10:34 says 'created recurring/branch-sweep for 2026-10-19' (commit 39fe8061c, whose template copy already had scope: clone); 10:45 'launched as a script (ticket.py)'; 10:46 task done; the Branch Sweep report was written onto the shared period task coga/tasks/recurring/branch-sweep/ticket.md, and no .coga/recurring-clone/ exists in the /home/n/Code/claude/coga clone. The operating coga is an editable uv tool install from the separate checkout /home/n/Code/coga, which may have lagged main at 10:34 (it is at main now). Decide whether the runner ignores scope: clone on some path (then fix it, with a regression test) or the install simply lagged (then record that failure mode). Related: PR #1033 (clone-local recurring work) had an unanswered P2 review thread on src/coga/recurring.py:989 'Catch malformed clone period keys'; draft state-sync-published-unmerged-recurring-templates covers the separate 2026-10-16 leak. The period task was deleted by Dream W43 Phase 4; git history (commit before deletion) holds it.

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

pr: https://github.com/FastJVM/coga/pull/1069
branch: docs/clone-scope-install-lag

## Finding (decided with owner 2026-10-19)

Install lag, not a runner bug. The editable install's checkout
(/home/n/Code/coga) sat at 573824fc5 (2026-10-16 12:29) until a 10:51
fast-forward on 10-19 (reflog); bbcc1f551 (clone scope) is not its ancestor and
its `recurring.py` has no `SCOPE_CLONE`, ignoring unknown keys. So the 10:34
sweep treated branch-sweep as a shared template (39fe8061c); the shim's
`COGA_TASK_SLUG` branch bumped it to done. Current code: both period-task create
paths (`recurring.scan_due` skip via `_declares_clone_scope`, `create_named`
refusal) are guarded and tested in tests/test_recurring_clone.py; no fix or new
regression test. Recorded the failure mode in coga/recurring/scheduling
(+ packaged twin). Out of scope follow-up: PR #1033 P2 thread "Catch malformed
clone period keys" (src/coga/recurring.py `scan_clone_due` area) still unanswered.

## Handoff (implement)

Changed: docs/contexts/coga/recurring/scheduling/SKILL.md ("Repo scope and
clone scope") gains one paragraph: an install older than clone scope ignores
`scope` and runs the template as a shared period task; shipped clone shims bump
it; the fix is upgrading the install. Packaged twin under
src/coga/resources/templates/coga/bootstrap/contexts/ updated byte-identically.
No code change and no new test, as agreed with the owner.

Pre-existing failures (also on base with the change stashed; not caused here):
- tests/test_compose.py::test_coga_repo_instructions_carry_the_minimal_core_boundary[CLAUDE.md]:
  CLAUDE.md is absent from this checkout (untracked, not present).
- tests/test_usage_report.py::test_shim_posts_once_on_the_important_route_and_bumps_through_the_cli:
  shim import set now includes `coga.tasks.read_ticket`/`resolve_task`, which the
  test's expected map lacks.

## Peer review

Completed direct Codex review of head `78fc906e6d656d1619c662b0f572927e1f48122f` against
base `b00587bb208485dc02b3ee7e38c123d4cc8883c7` after the final rebase and wording correction.
No unresolved must-fix findings remain. No nested reviewer CLI was run.

Authorship: Claude wrote the original paragraph (implement handoff and commit
co-author evidence). Codex independently reviewed that implementation, then
made the owner-approved qualification and reviewed the final combined diff.
The final PR receipt is marked self-review because it includes Codex's own
wording correction; it does not claim an independent review of that correction.

Resolved finding: a shared task's existence alone does not establish that the
currently running CLI is stale. The paragraph now asks the operator to check
the CLI/version and editable source checkout that created a shared task for a
template already declaring clone scope, and limits the upgrade remedy to that
mismatch. The owner approved this qualification in the attended review session.
Both topic copies remain byte-identical, and their install links resolve.

Diagnosis independently checked: HEAD and main reflogs place the editable
source checkout at `573824fc5` from 2026-10-16 12:29 until 2026-10-19 10:51
(local -07:00); `bbcc1f551` is not its ancestor. That source has no clone-scope
handling and ignores the unknown key. At `39fe8061c`, the template already
says `scope: clone`, and the copied shim bumps a shared task when
`COGA_TASK_SLUG` is set. Current `scan_due` skips clone templates,
`create_named` refuses them, and named launch dispatches them to the clone
runner; existing clone and shim tests cover these paths. No runner fix is
needed for this observed incident. The PR #1033 malformed-period-key concern
remains outside this change and was not reevaluated here.

Verification on the final head/base, with Python 3.12.12:
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q`:
  2 failed, 3801 passed, 7 skipped in 306.61s. The failures are exactly the
  two described in the implement handoff. Their tests, the usage-report shim,
  and repository instructions are identical to base; base also has no
  `CLAUDE.md`. The suite is recorded as failed, not waived.
- `git diff --check origin/main...HEAD`: passed.
- `cmp docs/contexts/coga/recurring/scheduling/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md`: passed.
- No terminal or Slack behavior changed, so interactive surface testing is
  inapplicable. No new regression test was added for this documentation change.

Earlier suite attempts were interrupted for the approved wording change and
an unrelated orientation launch that switched this checkout. After the owner
clarified that the other session was working in another repo, the branch was
rebased again and the full suite above ran without checkout movement. Those
interrupted attempts are not current verification receipts.

Reconciled with fetched origin/main at `b00587bb208485dc02b3ee7e38c123d4cc8883c7`, then pushed
`docs/clone-scope-install-lag` with `--force-with-lease`; it contains two commits
ahead of main. Loaded control's ticket before this handoff. With
`COGA_LAUNCH_RETURNS_CHECKOUT=1`, leave checkout return to the launcher after
bump. PR recommendation is deep because the full suite has recorded failures.

## PR

```yaml
title: Document clone scope under a lagging install
author: claude/codex
author_evidence: The implement handoff and commit co-author identify Claude Opus 5.5 as the original author.
  In this attended peer-review session, Codex authored the owner-approved diagnostic qualification in
  the final commit.
head: 78fc906e6d656d1619c662b0f572927e1f48122f
base: b00587bb208485dc02b3ee7e38c123d4cc8883c7
depth: deep
rationale: The documentation change is bounded and the install-lag diagnosis is supported by historical
  source and reflogs. Deep is required by the review-depth rubric because the full suite still has two
  pre-existing failures; the final wording correction also has self-review rather than a separate independent
  reviewer.
implementation: 'Documents how a CLI predating clone scope ignores scope: clone, creates a shared period
  task, and lets the compatible shim close it. Directs troubleshooting to the CLI and editable source
  checkout that created the task, with an install upgrade as the remedy for that mismatch. Keeps the packaged
  topic identical.'
deviations: Investigation established install lag rather than a runner defect, so the owner agreed to
  documentation only, with no runtime change or new regression test. Peer review qualified the blanket
  diagnosis with owner approval.
limitations: 'The full suite is not green because of the two documented baseline failures. The final diff
  includes a Codex-authored wording correction reviewed by Codex. The malformed clone period-key concern
  from PR #1033 is outside scope. No interactive surface changed, so no terminal or Slack exercise was
  applicable.'
files:
  docs/contexts/coga/recurring/scheduling/SKILL.md: Owns the failure mode, qualified diagnosis, and upgrade
    remedy for a CLI older than its clone-scoped templates.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: Byte-identical
    packaged twin of the canonical scheduling topic.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 78fc906e6d656d1619c662b0f572927e1f48122f
  base: b00587bb208485dc02b3ee7e38c123d4cc8883c7
  detail: Direct review completed on the final head/base with no unresolved findings. Codex independently
    reviewed the Claude implementation, then made the owner-approved wording qualification and reviewed
    the final diff. Marked self because that final correction has no separate independent reviewer; no
    nested review CLI was invoked.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q
  status: failed
  head: 78fc906e6d656d1619c662b0f572927e1f48122f
  base: b00587bb208485dc02b3ee7e38c123d4cc8883c7
  detail: '2 failed, 3801 passed, 7 skipped in 306.61s on Python 3.12.12. Both failures match the implement
    baseline: test_compose.py::test_coga_repo_instructions_carry_the_minimal_core_boundary[CLAUDE.md]
    reads an absent file; test_usage_report.py::test_shim_posts_once_on_the_important_route_and_bumps_through_the_cli
    omits read_ticket/resolve_task from its expected imports. The affected tests and shim are unchanged
    from base.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: 78fc906e6d656d1619c662b0f572927e1f48122f
  base: b00587bb208485dc02b3ee7e38c123d4cc8883c7
  detail: No whitespace errors in the final branch diff.
- command: cmp docs/contexts/coga/recurring/scheduling/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md
  status: passed
  head: 78fc906e6d656d1619c662b0f572927e1f48122f
  base: b00587bb208485dc02b3ee7e38c123d4cc8883c7
  detail: Canonical and packaged topics are byte-identical. Both relative install links were also inspected
    and resolve.
```
