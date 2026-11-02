---
title: Chat ticket edits strand the checkout on a chat branch
status: in_progress
owner: nicktoper
contexts:
- coga-dev/principles
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
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 5 (open-pr)
agent: claude
launch_generation: 950b8483-13d8-47d9-b7bf-9daf75536c16
---

## Description

Diagnose and propose a plan; implement only after the owner approves the design.

On 2026-10-22, a `coga chat` prepared `coga/chat-2a1ab1e4c2ff` and staged
renames of the three `coga/tasks/windows-native/` tickets without committing.
Later working-file edits and lifecycle state reached control, but the index
still contained the original renamed copies. The checkout remained on the
chat branch, and subsequent chat and ticket launches refused with "staged
content is not the published version". A plain `git pull` had no upstream to
use. The owner committed and pushed the stale copies as `df32b96df` to recover.

Routine ticket work should not require a code branch or a redundant commit
to leave the checkout usable. A failed return must make both the retained
work and the next safe action apparent. The design below separates the
reproduced refusal mechanism from the still-unverified original teardown.

### Diagnosis and evidence

1. **The index was a third version.** `df32b96df` has parent `1c4ecb1ea`
   (the 15:17:24 PDT chat launch-log commit) and contains three 100%-identical
   renames, with no content edits. Before that recovery commit at 15:21:35,
   control had `4d9e9a85b` at 15:20:47 (ticket 01 under its new name, at step 4)
   and `6717f3d2e` at 15:20:50 (the remaining renames and old-path deletion).
   Comparing the three new paths at `df32b96df` with `6717f3d2e` shows only
   control's newer cross-references and ticket 01's step advancement. The
   recovery commit was not missing implementation that needed a PR.
2. **Publication already goes to control, independently of the chat branch.**
   In `src/coga/git.py`, `sync_coga_state()` calls `publish()` over
   `coga_root_paths()`. `publish()` uses working-file contents and a temporary
   index; it does not commit the chat's index. A feature checkout therefore
   keeps both its working dirt and its independently staged version after a
   successful publish. The branch requirement comes from
   `src/coga/compose.py`, `CheckoutNotice.render()`, which currently instructs
   chat to prepare before editing **any** file; it is not a publication
   requirement.
3. **Return correctly refuses an unproved staged version.** In
   `src/coga/git.py`, `prepare_control_checkout()` calls `_plan_preparation()`.
   That planner requires each staged entry to equal the same path at HEAD
   or pinned control before calling `_published_proof()` on the working
   file. A renamed destination is absent at HEAD, and its staged bytes
   predate control's edits, so neither comparison passes. It does not infer
   that the destination is harmless because its blob existed at a different
   source path. Repeating publication cannot repair this index mismatch.
   An isolated reproduction using the incident's actual three file versions
   produces all three refusals while every working file equals control.
4. **Missing warning code is not established.** Both the source at
   `1c4ecb1ea` and current `src/coga/launch.py`, `_CheckoutBoundary.settle()`,
   publish before returning, print a prominent refusal, stop further
   settlement/chaining, and withhold the final sweep. Current
   `_LaunchInvocation._supervise_steps()` nevertheless returns success after
   a successful agent whose checkout return refused. Its generic warning
   also says remaining changes were "not published", which is misleading
   when working files landed but the index blocked cleanup. The durable
   `coga/log.md` usage record for session
   `756df393-1c1e-4dee-b05e-47ab8d002ede` says natural exit 0 at 15:20:22;
   the ticket publications above occurred later. That record describes the
   agent, not proof that the supervisor completed teardown. Original stderr
   and the running installation/version were not found in local `.coga/`
   records. An interrupted, different-version, or otherwise failed initial
   finalizer remains unverified; do not claim the staged check alone explains
   why that first chat failed to publish or display a warning.

### Options and tradeoffs

| Option | Benefit | Cost / decision |
| --- | --- | --- |
| Keep a branch for every chat edit; add instructions not to stage state and improve refusal text | Smallest policy change; preserves today's first-edit rule | Routine ticket work still allocates an unnecessary branch; an accidental `git mv` can still strand it. Viable fallback if the owner rejects the recommended branch policy. |
| Keep routine state-only edits on control; prepare a branch when work needs a PR; keep strict cleanup and add actionable failure reporting | Matches the existing publication boundary, prevents the common staged-ticket workflow, and preserves unknown work | Requires clear handling of a chat that moves from ticket edits to code. Direct state edits receive no pre-merge review, as already specified today. **Recommended.** |
| Automatically commit/push leftovers at chat end, or require all state to go through PRs | Makes branch dirt durable, or introduces pre-merge review | Commits can capture stale lifecycle fields or unwanted partial code; state-only commits are redundant with publication. PR-only state would redesign lifecycle/publication and delay shared task state. Do not adopt here. |
| Automatically drop anything that appears older, or treat historical blob presence as sufficient proof | Could recover more old checkouts without intervention | An older staged draft can still contain intentional, unique work. Publication provenance is not a semantic subsumption proof. Keep this out of the initial fix; any future relaxation needs a separately reviewed exact proof. |

