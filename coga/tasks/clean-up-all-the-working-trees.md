---
title: clean up all the working trees
status: in_progress
owner: nicktoper
workflow:
  name: maintenance/with-approval
  steps:
  - name: inventory
    skills: []
    assignee: agent
  - name: approve
    skills: []
    assignee: owner
  - name: cleanup-and-verify
    skills: []
    assignee: agent
step: 2 (approve)
agent: claude
---

## Description

Reclaim disk space by cleaning up unused Git worktrees under `/tmp` and
`~/Code` (`/home/n/Code`) across every repository in those locations. This is
a one-time maintenance task: inventory the worktrees, present an exact removal
list for the owner's approval, then remove approved eligible worktrees and
verify the result. Preserve worktrees with uncommitted files or unmerged work
and report them for review; do not back them up as a substitute for retaining
them. Done means the approved cleanup is verified and the blackboard records
what was removed, approximate space recovered, and what remains with reasons.


## Context

### Scope and boundaries

- The owner is `nicktoper`. Scope covers all repositories under both roots,
  including separate clones of the same project and their linked worktrees.
  Group worktrees by their actual Git common directory; one clone's
  `git worktree list --porcelain` does not enumerate another clone's worktrees.
- Remove eligible linked-worktree directories, not primary repositories or
  standalone clones. Identify standalone scratch clones and test fixtures in
  the inventory, but leave their deletion for a separate owner decision.
  Branch deletion, remote changes, general `/tmp` cleanup, and changes to
  Coga's cleanup automation are outside this ticket.
- Preserve primary/control checkouts, the checkout running this task, locked
  or in-use worktrees, and any worktree required by an unfinished task. Use
  available process/session and task evidence; directory age or an old branch
  name is not sufficient evidence that a worktree is unused. Uncertain cases
  stay in place for review.
- Resolve paths and inspect nested repositories before proposing removal.
  Preserve both roots themselves, paths outside them, and shared repository
  object stores and branch refs. Normal removal and approved pruning may
  remove the corresponding per-worktree administrative registrations. Do not
  follow a symlink into a different cleanup scope.

### Inventory and approval

1. Discover repositories and enumerate their registered worktrees using Git.
   Report inaccessible locations and discovery limits rather than claiming
   complete coverage. Distinguish existing directories, missing registered
   paths, standalone clones, and Git test fixtures.
2. For each candidate, record its absolute path, repository/common directory,
   branch or detached HEAD and commit, approximate allocated disk usage,
   tracked/untracked/ignored state, merge evidence, activity or task evidence,
   and a proposed action with its reason. Check for unfinished Git operations
   and commits that would lose their last durable reference on removal.
3. Preserve tracked modifications, untracked files, unmerged or unique work,
   and ignored local data such as credentials or machine configuration.
   Ignored caches may leave with an otherwise eligible worktree only when
   confirmed regenerable and described in the removal list. Unknown ignored
   data stays. Keep secret contents out of the inventory and blackboard.
4. A merged branch or PR alone does not prove the current worktree disposable:
   inspect commits added after the merge and account for squash/rebase merges.
   Use fresh evidence where available; missing or uncertain evidence means
   preserve and report. Keep local and remote branch refs unchanged.
5. Write the inventory and exact proposed paths/actions on this ticket's
   blackboard. The owner approves that concrete list at the `approve` step;
   approving this draft or launching it does not approve any deletions.
   Keep the approval table concise, with exact paths and evidence for every
   proposed action. Summarize repetitive retained test fixtures where that
   does not hide a candidate's eligibility or a discovery limitation.

### Cleanup and verification

- Recheck each approved path's identity, HEAD, local files, and activity just
  before removal. Changed or newly uncertain candidates stay and are reported;
  approval does not override the preservation rules above.
- Prefer normal `git worktree remove` for eligible linked worktrees. Do not
  force past a refusal or use recursive deletion as a fallback. Do not run
  Coga retirement or branch-sweep commands, which can also change branches or
  ticket state beyond this cleanup's scope.
- Missing worktree registrations may be pruned only after reviewing Git's
  dry-run output and confirming every affected registration is approved and
  in scope. A repository-wide prune with other affected entries must be
  skipped. Preserve locked registrations and uncertain missing paths.
- Verify removed directories and registrations, preserved primary checkouts,
  and remaining worktrees. Record removals, skips/failures, approximate space
  recovered, and retained candidates with actionable reasons. Do not call a
  failed removal successful; partial cleanup must be explicit.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Inventory — 2026-09-23 ~14:40 PDT (step 1, no cleanup performed)

