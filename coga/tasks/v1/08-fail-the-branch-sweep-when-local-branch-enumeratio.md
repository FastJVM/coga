---
title: Fail the branch sweep when local branch enumeration fails
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
launch_generation: pending:e582c072-3011-4e16-9f47-37d276448dfe
---

## Description

`branchsweep._local_branches` runs `git for-each-ref --format=%(refname:strip=2) refs/heads/` and parses stdout without checking the return code, so a failed local enumeration reads as no local branches. The sweep then proceeds on an empty local inventory, which can let an otherwise authorized remote-only delete run without a known local state, contrary to the rule that an incomplete scan preserves refs. Found during the 2026-10-05 terminal-owner cleanup (PR #963); never exercised. Fix: treat a non-zero exit as a sweep failure, like the worktree probe, with a regression test. Moved from the coga/checkout-cleanup/branch-sweep Known gap note by blocks/02.

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

### Code pointers

- `branchsweep._local_branches` calls `_git(root, "for-each-ref", ...)` and
  iterates `proc.stdout` without looking at `proc.returncode`. `sweep_branches`
  builds `names = local.keys() | remote.keys()` from it, so an empty local
  map turns every remote branch into an apparent remote-only branch.
- Model to copy: `branchsweep._worktree_branches`. On a non-zero exit it sets
  `result.worktree_unavailable` to stderr/stdout (or a fallback string), notes
  "... — sweep skipped: <detail>" via `_note`, and `sweep_branches` returns
  before any delete. Unlike `_remote_branches` (a partial sweep), a local
  enumeration failure stops the whole sweep: no per-branch decision is safe
  without local state. `_local_branches` will need `result` and `echo`
  parameters for this.
- A successful but empty `for-each-ref` (no branches, unborn HEAD) is
  legitimate and is not a failure.
- Failure plumbing to extend: `BranchSweepResult` (add a field such as
  `local_unavailable`), its `failure` property, and `render_sweep_report`,
  which labels `worktree_unavailable` / `state_root_unavailable` as "the sweep
  stopped early". `run_branch_sweep_recipe` exits 2 when `failure` is set.
- Required too: `_local_branches` silently drops a listed branch whose
  `_rev_parse` comes back empty. That branch then looks remote-only, which is
  the same unsafe outcome, so treat it as the same enumeration failure.
  Consider `--format=%(refname:strip=2) %(objectname)` instead: it removes the
  per-branch `rev-parse` and its empty case, and avoids failing the run when a
  branch is deleted between the two calls.
- Placement: the early return in `sweep_branches` goes before `_remote_branches`
  is called. Then no `ls-remote` call is wasted, and `remote_unavailable`
  cannot be reported ahead of the local failure. Add the new field to
  `failure` and to the "stopped early" condition in `render_sweep_report`.
- `checkout_disposal` also calls `sweep_branches(only=...)` and ignores
  `result.failure`. A local failure there only leaves owned branches in place,
  which is acceptable and needs no change.

### Tests

`tests/test_branchsweep.py`. Model the regression test on
`test_worktree_prune_failure_stops_sweep`: monkeypatch `bs._git` so that
`for-each-ref` returns a non-zero `CompletedProcess` while other calls pass
through to the real `_git`. The fake must accept `**kwargs`, because `_git`
takes `input=`; the model test's `fail_prune(root, *args)` does not. Then
assert the new failure field is set and `local_deleted` and `remote_deleted`
are both empty. Ideally, set up a remote-only branch that would otherwise be
deleted (with helpers such as `_merged_at_tip` / `_push_branch`), so the test
shows the delete is refused. Add the new field to the parametrized
`test_recipe_records_a_failed_sweep_on_the_blackboard` cases ("the sweep
stopped early", exit 2).

### Done

The work is done when a failed local enumeration (a non-zero `for-each-ref`
exit, or an unresolvable listed tip) stops the sweep with no local or remote
deletes, sets a named failure that appears in the report as "the sweep
stopped early", and makes the recipe exit 2. A regression test must cover
this, and the user topic and its twin must state the rule.

### Docs (same PR)

The rule is in `coga/checkout-cleanup/branch-sweep`
(`docs/contexts/coga/checkout-cleanup/branch-sweep/SKILL.md`; cited here, not
attached because this ticket edits it). It covers only per-branch failures
today. Add a short
statement that the sweep stops before any delete, records the reason in
`## Branch Sweep`, and exits 2 when it cannot establish local state: local
branch enumeration (new), worktree probe, or Coga root prefix. Keep this
separate from the per-branch paragraph. The packaged twin
`src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/branch-sweep/SKILL.md`
must stay byte-identical (`tests/test_packaging.py`).
`coga-dev/internals/branch-sweep` needs no change.

### Out of scope

The non-UTF-8 decode failure in `branchsweep._git` (the "Known failure mode"
in `coga-dev/internals/branch-sweep`) is a separate, unowned bug. Do not fix
it here.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: fail-sweep-on-local-enumeration

## Implement handoff (2026-11-04)

What changed (commit a65a8e686, pushed):
- `branchsweep._local_branches(root, result, echo)` now lists name and tip in
  one `for-each-ref --format=%(objectname) %(refname:strip=2)` (no per-branch
  `rev-parse`, no delete-between-calls race). A non-zero exit, or an entry it
  cannot split into tip + name, sets new `BranchSweepResult.local_unavailable`
  and notes "could not list local branches — sweep skipped: …". An empty
  successful listing is still fine.
- `sweep_branches` returns right after `_local_branches` on failure, before
  `_remote_branches` (no `ls-remote`, no remote_unavailable masking).
- `failure` includes `local_unavailable` (after state_root, before gh);
  `render_sweep_report` labels it "the sweep stopped early"; recipe exits 2.
- Docs: new paragraph in `coga/checkout-cleanup/branch-sweep` (+ byte-identical
  packaged twin) stating the stop-before-delete rule for local enumeration,
  worktree probe, and Coga root prefix.
- Tests: `test_local_branch_listing_failure_stops_sweep` (merged "feat" that
  would look remote-only stays on both sides), `test_unresolvable_local_branch_entry_stops_sweep`,
  plus `local_unavailable` case in `test_recipe_records_a_failed_sweep_on_the_blackboard`.
  Both new tests fail with the fix reverted.

Decision: an unresolvable entry is detected as an unparseable line from the
combined listing (the `rev-parse`-empty case no longer exists).

Environment note (not this ticket): the primary checkout carries an
uncommitted human edit to `pyproject.toml` (`tmp_path_retention_policy =
"failed"`). It was left untouched and unstaged. With it,
`tests/test_validate.py::test_validate_prunes_skill_dependencies_before_scanning`
errors at teardown (pathlib TypeError); with `-o tmp_path_retention_policy=all`
it passes. Whoever lands that pyproject tweak should fix that interaction.

No independent review yet; the workflow's later steps own review and PR.

## Peer review (2026-11-04)

Independent Codex direct review **completed**, with no must-fix findings and
no code changes. Covered head `29dc632c51dcb6c862d19b7342344fc24f99bc6c`
against base `e5e370fcc932b6202711dc58514f2ed0d9889273`. The implementation
was authored by Claude Code, evidenced by the implement handoff and the
original commit's Claude Opus 5.5 co-author trailer; this was an independent
review in the resumed Codex session.

Reviewed all four diff paths and their callers: a failed or malformed local
listing returns before remote enumeration or any branch/worktree deletion;
the named failure reaches the report and recipe exit 2; a successful empty
listing remains valid. The combined listing avoids the old per-branch
rev-parse race. Both documentation copies match. This change has plain-text
reporting only, so no raw-terminal, pager, or rendered Slack walkthrough was
applicable.

The human explicitly resolved the earlier checkout blocker, and `coga
unblock` recorded that resolution before review work. The pyproject setting
landed in `088c01908`; main's `5e07fbcfe` fixes the scandir teardown
interaction. The old implement full-suite receipt (4345 passed, 10 skipped,
one teardown error) was a failed run, despite its old label; it is superseded
by this session's clean full run: **4456 passed, 10 skipped** on Python 3.12.12.
Exact commands and revision receipts are in `## PR` below.

The recorded branch was rebased onto fetched main without conflicts and
pushed with an explicit lease. Its final head is `29dc632c51dcb6c862d19b7342344fc24f99bc6c`.
Main later advanced through unrelated task/log state only; the shared
publication freshness probe accepted that non-overlapping drift at
`9a716d24df5465a3569ad26b46b85e7551e5445e`. No tested or reviewed code
changed afterward. The checkout was returned clean to current main before
writing this handoff. Next step: the mechanical PR-opening step.

## PR

```yaml
title: Stop the branch sweep when local branch enumeration fails
author: claude
author_evidence: The implement handoff identifies Claude Code (claude-opus-5-5); original commit a65a8e686
  carries a Claude Opus 5.5 co-author trailer. Codex rebased and independently reviewed the implementation
  without changing code.
head: 29dc632c51dcb6c862d19b7342344fc24f99bc6c
base: e5e370fcc932b6202711dc58514f2ed0d9889273
depth: skim
rationale: Bounded failure-handling change with completed independent review and a green full suite. Read
  the description for the combined name/tip listing that replaces per-branch lookups.
implementation: Read local branch names and tips in one for-each-ref. A non-zero exit or malformed entry
  sets local_unavailable and stops the sweep before remote enumeration or deletion. The report says "the
  sweep stopped early" and the recipe exits 2; an empty successful listing remains valid.
deviations: Uses the combined objectname/refname listing suggested by the ticket, eliminating the per-branch
  rev-parse race. An entry missing its tip or name is the replacement failure case.
limitations: Verified on Linux with Python 3.12.12; Python 3.11 and Windows were not exercised. The separate
  known non-UTF-8 ref decoding issue remains out of scope.
files:
  src/coga/branchsweep.py: Record local enumeration failure, stop before the remote listing and deletion
    loop, and expose the failure through the result and report.
  tests/test_branchsweep.py: Prove failed and malformed listings preserve refs, and cover recipe exit
    2 with the stopped-early report.
  docs/contexts/coga/checkout-cleanup/branch-sweep/SKILL.md: Keep the surviving local topic identical
    to its package owner and document the stop-before-delete rule.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/branch-sweep/SKILL.md: Update
    the packaged contract for failures to establish local state and legitimate empty listings.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: 29dc632c51dcb6c862d19b7342344fc24f99bc6c
  base: e5e370fcc932b6202711dc58514f2ed0d9889273
  detail: Independent Codex direct review completed after rebase with no must-fix findings and no code
    changes. Reviewed every diff path, local/remote deletion gates, caller compatibility, empty and malformed
    listings, recipe failure reporting, and the documentation contract.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q --basetemp=/home/n/Code/coga-v108-review-br8nho/pytest
  status: passed
  head: 29dc632c51dcb6c862d19b7342344fc24f99bc6c
  base: e5e370fcc932b6202711dc58514f2ed0d9889273
  detail: 4456 passed, 10 skipped in 665.13 seconds on Linux/Python 3.12.12. Includes branch-sweep, packaging,
    retire/disposal, and the formerly failing validate teardown test with the committed tmp_path_retention_policy
    setting.
- command: env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /home/n/Code/coga-v108-review-br8nho/enumeration_smoke.py
  status: passed
  head: 29dc632c51dcb6c862d19b7342344fc24f99bc6c
  base: e5e370fcc932b6202711dc58514f2ed0d9889273
  detail: Passed two real-Git cases (unborn repository; nested branch with a same-name tag) and four injected
    cases (silent failure; partial failed output; missing tip; missing name). All failure cases stopped
    before remote enumeration and deletion and rendered the stopped-early report. The initial harness
    attempt stopped at config validation; unsetting the inherited undeclared webhook variable resolved
    that setup issue.
- command: git diff --check origin/main...HEAD
  status: passed
  head: 29dc632c51dcb6c862d19b7342344fc24f99bc6c
  base: e5e370fcc932b6202711dc58514f2ed0d9889273
  detail: Passed; no whitespace errors in the feature diff.
- command: cmp docs/contexts/coga/checkout-cleanup/branch-sweep/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/branch-sweep/SKILL.md
  status: passed
  head: 29dc632c51dcb6c862d19b7342344fc24f99bc6c
  base: e5e370fcc932b6202711dc58514f2ed0d9889273
  detail: Passed; the local topic and packaged owner are byte-identical.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -c 'from coga.github_preflight import check_branch_contains_control;
    result = check_branch_contains_control("origin", "main", cwd="/home/n/Code/coga", coga_root="/home/n/Code/coga/coga",
    head="refs/heads/fail-sweep-on-local-enumeration"); print(result); assert result.ok, result.detail'
  status: passed
  head: 29dc632c51dcb6c862d19b7342344fc24f99bc6c
  base: e5e370fcc932b6202711dc58514f2ed0d9889273
  detail: 'Passed with state-only-drift: origin/main advanced to 9a716d24df5465a3569ad26b46b85e7551e5445e
    only through non-overlapping Coga task/log state. No source, documentation, config, or overlapping
    change; the reviewed head and merge base are unchanged.'
```

## Blockers

- [x] [2026-11-04 11:11] [agent:codex] id=20261104T111105 Resolve the pre-existing human pyproject.toml edit (tmp_path_retention_policy = "failed") so /home/n/Code/coga has a clean checkout, then resume peer-review. No checkout preparation was supplied; coga/checkouts/manual requires a clean main and forbids switching, stashing, or an alternate worktree around this dirt. The edit is preserved; review, rebase, and tests remain unperformed.
  resolved: [2026-11-04 12:13] [human:nicktoper] The human confirmed the checkout blocker is resolved and authorized resuming peer review. The pyproject.toml tmp_path_retention_policy edit is now committed in 088c01908; the primary checkout is clean on main, refreshed from origin/main.
