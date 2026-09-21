---
title: Triage five review comments that merged unanswered in Aug-Sep 2026
status: done
owner: nicktoper
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: report-to-coga
    skills: []
    assignee: agent
agent: claude
---

## Description

Triage the five unanswered review comments identified by phase 2 of
`verify-the-pr-review-comment-loop-once-the-review` on 2026-09-13. Recheck each
concern against current code and later work, recommend **fix / won't fix /
already moot**, and prepare a separate follow-up draft for each proposed fix.
`nicktoper` makes the final verdicts; completion means all five have an explicit
owner decision with supporting evidence and every accepted fix has its own
scoped ticket. Implementation belongs to those follow-up tickets.

## Context

### Workflow and deliverable

1. **agent-produces:** Read the original review threads, current source, and
   existing tickets/Git history for later fixes. Record the assessment date and
   control-branch commit. On the blackboard, produce five rows: exact comment
   URL; original priority; current evidence; recommendation and tradeoff;
   follow-up link; owner verdict (initially unset). Start with PR 699's P1.
   Distinguish verified behavior from plausible concerns; an outdated thread
   or merged PR alone does not prove a fix.

   Use `coga create` for a separate **draft** per proposed fix, or reuse an
   equivalent follow-up. Include the original comment, this ticket,
   module/symbol pointers, expected behavior, scope, acceptance criteria and
   focused verification. Use `code/with-review` for a code or context change;
   preserve the owner's workflow choice for existing tickets. Keep new drafts
   unactivated.
2. **human-owns-and-finishes:** `nicktoper` chooses each verdict, edits or
   approves fix scopes, and decides whether rejected drafts should be revised
   or canceled. Advance this owner gate only when explicitly asked.
3. **report-to-coga:** Record dated owner verdicts, reasons and ticket links.
   Apply requested draft revisions and explicitly authorized cancellations
   (using the CLI for lifecycle changes). Verify that every accepted fix has
   a separate actionable ticket and every provisional draft has a disposition.
   Ask the owner about missing decisions or follow-ups before closing.

For **already moot**, cite the fixing change and evidence covering the original
scenario. Partial fixes still need a verdict on the residual concern. For
**won't fix**, preserve the owner's reason and accepted consequence.

This task covers triage and ticket preparation. Code fixes, live recurring
runs, GitHub replies or thread resolution, and changes to merge policy are
outside its scope. The separate
`coga/tasks/autoclose-should-name-unanswered-review-threads-on.md` owns automatic
reporting of unanswered threads; this task does not depend on it shipping or
on the live review queue becoming empty.

### Findings to recheck

These are historical audit findings to recheck. PR links are starting points;
capture exact comment URLs during triage. Recover the source ticket from Git
history if it has been retired.