### Discovery and limits
- `find /home/n/Code /tmp -xdev` for `.git` (pruned `node_modules`, `.venv`, `venv`, `__pycache__`): 1,087 entries. Each was classified by `git rev-parse --git-common-dir` / `--git-dir`. For every common dir with more than one worktree, `git worktree list --porcelain` + `git worktree prune --dry-run -v`.
- Unreadable: 10 `/tmp/systemd-private-*` dirs (root-owned). Worktrees inside `node_modules`/`.venv` dirs, and worktrees of repos stored outside both roots, are not covered unless their linked dir sits under a root (then its `.git` file was found).
- `/home/n/Code/.git` and `/tmp/.git` are **empty directories**, not repos. `/home/n/Code/codex/xpref/.git` is empty too, so it is not a repo.
- Test fixtures: `/tmp/pytest-of-n` (606M) holds 865 `.git` entries: 693 primary, 109 linked, 63 broken fixture repos. Retained; not in scope for removal.
- Process evidence (`/proc/*/cwd`): live sessions only in `/home/n/Code/coga`, `/home/n/Code/codex/multiply`, and `/home/n/Code/multiply` (all primaries). No process has its cwd in any linked worktree.
- Locked registrations: none. Unfinished git ops (merge/rebase/cherry-pick/revert/bisect): none.
- Merge evidence: PR state comes from `gh pr list --state all` (fresh). Worktree HEAD is compared with the PR head OID. HEAD=prhead or HEAD<prhead (HEAD is contained in the merged PR head) counts as merged, which also covers squash merges. For PR heads that are not local, the check used `gh pr view --json commits` or the `gh api compare`. Nothing was fetched and no refs were changed.
- Ticket evidence: every non-done/non-canceled ticket in coga, multiply, xpllm, patents, codex/magicator2, delivaudit, admin, and magicator was grepped for each worktree path, basename, and branch.
- Disk: `/` is 934G total, 356G free.

### Standalone clones and scratch (inventory only; deletion is a separate owner decision)
- Second clones of the same project: `~/Code/claude/coga` and `~/Code/codex/coga` (both FastJVM/coga, each with its own linked worktrees); `~/Code/codex/multiply` vs `~/Code/multiply`; `~/Code/claude/magicator2` vs `~/Code/codex/magicator2`; `~/Code/JavadocGithubAction` vs `~/Code/claude/JavadocGithubAction`.
- A clone (not a linked worktree) sits at `~/Code/coga/.coga/worktrees/build-week-readme.IcnXYp` (30M).
- `/tmp/multiply-e16.wBByFe` (1.6G) holds 4 scratch clones.
- Probe fixture repos, all nested inside checkouts: ~100 under `probes/local/**` in codex/multiply, multiply, multiply-harness-evidence, codex/multiply-debug-platform-contract, codex/multiply-startup-upgrade-probe, and claude/multiply-probe-harness. Also `xpllm/perfo-isolated/home*/work` (6) and `xpllm/research/magicator-llvm/.../candidates` (6).

### Eligibility rule applied
REMOVE only when all of these hold:
- clean (0 tracked changes, 0 untracked);
- merged PR with HEAD=prhead or HEAD<prhead, and no commits after the PR head;
- no unfinished (in_progress/blocked/paused/active) ticket that needs it;
- ignored data is only regenerable: `.pytest_cache`, `__pycache__`, Rust `target/`, `.venv`, an empty `probes/local/`, `coga/.agent-skills/` (installed skill copies), and `coga/coga.local.toml` only where its sha1 is **identical** to the primary checkout's copy.

The local branch refs stay, so each branch head keeps its reference after removal. Command: `git -C <common-primary> worktree remove <path>` (no `--force`).

