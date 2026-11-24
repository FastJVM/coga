---
title: Fix stale doc references left by the plain-Git migration
status: blocked
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: open-branch
    skills: []
    assignee: agent
    requires: branch
    run: git/open-branch
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
  - name: push-and-open-pr
    skills: []
    assignee: agent
    requires: pr
    run: git/push-and-open-pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 3 (peer-review)
agent: claude
---

## Description

Filed by Dream 2026-W48 (run 20261123T224856Z), Phases 2 and 3 (knowledge-scan shards ks-01, ks-02, ks-08, ks-10, ks-11, ks-12, ks-16; contract-audit shards ca-01, ca-03, ca-04, ca-06, ca-07, ca-08). Overlapping PRs: https://github.com/FastJVM/coga/pull/1279 (owner ticket v1/03-use-git-like-everyone-remove-coga-s-publication-ab, whose "Docs to change" list names most targets) and https://github.com/FastJVM/coga/pull/1280 (v1/no-weird-state-in-personal-dir). Handle this after those PRs' review; do not duplicate their edits.

The scans read the PR #1280 branch (stacked on #1279), where commit 1099f14c3 removes src/coga/git.py, autoclose.py, open_pr.py, retire_worklist.py, branchcleanup/branchsweep, the autoclose-merged and branch-sweep jobs and the autoclose alias, and changes the log.md merge attribute to union. On that branch these living docs still describe the removed code (all are accurate on main today, so nothing here can land before the migration):