### Recommended behavior

Use the second option, subject to owner review:

- A discussion or routine Coga-state-only chat stays on current control.
  Agents leave state unstaged, including renames: use a filesystem move and
  let publication detect deletion/addition, rather than `git mv` or `git add`.
  Publication remains through lifecycle commands, the existing sweep, or
  strict `coga run publish-state`; agents never hand-edit the log.
- The boundary is the **configured Coga and contexts roots**, not filename
  extensions and not a hard-coded `coga/` prefix. Code and docs outside those
  roots use the chat branch and a PR. Contexts, skills, and workflows inside
  the roots already publish directly. Implementation or deliberately reviewed
  knowledge prepares the branch before editing and commits the intended PR
  files, together with packaged twins where applicable, before a sweeping
  command. Placement inside a root does not exempt code from that procedure;
  committed routine task/log/recurring paths still follow today's adoption
  rules and are not promised PR isolation by this change. This preserves the
  existing publication/review tradeoff rather than silently redefining it.
- Before the first edit that needs the branch, strictly publish any pending
  routine state, require success and a clean checkout, then run the notice's
  exact `prepare-checkout --session ...` command. The no-path publish recipe
  covers deletions; named paths require surviving files but do not restrict
  the sweep. Failure stops this transition. The prepare recipe itself remains
  non-sweeping. Once on the branch, state can still publish from there; do not
  hop between branches for each kind of edit or promise a return after each
  conversation turn. Explicit knowledge review must be chosen before writing
  that knowledge on control.
- Keep the current cleanup proof. Exact published working/index copies and
  the existing union-log proof can already be cleaned automatically. A
  differing index or working version is preserved until reconciled. Label
  observations precisely: "working file matches control; staged copy differs"
  is a fact; "superseded" needs history/content review, not merely a newer
  control commit or a merged PR. No automatic commit, stash, reset, drop,
  branch deletion, or push of source work.
- A direct chat whose agent succeeds but whose armed checkout return refuses
  or fails exits **75**, with an actionable stderr handoff naming the branch,
  control target, and blockers. Keep the actual agent result in usage records;
  preserve a pre-existing nonzero agent/timeout/signal result. Ordinary task
  launch and delegated/recurring result contracts are unchanged. The direct
  `launch bootstrap/orient` spelling follows the same policy as `chat`.

### Acceptance criteria

- [x] A state-only direct chat can edit and rename tickets without creating a
  chat branch. Successful finalization publishes the new paths and prose,
  removes the old paths on control, and leaves a clean checkout on current
  control, including the usage log. Discussion-only behavior remains valid.
- [x] A chat that starts with routine state edits and then needs code or a
  reviewed knowledge edit publishes the former before preparing its reserved
  branch. Tests verify state reaches control, source stays on the branch,
  repeated preparation remains safe, and failed publication never causes a
  switch. Root-layout and relocated-context examples use configured roots.
- [x] Entry and return diagnostics distinguish an index-only mismatch from
  a working-file mismatch. The staged-rename reproduction reports that the
  working files are already on control while the staged copies differ; it
  preserves HEAD, index, files, and branch refs on refusal, apart from the
  documented fetch/publication preceding the cleanup planner.
- [x] Refusals provide configured, copyable inspection commands, backup and
  conditional recovery instructions, and the original invocation to retry.
  They do not require a chat branch to have an upstream or imply it has a
  ticket/PR. Paths containing spaces or Git pathspec metacharacters are
  handled literally; command rendering follows the platform's shell rules.
- [x] A fresh direct-chat return refusal after agent exit 0 exits 75 and
  names the checkout left behind; a nonzero agent result retains its code.
  Tests cover normal exit, failure/interrupt cleanup, refusal first observed
  at final teardown, and the Python launch boundary. Usage retains the real
  agent outcome, the guard releases, and the exit sweep stays withheld.
- [x] Exact published renames/deletions still return successfully. Distinct
  staged drafts, differing working files, staged union-log versions without
  sufficient proof, dirty source, unsupported modes/symlinks/submodules,
  ignored collisions, and changed evidence during planning still refuse
  without partial cleanup. No historical-content or semantic-drop heuristic
  is introduced.
- [x] A failed entry starts no agent; a refused return stops chaining. A
  second chat cannot take an active chat's checkout. Ordinary task-launch,
  recurring/delegated, prompt-report, and Git-disabled/remote-less exemptions
  retain their contracts. Recovery never replays a lifecycle transition.
- [x] Owning contexts, chat instructions, generated notices, and packaged
  twins agree. Relevant real-Git and CLI tests, composition checks, and the
  packaging twin checks pass; record exact validation commands and results.

### Proposed shape