### Proposed REMOVE (42 worktrees, ~15.4 GiB)
| # | Path | Branch / HEAD | Size | Evidence |
|---|---|---|---|---|
| R1 | `/home/n/Code/claude/coga-adjudicate-moved-premises` | adjudicate-moved-premises c3805432d | 23M | #826 merged, HEAD<prhead |
| R2 | `/home/n/Code/claude/coga-autoclose-retire-worklist` | autoclose-retire-worklist 8d30ad626 | 22M | #820 merged, HEAD<prhead |
| R3 | `/home/n/Code/claude/coga-autofix-analyst-fixes` | autofix-analyst-fixes 4a5502a5f | 29M | #816 merged, HEAD=prhead |
| R4 | `/home/n/Code/claude/coga-blackboard-writer-contract` | blackboard-writer-contract 2a15d11ff | 15M | #798 merged, HEAD<prhead |
| R5 | `/home/n/Code/claude/coga-ci-posture` | ci-posture 1c1e5255d | 23M | #787 merged, HEAD=prhead (a draft ticket names the branch only) |
| R6 | `/home/n/Code/claude/coga-dream-routing-holes` | dream-routing-holes 0b140fc5b | 24M | #799 merged, HEAD<prhead |
| R7 | `/home/n/Code/claude/coga-dream-w36-extract-backlog` | dream-w36-extract-backlog 901a9909a | 23M | #795 merged, HEAD=prhead |
| R8 | `/home/n/Code/claude/coga-feature-branch-state-boundary` | feature-branch-state-boundary 71ca71a20 | 30M | #785 merged, HEAD=prhead |
| R9 | `/home/n/Code/claude/coga-fresh-checkout-lacks` | fresh-checkout-lacks d4f754ee3 | 24M | #789 merged, HEAD<prhead |
| R10 | `/home/n/Code/claude/coga-init-clone-setup` | init-clone-setup 237aadd52 | 31M | #788 merged, HEAD<prhead |
| R11 | `/home/n/Code/claude/coga-period-task-recipe-firing` | period-task-recipe-firing 20a71bc47 | 23M | #817 merged, HEAD<prhead |
| R12 | `/home/n/Code/claude/coga-recurring-twin-note` | recurring-twin-note c16e34cfa | 23M | #792 merged, HEAD<prhead |
| R13 | `/home/n/Code/claude/coga-remove-digest` | remove-digest 9cb023188 | 30M | #786 merged, HEAD=prhead |
| R14 | `/home/n/Code/claude/coga-resolve-step-one-assignee` | resolve-step-one-assignee 63c530eab | 27M | #779 merged, HEAD<prhead |
| R15 | `/home/n/Code/claude/coga-scan-alert-nonfatal` | scan-alert-nonfatal db42f80d2 | 27M | #761 merged, HEAD=prhead |
| R16 | `/home/n/Code/claude/coga-sync-context-preflight` | sync-context-preflight ab4d2b8e3 | 23M | #791 merged, HEAD<prhead |
| R17 | `/home/n/Code/claude/coga-triage-inverted-premises` | triage-inverted-premises bb23768aa | 23M | #794 merged, HEAD<prhead |
| R18 | `/home/n/Code/claude/coga-validate-baseline` | validate-baseline 01ff2ce80 | 22M | #823 merged, HEAD<prhead (a draft ticket names the branch only) |
| R19 | `/home/n/Code/codex/coga-agent-peers` | agent-peers 5b96c6b4b | 24M | #727 merged, HEAD=prhead |
| R20 | `/home/n/Code/codex/coga-derive-twin-sync` | derive-twin-sync 1dbc76164 | 20M | #758 merged, HEAD in PR commits |
| R21 | `/home/n/Code/codex/coga-dream-reconcile-distinct-shards` | dream-reconcile-distinct-shards 0f10468f6 | 19M | #756 merged, HEAD=prhead |
| R22 | `/home/n/Code/codex/coga-put-build-back` | restore-coga-build 884bdb9e3 | 15M | #701 merged, HEAD=prhead |
| R23 | `/home/n/Code/codex/coga-select-session-conduct` | select-session-conduct c89baa30e | 24M | #729 merged, HEAD=prhead; ignored `coga/.agent-skills/` |
| R24 | `/home/n/Code/codex/coga-superseded-design-doc` | docs/superseded-design-home 4e544d356 | 25M | #755 merged, HEAD=prhead |
| R25 | `/home/n/Code/codex/coga-usage-report` | usage-report 7d1a7241b | 60M | #854 merged, HEAD<prhead; `.venv` + identical local.toml (a draft ticket names the branch only) |
| R26 | `/home/n/Code/codex/coga-validate-drift-kinds` | codex/validate-drift-kinds 9e06440fb | 20M | #702 merged, HEAD=prhead |
| R27 | `/home/n/Code/codex/coga-vendor-pypi-only` | vendor-pypi-only 895f6c0d2 | 27M | #759 merged, HEAD in PR commits |
| R28 | `/home/n/Code/codex/coga-launch-gates` (common: codex/multiply) | codex/launch-gates-skill 3c02f1cef | 47M | multiply #28 merged, HEAD=prhead; `target/` |
| R29 | `/home/n/Code/codex/multiply-hook-trust` | hook-trust 3f87b4c55 | 531M | #66 merged, HEAD=prhead; only `target/` (the multiply autofix ticket says this checkout awaits human cleanup) |
| R30 | `/home/n/Code/codex/multiply-updater-auto-update` | updater-auto-update 9a9936403 | 3.5G | #61 merged, HEAD=prhead; `target/` |
| R31 | `/home/n/Code/multiply-attempts-lineage` | attempts-lineage 90690c27e | 1.3G | #102 merged, HEAD<prhead; `target/`; files touched <3d ago (build) |
| R32 | `/home/n/Code/multiply-drop-profile-previous` | onboarding/drop-profile-previous 4b4a41395 | 1.7G | #125 merged, HEAD=prhead; `target/`, `.agent-skills`, identical local.toml; touched <3d |
| R33 | `/home/n/Code/multiply-harness-wording` | harness-wording 263ea0bba | 987M | #100 merged, HEAD=prhead; `target/` |
| R34 | `/home/n/Code/multiply-no-auto-repair` | harness/no-auto-repair ad2fdd577 | 1.6G | #121 merged, HEAD=prhead; `target/`, identical local.toml; touched <3d |
| R35 | `/home/n/Code/multiply-optim-harness` | codex/optim-harness 208545a42 | 1.0G | #92 merged, HEAD=prhead; `target/` |
| R36 | `/home/n/Code/multiply-optim-loop` | optim-loop e217bd1f9 | 1.9G | #122 merged, HEAD=prhead; the in-progress `v1/5b-optim-loop-rework` works on branch `optim-loop-rework` (PR #127), not this one |
| R37 | `/home/n/Code/multiply-regeneration` | harness/regeneration 63fa52200 | 1.8G | #124 merged, HEAD=prhead; `target/`; touched <3d |
| R38 | `/home/n/Code/multiply-simplify-optim-loop` | docs/simplify-optim-loop 6a9ca47aa | 7M | #123 merged, HEAD=prhead; identical local.toml |
| R39 | `/home/n/Code/patents/.claude/worktrees/agent-a49801375ceea3603` | dream/fix-auto-disclosure-candidate-schema 20644c116 | 31M | #79 merged, HEAD=prhead |
| R40 | `/home/n/Code/patents/.claude/worktrees/agent-a51345c6f3a5ced25` | codex/retro-patent-update-digest-emergency 18f9066ab | 31M | #78 merged, HEAD=prhead |
| R41 | `/home/n/Code/patents/.claude/worktrees/agent-ae8d78be181c434dc` | dream/fix-relay-codebase-context dacdf8846 | 31M | #80 merged, HEAD=prhead |
| R42 | `/home/n/Code/xpllm/.scratch/slice-channel-01` | slice-channel/01-audit 883bd7d8e | 264M | xpllm #57 merged, HEAD=prhead; pytest/pycache only |

