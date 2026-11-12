---
title: Hold dirty context edits on feature checkouts until merge
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
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
step: 7 (review)
agent: claude
---

## Description

The end-of-command sweep (`sync_coga_state` in `src/coga/git.py`) publishes every dirty eligible file under the Coga roots to control, even when invoked from a feature checkout. With `[layout] contexts = "docs/contexts"`, an in-progress context edit on a feature branch lands on main before review. Observed 2026-11-11: commit 39e20683e "Sync coga state" carried an unreviewed `coga-dev/current-direction` paragraph from branch `add-code-agent-merge-workflow` describing a workflow that existed only in that branch's uncommitted files. coga/state-publication documents this as the "pre-review publication hazard" and today relies on the human committing first.

**Decision (owner, 2026-11-11, attended design session):** on a feature or detached checkout, dirty knowledge files — contexts, skills, workflows, shared config, recurring definitions — are **held for merge**, exactly as committed ones already are. Runtime state that must land promptly (tickets and everything else under the task directory, the log, recurring blackboards and machine-written siblings) keeps publishing. The change is **universal** (no `[git]`/`[layout]` policy key), and guided authoring gets **no exception**.

Why feature checkouts become the exception to "instruction edits land directly" (coga/state-publication "The Coga roots"): that rule was decided for edits made where Coga state lives, on control. On a feature checkout a knowledge edit is presumptively part of the branch's reviewed work. A committed copy already waits for merge. Today's outcome turns on whether the author remembered to commit before the next sweeping command, and forgetting publishes unreviewed instructions that every later launch composes. Holding the dirty copy makes "dirty" and "committed" agree on feature checkouts. Direct publication stays available by making the edit on control. The cost: a repo on the default `coga/contexts` that edits knowledge on a feature branch and wants it to land directly now sees it held, and checkout return refuses until the file is committed on the branch or redone on control.

### Acceptance criteria

- [ ] On a feature checkout (symbolic HEAD ≠ configured control) or a detached HEAD, a sweep (`sync_coga_state`) with a dirty context (including a relocated contexts root), skill, workflow, `coga.toml`, or `context.md` leaves that file off control, while the ticket and log writes from the same command land in the same publication.
- [ ] Under the recurring directory on such a checkout: a dirty exact state-only carrier `ticket.md`, a definition `ticket.md` whose region above the blackboard fence equals control's copy, and a `RUNTIME_STATE_FILES` sibling (`retires.md`) publish. A `ticket.py`, runbook, `jobs.toml`, a definition `ticket.md` whose above-fence region changed or that control lacks, and a deleted `ticket.md` are held.
- [ ] A held definition `ticket.md` is held whole, including any blackboard change in the same file, and is reported.
- [ ] Each publish call that holds files writes one stderr report naming every held path (repo-relative) with the remedy (commit it on this branch for review, or redo the edit on control). It writes the report once, not once per push retry, and also when nothing else publishes. A dirty held-class file whose bytes and mode already equal control is not reported.
- [ ] A control checkout's publication is unchanged: dirty knowledge still lands directly.
- [ ] `coga run publish-state PATH` naming a held file exits 1, stderr names the path as held for merge, and the task/log writes that came with it are not published, matching today's committed-file behavior. The no-path form exits 0 after publishing routine state and prints the held report.
- [ ] Guided authoring (`coga ticket`) on a feature checkout that authored a held-class file refuses the whole transaction through its existing `require_paths` refusal: nothing publishes, edits stay on disk, the command exits non-zero, the sweep is withheld, and the message names the held file and the remedy.
- [ ] Checkout return (and launch entry) from a feature checkout with a dirty held file refuses with exit 75 under the existing launch-boundary refusal contract. The refusal's blocking entry for that path says it is held for merge and gives the remedy. Chaining stops and the end sweep is withheld, as for any return refusal. A test proves the file was not published by the preceding step-1 sweep.
- [ ] Direct chat: the pre-`prepare-checkout` clean-checkout requirement on control is unchanged. A chat that leaves a held file dirty on its `coga/chat-<id>` branch ends with the existing exit-75 return refusal naming that file.
- [ ] Tests: `tests/test_git.py` (path classes, report, control unchanged, detached HEAD, recurring cases), `tests/test_publish_state.py` (named held file exits 1 with no accompanying publish; no-path form), `tests/test_checkouts.py` (return refusal names the held file, no publication), `tests/test_authoring.py` (authoring refusal). `python -m pytest` passes.
- [ ] The same PR updates every surface listed under *Proposed shape → Docs*, and `coga validate --json` passes.