1. **Chat guidance and mixed-work ordering.** In `src/coga/checkouts.py`,
   `chat_notice()` supplies the root-aware policy to
   `src/coga/compose.py`, `CheckoutNotice.render()`. Replace the unconditional
   first-edit instruction for chat without weakening ticket projection
   notices. Update the `## Context` instructions of
   `src/coga/resources/templates/coga/bootstrap/orient/ticket.md`. Keep
   `src/coga/checkouts.py`, `prepare_chat_checkout()` and
   `run_prepare_checkout_recipe()`, strict about their live session, clean
   control entry, reservation, and idempotent reuse; do not turn preparation
   into an implicit sweep or introduce a filesystem watcher.
2. **Explain the proof failure.** Extend `src/coga/git.py`,
   `CheckoutPreparation` / `_plan_preparation()`, with enough structured
   observations for `src/coga/launch.py`, `_checkout_refusal_message()`, to
   distinguish the index and working tree without parsing English error
   strings. Use the same pinned revision, Git clean-filter semantics, mode
   checks, and literal paths as `_published_proof()`. A diagnostic probe must
   not weaken the planner or turn an unknown result into permission to clean.
   Keep these changes in shared checkout/publication infrastructure; no new
   command or `runner.RECIPES` entry is needed.
3. **Concrete recovery guidance.** `_checkout_refusal_message()` prints
   `git status --short --branch`, `git diff --cached --binary`,
   `git diff --binary`, and `git fetch <remote> <control>` inspection steps,
   with a pinned-control comparison for each blocking path (and explicit
   handling for untracked files). The linked launch-boundary recovery section
   explains saving HEAD, separate staged/unstaged patches, and copies of
   untracked files outside the checkout and verifying them. For a reviewed
   index-only duplicate whose working copy is published, give the conditional
   `git --literal-pathspecs restore --staged --source=HEAD -- <old> <new>`
   remedy, including both sides of a rename. This changes only the index;
   retry the original chat/launch so the boundary re-fetches and re-proves
   before cleanup. If working files differ, reconcile unique intent onto
   current control first under `coga/checkouts/reconciliation`; no blanket
   restore from control and no repeated bump. Never execute the suggested
   recovery merely because it was printed. Tailor wording for state versus
   source, and replace the blanket "remaining changes ... not published"
   claim with separate publication and checkout-return outcomes.
4. **Direct chat's command result.** In `src/coga/launch.py`, propagate an
   armed return's failure from `_CheckoutBoundary.settle()` and
   `_LaunchInvocation.return_checkout()` / `_supervise_steps()` to the direct
   `launch()` result boundary, including the final `finally` settlement.
   Base this on the current invocation's armed boundary outcome, not an
   ambient withheld-sweep flag left by an earlier Python API call.
   Use `LaunchBail(75)` for an otherwise successful direct chat; leave
   `LaunchResult`'s child-result meaning and nonzero exceptions intact.
   `src/coga/commands/launch.py`, `launch()`, already translates launch errors
   for the CLI. Keep `src/coga/cli.py`, `_should_sweep_coga_state()` and the
   withheld-sweep behavior consistent. Scope this to the direct entry route,
   not every delegated target whose slug happens to be `bootstrap/orient`.
5. **Tests and durable instructions.** Extend
   `tests/test_git.py`, around
   `test_prepare_refuses_staged_content_that_is_not_published()`, with the
   three-file staged-rename/edited-working-copy regression and its unstaged
   successful counterpart. Extend `tests/test_checkouts.py`, around
   `test_chat_discusses_on_control_then_prepares_and_reuses_one_branch()`,
   for state-only and state-then-code flows. Extend `tests/test_launch.py`,
   around `test_orientation_refusal_preserves_edits_and_explains_investigation()`
   and `test_orientation_returns_to_control_after_session_changes_branch()`,
   for chat teardown results and diagnostics. Keep the ordinary-launch
   result assertion in
   `test_launch_teardown_refusal_preserves_work_result_and_stops_chaining()`.
   Update composition/CLI coverage as needed. Change the owning
   `coga/checkouts/chat` and `coga/checkouts/launch-boundary` topics, reconcile
   references in `coga/checkouts` and `coga/state-publication`, and update
   packaged twins in the implementation PR. Do not rewrite current contracts
   as though this unapproved proposal already shipped.

### Out of scope

- Implementing before the owner approves this design, reopening or recovering
  the already-resolved incident branch, or changing the Windows tickets.
- A new state publication lane, broad PR requirements for Coga roots,
  automatic source commits/pushes, a recovery command, or a GitHub lookup in
  checkout preparation.
- Guessing whether old content is semantically superseded, relaxing index
  preservation, changing ordinary ticket-launch exit semantics, or expanding
  the chat occupancy guard to other launch types/manual Git.
- Retaining a new database of full session transcripts or proving which
  historical supervisor binary ran without evidence.

## Context

The diagnosis was checked against `main` at
`5cacaf7a88c8614a346e0a86153a0deec86e8911` on 2026-10-26. Verify symbols again
after reconciliation; commit IDs above identify historical evidence, not
runtime configuration.