### Proposed PRUNE of missing registrations (metadata only, negligible space)
Allowed only where the repo-wide `prune --dry-run` set is exactly these entries and each branch ref still exists:
- P1 `/home/n/Code/multiply`: `/tmp/multiply-debug-messages`, `/tmp/multiply-nice-messages`, `/tmp/multiply-sandbox-test-note`. All 3 local branches exist; drafts mention the branch names only. → `git -C /home/n/Code/multiply worktree prune`
- P2 `/home/n/Code/patents`: `/home/n/Code/patents-calendar-past-due-watchdog` (branch exists). → `git -C /home/n/Code/patents worktree prune`
- P3 `/home/n/Code/admin`: `/tmp/admin-ops-roadmap` (branch exists). → `git -C /home/n/Code/admin worktree prune`
- P4 `/home/n/Code/xpllm/perfo-isolated/home4/work`: `/tmp/opencode/dispatch-original` (detached cea93ab, contained in `master`). → `git -C … worktree prune`

Prune SKIPPED, because the dry-run set includes entries that must be kept:
- `claude/coga`: `/tmp/coga-retire-owner` is named by the in_progress multiply autofix ticket.
- `codex/coga` (16 missing): the set includes `pr873`/`pr875` (in_progress tickets), `coga-python311-ci` (blocked ticket), and `coga-phone-home` (telemetry ticket).
- `xpllm` (5): `xpllm-slicepoc-01` belongs to an in_progress ticket, and `/tmp/xpllm-ar00-audit` has detached 9e3a2cc4 that no ref contains, so pruning would drop its last reference.
- `magicator` (7): `magicator-slicepoc-pin` is explicitly retained by the xpllm slice-poc/01 ticket.