| PR / priority | Original concern and source pointer |
| --- | --- |
| [699](https://github.com/FastJVM/coga/pull/699) / P1 | `recurring_runner._broadcast_scan` in `src/coga/recurring_runner.py` marks `_LEDGER_LOADED` after pre-scan catch-up. The reported race lets another checkout publish the same period before the first create sync, while the cached ledger prevents a fresh check and permits a duplicate launch. Follow the create-sync and `_validate_control_serviced_period` paths when reassessing. |
| [704](https://github.com/FastJVM/coga/pull/704) / P2 | `config._require_trackable_context_entry` in `src/coga/config.py` accepts `path.is_file() or path.is_symlink()`. The concern is acceptance of a context artifact whose symlink target is outside the checkout, so another clone can compose a different prompt. Check actual artifact validation as well as root validation. |
| [705](https://github.com/FastJVM/coga/pull/705) / P2 | Recurring `ticket.py` shims, including `coga/recurring/autoclose-merged/ticket.py`, finish through plain `coga bump`. The audit observed `[human:nicktoper] task done` for headless completions on 2026-09-10 and 09-11 in `coga/log.md`; the comment requested system attribution. Inspect attribution through the child process, not just the shim's command spelling. |
| [747](https://github.com/FastJVM/coga/pull/747) / P2 | `commands.launch._reconcile_released_launch_admission` in `src/coga/commands/launch.py` captures `git.FileMutationRollback` after the control fetch instead of against the validated `current_bytes`. The reported window can overwrite a manual ticket edit made during that fetch with the earlier released revision. |
| [755](https://github.com/FastJVM/coga/pull/755) / P2 | `dev/code`, “Design pivots and superseded plans,” keeps superseded designs below the blackboard fence, so the archive enters future prompts. The original report also raised the synthesis gate for a long archive; the current documented mitigation excludes exact `## Superseded designs` sections in `blackboard.prelaunch_blackboard_synthesis_reason_text`. Recheck that mitigation separately from the remaining prompt-composition concern; moving the archive above the fence is the comment's proposal, not an approved design. |

PR 696 and PR 706 are excluded: the audit found them overtaken by PR 761
(`a-slack-repo-without-important-webhook-can-abort-t`) and PR 784
(`scripts/human_minutes.py` PR-regex rewrite), respectively.

### Focused reading

`coga/codebase` (`coga/contexts/coga/codebase/SKILL.md`) is cited rather than
attached: read the “Five bot review threads merged unanswered” bullet under
“Gotchas when editing coga's own code.” It preserves the original audit and
the partial PR 755 mitigation; treat its claim that no follow-up exists as
something to recheck against current tickets.

`dev/code` (`coga/contexts/dev/code/SKILL.md`) is cited rather than attached:
read “Review threads that merge unanswered” and “Design pivots and superseded
plans.” The owner retains merge and thread-resolution decisions, and archived
designs currently remain part of the composed blackboard. Any follow-up that
changes this behavior must update the owning context and its packaged twin in
the same PR; list those touchpoints in that draft.

<!-- coga:blackboard -->

## Owner review — assessment 2026-09-18

Assessed `main` at **`4d828256d28bf772d17aa8ffa1b47d6f436ca57b`**;
local `origin/main` and the read-only GitHub `refs/heads/main` query matched.
Subsequent Coga draft creation advances control state, but source, tests and
contexts still match that assessment commit. Began with PR 699's P1.

**Recommendation: fix all five residual concerns.** PR 755's synthesis-gate
subconcern is already moot; its prompt-inclusion concern remains. These are
agent recommendations, not owner decisions. All five follow-ups were
created through `coga create` on 2026-09-18, use **code/with-review**, and are
owned by **nicktoper**.

**Owner verdicts recorded 2026-09-20** (attended session): nicktoper accepted
all five recommendations as **fix**. Between the assessment and this gate the
owner had already launched all five follow-ups; each is `in_progress` at step 4
(review) with a non-draft PR open and unmerged as of 2026-09-20. Merge decisions
belong to those tickets' own review steps, not to this triage.

| Exact original comment | Original priority | Current evidence | Recommendation and tradeoff | Separate follow-up | Owner verdict |
| --- | --- | --- | --- | --- | --- |
| [PR 699 / r3806973475](https://github.com/FastJVM/coga/pull/699#discussion_r3806973475) | P1 | **Verified in local Git:** another checkout's same-period record, with its task already absent, lands after pre-scan catch-up. The preloaded cache lets the first checkout republish the task and keep it launch-eligible. The non-preloaded comparison skips it. Loaded `_validate_control_serviced_period` does not refresh it. | **Fix.** Revalidate the pre-publication snapshot. Preserve bounded reads and the shared-log protection against mistaking this sweep's own pending records for a rival's. | [Refresh recurring ledger before first create sync](refresh-recurring-ledger-before-first-create-sync.md) — in_progress, step 4 (review), [PR 838](https://github.com/FastJVM/coga/pull/838) open | **Fix** (2026-09-20). Owner accepted the recommendation as stated: revalidate the pre-publication snapshot, keep bounded reads and the shared-log protection. Scope approved 2026-09-18. |
| [PR 704 / r3834289315](https://github.com/FastJVM/coga/pull/704#discussion_r3834289315) | P2 | **Verified:** a tracked external-target `SKILL.md` symlink passes config and task validation and its external content enters the prompt. Removing the external file changes resolution while config still loads. Root-component checks do not protect the artifact. | **Fix.** Reject unreproducible context targets. This constrains local symlink setups; accepting only provably publishable internal targets versus rejecting artifact symlinks altogether is explicit scope input for the owner. | [Reject context artifacts that escape the checkout](reject-context-artifacts-that-escape-the-checkout.md) — in_progress, step 4 (review), [PR 844](https://github.com/FastJVM/coga/pull/844) open | **Fix** (2026-09-20). Owner accepted the recommendation; symlink policy chosen 2026-09-19 is the strict one — reject all context artifact symlinks and symlinked ancestors (internal, escaping, dangling, cyclic) for default and relocated roots; internal-link publication proof out of scope. Accepted consequence: repos using context links need real files under the contexts root. |
| [PR 705 / r3834701954](https://github.com/FastJVM/coga/pull/705#discussion_r3834701954) | P2 | **Verified through a real child CLI:** deterministic script completion logs `[human:marc] task done` and says `claude finished`, with no agent run. The live log still has `[human:nicktoper]` autoclose completion on 2026-09-18 08:33. Digest was removed, but four shims remain. | **Fix residual behavior.** Carry narrow system attribution through script completion without granting lifecycle/owner authority or signaling an outer agent session. No historical log rewrite or digest restoration. | [Attribute headless recurring completions to system](attribute-headless-recurring-completions-to-system.md) — in_progress, step 4 (review), [PR 835](https://github.com/FastJVM/coga/pull/835) open | **Fix** (2026-09-20). Owner accepted the residual-behavior fix: narrow system attribution through script completion; no historical log rewrite, no digest restoration. |
| [PR 747 / r3932656206](https://github.com/FastJVM/coga/pull/747#discussion_r3932656206) | P2 | **Verified in local Git:** a manual correction injected during control fetch is lost by reconciliation, for both matching pending and already-admitted remote claims. The helper captures its rollback baseline after the fetch. | **Fix.** Compare/capture against the validated bytes. A concurrent manual correction should produce a recoverable refusal; preserving it costs a retry. This is a fix for the reported fetch window, not a global editor lock. | [Preserve edits during released claim recovery](preserve-edits-during-released-claim-recovery.md) — in_progress, step 4 (review), [PR 842](https://github.com/FastJVM/coga/pull/842) open | **Fix** (2026-09-20). Owner accepted the recommendation: capture/compare against validated bytes so a concurrent manual correction yields a recoverable refusal, not a silent overwrite; fetch-window fix only, no global editor lock. |
| [PR 755 / r3937900285](https://github.com/FastJVM/coga/pull/755#discussion_r3937900285) | P2 | **Partial fix verified:** a 1,558-character exact archive passes synthesis and unrelated scratch still fails. All 60 abandoned-design markers nevertheless enter the prompt. `4e544d35`, merged in `c4482fae` / PR 755, covers the gate, not composition. | **Fix prompt inclusion; gate already moot.** Propose retaining the archive on disk and excluding it from automatic composition with a pointer. This removes historical alternatives from automatic context, so keep relevant current rationale live. The above-fence move is an unapproved alternative. | [Exclude superseded designs from launch prompts](exclude-superseded-designs-from-launch-prompts.md) — in_progress, step 4 (review), [PR 840](https://github.com/FastJVM/coga/pull/840) open | **Fix prompt inclusion; gate already moot** (2026-09-20). Owner accepted retaining the archive on disk and excluding it from automatic composition with a pointer; the above-fence move is rejected. Synthesis-gate subconcern already moot via `4e544d35` / PR 755. |

### Evidence and limits

- **PR 699:** `src/coga/recurring_runner.py` symbols `_broadcast_scan`
  (4876; loaded mark 4917), `_sync_recurring_create_paths` (3562),
  `_land_recurring_create_on_control_branch` (3827),
  `_control_serviced_period_cached` (4071), and
  `_validate_control_serviced_period` (4114). The two-checkout probe starts
  from a successful catch-up, calls `scan_due`, then pushes the competing
  `created recurring/weekly-check for 2026-W24` record to a local bare remote
  with no remaining task. `_broadcast_scan(control_is_fresh=True)` republishes
  and retains the task; `False` suppresses it. This reproduces publication and
  admission, **not a second production side effect**; duplicate dispatch is
  the consequence inferred from the retained launch list. Later period
  comparison/validation and generation guards do not repair this cache window.
- **PR 704:** `config._require_trackable_context_entry` (1256), including
  the trackable set and the subsequent `rglob("SKILL.md")` membership check,
  never establish target containment. `paths.resolve_context_path` (131)
  follows `is_file`; `compose_prompt_report` reads that path. The probe uses a
  committed artifact symlink under a real configured root and validates a
  task attached to it, then removes only the external target. Prompt content
  and resolution change as reported. This is a controlled missing-target
  simulation, not evidence that a production clone has already diverged.
  Root rejection remains covered by existing tests. The accepting expression
  dates to merge `11372a0c` / PR 704.
- **PR 705:** `launch_script.run_script_phase` strips `COGA_SUPERVISED`
  at line 276; the successful shim invokes a separate CLI process with the
  task slug. `commands/bump.py` terminal handling (275–301) selects the human
  actor when there is no assist while deriving the finisher from the configured
  operator. A real script → child `python -m coga.cli bump` probe, with Git and
  notifications disabled in its disposable fixture, reaches exactly this
  result. No production recipe ran. Live log evidence extends the original
  09-10/11 observations through 09-18. `5b5f3e1f` / PR 786 removes digest;
  `368ae080` / PR 827 adds recipe failure reporting but retains ordinary bump
  in autoclose, blocker-reminders, branch-sweep and skill-update.
- **PR 747:** `_reconcile_released_launch_admission` validates
  `current_bytes` before `_control_base_for_attempt`, then captures
  `FileMutationRollback` at line 612. The probe performs the real local-remote
  fetch, inserts a manual body correction before it returns, and observes
  successful admission with the correction missing locally and from the
  published ticket. Both control-generation variants reproduce. This models
  an ordinary editor that does not acquire the Coga publication barrier.
  `git log -L` shows no later change to this helper since `5c91ed74` / PR 747.
- **PR 755:** `blackboard.prelaunch_blackboard_synthesis_reason_text` (206)
  removes exact archive sections; `compose_prompt_report` (300) still inserts
  the unfiltered blackboard. Fixing change:
  [`4e544d356a53b94a332c24e793ca8d6a1c833d51`](https://github.com/FastJVM/coga/commit/4e544d356a53b94a332c24e793ca8d6a1c833d51),
  merged via [`c4482fae9cb6e63e41c47dd156c08f66f2fee09c`](https://github.com/FastJVM/coga/commit/c4482fae9cb6e63e41c47dd156c08f66f2fee09c).
  Existing tests prove synthesis and activation preservation, including
  unrelated scratch before/after an archive; the additional probe proves
  continued composition. **Prompt inclusion and its token cost are verified;
  an agent following an abandoned plan is a plausible risk, not an observed
  production failure.**

### Original threads and later-work search

Read the original threads with GitHub GraphQL `reviewThreads`, including all
comments and pagination checks. Each target is still unresolved, not outdated,
and has only its opening comment; no target thread or comment page was omitted.
This metadata is not used as proof that the behavior survives. The other
resolved PR 747 threads were not substituted for its final unanswered comment.

All five source PR tickets are still present and linked in their respective
drafts. Recovered the retired audit with
`git show 6c305673^:coga/tasks/verify-the-pr-review-comment-loop-once-the-review.md`
and read its phase-2 table. Searched current task bodies/titles, path history,
symbol history and relevant commits for equivalent fixes. None was found for
the five residual scopes. Relevant adjacent work:

- [Blackboard-bloat remedy](document-the-remedy-for-a-bloated-blackboard-sibli.md)
  is at its PR-preparation step and teaches manual archival. Its documented
  changes do not exclude the standard superseded section automatically, so
  it is not an equivalent PR 755 follow-up. Coordinate shared context hunks.
- [Documentation redesign](redo-documentation-dir-and-merge-it-with-context-b.md)
  names context relocation/resolution as source anchors; it does not own
  rejection of external context artifacts.
- [Unanswered-thread reporting](autoclose-should-name-unanswered-review-threads-on.md)
  remains separate; no dependency on its shipping or an empty live queue.
- `v2/document-design-pivot-in-blackboard-convention` is canceled and the
  shipped PR 755 source ticket is done; neither is a residual-composition fix.

The historical `coga/codebase` assertion that no fix tickets exist is now
superseded by the five links above. Each draft names the owning behavioral
context and packaged twin to update with its eventual implementation; no
behavioral context was changed or fixing PR opened in this triage step.

### Verification

**7 diagnostic cases passed**, asserting the observations above (two PR 699
cache variants, PR 704, real-child PR 705, two PR 747 control variants, and
PR 755). Temporary probe script: `/tmp/test_coga_review_triage_20260918.py`;
the durable reproduction methods and outputs are summarized above. The file
is disposable, not a shipped regression suite. Exact invocation:

```sh
PYTHONPATH=/home/n/Code/codex/coga/src:/home/n/Code/codex/coga/tests /home/n/Code/claude/coga/.venv/bin/python -m pytest -p conftest /tmp/test_coga_review_triage_20260918.py -q -s -o cache_dir=/tmp/coga-triage-pytest-cache
```

**19 existing focused tests passed** (7.61 s), using this checkout's source
with the available development interpreter:

```sh
PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/claude/coga/.venv/bin/python -m pytest tests/test_blackboard.py::test_prelaunch_blackboard_preserves_large_superseded_design tests/test_mark.py::test_mark_active_preserves_intentional_blackboard tests/test_launch.py::test_released_launch_admission_reconciles_control_ticket tests/test_config.py::test_layout_contexts_symlink_to_checkout_root_rejected tests/test_config.py::test_layout_contexts_internal_symlink_rejected tests/test_config.py::test_layout_contexts_ignored_context_rejected_even_with_trackable_marker tests/test_recurring.py::test_broadcast_reuses_the_fresh_prescan_control_ledger tests/test_recurring.py::test_recurring_create_sync_restores_control_ledger_for_handled_period tests/test_recurring.py::test_control_ledger_rejects_malformed_period tests/test_recurring_shims.py -q -o cache_dir=/tmp/coga-triage-existing-pytest-cache
```

These passing tests do not assert the missing protections; the diagnostic
cases deliberately assert current behavior. No live recurring run, GitHub
reply, thread resolution, merge-policy change or implementation was performed.

Final authoring checks: `coga validate --task <slug> --json` returned one
valid task and zero issues for this ticket and each of the five linked draft
slugs. `coga validate --json` returned 219 OK, 49 warnings and four
`unsynthesized-draft-blackboard` errors elsewhere; none concerns these six
tickets. `git diff --check` passed. Verified all five table rows have unset
verdicts, all follow-up links resolve to unactivated `code/with-review` drafts,
and this ticket's entire region above the fence is unchanged from the
assessment commit. The final blackboard remains below the 32 KiB warning
threshold.

### Handoff and draft disposition

Verdicts recorded 2026-09-20; see the table. No draft remains provisional:
every follow-up was launched by the owner (09-18 / 09-19) and sits at its own
review gate with an open PR (835, 838, 840, 842, 844). No rejection, revision
or cancellation was requested, so none is authorized. The report step must
re-verify the five links, record any PR merges that have landed by then, and
confirm every accepted fix still has exactly one actionable ticket before
closing. Owner has not yet asked to advance this gate.

## Report — 2026-09-20 (report-to-coga)

**Produced:** five recommendations with reproduced evidence (table above),
five `code/with-review` follow-up tickets created 2026-09-18, and dated owner
verdicts. **Owner decided (2026-09-20):** fix on all five; PR 755's
synthesis-gate subconcern already moot via `4e544d35`; PR 704's symlink policy
is the strict reject-all variant (2026-09-19); PR 755's above-fence move is
rejected. No draft revision or cancellation was requested, so none was
applied. **Where it landed:** verdicts and reasons are in the table on this
blackboard; implementation lives in the five follow-up tickets.

Re-verified on 2026-09-20 with `origin/main` at `93f9ac03`:

| Follow-up | Ticket state | PR | Merged |
| --- | --- | --- | --- |
| refresh-recurring-ledger-before-first-create-sync | in_progress, step 4 (review) | [838](https://github.com/FastJVM/coga/pull/838) `fix/recurring-ledger-freshness` @ `df6ed6cb` | no |
| reject-context-artifacts-that-escape-the-checkout | in_progress, step 4 (review) | [844](https://github.com/FastJVM/coga/pull/844) `fix/context-artifacts` @ `c6de5b7b` | no |
| attribute-headless-recurring-completions-to-system | in_progress, step 4 (review) | [835](https://github.com/FastJVM/coga/pull/835) `fix/headless-completion-system` @ `0477f3dc` | no |
| preserve-edits-during-released-claim-recovery | in_progress, step 4 (review) | [842](https://github.com/FastJVM/coga/pull/842) `fix/released-claim-edits` @ `50c9cfe9` | no |
| exclude-superseded-designs-from-launch-prompts | in_progress, step 4 (review) | [840](https://github.com/FastJVM/coga/pull/840) `codex/exclude-superseded-designs` @ `78d6e8e6` | no |

Every accepted fix has exactly one actionable ticket; no provisional draft
remains. All five PRs are non-draft and open; none has merged, so no merge
was recorded.

**Merge-order note for the owner.** The `coga/codebase` gotcha bullet "Five
bot review threads merged unanswered" still says the triage brief is a draft
and "none has a fix ticket yet"; that claim is superseded by the table above.
This ticket did not edit the bullet because all five PRs rewrite it (both the
live context and the packaged `bootstrap` twin). `git merge-tree` on
2026-09-20 shows each branch merges cleanly onto `origin/main` alone, but
every pair conflicts on both copies of that bullet, and PR 840 + PR 844 also
conflict in `src/coga/compose.py`. Whichever PR merges first, the remaining
four need a rebase that reconciles their bullet rewrite; that work belongs to
each ticket's own review step, not to this triage.

Out of scope and untouched, as specified: GitHub replies, thread resolution,
merge decisions, merge-policy changes, live recurring runs, behavioral
contexts and their packaged twins.

## Retro

status: processed
skill: retro/done-ticket
result: knowledge-pr
title: New context: fan-out follow-ups that rewrite one shared context bullet conflict pairwise
