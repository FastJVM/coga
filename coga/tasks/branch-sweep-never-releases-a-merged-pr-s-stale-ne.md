---
title: Branch sweep never releases a merged PR's stale never-pushed local draft
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
step: 4 (implement)
agent: claude
contexts:
- coga/checkout-cleanup/branch-sweep
---

## Description

The daily branch sweep keeps a local branch when its PR merged but its local tip still carries unique source changes. This happens when an older draft was amended or rebased before push, or when the PR came from another checkout. On 2026-11-09 all 12 local branches with merged PRs in the primary clone were reported in this state. The operator archived 11 of them by hand under `retired/<branch>` tags and deleted their local refs.

A commit date and a merged PR establish neither the intent behind those unique changes nor whether the operator is willing to publish them. Keep these branches during unattended sweeps, and give the operator a one-command way to archive and release a specific tip after reviewing it. The same evidence can describe valuable local follow-up work, so the report should describe the source differences and let the operator decide.

### Acceptance criteria

- [ ] A no-argument sweep reports a retained local draft when a merged PR exists, no PR for that branch name is open, and a successful comparison finds unmatched non-bookkeeping changes that prevent automatic release. The run report includes the branch, its full local commit ID, the PR number and head, representative paths, and where to find the manual procedure. The branch, its remote branch if present, and its worktrees stay in place. This retention is a normal result.
- [ ] Open PRs, closed-unmerged PRs alone, protected or live-ticket branches, and cases where comparison only failed produce no manual release candidate. Existing automatic landing, archival, worktree, and remote-ref behavior continues to apply. A restricted checkout-disposal pass gains no manual release behavior.
- [ ] `coga run branch-sweep --publish-and-release-local <branch> <full-local-oid>` is an explicit request to publish that reviewed commit to the configured Git remote and delete just the named local branch. Recheck the merged-PR/source-difference condition and check the exact current local tip, control and shared-branch protections, live-ticket claims, and worktree occupancy. Refuse on a missing or changed tip, uncertain required checks, or a branch held by a worktree. Git's branch deletion must still enforce its worktree guard, including during rebase and bisect.
- [ ] The command publishes or verifies a containing retirement tag before local deletion, using the existing base name and collision fallback. It reports the archived commit, tag and remote, and whether local deletion succeeded. Archive failure, a changed tip detected after publication, or a Git deletion refusal leaves the local branch in place and exits nonzero. If a tag was already published, report it so the operator can restore the draft or retry. No remote branch is deleted, no worktree is removed, and no other branch or retire follow-up is processed by this invocation.
- [ ] Add regression tests in `tests/test_branchsweep.py` for a divergent draft dated before a different merged head and for unique work added after merge. Both are retained by the ordinary recipe and described without claiming they are abandoned or proving they were never pushed. Cover manual success with recovery of the reviewed tip from the tag, the remote branch remaining untouched, archive failure and retry, a changed tip before and after archive publication, and refusals for open PRs, protected or claimed branches, worktree occupancy, and unavailable evidence. Exercise the normal recipe entry point and keep existing automatic sweep regressions passing.
- [ ] Update the shipped `coga/checkout-cleanup/branch-sweep` topic with report interpretation, review and invocation instructions, the effect of publishing formerly local content, and restoration from the reported tag. Record the Linux and native Windows full-suite receipts required by `coga-dev/testing` for Git-behavior changes.

### Proposed shape