- `coga/checkouts/chat` (`docs/contexts/coga/checkouts/chat/SKILL.md`) is cited
  rather than attached: read **Direct chat occupancy** and **Preparing the
  chat's branch**, which this ticket proposes changing. In
  `src/coga/launch.py`, `launch()` acquires `_orientation_checkout_guard()`
  for direct `bootstrap/orient`; `src/coga/checkouts.py`,
  `install_chat_session()`, reserves the identity used by
  `prepare_chat_checkout()`. Preserve that ownership chain.
- `coga/checkouts/launch-boundary`
  (`docs/contexts/coga/checkouts/launch-boundary/SKILL.md`) is cited rather
  than attached: read **Preparation and return** and **Checkout recovery**.
  `src/coga/launch.py`, `_CheckoutBoundary.enter()` and `settle()`, call
  publication before `src/coga/git.py`, `prepare_control_checkout()`;
  `_apply_preparation()` mutates only after `_plan_preparation()` and its
  evidence recheck pass. A refusal is not authorization to discard work.
- `coga/state-publication`
  (`docs/contexts/coga/state-publication/SKILL.md`) is cited rather than
  attached: read **The Coga roots**, **When Coga publishes**, **Control versus
  feature checkouts**, and **Strict publication on demand**. In
  `src/coga/git.py`, `publish()` selects via `_candidates()` and reads working
  bytes; `fast_forward_control()` updates control but leaves feature dirt.
  `src/coga/publish_state.py`, `run_publish_state_recipe()`, requires named
  files while publishing eligible changes from the full root set.
- `coga/sync` (`docs/contexts/coga/sync/SKILL.md`) is cited rather than
  attached: read **Sync layers — notifications and git** for the distinction
  between durable file writes, publication, and notifications; detailed Git
  behavior belongs to the preceding topic.
- `coga/checkouts/reconciliation`
  (`docs/contexts/coga/checkouts/reconciliation/SKILL.md`) is cited rather
  than attached: read **Preserve both sides** before designing or executing
  recovery. `src/coga/git.py`, `_provenance()` / `_guard()`, protect publication
  against a newer control copy; this proposal must not bypass them to clear
  the cleanup refusal.
- `coga-dev/testing` (`docs/contexts/coga-dev/testing/SKILL.md`) and
  `coga-dev/packaging` (`docs/contexts/coga-dev/packaging/SKILL.md`) are cited
  rather than attached: read **Which code you are actually testing** and
  **Canonical copies and twins**. The orient ticket is package-owned with no
  live override here. Canonical checkout topics have fallback twins under
  `src/coga/resources/templates/coga/bootstrap/contexts/`.

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

Previous ref: `chat-ticket-edits-strand-the-checkout-on-a-chat-br` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

## Design handoff — 2026-10-26

The spec, evidence, options, acceptance criteria, and proposed changes are under
Description; required reads and symbol relationships are under Context. Only
this ticket was edited. No implementation, task branch, manual Git commit, or
PR was made. Current contracts remain unchanged pending owner review.

Recommended: state-only chat edits stay on control and unstaged; mixed work
publishes routine state before branch preparation; retain the existing cleanup
proof; explain index versus working-file blockers with conditional recovery;
return 75 when an otherwise successful direct chat cannot return its checkout.
Do not widen this into a generic automatic-drop or state-review redesign.

## Evidence and verification

- Started on clean `main`; `git fetch origin main` and
  `git merge --ff-only origin/main` succeeded. Investigation baseline:
  `5cacaf7a88c8614a346e0a86153a0deec86e8911`.
- Historical comparisons: `git show --find-renames df32b96df --
  coga/tasks/windows-native` proves three content-identical renames. Compare
  the three destination blobs at that commit with `6717f3d2e`; their differences
  are newer control cross-references and ticket 01's step. These comparisons
  do not depend on the retired branch ref still existing.
- Isolated real-Git reproduction (no live checkout mutation): using
  `tests/conftest.py`, `init_git_repo()`, seed the old paths from
  `df32b96df^`, create a fixture branch, `git mv` all three to their new names,
  write each working destination from `6717f3d2e`, then call
  `src/coga/git.py`, `publish()` followed by `prepare_control_checkout()`.
  Publication succeeded; all three working files equaled control; all three
  staged destinations refused; status was unchanged by the refusal. In that
  reviewed fixture only, restoring the index from HEAD for both rename sides
  made the next preparation succeed on clean `main`. Scratch data is at
  `/tmp/coga-chat-rename-design-9v0fl4um`; the procedure and historical blobs
  above are sufficient to reproduce it without that local artifact.
- This command passed **6 tests** in 2.16s against current source:

  ```sh
  PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q \
    tests/test_git.py::test_prepare_refuses_staged_content_that_is_not_published \
    tests/test_git.py::test_prepare_cleans_published_untracked_and_deleted_state \
    tests/test_git.py::test_prepare_refuses_mixed_state_without_partial_cleanup \
    tests/test_launch.py::test_launch_teardown_refusal_preserves_work_result_and_stops_chaining \
    tests/test_launch.py::test_orientation_refusal_preserves_edits_and_explains_investigation \
    tests/test_launch.py::test_orientation_returns_to_control_after_session_changes_branch
  ```

- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate
  --task chat-ticket-edits-strand-the-checkout-on-a-chat-br --json` passed
  (one task, no issues). `git diff --check` passed. These validate the design
  artifact and existing behavior, not an implementation of this proposal.
- Read-only `src/coga/compose.py`, `compose_prompt_report()` with
  `launch_context="megalaunch"`, confirmed all six Description subsections and
  Open Questions compose. Structural assertions confirmed unchanged CLI-owned
  frontmatter, one blackboard fence, and the preserved ticket guide. An initial
  probe used the invalid label `queue`; rerunning with the actual supported
  context passed without changing launch state.
- Before handoff, fetched and inspected main's advance to `5cff2b912`, including
  the updated testing topic (CI paused; local step verification still required).
  No investigated source or this ticket changed upstream. Preserved and verified
  the edited ticket outside the checkout, restored its HEAD copy, fast-forwarded
  main, and reapplied identical saved bytes. No code-test rerun was needed for
  the unrelated state/documentation changes.

## Open Questions

1. Resolved at the owner gate on 2026-10-29: routine state-only chat edits
   stay on control; implementation and deliberately reviewed knowledge prepare
   a branch. The audit records human:nicktoper advancing to implement.
2. Resolved by that same approval: an otherwise successful direct chat whose
   checkout return fails exits 75; actual usage and existing nonzero results
   remain unchanged. Ordinary task transitions must not be replayed.
3. Historical evidence gap: original supervisor stderr and installed version
   are unavailable locally. Recover those only if an exact explanation of
   the first chat's missing finalization is required. The staged-index refusal
   is independently reproduced, and the proposed prevention/recovery changes
   do not depend on guessing the missing history. This is not a blocker to
   evaluating the design.

## Evaluator review

Reviewed on 2026-10-26, reconciled to `main` at `94d3dad35`.
**One must-fix before implementation.** The proposed branch policy,
diagnostics, and direct-chat exit contract otherwise form a coherent change.
The two explicit owner decisions remain for `review-design`; this review
does not approve them. Only this blackboard section was authored.

### Must fix before implementation

1. **P1 — Protect the distinct staged version during control publication,
   before the cleanup planner runs.** Recommended behavior promises that a
   differing index is preserved until reconciled, and Acceptance criteria
   require distinct staged drafts to refuse without partial cleanup. Keeping
   state-only chat on control exposes an earlier mutation that the proposed
   planner/diagnostic changes do not cover.

   In `src/coga/launch.py`, `_CheckoutBoundary.settle()` publishes before
   planning. In `src/coga/git.py`, `_publish_locked()` calls
   `fast_forward_control()` with the working/landed bytes; when this checkout
   holds control, `_stage_landed()` checks only that the working bytes still
   equal the bytes read, then runs `git add --all -- <path>`. It never proves
   the existing index version before replacing it. By the time
   `_plan_preparation()` runs, the staged draft can already be gone.

   **Reproduced with real Git:** seed a ticket on clean `main`, arm
   `_CheckoutBoundary.enter()`, stage a blackboard containing `unique staged
   intent`, then write different `working prose` without staging and call
   `settle()`. Return succeeds, `main` is clean, and control contains the
   working prose; the unique staged text is absent from both the index and
   control. Scratch fixture: `/tmp/coga-chat-evaluator-kf0i33x7`. This is
   existing control-publication behavior, not evidence about the historical
   supervisor. The existing
   `tests/test_git.py::test_prepare_refuses_staged_content_that_is_not_published`
   tests a feature checkout and calls preparation directly, so it cannot
   catch this path.

   **Required design correction:** specify how control publication preserves
   a distinct index before `_stage_landed()` changes it, and account for
   publication during the chat as well as at return. Retaining the cleanup
   proof or telling agents not to stage does not establish that protection.
   Add real-Git acceptance coverage for the complete publish-then-return
   path on control, with a distinct staged ticket draft and a staged rename
   whose working version changed. Working state may publish, but the staged
   version must remain preserved for the refusal/recovery path. Keep the
   unstaged success case and explicitly account for any effect on ordinary
   publication callers if this is fixed in shared infrastructure.

### Optional recommendation

- Consider independent implementation review for the Git preservation change.
  Main advanced during this evaluation and the packaged
  `bootstrap/workflows/code/design-then-implement.md` now includes
  `peer-review`, but this ticket's frozen six-step workflow still goes from
  `implement` to `open-pr`. The current template explicitly preserves that
  older behavior. Owner design approval will not imply code review; no
  workflow fields were changed here.

### Verified scope and evidence

- Description subsections and Context are correctly placed and sufficient
  to expose the proposal to the implementer. The frozen `evaluate-design`
  step hands off to the owner gate. The cited publication, launch, checkout,
  strict-recipe, composition, and test symbols exist. The proposed work
  belongs in the shared checkout/launch infrastructure and existing recipe
  contract; no new command or recipe is needed.
- Independently compared `df32b96df` and `6717f3d2e`: three identical-content
  renames, followed on control by cross-reference changes and ticket 01's
  step advancement. Source at `1c4ecb1ea` already has publish-before-return,
  refusal reporting, and sweep withholding. The original stderr/version gap
  remains appropriately qualified.
- Repeated the historical three-file experiment using
  `tests/conftest.py::init_git_repo()`: seed source paths from `df32b96df^`,
  stage the renames on a fixture branch, and write destinations from
  `6717f3d2e`. Publication succeeds; preparation refuses all three staged
  destinations while the working files equal control. HEAD, index entries,
  refs, and status remain unchanged by preparation. In a separate control
  fixture, filesystem renames plus the same working edits return successfully
  with all new paths published, old paths absent, clean `main`, and no chat
  branch. Fixtures: `/tmp/coga-evaluator-historical-i7deciqk` and
  `/tmp/coga-evaluator-historical-g7tw_2u7`. These exercise current mechanisms,
  not an implementation of the proposed guidance or exit code.

### Validation and reconciliation

Python 3.12.12; the following baseline command passed **13 tests** in 5.00s:

```sh
PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q \
  tests/test_git.py::test_prepare_refuses_staged_content_that_is_not_published \
  tests/test_git.py::test_prepare_cleans_published_untracked_and_deleted_state \
  tests/test_git.py::test_prepare_refuses_mixed_state_without_partial_cleanup \
  tests/test_git.py::test_prepare_refuses_when_evidence_changes_before_mutation \
  tests/test_git.py::test_prepare_uses_the_configured_remote_and_control_names \
  tests/test_checkouts.py::test_chat_discusses_on_control_then_prepares_and_reuses_one_branch \
  tests/test_checkouts.py::test_chat_recipe_refuses_a_dirty_control_checkout \
  tests/test_checkouts.py::test_chat_launch_notice_carries_the_exact_invocation \
  tests/test_launch.py::test_launch_teardown_refusal_preserves_work_result_and_stops_chaining \
  tests/test_launch.py::test_orientation_refusal_preserves_edits_and_explains_investigation \
  tests/test_launch.py::test_orientation_returns_to_control_after_session_changes_branch \
  tests/test_launch.py::test_second_chat_cannot_switch_an_active_chats_clean_feature_checkout \
  tests/test_launch.py::test_delegated_orientation_keeps_callers_checkout
