---
title: Skill update rebuilds its PR branch every period and silently discards hand-pushed
  commits
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
step: 6 (open-pr)
agent: claude
---

## Description

`coga skill update --all --pr` rebuilds `coga/skill-update` from the control
branch on every run, then force-pushes it. If someone pushes a fix by hand
onto the open skill-update PR, the next weekly run overwrites the branch and
the fix is gone. Nothing rejects the push and nothing reports it. The explicit
`--force-with-lease` that #734 added cannot catch a hand-pushed commit already
on the branch: the lease is resolved moments before the push and accepts the
tip it just observed. It can reject only a concurrent change after that
observation.

The ask: when the remote branch carries commits the job did not make, carry
them forward or refuse to overwrite them. Do not discard them.

**Decision: refuse.** Before any update is applied, the run checks the remote
`coga/skill-update` branch. If an open PR's branch carries commits the job did
not make, the run stops with a named error that lists those commits. It does
not carry them forward. Reasons:

- A hand-pushed fix on this PR most often touches the skill files the job
  regenerates. Cherry-picking it onto the rebuilt branch would conflict, or
  would quietly re-apply an edit over a newer upstream version. Neither
  should happen in an unattended weekly job.
- Hand commits mean a human is already working on the PR. The useful action
  is to merge or close it. Refusing tells that human to finish the job; a
  carry-forward would mix new upstream changes into a PR under review.
- A refusal is deterministic, and the existing recipe failure path already
  reports it (exit 2, stderr on the period blackboard). A carry-forward needs
  new conflict handling and a new report status.

The cost: while the PR stays open with hand commits, every weekly run exits 2,
including weeks with no upstream change. That is deliberate. The guard runs
before the updates are known, for the same reason v1/10's preflight does: a
refusal must leave the working tree untouched. A failing period task is the
signal that the PR needs a human. Closing the PR is the explicit way to
abandon its hand commits.

### Acceptance criteria

- [ ] **Hand commit on an open PR → refusal.** The remote `coga/skill-update`
      has an open PR, and its branch carries a commit that is not one of the
      job's own commits and is not on (or patch-equivalent to a commit on) the
      freshly fetched `<remote>/<control>`. Then `coga skill update --all --pr`
      exits non-zero before `update_skills` runs. Nothing is pushed. The PR,
      the caller's branch, HEAD, and the working tree are unchanged. No
      skill file is written.
- [ ] The error names the branch and the open PR URL. It lists each foreign
      commit as `<short-sha> <subject>`. It says how to resolve: merge the PR,
      move the commits elsewhere, or close the PR to discard them deliberately,
      then retry.
- [ ] Through the recurring job, that error reaches the period blackboard via
      `skill_update.run_update_json` → `RuntimeError` → `runner.run_recipe`
      (stderr tail), and the period task exits 2. No new swallow path.
- [ ] **Only job commits → proceeds.** An open PR whose branch holds only job
      commits (the full message is exactly `Update Coga-managed skills`) and
      merge commits (for example GitHub "Update branch" from the control
      branch) is rebuilt and force-pushed as today.
- [ ] **Hand commit already on control → proceeds.** A hand commit that is
      also on `<remote>/<control>`, as an ancestor or as a patch-equivalent
      cherry-pick, is not foreign.
- [ ] **No open PR → proceeds.** If the remote branch exists but no open PR
      uses it (merged or closed, branch left behind, including a squash merge),
      the guard does not inspect commits and the run proceeds. This is
      documented as deliberate: merging or closing is the human decision.
- [ ] **No remote branch → proceeds.** With no remote branch (the #734
      merged-then-deleted case), the guard makes no `gh` or `fetch` call. The
      push is unchanged: no lease, pushed cleanly.
- [ ] **The lease uses the guarded tip.** When the guard observed a remote
      tip, `open_or_update_pr` leases the push against that OID and skips
      its own fresh `ls-remote`. A hand push that lands after the guard, while
      updates and verification run, fails the lease instead of being
      overwritten.
- [ ] If the fetched `<remote>/<branch>` does not equal the OID the guard
      observed with `ls-remote`, the run refuses with a "branch moved while
      checking, retry" error. It does not guess.
- [ ] Weeks with no upstream change: if the guard passes, the existing early
      return in `run_skill_update_pr_flow` is unchanged (nothing committed,
      nothing pushed). If the guard refuses, the run exits non-zero as above.
- [ ] Docs updated in the same PR: `coga/skill-management` (package copy and
      legacy twin), and the package `recurring/skill-update/ticket.md`. That
      includes its "A week with no upstream changes is a quiet no-op"
      paragraph, which must now name this exception.