- In `src/coga/branchsweep.py`, have `merged_pr_verdict()` carry structured evidence for a successfully inspected merged head with unmatched source paths. Keep that evidence separate from the `landed` decision and from lookup or comparison failures. An eligible closed-unmerged PR or an independently landed local tip can still authorize ordinary cleanup. When no existing gate authorizes release and no open PR blocks it, `sweep_branches()` can add the evidence and observed local OID to its existing notes. `render_sweep_report()` already publishes those notes to the run record via `run_branch_sweep_recipe()`.
- Add the single-branch mode to the existing `run_branch_sweep_recipe()` argv contract. Check the explicit local branch ref and full OID, reuse the existing merged/open PR queries, verdict and ticket protections, and use a read-only worktree probe for preflight. Recheck the tip and relevant claims after the network operation. Pass only the reviewed local OID to `_publish_retirement_tag()` and retain Git's worktree-aware porcelain for local deletion. The operator's explicit request supplies the authority for deletion. Keep that authority distinct from a PR landing verdict in messages and code.
- Use the final tip recheck immediately before Git's worktree-aware deletion, as `src/coga/branchcleanup.py` does in `_recheck_and_force_delete()`. Document that the operator must avoid concurrent updates of the target branch during this command because the check and porcelain delete are separate operations. An observed move preserves the ref even if the old tip already has a tag.

### Out of scope

- Commit-age heuristics, PR push-history reconstruction, bulk or unattended release of unique drafts, retirement-tag expiration, remote branch cleanup in the explicit command, and changes to checkout-disposal ownership rules.

## Context

- `src/coga/branchsweep.py`, `sweep_branches()`, calls `merged_pr_verdict()` after its protected-name, live-ticket and PR checks. It uses the verdict alongside `local_branch_landed()` to build `retirement_tips`. It attempts remote deletion only if the local ref was absent or this pass removed it. `src/coga/checkout_disposal.py`, `_sweep_owned_branches()`, calls this same entry point with `only=`.
- `src/coga/branchsweep.py`, `merged_pr_verdict()`, compares commits outside the PR head and control history, uses `_verbatim_patch_ids()` to remove patch-equivalent copies, and asks `_non_state_paths()` for remaining source changes. Failed fetch or comparison and successful detection of unique source work currently share the same negative `landed` result. The ordinary sweep can use structured evidence to explain that distinction without parsing the reason text.
- `src/coga/branchsweep.py`, `_publish_retirement_tag()`, accepts the tips the caller authorized and owns the no-force push, reuse and collision rules. `src/coga/branchcleanup.py`, `_recheck_and_force_delete()`, retains `git branch -D` for the hidden rebase/bisect worktree protections that `git update-ref -d` would bypass.
- `src/coga/runner.py`, `RECIPES`, maps `branch-sweep` to `run_branch_sweep_recipe()`. `src/coga/resources/templates/coga/recurring/branch-sweep/ticket.py` calls it through `run_recipe()` with empty argv. The manual mode belongs to this existing recipe so it can reuse the same proofs and archive rules.
- `tests/test_branchsweep.py`, `test_diverged_lineage_with_local_work_is_skipped()`, exercises a divergent local source commit while the merged head is available through the PR ref. `test_merged_head_that_cannot_be_fetched_keeps_branch()` exercises comparison failure. The new regressions should distinguish those two reasons in the report.

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

Proposed report-only behavior for the daily sweep and explicit release of one reviewed local commit. Dates cannot distinguish a superseded draft from still-needed work. The existing retirement helper can preserve the reviewed tip, and the existing Git porcelain protects checked-out branches. Its last tip check and deletion have a small race window, so the proposed command requires a quiescent target branch during release.

## Open Questions

- Is explicit publication of previously local content to the configured Git remote acceptable for this command? The proposal makes publication part of `--publish-and-release-local` so the archive survives loss of this clone and reuses the existing recovery procedure. If release must stay private to the clone, choose a local-only archive at design review and revise the recovery and collision criteria before implementation.

## Evaluator review

The design needs clarification before implementation. The ticket body composes in full, the frozen workflow matches `code/design-then-implement`, and the existing recipe can carry this change in one PR. `src/coga/commands/run.py` forwards trailing arguments to the fixed registry in `src/coga/runner.py`, and the shipped recurring `branch-sweep/ticket.py` passes empty argv. The Linux and native Windows receipts match `coga-dev/testing`, under **Verification tiers and receipts**.

### Must fix before implementation