```

Fetched main again and inspected its advance from `4d63f6826` to `18ec1d76a`.
The ticket, review skill, Git/launch implementation, and focused leaf
contracts were unchanged. Read the checkout-policy and workflow changes,
then ran `git merge --ff-only --no-stat origin/main` from the still-clean
checkout. Against the reconciled checkout this command passed **4 tests**
in 1.06s (three repeats plus the legacy-workflow check):

```sh
PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q \
  tests/test_checkouts.py::test_policy_supports_older_frozen_snapshots \
  tests/test_checkouts.py::test_chat_discusses_on_control_then_prepares_and_reuses_one_branch \
  tests/test_checkouts.py::test_chat_recipe_refuses_a_dirty_control_checkout \
  tests/test_checkouts.py::test_chat_launch_notice_carries_the_exact_invocation
```

Final fetch observed another advance to `94d3dad35`, concerning recurring
and blocker behavior. Inspected the lifecycle/mark changes and verified no
change to this ticket, the review skill, reviewed Git/launch/checkout code,
relevant tests, or checkout/publication contracts. Saved and byte-verified
the edited ticket outside the checkout, restored its HEAD copy,
fast-forwarded, and reapplied the identical review. No additional source-test
run was needed for those unrelated changes.

`PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task
chat-ticket-edits-strand-the-checkout-on-a-chat-br --json` reports one valid
task and no issues; `git diff --check` passes. Byte checks verify the
pre-existing ticket is intact, the only added content is this evaluator
section, there is one blackboard fence, and the index is unchanged. The five
relevant checkout/publication context pairs remain byte-identical. No
ticket-body edit, implementation, task branch, manual commit, or PR was made.

## Dev

branch: coga/chat-state-checkout-05

## Implementation — 2026-10-29

Owner approval is recorded in the audit: human:nicktoper advanced the owner
review-design gate to implement on 2026-10-29. The earlier open decisions
are approved by that transition; the original supervisor evidence gap remains
unresolved and is not needed for this fix.

Implement the proposed state-only chat policy, structured refusal diagnostics,
and direct-chat exit 75. Include the evaluator's preservation correction in
shared control publication: prove the existing index before staging landed
working bytes or advancing control, so an independent staged draft survives
publication during a chat and at teardown. Keep strict checkout proofs and
ordinary/delegated launch result contracts. Add regression coverage before
fixing behavior, update owning topics and packaged twins, run the full suite,
then commit, reconcile, push, return to main, and hand off without a PR.

### Current implementation and verification

Committed as `7e3acbee7b57a29c4231af5dc241a34a90b41032`; reconciled with
`origin/main` at `ef94eacb040f216b7b576d4b9fefe91f571b1091`.

- `src/coga/git.py`, `_stage_landed`, now checks the entire selected index
  against HEAD and the landed revision, then rechecks index and HEAD before
  any file is staged or rewritten. A distinct index keeps local control
  behind without undoing successful remote working-state publication. This
  applies to ordinary callers as well as chat; remote-less inability to move
  the only durable control ref remains a publication failure. Exact staged
  deletions use `update-index --remove`, including rename sources already
  absent from the index. No historical-content drop heuristic was added.
- `git.CheckoutObservation` carries pinned path/index/working observations
  for `launch._checkout_refusal_message`, without parsing error prose or
  changing cleanup permissions. Diagnostics include literal comparisons,
  explicit untracked hashes, configured fetch, backup instructions, conditional
  index-only recovery for reviewed duplicates, and the invocation to retry.
- `launch._launch` checks this invocation's armed boundary after all final
  settlement. A successful direct chat becomes exit 75 on failed return;
  actual child usage and nonzero results, ordinary task launch, and delegated
  routes keep their contracts.
- Chat notices and the orient ticket now keep unstaged routine state on
  control and require strict publication plus cleanliness before preparing
  implementation/review work. Owning topics and all five packaged context
  twins agree. Related real-Git fixtures cover nested, root, and relocated
  context layouts; the seeded repository schema does not change.

Regression-first run: 7 failures / 3 passes exposed overwritten staged copies,
missing structured observations/diagnostics, and successful chat exits after
refused return. The same 10 tests passed after the fix. A broader four-module
run had 758 passes / 3 failures in newly added fixture setup/assertions; those
fixtures were corrected, and the focused rerun passed 12 tests. Additional
index preservation and packaging checks passed 36 tests. The full suite at
`7e3acbee7b57a29c4231af5dc241a34a90b41032` passed 4337 tests, with 10 native
Windows skips. A final fixture-only portability correction produced
`85774628bc7127b025c3cf485806fb4977a45653`; its full checkout module passed
149 tests and packaging passed 31. Runtime code and docs are byte-identical
between these heads. The exact commands and per-run OIDs are retained below.

No independent code review has run in this implementation step. The frozen
workflow goes directly to open-pr; use advisory depth deep and retain this
review limitation. Original historical supervisor stderr/version remain
unavailable, as recorded in the design; this implementation makes no claim
to establish them.

### Handoff to open-pr

The evaluator's P1 is implemented in shared publication and covered through
publication during a chat and complete publish/return flows on control.
All acceptance items are implemented and verified on this branch. Reconciliation
found no intervening main changes; the no-op rebase kept the tested source.
The branch is pushed at `85774628bc7127b025c3cf485806fb4977a45653`, verified
against its remote-tracking ref. Strict ticket publication succeeded. The
published working ticket was byte-verified against `origin/main` and backed
up before restoring its branch copy; the manual return then left clean main
at `b23d0cfd4` before this final handoff update. The terminal bump publishes
this update and advances exactly once to open-pr.
Do not create another branch or repeat a lifecycle transition to publish state.

No implementation findings remain open. The historical evidence gap, absent
independent code review, and unexecuted Python 3.11/native Windows checks are
limitations, not claims of verification. The next step should publish this
branch with the deep preparation below; no PR was opened during implement.

## PR

```yaml
title: Keep routine chat state on control and preserve distinct staged drafts
author: codex
author_evidence: Actual implementer was Codex in this API session (GPT-6 family per session instructions).
  Exact model variant and override metadata were not exposed; the ticket-configured claude identity is
  not used as authorship evidence.