- [ ] Tests (see Proposed shape) pass. `python -m pytest` and
      `coga validate --json` are green.

### Proposed shape

1. **`src/coga/skill_manager.py`: name the job commit.** Add the module
   constant `SKILL_UPDATE_COMMIT_SUBJECT = "Update Coga-managed skills"`.
   `_commit_skill_updates` uses it for `git commit -m`. Do not add a trailer.
   Do not touch `recurring_activity` or the `--pr-title` default; they keep
   their own literal.
   *Identifying the job's own commits:* a commit is the job's own when its
   whole message, stripped, equals that constant (subject only, empty body).
   The author cannot tell the job from a human, because the sweep commits as
   its operator. A trailer would mark only future commits, and a human could
   copy it as easily as the subject. Because the branch is rebuilt every
   period, at most one job commit is expected. The remaining risk is a human
   writing exactly the bot's message with no body. Accept it and document it.

2. **`skill_manager`: new guard `assert_skill_update_branch_unclaimed(cfg, *,
   runner=None, branch=SKILL_UPDATE_BRANCH) -> str | None`.** It returns the
   remote tip OID it verified, or `None` when there is no remote branch.
   Steps, all run in `cfg.repo_root.parent`:
   1. `oid = _remote_branch_oid(run, cfg.git_remote, branch, cwd)`. Reuse it
      so the guard and the push agree about push URLs. If `None`, return
      `None`.
   2. Look up the open PR with `gh pr list --head <branch> --state open
      --json url --jq '.[0].url // ""'`. Factor that call, and the
      `FileNotFoundError` → "gh is required" translation, out of
      `open_or_update_pr`'s nested `run_gh` into a module helper (for example
      `_run_gh(run, args, cwd)` plus `_open_pr_url(run, branch, cwd)`), so
      both call sites share one copy. If there is no open PR, return `oid`.
   3. Run `git fetch --no-tags <remote>
      +refs/heads/<control>:refs/remotes/<remote>/<control>
      +refs/heads/<branch>:refs/remotes/<remote>/<branch>`. A non-zero exit
      raises `SkillManagerError` naming the command. "On the control branch"
      means this freshly fetched `<remote>/<control>`, not local
      `cfg.git_control_branch`, so a stale local `main` cannot make merged
      work look foreign. (`_commit_skill_updates` still builds from the
      local control branch; that is unchanged.)
   4. `git rev-parse --verify refs/remotes/<remote>/<branch>` must equal
      `oid`. Otherwise raise the "moved while checking" error.
   5. List candidates with `git log --no-merges --cherry-pick --right-only
      --format=%H%x00%s%x00%B%x1e
      refs/remotes/<remote>/<control>...<oid>`. Merge commits are skipped,
      and so are commits already on control or patch-equivalent to one
      there. Drop job commits (step 1 rule). Anything left is foreign.
   6. If anything is foreign, raise `SkillManagerError` with the message from
      the acceptance criteria. Otherwise return `oid`.