1. **Define the claim proof for both reporting and release.** The acceptance criteria exclude live-ticket candidates and require refusal when required checks are uncertain. `src/coga/branchsweep.py` (`_live_ticket_branches`) scans prose and attachments only in the current workspace and skips unreadable files. `src/coga/checkout_disposal.py` (`live_checkout_claim`) scans recorded `## Dev` claims across workspaces and refuses an incomplete scan. Either helper alone misses a class of protection. Specify which claims the candidate report and manual mode check, and which read failures suppress the candidate or refuse publication. At minimum the manual command should preserve the existing mention protection and refuse on cross-workspace recorded claims or incomplete evidence. Cover a second workspace recording the branch, an unreadable claim source, and a claim appearing during archival. `tests/test_branchsweep.py` already has cross-workspace claim fixtures in `test_disposal_proves_secondary_merged_branch_unclaimed_across_workspaces`.

2. **Identify which repository supplies the PR evidence.** The proposed reuse of `src/coga/autoclose.py` (`prs_for_head`) would query the ambient GitHub CLI repository. That helper passes neither `--repo` nor a working directory, and `gh repo set-default` or `GH_REPO` can select a different repository from `[git].remote`, where `_fetch_pr_head` and `_publish_retirement_tag` operate. If the other repository's merged head is already available locally, the verdict can accept it without fetching the PR ref from the configured remote. Define the authoritative PR repository for manual release and the behavior when it cannot be verified. Cover a mismatched repository in the refusal tests. The automatic sweep's lookup can stay outside this change.

3. **Specify how worktree occupancy affects the report and when it prevents publication.** In `src/coga/branchsweep.py` (`sweep_branches`), a linked worktree plus a remote ref at the merged PR head can reach an early `continue` before the local verdict note, under either `worktrees_ticket_owned` setting. The first criterion calls for a draft report in that case. State where to emit it and identify a worktree-held draft as currently ineligible for manual release. For manual release, `src/coga/branchcleanup.py` (`_recheck_and_force_delete`) explains that `git worktree list --porcelain` misses the original branch during rebase or bisect. Decide whether a hidden hold may publish the tag before `git branch -D` refuses, or whether it must also prevent publication. The proposed list probe only supports the former by itself. Exercise the ordinary linked-worktree preflight and a detached operation that reaches Git's final guard, asserting the expected tag state in each case. `test_rebasing_worktree_preserves_both_refs_with_distinct_outcome` shows the detached listing in the current fixture.

4. **Make the manual eligibility rule explicit for multiple PRs and independent landing.** `src/coga/branchsweep.py` (`merged_pr_verdict`) tries merged heads and eligible closed-unmerged heads, returns on any landing proof, and keeps only the last negative reason. A valid source-difference result can therefore precede a failed comparison or an authorization from another PR. `sweep_branches` also checks `local_branch_landed` independently. Define whether a successful mismatch plus another failed comparison qualifies, whether manual mode must still refuse when any ordinary landing proof applies, and which PR to report when several comparisons find differences. Add a mixed-result regression so changing PR order cannot change eligibility. State whether the no-open-PR condition must also be checked after archival, alongside the ticket claims and final tip check.

5. **Restore the reported commit when a tag contains it.** `src/coga/branchsweep.py` (`_publish_retirement_tag`) can reuse a remote tag at a descendant. The shipped branch-sweep topic currently restores at the tag, which would recreate that descendant. Have the manual procedure fetch the reported archive and create the recovery branch at the full reported OID. Extend manual success coverage to reuse a descendant tag and recover the exact reviewed tip. `test_retirement_tag_containing_the_tip_counts_as_archived` already demonstrates the existing containment rule.

### Owner decision

The publication question above is still open. A tag exposes the reviewed commit and its reachable history to readers of the configured remote, even if a later check or Git refusal preserves the local branch. The procedure should describe that outcome if the owner approves remote archival.

### Optional

- Retitle the ticket to describe a retained local branch with unmatched source changes. The current title labels the work stale and never pushed, claims the proposed comparison cannot establish. Also update the shipped topic's existing “unpushed non-bookkeeping commits” wording when adding the new report interpretation.