head: 85774628bc7127b025c3cf485806fb4977a45653
base: ef94eacb040f216b7b576d4b9fefe91f571b1091
depth: deep
rationale: Changes shared Git index preservation and direct-chat command results. No independent code
  review has run. Full-suite evidence is retained at its actual parent commit; the final fixture-only
  change has fresh checkout and packaging verification.
implementation: Routine state-only chats remain unstaged on control. Mixed work strictly publishes before
  preparing a branch. Shared publication preserves independent index versions before any selected staging.
  Refusals show pinned working/index facts, literal inspection and conditional recovery. Successful direct
  chats with failed checkout return exit 75 after all finalization; actual child usage and nonzero results
  remain unchanged.
deviations: Includes the evaluator-required shared publication guard and exact staged-deletion handling.
  No new command/recipe or cleanup heuristic. Retry guidance renders an equivalent canonical launch invocation
  with target, options and arguments.
limitations: Original historical supervisor stderr/version remain unavailable. No independent code review,
  Python 3.11 run, or native Windows execution. PowerShell literal rendering is unit-tested; the root
  fixture is ordered for Windows. The full suite was not repeated after the fixture-only chdir fix; all
  149 checkout tests and 31 packaging tests passed on the final head, and src/docs are identical to the
  full-suite head.