3. **`src/coga/commands/skill.py` `update`: call the guard before
   `update_skills` when `pr` is set.** The "--pr needs --all" refusal comes
   first. If v1/10 (PR #1168) has merged, call the guard right after
   `assert_skill_update_pr_preflight(cfg)`. Local checks run first because
   they are cheap and need no network. If v1/10 has not merged, place the
   call in the same position, before `update_skills`, and reconcile when it
   lands. Pass the returned OID to `run_skill_update_pr_flow`.

4. **Thread the OID to the push.** `run_skill_update_pr_flow` gains the
   keyword `expected_remote_oid: str | None = None` and passes it to
   `open_or_update_pr(..., expected_remote_oid=...)`. In `open_or_update_pr`,
   a non-`None` value is used as the lease OID and the `_remote_branch_oid`
   call is skipped. With `None`, behaviour is exactly today's: a fresh
   `ls-remote`, and no lease when the branch is absent. Other callers of
   `open_or_update_pr` are unaffected.

5. **Docs.**
   - `coga/skill-management`, package copy
     `src/coga/resources/templates/coga/bootstrap/contexts/coga/skill-management/SKILL.md`
     plus the legacy twin `docs/contexts/coga/skill-management/SKILL.md`,
     which must stay byte-identical. Add a bullet to "Rules for managed
     packs". It covers: the shared branch is rebuilt each run; hand commits
     on an open PR make `--pr` refuse and list them; how to resolve; closing
     the PR discards them deliberately; and the job's commits are recognised
     by the exact message. Also add a short clause to the `--pr` bullet in
     the command section. Keep it consistent with whatever v1/10 adds there.
   - Package `src/coga/resources/templates/coga/recurring/skill-update/ticket.md`:
     in step 3 and the "quiet no-op" / exit-2 paragraphs, state that an open
     PR carrying hand commits fails the run with exit 2 and lists the commits.
     The live recurring copy `coga/recurring/skill-update/ticket.md` must not
     be hand-edited. Follow AGENTS.md: record the reviewed difference in
     `LEGACY_DEFINITION_DIFFERENCES` in `tests/test_packaging.py` if the
     packaging test requires it.

6. **Tests.**
   - `tests/test_skill_manager.py`, guard unit tests with fake runners:
     - (a) no remote branch: returns `None`; no `gh`, `fetch`, or `log` calls;
     - (b) branch present, no open PR: returns the OID with no fetch;
     - (c) open PR with only job commits: returns the OID;
     - (d) open PR with a hand commit: raises, and the message carries the
       short SHA, the subject, and the PR URL;
     - (e) fetched tip ≠ observed OID: raises.
   - One real-git `tmp_path` test with a bare remote, where the runner sends
     `git` to `run_subprocess` and stubs `gh`. Cover: a hand commit (refused);
     a GitHub-style merge of control into the branch plus the job commit
     (passes); and a hand commit cherry-picked onto control (passes).
   - `open_or_update_pr` with `expected_remote_oid`: the push argv carries
     `--force-with-lease=refs/heads/coga/skill-update:<that oid>`, and no
     `ls-remote` runs. The existing `_lease_stub` tests stay as they are for
     the `None` path.
   - CLI (`CliRunner`, as in `test_update_cli_emits_json_summary`):
     `skill update --all --pr` with the guard raising exits non-zero, prints
     the error, and never calls `update_skills`. Assert with a monkeypatched
     sentinel and an unchanged skill file.
   - Existing PR-flow tests that assert exact command sequences: update them
     only as far as the new keyword requires. The guard lives outside
     `run_skill_update_pr_flow`, so most sequences should not change.

### Out of scope

- Carrying hand commits forward onto the rebuilt branch.
- Restoring the working tree after a late refusal. The guard runs before any
  write instead.
- Changing the commit subject, adding a trailer, changing `--pr-title`, or
  changing `recurring_activity`'s machine-commit pattern.
- Leasing on branch absence (`--force-with-lease=<ref>:` with an empty
  expectation). The `None` path keeps #734's behaviour.
- Detecting hand edits hidden inside a merge commit's conflict resolution.
  `--no-merges` skips merges; record this as a known limit in the code
  comment only.
- PRs opened from forks under the same head branch name.
- v1/10's dirty-file preflight itself. Reconcile with it; do not re-implement
  it.

## Context

Every symbol below was checked on `origin/main` `ed32d6052` (2026-11-04).
v1/10's code was read from `origin/coga/v1-10-preflight-dirty-skill-update`
(PR #1168, unmerged at design time).

- `skill_manager.run_skill_update_pr_flow`: returns early when no result has
  `changed`. Otherwise it calls `_assert_no_unmerged_paths` (v1/10 moves that
  into its preflight), records `original_branch`, then calls
  `_commit_skill_updates(base_branch=cfg.git_control_branch)`, runs the
  verify commands, and calls `open_or_update_pr(title, body, branch=,
  remote=cfg.git_remote)`. A `finally` returns to `original_branch`.
- `_commit_skill_updates` → `_checkout(create=True, start_point=base)`, which
  is `git checkout -B <branch> <base>`. It then commits with the literal
  `"Update Coga-managed skills"`. v1/10 changes this call to
  `git commit --only -m ... -- <skills_root>`; keep whichever form is on
  main and swap in the constant.
- `open_or_update_pr` calls `_remote_branch_oid(run, remote, branch, cwd)`,
  which runs `ls-remote` per push URL and refuses if the URLs disagree. It
  leases `--force-with-lease=refs/heads/<branch>:<oid>`, or uses no lease
  when the branch is absent. It then calls `gh pr list --head <branch>
  --state open` and edits that PR or creates a draft. `run_gh` is a closure
  there today.
- `commands/skill.py` `update` calls `update_skills` first, then (with
  `--pr`) the PR flow, and turns `SkillManagerError` into `_bail` (non-zero
  exit, message on stderr). v1/10 adds `assert_skill_update_pr_preflight(cfg)`
  before `update_skills`.
- The recurring path is `recurring/skill-update/ticket.py` →
  `runner.run_recipe(cfg, "skill-update", [])` →
  `skill_update.run_skill_update_recipe` → `run_update_json`, which runs
  `python -m coga.cli skill update --all --json --pr --pr-title ...`. A
  non-zero exit raises `RuntimeError` with stderr in its detail.
  `run_recipe` records the failure on the period blackboard. Keep the error
  message compact: the blackboard keeps a bounded stderr tail.
- The literal `Update Coga-managed skills` also appears in
  `skill_update.recipe_parser` (the `--pr-title` default), in
  `commands/skill.py` (the `--pr-title` default), in `recurring_activity`
  (the machine-commit regex), and in the inactivity topic. None of these
  change.
- Config: `cfg.git_remote` (default `origin`), `cfg.git_control_branch`
  (default `main`). `SKILL_UPDATE_BRANCH` is `coga/skill-update`.
- Origin of this ticket: when #734 shipped the explicit lease, its review
  recorded this gap as an agreed follow-up (FastJVM/admin `7e6da920`). The
  bare lease it replaced protected this case only by accident.

Previous ref: `skill-update-rebuilds-its-branch-and-discards-hand-pushed-commits` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

## Dev

branch: coga/v1-11-skill-update-rebuilds-its-branch-and-disca-0af198


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design notes

- Chose **refuse** over carry-forward (reasons under Description). Guard runs
  pre-`update_skills` in the CLI handler, after v1/10's local preflight, and
  hands its observed OID to the push lease to close the guard→push window.
- Job-commit identity = exact message `Update Coga-managed skills`, no
  trailer. "On control" = freshly fetched `<remote>/<control>` with
  `--cherry-pick` patch equivalence; merges skipped via `--no-merges`.
- No open PR (merged/closed, branch left) → guard skips the commit check.
- v1/10 is PR #1168 (unmerged at design time); its preflight is the
  insertion point.

## Open Questions

All three resolved by the owner on 2026-11-06: accepted as proposed (see
Implementation decisions). Kept below for the record.

- Quiet weeks: an open PR with hand commits makes every weekly run exit 2,
  even with no upstream change, because the guard runs before updates are
  known. Accept (proposed), or prefer post-update guard + restore of the
  skills tree so no-change weeks stay silent?
- Closed-without-merge PR whose branch still holds hand commits: proposed
  behaviour treats closing as the decision to discard and overwrites. OK, or
  should a closed (not merged) PR also refuse?
- Subject-only job-commit identification (no trailer): acceptable residual
  risk of a human using the exact bot message with an empty body?

## Implementation decisions (owner, 2026-11-06, attended implement session)

Owner approved resolutions to the evaluator's must-fix findings and accepted
all three Open Questions as proposed (weekly refusal while hand commits sit on
an open PR; closing the PR discards deliberately; exact-message job identity).

- P1 repo binding: the guard parses owner/repo from every push URL of
  `cfg.git_remote` (github.com only, via `github_source.github_owner_repo`;
  shorthand rejected). All must agree, otherwise it refuses. Then
  `gh pr list --repo <owner/repo>`, and fetch control + branch from the push
  URL into private refs `refs/coga/skill-update-guard/{control,branch}`
  (tracking refs untouched). `open_or_update_pr`'s own gh calls unchanged.
- P1 sweep: a guard refusal sets `git.state_sweep_withheld` before `_bail`,
  so cli.main does not publish unrelated dirty Coga state; exit stays 2.
- P2 patch equivalence: after `--cherry-pick --right-only`, re-check the
  leftover non-job commits with `branchsweep._verbatim_patch_ids` against the
  control commits since the branch's base (stricter, fails closed).

## Evaluator review

**Verdict: resolve the three must-fix findings before implementation.**
Reviewed the body independently against fresh `origin/main` `880ce84ed`.
PR #1168 remains open; its preflight placement and commit changes match the
Context section. The ticket's section hierarchy and frozen workflow are
correct. The scope fits one PR in the existing skill tooling; relocating
`skill *` is explicitly deferred by `coga-dev/microkernel` (Open command
placements).

### Must fix

1. **P1 — Bind PR lookup and history inspection to the push destination.**
   Proposed shape 2 reads the OID from the effective push URL, but its bare
   `gh pr list` uses gh's default repository and `git fetch <remote>` uses
   the fetch URL. Those need not identify the repository that will be
   overwritten. If gh's default repository has no matching open PR while
   the push destination does, the guard takes the "no open PR" bypass,
   returns the destination's OID, and the later lease permits overwriting
   its hand commits. This leaves the ticket's central loss scenario open.
   Evidence: `src/coga/skill_manager.py::_remote_push_urls`,
   `_remote_branch_oid`, and `open_or_update_pr`; existing
   `tests/test_skill_manager.py::test_skill_update_pr_leases_against_the_push_url_not_the_fetch_url`
   and `test_dream_pr_summary_pushes_to_configured_non_origin_remote`
   deliberately support these configurations. A read-only gh 2.92.0 probe
   with origin fetching `git/git` and pushing `FastJVM/coga` resolved bare
   `gh repo view --json nameWithOwner` to `git/git`.
   Specify how the guard proves that PR lookup, fetched control/history,
   and every push destination describe the same repository. Resolve the
   intended repository explicitly, or refuse unsupported mappings before
   treating an empty PR lookup as permission. Add a regression with an
   open PR only at the configured push destination, plus split fetch/push
   and non-origin coverage.

2. **P1 — A handler refusal does not meet the no-push/unchanged-HEAD promise.**
   `src/coga/commands/skill.py::_bail` exits 2, but
   `src/coga/cli.py::main` calls `_sweep_coga_state` on that exit;
   `_SWEEPING_SKILL_SUBCOMMANDS` includes `update`. Existing dirty Coga
   state can therefore be committed and pushed after the new guard
   refuses. v1/10 permits unrelated local edits, so its preflight does not
   close this gap. Reproduced against a temporary bare remote using the
   real `cli.main` dispatch, with `update_skills` replaced by an immediate
   `SkillManagerError` to model the pre-update refusal: exit was 2, an
   unrelated untracked `coga/context.md` was published, local HEAD and
   remote main both advanced, and the worktree became clean.
   Specify how this refusal withholds the outer state sweep while retaining
   exit 2 and recurring failure reporting (the existing
   `git.state_sweep_withheld` mechanism is relevant). Add an entrypoint
   regression with pre-existing unrelated Coga edits and a real local
   remote. The proposed `CliRunner().invoke(app, ...)` test bypasses
   `cli.main`, so it cannot verify this acceptance criterion.

3. **P2 — The proposed symmetric-difference query misses patch equivalence
   after control is merged into the PR branch.** Git's `--cherry-pick`
   compares commits on opposite sides of the symmetric difference, not
   every commit reachable from control. Reproduced with Git 2.43.0:
   create a job commit and hand fix on the PR branch, cherry-pick the hand
   fix onto main, then merge main into the PR branch. Before the merge,
   the exact proposed `git log --no-merges --cherry-pick --right-only`
   query returns only the job commit. After the merge it also returns the
   original hand fix, although `git patch-id --stable` confirms its patch
   equals the copy on main. The copy is now shared ancestry and cannot be
   the left-side match. Thus the guard incorrectly refuses the "Hand commit
   already on control" case after an ordinary "Update branch" operation.
   Specify a comparison that also recognizes equivalent patches in shared
   control history, and add this combined cherry-pick-then-merge case to
   the real-Git test. Testing those operations separately misses it.

### Recommendations and owner decisions

- Update `docs/contexts/coga-dev/packaging/SKILL.md` (Canonical copies and
  twins) alongside the listed docs: it currently requires a reused-branch
  lease to resolve the tip "at push time". Align that summary with the
  intended earlier guarded OID, preferably linking the owning topic.
- Explicitly test fail-closed behavior for PR lookup, fetch, `rev-parse`,
  and history-command errors, and distinguish the exact job message from
  the same subject with a nonempty body.
- Quiet-week refusal, intentional abandonment by closing, exact-message
  identity, and the merge-resolution/branch-absence limitations are
  stated product tradeoffs. The existing Open Questions remain for the
  owner; this review does not approve them. The error-reporting chain
  through `skill_update.run_update_json`, `run_skill_update_recipe`, and
  `runner.run_recipe` is present and retains exit 2 and blackboard evidence.

### Verification

- Fresh fetch confirmed local main equals `origin/main`; no task feature
  branch or PR is recorded. No ticket-body or implementation edits made.
- Three isolated probes verified the patch-equivalence counterexample,
  the real CLI's post-refusal publication, and gh's repository selection.
  All Git writes from those probes stayed in temporary local repositories.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_skill_manager.py -k 'dream_pr_summary or skill_update_pr or update_cli_emits_json_summary'`
  — **13 passed, 82 deselected**. These verify the current baseline, not
  the proposed guard; the full implementation suite remains for that step.
- `coga validate --task v1/11-skill-update-rebuilds-its-branch-and-discards-hand-pushed-commits --json`
  — **1 valid ticket, no issues**. `git diff --check` passed; byte comparison
  against HEAD confirmed the entire ticket body and frontmatter unchanged.

## Implement handoff (2026-11-06)

Branch `coga/v1-11-skill-update-rebuilds-its-branch-and-disca-0af198` pushed
at `1dac58ab8`, rebased on origin/main `d4dc3ac2d`. Rebasing brought in only
Coga state, no src/tests/docs changes.

- `skill_manager`: `SKILL_UPDATE_COMMIT_SUBJECT`; guard
  `assert_skill_update_branch_unclaimed` plus helpers `_run_gh`,
  `_open_pr_url(repo=)`, `_push_destination_github_repo`, `_git_checked`, and
  `_drop_patches_on_control` (lazy wrapper over `branchsweep._verbatim_patch_ids`,
  because branchsweep imports skill_manager). The `ls-remote` OID check runs
  first, then repo binding, the PR lookup, a fetch from the push URL into
  `refs/coga/skill-update-guard/*` (deleted in `finally`), a `rev-parse`
  equality check, `log --no-merges --cherry-pick --right-only`, dropping job
  commits, and the patch-ID recheck against `control ^<candidate>^`.
  `run_skill_update_pr_flow` and `open_or_update_pr` take
  `expected_remote_oid`.
- `commands/skill.py update`: the `--pr` needs `--all` refusal now comes first
  (before, `update_skills` ran and only then refused). The guard runs before
  `update_skills`, and a refusal sets `git.state_sweep_withheld`.
- v1/10 (PR #1168) is still open and its preflight is not on main. When it
  lands, call the guard after `assert_skill_update_pr_preflight(cfg)` and keep
  the `-m SKILL_UPDATE_COMMIT_SUBJECT` constant in its `commit --only` form.
- Behavior note: `--pr` now needs a git repo whose remote push URLs name one
  github.com repo, even when nothing would change. The old
  `test_skill_update` no-op test ran in a non-git directory; it now gets a
  bare origin. GitHub Enterprise or non-GitHub push hosts are refused (fail
  closed).
- Mutation-checked: removing the sweep withholding fails
  `test_update_entrypoint_refusal_publishes_nothing`. Removing the patch-ID
  recheck fails `test_guard_real_git_passes_hand_commit_cherry_picked_onto_control[True]`.
- Pre-existing, unrelated failures, identical on unchanged origin/main:
  `test_packaging.py::test_live_and_packaged_copies_stay_identical` (drift in
  the `coga/checkouts/launch-boundary` twin) and
  `test_context_navigation_has_no_broken_links` (anchors in
  `coga-dev/current-direction`). Not fixed here.
- `LEGACY_DEFINITION_DIFFERENCES` already lists the package
  `recurring/skill-update/ticket.md`; the live copy was left untouched.

## Peer review

Direct Codex review **completed** on final head
`2c05ec3e8289049b22040d9fd23420e311b5fb26`, against base
`c1826714eaa14ad9de49673f6b1384b3a582c8aa`. The initial review was
independent of Claude's implementation; Codex then authored and self-reviewed
fixes `04a0ff184` and `2c05ec3e8`. No unresolved findings remain. Full Linux
verification completed with only the two independently reproduced baseline
failures.

Owner approved the two code fixes in this attended session; the later
documentation correction keeps the required package-owner link:

- **P1 fixed — Pin the PR lookup's host.** `--repo owner/repo` still obeyed
  `GH_HOST`, permitting an empty PR lookup on another host to bypass the
  commit check. A credential-free probe of installed gh confirmed that
  `GH_HOST=127.0.0.1:1` with `--repo FastJVM/coga` targets that host.
  The guard now passes `--repo github.com/FastJVM/coga` (derived from the
  push destination); regressions cover an Enterprise `GH_HOST` and the
  configured non-origin push repository. The owning topic and twin explain
  the host/repository binding and supported destination constraint.
- **P2 fixed — Keep candidate history comparisons separate.** A real Git
  probe with A cherry-picked to main, main merged into the PR branch, then B
  cherry-picked and main merged again incorrectly listed A as foreign.
  Combining parent exclusions removed A's landed copy. Each candidate now
  has its own control-history comparison, at the cost of extra Git reads for
  leftover hand commits. Regressions prove both landed commits pass and a
  later unlanded commit alone is refused. Rev-parse and patch-comparison
  failures also have explicit fail-closed tests.
- **P2 fixed — Link the package owner.** The first completed full suite
  reported the same two failing tests as main, but comparison of individual
  navigation diagnostics revealed an additional introduced link from the
  packaging topic to a removable legacy copy. Commit `2c05ec3e8` points to
  the package owner. Navigation diagnostics now exactly match main; source
  and tests are byte-identical to `04a0ff184`. The final link change was
  directly re-reviewed.

All four new reproduction cases failed before the fixes. The focused suite
passed afterward (145 tests); both standalone history and refusal probes
also pass. The real-subprocess refusal probe used a scratch bare remote with
only GitHub transport stubbed: exit 2 named the branch, PR URL and commit,
while preserving HEAD, remote control/PR tips, index bytes, status and skill
bytes. Through `runner.run_recipe`, that same error returned 2 and reached
both `## Skill Update` and `## Recipe Failure` on the scratch period
blackboard. Plain stderr was inspected; no interactive/TTY surface changes.

`coga validate --json` reports 98 valid tickets and eight pre-existing
warnings, with no error-severity issues. The reported baseline packaging twin
drift and broken navigation links were independently reproduced in an export
of unchanged main; neither is caused by this diff. The initial Linux suite
was interrupted after owner approval of the fixes, before changing source;
its partial run is not a verification receipt. The first full suite completed
at `04a0ff184`: 4514 passed, 10 skipped,
2 failed in 771.88s. One failing navigation test included the introduced
link issue above alongside baseline errors; that issue is now fixed. The final
suite at `2c05ec3e8` completed: **2 failed, 4514 passed, 10 skipped in
633.23s (0:10:33)**. Its two failures
are now entirely baseline: launch-boundary twin drift, and the missing
anchors in current-direction/testing. A real Git lease probe also passed:
a hand push after the guard survived, and the job push failed with
`stale info`, without another `ls-remote` or PR edit.

**Native Windows waiver:** the owner explicitly answered "Waive Windows for
this ticket" in this attended peer-review session (2026-11-06). No Windows
suite was run and no AWS host was provisioned. This is a ticket-specific
exception to `coga-dev/testing`, not native-platform evidence.

Freshness: the required rebase preserved the projected ticket byte-for-byte;
main's intervening changes were ticket/log state only. Final fixes are pushed.
PR #1168 remains open, so its preflight integration still belongs to whichever
branch lands second. Ticket body/frontmatter remain unchanged.

## PR

```yaml
title: Refuse to rebuild skill-update branch over hand-pushed commits
author: claude/codex
author_evidence: Claude implemented the original change (implement launch 71ea29e2-5009-4e12-8cfa-16dd1dda98da, original commit 1dac58ab8, rebased to 6d6763ab6). Codex authored review fixes 04a0ff184 in peer-review launch 748c82e6-763d-4e51-b68d-593d77e04474. Codex also corrected the introduced package-owner link in 2c05ec3e8.
head: 2c05ec3e8289049b22040d9fd23420e311b5fb26
base: c1826714eaa14ad9de49673f6b1384b3a582c8aa
depth: deep
rationale: Changes the overwrite and force-push rules of an unattended job. Inspect host binding, commit identity and patch equivalence. Final fixes have Codex self-review; native Windows verification was explicitly waived by the owner. The full Linux suite has only two independently reproduced failures on unchanged main; both remain visible below.
implementation: Before updating skills, the PR flow checks the push destination for an open skill-update PR and refuses if its branch carries unlanded hand commits. The guard pins the GitHub hostname and repository, fetches control and branch into private refs, recognizes landed patches even across repeated control merges, withholds CLI state publication on refusal, and leases the later push against the checked tip.
deviations: Owner-approved evaluator fixes bind history and PR lookup to the push destination, use temporary private refs rather than tracking refs, and supplement Git cherry comparison with whitespace-sensitive patch IDs. Review fixes pin github.com despite GH_HOST and compare each candidate against its own control-history range. The --pr requires --all check runs before any update. Review also corrected the packaging topic link to its canonical package owner.
limitations: 'An existing remote branch requires push URLs naming one github.com repository. Exact job-message impersonation and hand edits in merge conflict resolutions remain accepted limits. Branch-absence push behavior is unchanged. PR 1168 is still open; its local preflight must precede this guard when the branches reconcile. Linux/Python 3.12 only: the owner explicitly waived native Windows verification for this ticket on 2026-11-06. Final Codex fixes have self-review.'
files:
  src/coga/skill_manager.py: Job commit identity, fail-closed branch guard bound to the push host/repository, per-candidate patch comparisons, and guarded push-lease threading.
  src/coga/commands/skill.py: Call the guard before update_skills, withhold the sweep on refusal, and pass the guarded OID to the PR flow.
  tests/test_skill_manager.py: Guard and lease tests, real-Git landed/foreign histories including repeated control merges, GH_HOST and non-origin binding, lookup/patch failures, CLI ordering, and publication refusal regressions.
  tests/test_skill_update.py: The no-op recipe test now gives the --pr subprocess a git repo with a bare origin, which the guard needs.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/skill-management/SKILL.md: Owns the refusal/remedy, job commit identity, and explicit supported push-host/repository binding.
  docs/contexts/coga/skill-management/SKILL.md: Byte-identical legacy twin of the package topic.
  src/coga/resources/templates/coga/recurring/skill-update/ticket.md: Name the hand-commit exception to the quiet no-op and the exit-2 report.
  docs/contexts/coga-dev/packaging/SKILL.md: Align the lease summary with the guarded tip and link the owning package topic rather than a removable legacy copy.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 2c05ec3e8289049b22040d9fd23420e311b5fb26
  base: c1826714eaa14ad9de49673f6b1384b3a582c8aa
  detail: Direct review completed on the final head/base with no unresolved code findings. Codex independently reviewed the Claude implementation, then fixed and self-reviewed GH_HOST misbinding and lost patch evidence after repeated merges. The final receipt is conservatively self-review. The final documentation-only commit was re-reviewed and its navigation diagnostics now exactly match unchanged main.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q --basetemp=/home/n/Code/coga-review-v1-11-complete-748c82e6
  status: failed
  head: 2c05ec3e8289049b22040d9fd23420e311b5fb26
  base: c1826714eaa14ad9de49673f6b1384b3a582c8aa
  detail: '2 failed, 4514 passed, 10 skipped in 633.23s (0:10:33). Both failures also reproduce on unchanged main c1826714e: launch-boundary package/live twin drift, and missing navigation anchors in coga-dev/current-direction and coga-dev/testing. No new test failures.'
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_skill_manager.py tests/test_skill_update.py
  status: passed
  head: 04a0ff1842ad4e9bbf1be964bf031fd9307a9ed1
  base: c1826714eaa14ad9de49673f6b1384b3a582c8aa
  detail: 145 passed in 3.33s. The four host-binding/repeated-merge reproduction cases failed before the fixes.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/coga validate --json
  status: passed
  head: 2c05ec3e8289049b22040d9fd23420e311b5fb26
  base: c1826714eaa14ad9de49673f6b1384b3a582c8aa
  detail: 98 valid tickets, no error-severity issues; eight pre-existing warnings.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /tmp/coga-v1-11-review-entrypoint-probe.py
  status: passed
  head: 04a0ff1842ad4e9bbf1be964bf031fd9307a9ed1
  base: c1826714eaa14ad9de49673f6b1384b3a582c8aa
  detail: 'Real subprocess CLI and Git history with only GitHub transport stubbed: refusal exits 2, preserves HEAD, remote tips, index, status and skill bytes; recurring recipe records the PR URL and hand commit in both blackboard failure reports. Plain stderr inspected.'
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /tmp/coga-v1-11-review-history-probe.py
  status: passed
  head: 04a0ff1842ad4e9bbf1be964bf031fd9307a9ed1
  base: c1826714eaa14ad9de49673f6b1384b3a582c8aa
  detail: Two successive hand-fix cherry-picks and control merges now pass; the same history incorrectly refused before the fix.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /tmp/coga-v1-11-review-lease-probe.py
  status: passed
  head: 04a0ff1842ad4e9bbf1be964bf031fd9307a9ed1
  base: c1826714eaa14ad9de49673f6b1384b3a582c8aa
  detail: 'A real Git hand push after the guard is preserved: the later push fails with stale info, without a fresh ls-remote or a PR edit.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: 2c05ec3e8289049b22040d9fd23420e311b5fb26
  base: c1826714eaa14ad9de49673f6b1384b3a582c8aa
  detail: No whitespace errors. The skill-management package/live twins match.
- command: python -m pytest
  status: not-run
  detail: Native Windows full suite explicitly waived by the owner in this attended peer-review session on 2026-11-06. No AWS host provisioned; no native Windows receipt claimed.
- command: PYTHONPATH=/home/n/Code/coga-review-v1-11-baseline-748c82e6/src /home/n/Code/coga/.venv/bin/python -m pytest -q tests/test_packaging.py::test_live_and_packaged_copies_stay_identical tests/test_packaging.py::test_context_navigation_has_no_broken_links
  status: failed
  head: c1826714eaa14ad9de49673f6b1384b3a582c8aa
  base: c1826714eaa14ad9de49673f6b1384b3a582c8aa
  detail: Both tests fail identically in a clean export of unchanged origin/main. This is baseline diagnosis, not verification of the feature head.
```