- B1 docs/contexts/coga-dev/codebase/gotchas: create_task "calls git.write_ticket" (now Ticket.write); the --show-current item cites git.current_branch, branchcleanup/branchsweep._current_branch, open_pr.py; the Windows item cites git.publish/write_ticket expect= and git._git_env gc.autoDetach; the blackboard item's state-publication barrier; mark_active "optionally syncs".
- B2 coga-dev/internals/activity-capture: teardown "publishes ... through git.sync_log" (launch.spawn_agent_session only calls usage_tracking.capture_session).
- B3 coga-dev/internals index lists 5 pages; activity-capture, agent-config, compose, notifications, recurring-autofix, recurring-clone, usage-pricing are unlinked.
- B4 coga-dev/internals/agent-spawn: git.prepare_control_checkout, git.retry_session_publication, sync_log, _reblock_unresolved_resume, before_recompose, COGA_LAUNCH_RETURNS_CHECKOUT, repl_supervisor._admit_held_child do not exist; also missing the run-state tmp scope (run_state.launch_tmp_scope opened in _launch; ensure_task_data_dir/apply_tmp_env at spawn call sites; link coga/launch#run-state) — the #1280 part.
- B5 coga-dev/internals/compose: compose.CheckoutNotice and _prepare_step_checkout gone; compose_prompt_report (compose.py ~383) takes no notice.
- B6 coga-dev/internals/notifications: autoclose.py callers (_report_retire_followups, _report_followup, _preflight_recipe_notifications, run_autoclose_recipe), branchsweep, recurring_runner._broadcast_scan/_flag_period_contradiction, launch _prepare_step_checkout; preflight_post's real callers are commands/bump.py and commands/mark.py.
- B7 coga-dev/internals/recurring-clone: clone_state_dir "resolves through git's common dir" — now cfg.repo_root / .coga/recurring-clone (recurring_clone.py ~51,75-77).
- B8 coga-dev/microkernel: autoclose.py as shared-infra example, launch._preflight_push_auth, github_preflight.check_git_auth, git.RETRY_WITHOUT_SWEEP_EXIT_CODE.
- B9 package coga/recurring/templates: retires.md "owned by src/coga/retire_worklist.py" with rules in coga/autoclose/sweep; "shipped autoclose-merged, branch-sweep and trim-log opt in" to run_when_inactive; "registered-recipe shims call run_recipe" (RECIPES is recurring-scan, autofix-analyze, delete-task; shims call coga_edge mains).
- B10 package skills code/design (l.22-24) and bootstrap/ticket (l.198-205) use src/coga/git.py / sync_task_state as the model citation; use a live symbol such as step_gate.gate_unmet_reason.
- B11 package coga/first-task (l.49-51) documents coga validate --check-github (not a CLI option on the branch; only the validate.py docstring keeps it).
- B12 package recurring/resolve-conflicts template (l.3, l.16) "after branch-sweep".
- B13 package coga/usage (l.118-119, 143-144) says log.md is -merge and union is "former"; the branch scaffold .gitattributes is /log.md merge=union.
- B14 package recurring/dream Phase 4 names autoclose.parse_branch_names, retire_worklist.is_discharged, worktree_owner, owner_branch_remains, and says coga retire "disposes of the checkout" (branch bootstrap/retire only deletes the ticket); same framing in the knowledge-scan skill's source: done+checkout bullet. Restate the live-checkout test in plain Git terms.
- B15 package coga/workflows (l.95-109) "Obligations the merge does not discharge" rests on autoclose-merged merge-triggered closure.
- B16 package coga/notifications/producers (l.25-26, 40, 47, 56) autoclose checkout summaries, coga/autoclose/sweep, autoclose as sole automatic done trigger, branch-sweep report.
- B17 package coga/recurring overview "Internals" links recurring-control and recurring-temp-worktrees to SKILL.md itself (topics deleted).
- B18 package coga/recurring/autofix (l.9) "coga dream, coga autoclose, coga skill-update" (also comment src/coga/recurring_autofix.py:173, workflow.py:185, aliases.py:49-50).
- B19 package coga/sandboxes: "[git] sync failed" attribution, publication failing at git hash-object, control-branch worktree relay.
- B20 coga-dev/internals/assist-publication: description promises alignment loop and control publication; body is a five-line attribution note.
- B21 coga-dev/internals/recurring-admission: description promises generations/leases, ledger freshness, delegated publication; body is a 4-sentence stub (period_generation still deserves a line).
- B22 coga-dev/internals/spool-merge: name/description (spool, retire-worklist union merging, writer locking) exceed the body (append_log, union driver, trim_log); consider renaming the ref (patterns l.39 and the index point at it).
- B23 coga-dev/internals/blackboard-io and src/coga/taskfile.py:238 comment name the removed open_pr reader of ## PR.
- B24 package retro/done-ticket step 9 (l.~583) "review its local deletions and audit log" and Inbound references (l.~279) "coga delete publishes only the task and the log" — on the branch coga delete only removes the directory and writes no log line.

Acceptance: after #1279/#1280 merge (or on their branch before merge), each claim above matches the code, verified by a grep per named symbol; coga validate --json shows no new issues; tests/test_packaging.py passes. Any item the migration PRs already fixed is dropped with a note.

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
        - name: open-branch
          run: git/open-branch               # Local-first skill directory containing run.py.
          assignee: agent
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (open-branch)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
A workflow run: selects a script for its step. A sibling ticket.py supplies the default script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

The recurring runner writes delegate on materialized period tickets. It
names the parent template's frozen bootstrap/<name> target.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev records branch:, base:, remote:, reviewed: (the commit OID),
and pr: (the full /pull/ URL). Write one field per line and omit unknown
values. coga/git owns the fields and the workflow that writes them.

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

branch: coga/fix-stale-doc-references-left-by-the-plain-git-m-bc5100
base: coga/correct-three-stale-doc-claims-that-pr-1279-also-abb6b6
remote: origin
reviewed: e9f49b2089c16f76a0c734e8e61be8516c5240bf


## Implement handoff

Commit 742370dd4 on top of the PR #1280 tip (origin/coga/v1-no-weird-state-in-personal-dir-d9bd4b is an ancestor) and the recorded base. The migration is not on origin/main yet (src/coga/git.py still exists there), so this branch must merge after #1279/#1280.

Every item B1-B24 was still live on the branch and was fixed. None had already been fixed by the migration PRs. Decisions:
- B22: kept the `coga-dev/internals/spool-merge` ref. The shipped `coga/usage` links to it by GitHub main URL, so renaming it would break installed copies. Fixed the description and added the encoding and union facts to the body instead.
- B21: `period_generation`/`launch_generation` are now obsolete (validate `obsolete-key`). recurring-admission says so, and coga/recurring/templates no longer claims the creator stamps or rejects it.
- Extra fixes in the same family: gotchas mark_* now validate before writing; current-direction autoclose mentions; stale docstrings or comments in compose.py, launch.py (`_publish_startup`), validate.py (`--check-github`), taskfile.py, workflow.py, aliases.py, recurring_autofix.py, skill_update_pr.py.

Remaining work for follow-up tickets (not done here):
- src/coga_edge/validate_drift.py:357,371 messages and tests/fixtures/seeded-repo (trim-log/operations.md, tasks/blackboard-state-cleanup.md) still name the deleted `coga/state-publication`.
- Vestigial code: `mark_active(sync_state=)`, `spawn_agent_session(commit_log=)`, the unused `preflight_post` import in launch.py, and the `repl_supervisor_nt` module docstring describing a gate the supervisor no longer arms.

Scratch: one dedicated `mktemp -d -p /tmp coga-verify.*` dir held pytest temp space for a rerun with TMPDIR outside the repo. It was deleted after the run (the base prompt allows a disposable dir under system temp).

## Incident: the implementation test run uninstalled parts of this checkout

`.venv/bin/python -m pytest -q`, run during implement with the launch's TMPDIR inside the repo (`coga/.coga/tmp/<token>/`), ran `tests/test_uninstall.py::test_uninstall_outside_repo_errors`. That test assumes `tmp_path` is outside any repo and runs `coga uninstall --yes` from it. It found this repo and ran `_execute_plan`: it removed the docs/contexts root, then `shutil.rmtree(coga/)` partway before bailing (tasks/, recurring/ and skills/ survived).
- Restored from HEAD: coga/{.gitattributes,.gitignore,coga.toml,context.md,log.md,workflows/} and every tracked file under docs/contexts/ (including this ticket's committed edits).
- Lost, not in git: coga/coga.local.toml (validate now reports `missing-user`), coga/.coga/data/ (durable agent state), coga/.coga/megalaunch-selection.json, the uncommitted coga/log.md lines added since c306d14d1, and any ignored files under coga/ or docs/contexts/. I did not recreate coga.local.toml (agents may not edit it).
- The local config is present again, as confirmed during peer review. The separate `correct-three-stale-doc-claims-that-pr-1279-also-e` ticket records its restoration. Lost uncommitted audit lines and durable state are still recorded above.
- Follow-up: make the uninstall "outside repo" test (and the temp-sensitive tests in test_run_state, test_oscompat and test_launch_script) independent of an in-repo TMPDIR, for example by pinning the test's cwd under a verified non-repo root or setting `GIT_CEILING_DIRECTORIES`. Until then, run the full suite with TMPDIR outside the checkout.

## Peer-review handoff

Codex reviewed all 38 files against the recorded base at `5edf21b45`. The
branch contains #1280 at `c306d14d1`. #1279's `610efffd4` and #1280's
equivalent pre-run-state `c09a8e095` have identical code and live topic trees.
No B1–B24 item was already fixed by those PRs. The Python AST comparison
confirmed all nine source changes are docstrings or comments.

Review commits `9a32d780f` and `e9f49b208` correct remaining stale claims about
launch, recurring admission and Git operations. The Dream procedure retains
the legacy primary-checkout exemption and checks branches in that clone.
Clone-scoped scripts get temp space and shared data. Read-only scripts get
temp space. The Retro wording covers both file and directory task forms.

`git fetch origin` succeeded. The recorded base is the local branch of
`correct-three-stale-doc-claims-that-pr-1279-also-e`, which has no head on
`origin` and is itself at `push-and-open-pr`. This branch needs that base
published before PR creation. GitHub reports conflicts against the current
bases of #1279 and #1280. Refresh against the published base after the stack
is reconciled. The shared checkout also contains unrelated task changes.
Preserve them and use a clean checkout for publication.

## PR

```yaml
title: Fix stale doc references left by the plain-Git migration
author: claude
author_evidence: >-
  Claude Code (claude-opus-5-5) wrote 742370dd4 in launch 9304844e.
  Codex wrote 9a32d780f and e9f49b208 during peer review.
head: e9f49b2089c16f76a0c734e8e61be8516c5240bf
base: 5edf21b45b76c636aa90c7cbace2824b3f90e5e5
depth: skim
rationale: >-
  This documentation change is stacked on a local branch based on #1280,
  which is stacked on #1279. Review the Git eligibility probes and the
  publication dependency in the handoff.
implementation: >-
  Reconciles the B1–B24 claims with the post-migration code. Indexes seven
  internals pages and documents the temp and data environment of launch.
deviations: >-
  Keeps the spool-merge ref so the URL shipped in coga/usage keeps working.
  The review also corrected adjacent stale descriptions of launch and owner
  reassignment.
limitations: >-
  The validate-drift remediation strings and two seeded fixtures still cite
  coga/state-publication. Unused parameters and imports remain for follow-up.
  Native Windows and macOS verification is deferred to release.
files:
  docs/contexts/coga-dev/codebase/gotchas/SKILL.md: "B1 removed git/branchsweep/open_pr symbols and mark_* validation order."
  docs/contexts/coga-dev/current-direction/SKILL.md: "Drop autoclose-merged claims from live posture."
  docs/contexts/coga-dev/internals/SKILL.md: "B3 index all internals pages and fix the description."
  docs/contexts/coga-dev/internals/activity-capture/SKILL.md: "B2 teardown captures usage only."
  docs/contexts/coga-dev/internals/agent-spawn/SKILL.md: "B4 current phases, spawn and completion, and temp/data scope per launch route."
  docs/contexts/coga-dev/internals/assist-publication/SKILL.md: "B20 description matches the body."
  docs/contexts/coga-dev/internals/blackboard-io/SKILL.md: "B23 git/push-and-open-pr is the ## PR reader."
  docs/contexts/coga-dev/internals/compose/SKILL.md: "B5 no checkout notice."
  docs/contexts/coga-dev/internals/notifications/SKILL.md: "B6 live post and preflight_post callers."
  docs/contexts/coga-dev/internals/recurring-admission/SKILL.md: "B21 description and obsolete generation keys."
  docs/contexts/coga-dev/internals/recurring-clone/SKILL.md: "B7 per-checkout clone state dir."
  docs/contexts/coga-dev/internals/spool-merge/SKILL.md: "B22 description, encoding and union driver."
  docs/contexts/coga-dev/microkernel/SKILL.md: "B8 live shared-infra example, no push-auth preflight, no exit 75."
  src/coga/aliases.py: "B18 drop the autoclose alias comment."
  src/coga/compose.py: "B5 compose_prompt_report docstring has no checkout notice."
  src/coga/launch.py: "Update activation and command refusal docstrings for local launch."
  src/coga/recurring_autofix.py: "B18 comment drops coga autoclose."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md: "B14 retire deletes without Retro."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md: "B11 drop --check-github."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/producers/SKILL.md: "B16 drop autoclose and branch-sweep producers."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md: "B17 drop deleted-topic self-links."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/autofix/SKILL.md: "B18 use the current aliases and local period ledger."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/SKILL.md: "B9 retires.md, run_when_inactive and shim shapes; period_generation is obsolete."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/sandboxes/SKILL.md: "B19 plain Git failure attribution."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/SKILL.md: "Remove obsolete generation and publication gates from owner reassignment."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/usage/SKILL.md: "B13 log.md uses merge=union."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md: "B15 closure via final bump or merge-pr."
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/knowledge-scan/SKILL.md: "B14 plain-Git live-checkout rule."
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md: "B10 live citation examples."
  src/coga/resources/templates/coga/bootstrap/skills/code/design/SKILL.md: "B10 live citation example."
  src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md: "B24 coga delete removes the task file or directory, without a log line."
  src/coga/resources/templates/coga/recurring/dream/ticket.md: "B14 Phase 4 live-checkout test in Git terms; retire deletes."
  src/coga/resources/templates/coga/recurring/resolve-conflicts/ticket.md: "B12 drop the branch-sweep ordering."
  src/coga/taskfile.py: "B23 comment names the git/push-and-open-pr reader."
  src/coga/usage.py: "Describe duplicate handling with the current union merge driver."
  src/coga/validate.py: "B11 docstring drops --check-github."
  src/coga/workflow.py: "Comment drops the step_gate -> autoclose cycle."
  src/coga_edge/skill_update_pr.py: "Document the existing fresh remote OID lookup without relying on removed helpers."
review:
  reviewer: codex
  kind: independent
  status: passed
  head: e9f49b2089c16f76a0c734e8e61be8516c5240bf
  base: 5edf21b45b76c636aa90c7cbace2824b3f90e5e5
  detail: >-
    Codex manually reviewed the entire recorded-base diff and verified symbols
    against the live code. Forty individual rg probes found zero remaining
    references to the removed symbols in live topics and package code. Ten
    added local link targets resolve. Claude implemented the original change
    in a separate session. Codex wrote and reviewed the corrections above.
checks:
  - command: "env -u COGA_SYSTEM_TMPDIR TMPDIR=/tmp/coga-peer-review.kVUHSt3i/final-tmp TMP=/tmp/coga-peer-review.kVUHSt3i/final-tmp TEMP=/tmp/coga-peer-review.kVUHSt3i/final-tmp TERM=dumb PYTHONPATH=/tmp/coga-peer-review.kVUHSt3i/final/src PATH=/home/n/Code/coga/.venv/bin:$PATH /home/n/Code/coga/.venv/bin/python -m pytest -q"
    status: passed
    head: e9f49b2089c16f76a0c734e8e61be8516c5240bf
    base: 5edf21b45b76c636aa90c7cbace2824b3f90e5e5
    detail: "3,190 passed, 29 skipped in 195.94s on Pop!_OS 24.04 LTS, Python 3.12.12. Temporary test data was outside every checkout."
  - command: "env -u COGA_SYSTEM_TMPDIR TMPDIR=/tmp/coga-peer-review.kVUHSt3i/final-tmp TERM=dumb PYTHONPATH=/tmp/coga-peer-review.kVUHSt3i/final/src /home/n/Code/coga/.venv/bin/python -m pytest tests/test_packaging.py -q"
    status: passed
    head: e9f49b2089c16f76a0c734e8e61be8516c5240bf
    base: 5edf21b45b76c636aa90c7cbace2824b3f90e5e5
    detail: "41 passed in 10.72s on Pop!_OS 24.04 LTS, Python 3.12.12."
  - command: "PYTHONPATH=<absolute-checkout>/src /home/n/Code/coga/.venv/bin/python -m coga.cli validate --json"
    status: passed
    head: e9f49b2089c16f76a0c734e8e61be8516c5240bf
    base: 5edf21b45b76c636aa90c7cbace2824b3f90e5e5
    detail: "Both clean checkouts exited 0 with the same 116 findings after normalizing checkout paths."
  - command: "git diff --check 5edf21b45 HEAD"
    status: passed
    head: e9f49b2089c16f76a0c734e8e61be8516c5240bf
    base: 5edf21b45b76c636aa90c7cbace2824b3f90e5e5
    detail: "No whitespace errors in the recorded-base diff."
```

---

## Blockers

- [ ] [2026-11-23 17:12] [agent:codex] id=20261123T171254 Publish the recorded base branch from correct-three-stale-doc-claims-that-pr-1279-also-e to origin. The peer-reviewed docs are ready, but push-and-open-pr requires that remote base to exist.