files:
  docs/contexts/coga-dev/internals/git-refresh/SKILL.md: Describe the all-path index check and evidence
    recheck before staging landed state.
  docs/contexts/coga-dev/internals/state-publication/SKILL.md: Link the direct-chat command-result exception
    without changing ordinary sweep contracts.
  docs/contexts/coga/checkouts/SKILL.md: Align the checkout overview with routine chat state on control
    and strict mixed-work ordering.
  docs/contexts/coga/checkouts/chat/SKILL.md: Own the state-only and reviewed-work chat policy plus direct-chat
    return exit 75.
  docs/contexts/coga/checkouts/launch-boundary/SKILL.md: Own index-versus-working observations, publication/return
    distinctions, and conditional recovery.
  docs/contexts/coga/launch/SKILL.md: Link the direct-chat checkout-return exception from the launch exit
    index.
  docs/contexts/coga/state-publication/SKILL.md: Document distinct-index preservation for every publication
    caller and remote-less failure semantics.
  src/coga/checkouts.py: Pass configured publication roots into the generated chat notice.
  src/coga/compose.py: Render routine-state guidance and publication-before-preparation ordering without
    changing ticket projection notices.
  src/coga/git.py: Protect independent staged versions before local integration, handle exact staged deletions,
    and expose pinned diagnostic observations without weakening cleanup proofs.
  src/coga/launch.py: Report configured literal recovery commands and direct-chat return failure after
    final settlement while retaining actual child results.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md: Ship the byte-identical
    fallback of docs/contexts/coga/checkouts/SKILL.md.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/chat/SKILL.md: Ship the byte-identical
    fallback of docs/contexts/coga/checkouts/chat/SKILL.md.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/launch-boundary/SKILL.md: Ship the
    byte-identical fallback of docs/contexts/coga/checkouts/launch-boundary/SKILL.md.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md: Ship the byte-identical fallback
    of docs/contexts/coga/launch/SKILL.md.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md: Ship the byte-identical
    fallback of docs/contexts/coga/state-publication/SKILL.md.
  src/coga/resources/templates/coga/bootstrap/orient/ticket.md: Give the package-owned chat agent the
    same state and branch policy.
  tests/test_checkouts.py: Exercise real chat state/draft/rename/usage paths, strict mixed-work preparation,
    and nested/root/relocated layouts with portable fixture setup.
  tests/test_git.py: Cover distinct and exact staged renames, draft and union-log preservation, and changed-index
    evidence with real Git.
  tests/test_launch.py: Cover direct-chat result boundaries, failure/interrupt/final teardown, guard release,
    and configured literal recovery diagnostics.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: This implement step does not perform code review. The legacy frozen workflow goes directly to
    open-pr; owner design approval is not implementation review.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest > /tmp/coga-chat-state-full-pytest.log
    2>&1
  status: passed
  head: 7e3acbee7b57a29c4231af5dc241a34a90b41032
  base: ef94eacb040f216b7b576d4b9fefe91f571b1091
  detail: 4337 passed, 10 skipped in 546.93s on Linux / Python 3.12.12. All skips require native Windows.
    This receipt retains the actual tested commit; the subsequent commit only moves chdir before removing
    a test fixture directory.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_checkouts.py > /tmp/coga-chat-state-final-checkouts.log
    2>&1
  status: passed
  head: 85774628bc7127b025c3cf485806fb4977a45653
  base: ef94eacb040f216b7b576d4b9fefe91f571b1091
  detail: 149 passed in 122.02s on the final head, including the root-layout portability correction.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_packaging.py
  status: passed
  head: 85774628bc7127b025c3cf485806fb4977a45653
  base: ef94eacb040f216b7b576d4b9fefe91f571b1091
  detail: 31 passed in 3.78s, including all canonical/package twins.
- command: git diff 7e3acbee7b57a29c4231af5dc241a34a90b41032..HEAD -- src docs
  status: passed
  head: 85774628bc7127b025c3cf485806fb4977a45653
  base: ef94eacb040f216b7b576d4b9fefe91f571b1091
  detail: 'Empty: final runtime code and documentation are identical to the full-suite-tested revision.'
- command: env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/python
    -m coga.cli validate --json
  status: passed
  head: 85774628bc7127b025c3cf485806fb4977a45653
  base: ef94eacb040f216b7b576d4b9fefe91f571b1091
  detail: 'Ran from tests/fixtures/seeded-repo/coga on the final head: 5 valid tasks, no issues.'
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task v1/05-chat-ticket-edits-strand-the-checkout-on-a-chat-br
    --json
  status: passed
  head: 85774628bc7127b025c3cf485806fb4977a45653
  base: ef94eacb040f216b7b576d4b9fefe91f571b1091
  detail: 'Final-head live ticket validation: 1 valid task, no issues.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: 85774628bc7127b025c3cf485806fb4977a45653
  base: ef94eacb040f216b7b576d4b9fefe91f571b1091
  detail: Passed for the complete implementation diff.
- command: git diff --check
  status: passed
  head: 85774628bc7127b025c3cf485806fb4977a45653
  base: ef94eacb040f216b7b576d4b9fefe91f571b1091
  detail: Passed for the unstaged live-ticket handoff.

```