### RETAINED (with reasons)
- **Unfinished ticket:**
  - claude/coga-autoclose-unanswered-threads (in_progress, PR #881)
  - claude/coga-reconcile-audit-lifecycle (in_progress, no PR, unpushed)
  - claude/coga-split-ticket-contract (in_progress, no PR, unpushed)
  - claude/coga-ticket-relationships (in_progress/blocked, unpushed)
  - claude/coga-recurring-control-worktree and codex/coga-recurring-control-worktree (blocked ticket; unpushed commits)
  - multiply-install-onboarding (v1/4-onboarding in_progress)
  - multiply-license-and-terms (in_progress, no PR)
  - multiply-pass-events (created 14:38 today, in_progress)
  - /tmp/multiply-reporting (1.4G; no PR, commit today 14:14, unpushed)
- **Commits after the merged PR head (unmerged work):** claude/coga-branch-sweep-landed (+3), -doc-context-boundary (+2, unpushed), -dream-w38-extract-backlog (+2), -recurring-missing-workflow (+1), -shebang-exec-check (+3, unpushed), -skill-update-per-skill (+4, unpushed), -sweep-abandoned-record (+3), -title-only-validator (+1), -v2-premise-holes (+1, unpushed), and codex/coga-observation-loop-cleanup (+3, unpushed, 496M).
- **HEAD not in the merged PR (diverged or rebased; uncertain):** claude/coga-bloated-blackboard-remedy, codex/coga-remove-narrative-candidates (HEAD not on GitHub), codex/coga-simplify-ticket-format, and claude/coga-scrub-sa-token (no PR, unpushed).
- **Tracked modifications:**
  - claude/coga-remove-build-project (20 files)
  - claude/delivaudit-layer1 (41 + 2 untracked, 62M)
  - claude/delivaudit-layer2-score (47 + 1 untracked, 62M)
  - xpllm/.coga/worktrees/aa60a6… and d4a3a6… (each has modified `coga/log.md` and a task file; 230M each)
- **Detached HEAD that no ref contains:** codex/coga-docs-migration-closeout (19d400c61, 262M) and xpllm/.scratch/slice-poc-01-audit (9ebafb22c, 271M; an in_progress ticket mentions it).
- **Unknown ignored data:**
  - codex/multiply-startup-upgrade-probe: 4.3G, of which `probes/local/` is 1.3G of probe evidence and `target/` is 3.1G.
  - codex/multiply-debug-platform-contract: 2.2G, of which `probes/local/` is 1.2G and `target/` is 1.1G.
  - multiply-harness-evidence: 2.5G, of which `probes/local/` is 5.9M and `target/` is 2.5G.
  - xpllm/.scratch/annotation-research-01: 267M. It holds `perfo-isolated/auth` (credentials; contents not read) and `xp1/runs/`, has unpushed commits, and its ticket is paused.
  - All four are merged and clean otherwise. The owner can decide separately whether the probe data is disposable, which would add about 9G.
- **Unmerged local-only branch:** multiply/.claude/worktrees/try-posthog-design (no PR, 1 local commit).
- **Broken back-link:** claude/multiply-probe-harness (379M) is registered in `codex/multiply`, but its `.git` points at the nonexistent `claude/multiply/.git/worktrees/…`. Its PR #13 is merged with HEAD=prhead. `git worktree remove` will refuse until `git -C /home/n/Code/codex/multiply worktree repair /home/n/Code/claude/multiply-probe-harness` is run, and the path also contains nested probe fixture repos. Retained; optional owner item O1 = repair, then normal remove.

### Verification plan (cleanup step)
1. Before each removal, recheck: path exists; `git rev-parse --git-common-dir` matches; HEAD sha matches the table; `git status --porcelain` is empty; no process has its cwd under the path; no new ticket reference. Any change means skip and report.
2. Run `git -C <primary> worktree remove <path>` with no `--force`. A refusal means skip and report; there is no fallback.
3. For P1–P4: rerun `worktree prune --dry-run -v` and prune only if the output exactly matches the approved list.
4. Afterwards confirm: the path is gone; `git worktree list` no longer shows it; the branch ref is unchanged; the primaries (`~/Code/coga`, `claude/coga`, `codex/coga`, `multiply`, `codex/multiply`, `patents`, `xpllm`, `admin`, `perfo…/home4/work`) still have `git status` working. Also run `df` before and after, and record per-path du totals.

### Owner decision needed at `approve`
Approve R1–R42 and P1–P4 individually or as a set. Optionally approve O1. The probe-data worktrees stay retained unless you decide otherwise.