### Proposed shape

**1. Classification (`src/coga/git.py`).** Add one predicate that decides whether a dirty path publishes from a non-control checkout, for example `_publishes_from_feature(cfg, root, base, rel) -> bool`:

- `True` when `_in_areas(rel, _routine_state_areas(cfg, root))`, which covers the task directory (all files, including `tasks/recurring/` periods, attachments, and a task-directory `ticket.py`) and the log. Reuse it rather than restating those paths.
- Under `recurring_dir(cfg)`, `True` for:
  - a direct child `<name>/<f>` with `f` in `recurring_state.RUNTIME_STATE_FILES`;
  - a direct child `<name>/ticket.md` whose working copy is an exact carrier (`recurring_state.carrier_problem(text) is None`);
  - a direct child `<name>/ticket.md` whose working text above the first `BLACKBOARD_FENCE` line (CRLF-normalized, as `carrier_problem` does) equals the same region of `tree_bytes(root, base, rel)`. Both copies must exist and contain a fence.
- `False` for everything else under the roots. Held paths are therefore defined as "under the roots and not routine", not as an enumerated list of knowledge directories. In the root layout this also holds ordinary source files on a feature branch.

**2. Selection.** `_publish_locked` already computes `adopt_only` from `symbolic_head(root) == control`. On a non-control checkout it also builds the predicate above (bound to `cfg`, `root`, and the attempt's `base`). It passes the predicate to `_candidates`, which drops failing **dirty** paths from `_dirty_paths` before the symlink filter and returns them separately as `held`. Held paths are not exempted for being named explicitly in `pathspecs`; authoring passes explicit paths and must still be held. The committed-path branch keeps its `adopt_only` filter unchanged. Prepared and pending ticket rels are under the task directory and are unaffected.

**3. Required-file refusal.** In `_publish_locked`'s `require_paths` loop, a required rel that is in `held` and differs from control (same `_tree_entry` comparison) raises `GitError` with a held-specific message, for example `"<rel>: held for merge on a feature checkout and differs from control; commit it on this branch for review, or redo the edit on <control>"`. Other exclusions keep the existing ignore-rules message. Raising before any tree is built is what gives publish-state and authoring their refuse-everything behavior. `publish_state._publish_state` and `authoring.finalize_authored` need no logic change beyond surfacing that text.

**4. Reporting.** Report held paths that differ from the base's `_tree_entry` once per `publish()` call: from the first attempt in `_publish_locked`, or collected and written by `publish()`. Use stderr lines prefixed `[git] held for merge (<branch>|detached HEAD):`, then one remedy line. Do not append to `coga/log.md`; that write would itself publish. `coga status` already lists such files through `feature_sync_plan` (`manual`, "differs from control"/"not on control"). Verify that and leave it unchanged.

**5. Checkout return annotation.** `_plan_preparation` already refuses a dirty roots file that is not on the pinned control (`_published_proof`). When HEAD is not control and a blocking rel fails the step-1 predicate, render its blocking reason as held for merge with the remedy instead of the bare proof text. Do not change the decision logic, only the reason text. The predicate's `base` here is the pinned commit.

**6. Docs (same PR; package copies under `src/coga/resources/templates/coga/bootstrap/`).**
- `contexts/coga/state-publication/SKILL.md`:
  - "The Coga roots": direct landing applies from control; feature checkouts hold dirty knowledge.
  - "When Coga publishes": the sweep bullet; the guided-authoring bullet gets the feature-checkout refusal; "Ordinary manual edits".
  - "Control versus feature checkouts": replace the "Pre-review publication hazard" paragraph with the held-for-merge rule: path classes, the recurring whole-file rule, the report, and that return refuses. Keep a short heading or anchor so `code/self-qa` can cite it.
  - "Strict publication on demand": a named held file refuses.
- `contexts/coga/checkouts/SKILL.md`: "Start, work, end" step 2 ("left dirty, the sweep publishes it" becomes "is held and blocks return"); "Direct chat"; "Which checkout you invoke Coga from".
- `contexts/coga/checkouts/launch-boundary/SKILL.md` "Preparation and return" step 1: on a feature checkout the sweep lands routine state only, and step 3 refuses held files with the held remedy.
- `contexts/coga/checkouts/chat/SKILL.md` "Preparing the chat's branch": commit intended PR knowledge before the chat ends; dirty held files are not published and make return refuse.
- `skills/code/self-qa/SKILL.md` "Gotchas": re-point the citation to the new anchor and wording.
- `docs/contexts/coga-dev/internals/state-publication/SKILL.md`: add this owner decision (2026-11-11) beside the 2026-10-07 one, and describe the predicate.
- Grep for remaining restatements before finishing: "land directly", "sweep publishes", "Pre-review publication hazard", "publication hazard". Also check `coga/checkouts/manual`. No config docs, since there is no policy key.

**Order of work:** the predicate and its unit tests, then selection/required/report in `_publish_locked` with `test_git.py` cases, then publish-state and authoring tests, then the return annotation and `test_checkouts.py`, then docs.

### Out of scope

- A per-repo `[git]`/`[layout]` policy key (owner chose universal).
- Changing the committed-state boundary (`adopt_only`). For example, committed recurring blackboards still wait for merge.
- Any change on a control checkout.
- Moving held edits automatically: no stash, auto-commit, or transplant to control.
- New `coga status` output, beyond verifying the existing `feature_sync_plan` report covers held files.
- Writing held-file notices to `coga/log.md`.
- Splitting guided authoring's transaction, or giving it a bypass.

## Context

### Key facts and sources

- Direct publication of instruction edits is an owner decision of 2026-10-07 (`docs/contexts/coga-dev/internals/state-publication/SKILL.md`; user contract in coga/state-publication#the-coga-roots and #when-coga-publishes). This ticket narrows it for non-control checkouts only.
- `src/coga/git.py`:
  - `_publish_locked` sets `adopt_only = None if symbolic_head(root) == control else _routine_state_areas(cfg, root)` and passes it to `_candidates`, which applies it only to the committed `base..HEAD` diff. Dirty paths from `_dirty_paths` are never filtered today; that is the bug.
  - `_routine_state_areas` returns the task-directory prefix and the log path.
  - `_publish_locked`'s `required` loop raises `GitError("…required file is excluded from publication…")` before any tree is built. That refusal is the mechanism publish-state and authoring rely on.
- Callers that pass `require_paths`:
  - `publish_state._publish_state` passes `coga_root_paths(cfg)` as paths and the named files as `require_paths`.
  - `authoring.finalize_authored` passes the exact changed files as both paths and `require_paths`. A `GitError` there becomes `AuthoringError` (edits kept, sweep withheld).
- Checkout return/entry: `prepare_control_checkout` → `_plan_preparation`. For each status entry under `_state_areas`, `_published_proof` must show the file is already on the pinned control, or the path is added to `blocking` and the result is `refused` ("uncommitted changes would be lost…"). A held file can therefore never ride a switch onto `main`. Only the reason text changes.
- Recurring files: `src/coga/recurring_state.py`. `STATE_MARKER`, `CARRIER_PREFIX`, and `carrier_problem()` define the exact state-only carrier. `RUNTIME_STATE_FILES = {"retires.md"}` is the recognized runtime sibling set, and anything else in a parent directory is definition material. In this repo every `coga/recurring/<name>/ticket.md` is a carrier. `coga/recurring/jobs.toml` is job-enablement config (`recurring.JOBS_FILE`).
- `taskfile.BLACKBOARD_FENCE` is the fence line. `taskfile.split_body` splits a parsed body; the predicate compares raw text above the fence, frontmatter included.
- `feature_sync_plan` / `_feature_sync_obstacle` (`git.py`, used by `views.py`) already report feature-checkout dirty roots files that differ from control under `coga status`.
- Packaged doc sources: `src/coga/resources/templates/coga/bootstrap/contexts/coga/{state-publication,checkouts,checkouts/launch-boundary,checkouts/chat}/SKILL.md` and `.../skills/code/self-qa/SKILL.md`.

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

pr: https://github.com/FastJVM/coga/pull/1199
branch: coga/hold-dirty-context-edits-on-feature-checkouts-un-d9bafa


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design step (2026-11-11)

Spec written under `## Description` (Acceptance criteria / Proposed shape / Out of scope) and `## Context`. The owner was present and decided:
- **Universal**, no policy key. Dirty knowledge on a feature or detached checkout is held, the same as committed knowledge.
- **Guided authoring gets no exception.** Its existing `require_paths` refusal rejects the whole transaction.

Findings that shaped the design:
- Checkout return needs no new decision logic. `_plan_preparation` already refuses any dirty roots file not on pinned control, so a held file can't ride a switch onto main. Only the refusal reason text gains a held-for-merge remedy.
- publish-state and authoring get exit-1, nothing-published behavior for free from the `required` loop in `_publish_locked` once `_candidates` drops held dirty paths, provided explicit pathspecs are not exempt from the hold.
- Recurring dir: classify per file. Carrier, blackboard-only change to a definition `ticket.md` (above-fence region equals control's), or `RUNTIME_STATE_FILES` publishes. Everything else is held whole.

## Implement handoff (2026-11-11)

Commit `7ff2f3d99` on the branch, rebased on origin/main and pushed. No PR yet.

- `git._publishes_from_feature(cfg, root, base, rel)` is the one predicate. It covers routine areas, plus, under `recurring/<name>/`, a `RUNTIME_STATE_FILES` sibling, a carrier only where control has none or has a carrier (must-fix 1), and a definition `ticket.md` whose above-fence region equals control's. `_publish_locked` passes it to `_candidates` off control, and held dirty paths go into `held`. The first attempt writes one stderr report (`[git] held for merge (<branch>|detached HEAD): <rel>` lines plus a remedy line) for held paths that differ from base by `_tree_entry`. The `require_paths` loop raises a held-specific `GitError`. `_plan_preparation` only rewords blocking entries (`<rel> (held for merge on '<branch>': <proof>; <remedy>)`).
- Exit contract per must-fix 2 is unchanged: entry refuses with 75, ordinary return keeps the session result but stops chaining and withholds the sweep, and direct chat keeps its conditional 75 (covered by a new chat test).
- Existing tests revised to the new behavior, keeping their control cases: the sweep/every-eligible test, the recurring runtime test, prepare-cleans (split into a feature-refusal test and a control-clean test), symlinked skill dir (now parametrized feature/control), authoring relocation, the checkout-return config reload, recurring re-adoption (now uses a blackboard-only write to model prior publication), the package-edit sweep, and the launch diagnostics test (fixture moved under the task directory).
- Docs: state-publication gets a new `### Held for merge on feature checkouts` section that replaces "Pre-review publication hazard". Also updated: checkouts, launch-boundary, chat, manual, reconciliation (remedy for held files), the self-qa citation, the coga-dev internals owner decision 2026-11-11, and the coga-dev packaging note.
- Not changed: `coga status`/`feature_sync_plan`. The authoring bail text still suggests `coga run publish-state` generically; the held error text before it carries the actual remedy. That is a possible follow-up wording polish, not a defect.
- Native Windows receipt is still needed before merge: the change is platform-sensitive (Git modes and CRLF in the above-fence comparison).

## Peer review

Direct review **completed** by Codex on final head `e4e72af3dd542e079798354b40407bce44f0dbff`, base `f8b85ace2ecb4e88b54ad5fa229911a0d6b86989` (2026-11-11). Codex independently reviewed Claude's original implementation; the fixes below are Codex-authored and self-reviewed. No nested reviewer or subagent was invoked. No unresolved code findings.

- **Fixed reporting bug.** On a rejected push, a concurrent recurring-definition edit can make a previously publishable blackboard update held on the next attempt. Reporting only on attempt zero silently omitted that path. Reproduced using a real competing commit, then fixed in `e4e72af3d`: accumulate differing held paths on every attempt and emit one report from `publish`'s `finally`, including required-file refusals. The owner approved the fix. Added regressions for routine publication after retry and required-file refusal; focused tests: 3 passed, 377 deselected in 1.72s. The original reproducer now reports the held path correctly.
- **Corrected the owning internals leaf** in `e7e72d08d`: it still described unfiltered dirty selection. It now names the hold predicate and links to the owning classification explanation.
- **Terminal check completed** at 80x24 and 40x12 on the final head. Named context: exit 1, readable held path/remedy, no accompanying publication. No-path form: exit 0, ticket lands, context remains held and is reported once. Existing `feature_sync_plan` lists the context as `differs from control`. Scratch scripts: `/tmp/coga-held-peer-review-terminal.py` and `/tmp/coga-held-peer-review-retry.py`. An initial scratch status probe needed the bare Slack variable unset; the corrected fixture and the final-head reruns passed.
- **Verification:** full Linux suite passed at the final committed head: **4799 passed, 33 skipped in 774.62s**, Pop!_OS 24.04 LTS, Python 3.12.12. Earlier pre-fix run deliberately interrupted before changing source, with no passed receipt claimed. Final-head validation passed: 113 OK, no errors, 12 existing warnings. Detailed commands and receipts are in `## PR`.
- **Windows explicitly deferred by owner** in this attended peer-review session: "I defer the win check here". No instance provisioned; no native Windows pass claimed. Keep this omission visible for the human merge decision.
- **Reconciliation:** fetched origin/main and rebased unconditionally, preserving and byte-verifying the projected ticket through `/tmp/coga-held-peer-review-ticket.md`. Final fetch after the suite reached 90% still matched the reviewed base. Remote branch verified at the final head. Branch and review fixes pushed; the live ticket remains unstaged. Prepared recommendation: deep, with the owner-deferred Windows omission and the self-reviewed fixes disclosed. Ready for the mechanical PR-opening step.

## PR

```yaml
title: Hold dirty knowledge on feature checkouts until merge
author: claude/codex
author_evidence: Claude Code authored the initial implementation; Codex authored the peer-review documentation
  correction and the owner-approved retry-report fix and regressions.
head: e4e72af3dd542e079798354b40407bce44f0dbff
base: f8b85ace2ecb4e88b54ad5fa229911a0d6b86989
depth: deep
rationale: Changes publication selection for every non-control checkout and narrows an owner decision.
  Inspect the recurring per-file boundary and transaction refusals. Native Windows verification was explicitly
  deferred by the owner; the Codex-authored review fixes are self-reviewed.
implementation: Adds _publishes_from_feature and filters dirty non-routine files on feature and detached
  checkouts. Reports differing held paths once per publish call, including files first held after a push
  retry; required held files refuse publication atomically. Checkout blocking entries explain the hold
  and remedy. Control publication and launch exit contracts are unchanged.
deviations: 'Owner resolved the evaluator must-fixes at implement start: a carrier publishes only where
  control lacks the file or holds a carrier, and the launch exit contract is unchanged (entry 75; ordinary
  return keeps its result).'
limitations: Native Windows full suite explicitly deferred by the attending owner on 2026-11-11; no Windows
  pass is claimed. Codex independently reviewed the original Claude implementation but self-reviewed its
  own small reporting and documentation fixes. coga status remains unchanged and does not report held
  files on detached HEAD or without a remote-tracking control ref.
files:
  src/coga/git.py: Hold predicate, selection, required-file refusal and checkout wording; collect held
    paths across retries and report once on return or exception.
  tests/test_git.py: Path classes, detached HEAD, report-once/control cases; actual competing-definition
    retry regressions for successful publication and required-file refusal.
  tests/test_publish_state.py: Named held file refuses with nothing published; no-path form reports held.
  tests/test_authoring.py: coga ticket on a feature checkout refuses held knowledge and withholds the
    sweep.
  tests/test_checkouts.py: Return refuses a held context without publishing it; direct chat ends with
    exit 75.
  tests/test_launch.py: Keep diagnostics fixture publishable by moving it under the task directory.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md: Held-for-merge
    contract replaces the pre-review hazard.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md: Work step, direct chat,
    and invoking-checkout rule.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/launch-boundary/SKILL.md: Return
    steps 1 and 3 for held files.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/chat/SKILL.md: Commit PR knowledge
    before the chat ends.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/manual/SKILL.md: Held files belong
    in the branch commit.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/reconciliation/SKILL.md: Held files
    cannot be published from the branch.
  src/coga/resources/templates/coga/bootstrap/skills/code/self-qa/SKILL.md: Re-point the citation to the
    new anchor.
  docs/contexts/coga-dev/internals/state-publication/SKILL.md: Record the 2026-11-11 owner decision and
    the predicate.
  docs/contexts/coga-dev/packaging/SKILL.md: Update the commit-before-sweep note.
  docs/contexts/coga-dev/internals/state-publication/publish/SKILL.md: Correct the publication primitive
    leaf to describe filtered dirty selection and link to the owning classification rules.
review:
  reviewer: codex
  kind: self
  status: passed
  head: e4e72af3dd542e079798354b40407bce44f0dbff
  base: f8b85ace2ecb4e88b54ad5fa229911a0d6b86989
  detail: Direct review completed on the final diff. Independently reviewed Claude's implementation, reproduced
    and fixed a missing notice when a recurring file first became held after a push retry, and corrected
    the publication leaf. Those Codex-authored fixes were self-reviewed; there was no second reviewer
    or nested review tool. No unresolved code findings. Native Windows verification deferred by owner.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest -q -p no:cacheprovider
  status: passed
  head: e4e72af3dd542e079798354b40407bce44f0dbff
  base: f8b85ace2ecb4e88b54ad5fa229911a0d6b86989
  detail: 4799 passed, 33 skipped in 774.62s (12m54s). Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic,
    Python 3.12.12. Full run at this committed head. Earlier pre-fix run intentionally interrupted before
    source changes; it is not a passed receipt.
- command: PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest -q -p no:cacheprovider
    tests/test_git.py -k 'held_report'
  status: passed
  head: e4e72af3dd542e079798354b40407bce44f0dbff
  base: f8b85ace2ecb4e88b54ad5fa229911a0d6b86989
  detail: 3 passed, 377 deselected in 1.72s. Ran on the uncommitted tree subsequently committed unchanged
    at this head.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/coga validate --json
  status: passed
  head: e4e72af3dd542e079798354b40407bce44f0dbff
  base: f8b85ace2ecb4e88b54ad5fa229911a0d6b86989
  detail: Exit 0; 113 OK, zero errors, 12 existing warnings.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /tmp/coga-held-peer-review-retry.py
  status: passed
  head: e4e72af3dd542e079798354b40407bce44f0dbff
  base: f8b85ace2ecb4e88b54ad5fa229911a0d6b86989
  detail: 'Real competing definition update forces a second attempt: ticket publishes, local blackboard
    update remains held, and stderr names its path once with the remedy.'
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /tmp/coga-held-peer-review-terminal.py
  status: passed
  head: e4e72af3dd542e079798354b40407bce44f0dbff
  base: f8b85ace2ecb4e88b54ad5fa229911a0d6b86989
  detail: 'Real PTY at 80x24 and 40x12: readable held path/remedy, named-file exit 1 with control unchanged,
    no-path exit 0 with routine ticket published and knowledge held. Existing feature_sync_plan reports
    differs from control.'
- command: 'Native Windows: uv run --directory coga-work python -m pytest'
  status: not-run
  detail: 'Attending owner explicitly deferred Windows verification in this peer-review session: "I defer
    the win check here". No instance provisioned.'
```

## Implement-step decisions (owner, attended, 2026-11-11)

review-design advanced without recording resolutions; the owner answered at the start of implement:
- Evaluator must-fix 1 adopted: an exact carrier `ticket.md` publishes only when control lacks the path or control's copy is itself an exact carrier. Replacing a control definition with a carrier is held whole (regression test).
- Evaluator must-fix 2 adopted: no launch-result change. Entry refusal exits 75; ordinary return keeps the session's own result while stopping chaining and withholding the sweep; direct chat keeps its existing conditional exit 75.
- Open Questions 1-3: proposed answers accepted (keep the above-fence comparison; stderr-only report; root layout holds non-routine source too).

## Open Questions

1. **Definition `ticket.md` blackboard-only writes from a feature checkout.** The spec publishes them when the above-fence region equals control's. Recurring runs normally execute on control or the temporary control worktree, so this case is rare. The simpler alternative holds every non-carrier `ticket.md` on a feature checkout. Proposed: keep the comparison. It is a few lines and avoids a spurious return refusal.
2. **No log line for held files.** The spec reports on stderr only, because a log write on a feature checkout would itself publish, and `coga status` already lists the files. Confirm stderr plus status plus return refusal is enough to satisfy "never silently stranded".
3. **Root layout.** With "held = under the roots and not routine", a repo whose Coga root is the checkout also stops publishing dirty source files from feature branches. That looks like a strict improvement, but it is a visible change for root-layout repos. Confirm.

## Evaluator review

**Verdict: resolve two must-fix findings before implementation.** The revised spec addresses the prior review's policy, checkout-proof, recurring whole-file, documentation, and objective acceptance concerns. Its body regions compose correctly. The remaining issues are a definition-removal escape through carrier recognition and a contradictory command exit contract.

### Must fix

1. **Carrier recognition can publish removal of a recurring definition.** Proposed shape 1 accepts a working `ticket.md` whenever `recurring_state.carrier_problem(text) is None`, without checking what control holds. Consider control and HEAD containing a full local recurring definition, with the feature checkout replacing it, uncommitted, with `recurring_state.render_carrier(...)`. The predicate accepts the working carrier and publishes away the schedule, workflow, and instructions. This contradicts the intent to hold recurring definition changes, including deletions. Evidence: `src/coga/recurring_state.py`'s `carrier_problem` checks only the incoming prefix and fence count; `inspect_parent_dir` distinguishes a full local definition from a carrier; `src/coga/git.py`'s `_guard` permits replacement when control equals the HEAD provenance, so it supplies no later defense. Restrict the unconditional carrier case to a missing control path or an existing exact control carrier; replacing a control definition with a carrier must be held whole. Add an objective criterion and regression for that conversion while retaining coverage for initial carrier creation and carrier blackboard updates. If definition-to-carrier conversion is intentionally allowed before review, the owner must explicitly accept that exception instead.

2. **Ordinary checkout return does not have the asserted exit-75 contract.** The checkout-return criterion groups return and launch entry as exit 75, but Proposed shape 5 allows only reason-text changes and the criterion describes this as existing behavior. Evidence: `src/coga/launch.py`'s `_LaunchCheckoutBoundary.settle` returns `False`, withholds the sweep, and says the session's own result stands; `_LaunchInvocation._supervise_steps` stops chaining after a successful child without converting its result to 75. `_launch` applies that conversion specifically to an otherwise successful direct chat. `contexts/coga/checkouts/launch-boundary/SKILL.md`, "Preparation and return", likewise distinguishes entry exit 75 from ordinary return's preserved session result. Narrow acceptance to entry exit 75, ordinary return preserving its session result while stopping chaining/withholding the sweep, and direct chat's existing conditional exit 75 (preexisting nonzero results remain unchanged). Alternatively, explicitly scope and justify a launch-result change, with source and tests; it is not obtained through the proposed annotation alone.

### Optional recommendations

- Add `contexts/coga/checkouts/reconciliation/SKILL.md`, "Sync a feature branch with control", to the docs pass. Its differing-file remedy currently starts with `coga run publish-state`; after this change that command cannot land held knowledge. Point such files to committing/review or manual reconciliation, preserving the existing proof requirements.
- Qualify the status claim: `git.feature_sync_plan` returns `None` for detached HEAD and when no remote-tracking control ref exists. Keeping status unchanged is coherent, but stderr and the boundary refusal carry the diagnostic in those cases.
- Name existing tests to revise as well as new tests to add: `tests/test_git.py::test_sweep_publishes_every_eligible_file_under_the_coga_roots`, `test_sweep_publishes_dirty_recurring_runtime_files`, and `test_prepare_cleans_a_published_context_and_skill_from_a_feature_checkout` currently encode the publication behavior being changed. Preserve their control cases. Git mode/line-ending coverage also falls under the native Windows receipt requirement in `coga-dev/testing` before merge.

### Checked claims and scope

- `_candidates` currently filters only committed adoption through `adopt_only`; dirty paths bypass it. `_publish_locked` performs the required-file check before tree construction, supporting strict publish-state and authoring's whole-finalization refusal. `authoring.finalize_authored` and `commands.ticket._run_authoring_session` surface the error and withhold the sweep as described.
- `_plan_preparation` uses `_published_proof` before cleanup, so a differing held regular file already refuses without new checkout decision logic. Preserve staged-version and nonregular-file diagnostics when adding the held remedy.
- The predicate has two real core consumers (publication selection and checkout annotation), fitting the microkernel rule. This remains one coherent PR; no policy key or guided-authoring exception is needed to implement the owner's recorded decision.
- The frozen workflow matches packaged `code/design-then-implement`: this evaluation hands findings to owner `review-design`, which resolves findings and the preserved Open Questions. The body is sufficiently concrete to implement after the two corrections; no additional attached context is necessary.

Reviewed source, tests, workflow, and owning documentation against `f12937d9388457ecd8db9dd53887333003a40ea3` (fetched `origin/main`). No implementation or ticket-body edits were made; no tests were run for this design-only review.
