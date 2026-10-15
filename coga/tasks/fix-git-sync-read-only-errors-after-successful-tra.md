---
title: Fix Git sync read-only errors after successful transitions
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
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 2 (evaluate-design)
agent: claude
---

## Description

Automatic Git publication can fail after a successful local workflow transition. Preserve the completed transition and explain which publication operation failed, where Git was writing, and how to publish the recorded state without advancing again.

Observed on 2026-10-14 in `/home/n/Code/codex/multiply`: `coga bump v0/add-a-harness-inspection-and-manual-run-debug-tool` reported step 3 (`review-design`), assigned to nicktoper, and exited 0. Two subsequent messages, labeled `Ticket: ... — step 3 (review-design)` and `Sync coga state`, reported:

```text
[git] sync failed: `git hash-object` failed: error: unable to create temporary file: Read-only file system
fatal: Unable to add coga/tasks/v0/add-a-harness-inspection-and-manual-run-debug-tool.md to database.
```

The ticket write succeeded. Raw Git stderr makes this look like the whole checkout is read-only. A later draft-creation failure had the reverse permissions (working tree read-only, `.git` writable) and is a separate observation. The original session's exact policy and denied path remain unverified; do not turn the sandbox hypothesis into a diagnosis.

Design investigation reproduced the mechanism with real Git in a disposable checkout: an explicitly selected object directory without write permission caused both publication attempts to fail while `bump` advanced once. The existing `coga run publish-state` then published the ticket and log without another transition, and a second recovery invocation was a no-op. No publication-path defect was found in that reproduction; the proposed change is diagnostic and recovery guidance.

### Acceptance criteria

- [ ] A reproducible object-write permission failure names the checkout, effective object directory, and cause. Cover ordinary `.git`, a linked checkout's shared object store, and a `GIT_OBJECT_DIRECTORY` override in path-resolution tests; do not assume `<checkout>/.git/objects`. The original Codex session need not be recreated. Record whether the reproduction is permission-denied or EROFS rather than claiming they are identical observations.
- [ ] For an ordinary forward `bump` whose task sync and exit sweep both fail, stdout still reports the completed step, exit status remains 0, and the ticket and transition audit record remain local. Stderr explicitly distinguishes the saved local transition from failed Git publication and says not to rerun `bump` to recover.
- [ ] Object-write diagnostics identify `git hash-object -w`, the relative file being hashed, absolute checkout and effective object-directory paths, and the underlying Git error. Diagnostic lookup failure preserves the original error and reports the location as unavailable; it never replaces the error or makes a best-effort sync fatal. Preserve existing redaction protections.
- [ ] Recovery guidance points to `coga run publish-state` in the same checkout after the operator restores permitted Git access (including an external object directory when applicable). It must not automatically modify permissions, sandbox configuration, environment routing, or object storage. Permission or sandbox causation is conditional unless established.
- [ ] A real-Git test invokes the CLI through its exit sweep, observes the failed publication after one successful transition, restores access, and runs `coga run publish-state <ticket-file> <log-file>`. Verify the remote control branch contains the recorded ticket and log, the step is unchanged by recovery, and the transition audit entry appears exactly once. A repeated recovery succeeds without another transition or publication commit. Also verify recovery while access is still denied exits nonzero and keeps the state.
- [ ] Shared reporting preserves existing caller policies: best-effort remains nonfatal, strict paths still raise and let their callers restore state, refusal and uncertain-publication semantics remain distinct, log-only sync stays stderr-only, and recurring failure sinks retain their existing behavior. Generic or strict callers must not claim a local transition succeeded. A diagnostic/audit-write failure must not overturn an already successful best-effort transition.
- [ ] Update the owning publication and recovery topics and the existing restricted-sandbox guidance; keep their packaged twins byte-identical. Lifecycle and checkout guidance must remain consistent that publication failure never authorizes another forward bump or discarding unpublished state.

### Proposed shape

1. **Enrich the failure at its source.** In `src/coga/git.py`, extend `_hash_blob`'s failure branch with best-effort location lookup using Git itself: `git -C <root> rev-parse --path-format=absolute --git-path objects`. Use the same inherited environment as the failed write (`_run` / `_git_env`), so linked worktrees and absolute or relative `GIT_OBJECT_DIRECTORY` values resolve as Git sees them. Show the absolute checkout and optionally Git/common directories for context; the effective object directory is the write destination that matters. Resolve only after failure, retain the original stderr, and tolerate failed probes. Do not claim an individual temporary filename is known when Git did not disclose it. Apply the existing redaction conventions to emitted error text.
2. **Share presentation, retain transaction ownership.** Add a small failure formatter/reporter in `src/coga/git.py` for the existing Git sync handlers. Its real consumers are `sync_task_state`, `sync_coga_state`, `sync_log`, `src/coga/mark.py` `_publish`, and the existing recurring/delete handlers listed in Context. Prefer shared formatting with caller-owned logging, exception propagation, and recurring sinks over a new publication abstraction. Retain recognizable `[git] sync failed` / `[git] log sync failed` prefixes and the publication subject identifying task sync versus sweep. The ordinary task path can say local state was saved; the sweep can say local files were retained. Strict and recurring adoption paths use neutral wording. Audit details remain concise; remedy prose belongs on stderr. Ensure a failed diagnostic log append cannot escape a best-effort failure handler.
3. **Give recovery, not another transition.** For object-write failures, explain that writing the checkout file and writing Git's object database are separate operations. A representative ordinary-bump message is: `Local task state was saved; Git publication failed. Do not rerun bump. Restore permitted access to the Git storage shown above, then run coga run publish-state from this checkout.` Where a concrete existing ticket file is available, include it and the configured log path as required files, shell-quoted and valid from the stated directory. Use the actual `ticket.md` for directory-form tasks. A sweep or deletion can recommend the no-path form, since deleted paths are invalid explicit arguments but are included in the root sweep. Never imply the recovery publishes only named files: the recipe covers all eligible state under the Coga roots.
4. **Keep the existing recovery contract.** `src/coga/publish_state.py` `run_publish_state_recipe` already supplies fetch, guarded publication, explicit confirmation and failure exit codes without a transition. No new command is needed. With Git disabled its success text means local-only, not publication; retain that qualification. Generic transport failures and `UncertainPublishError` must not acquire permission diagnoses or a false assertion that remote state definitely did not land. Existing strict refusal/reconciliation guidance takes precedence over a generic retry hint.
5. **Turn the experiment into focused regression coverage.** Extend `tests/test_git.py`, `tests/test_publish_state.py`, and lifecycle tests where needed. Use a disposable real repo plus bare origin and a genuinely unwritable object directory for the integration case; restore temporary permissions in cleanup. Environments that ignore chmod (such as root) need an explicit capability skip for that case, with deterministic failure injection still covering message/exit behavior everywhere. Test EROFS stderr through injection, location-probe failure, a relative override from a different process cwd, and a path containing spaces. Check strict exceptions and stderr-only log sync as regressions. Exercise `cli.main` via subprocess, since `CliRunner.invoke(app, ...)` alone omits the exit sweep. Do not change the live repository's permissions or settings.
6. **Update contracts with implementation.** Own detailed failure reporting in `docs/contexts/coga/internals/state-publication/publish/SKILL.md` and recovery in its sibling `sweep/SKILL.md`; link rather than duplicate from the overview or lifecycle topics as necessary. Extend the existing `Restricted sandboxes` bullet in `docs/contexts/coga/testing/SKILL.md` to distinguish checkout writes, object writes, and index locks, with actual Git-resolved destinations and operator-authorized recovery. Keep `docs/contexts/dev/checkouts/SKILL.md` consistent about retained unpublished handoffs. Update each changed topic's corresponding `src/coga/resources/templates/coga/bootstrap/contexts/<ref>/SKILL.md` in the implementation PR and run packaging twin checks.

### Out of scope

Changing publication retries, suppressing the second sweep failure, adding a queue or recovery command, altering success exit codes for ordinary lifecycle commands, changing strict rollback/refusal/provenance semantics, or repairing control-branch divergence. The canceled `fix-git-sync-failure` ticket addressed divergence and fast-forward refresh, a separate problem. No changes to `coga.toml`, `coga.local.toml`, agent launch flags, sandbox policies, or the original multiply checkout. A different publication or permission-integration defect discovered during implementation must be evidenced and discussed before expanding this design.

## Context

### Verified code relationships

- `src/coga/commands/bump.py` `bump` calls `src/coga/bump.py` `advance_step`. That function validates prospective state, writes the ticket and audit record, echoes the step, then calls `src/coga/git.py` `sync_task_state` for an ordinary forward move. The original pointer to `mark._publish` was incomplete: ordinary step advancement uses `sync_task_state`; `src/coga/mark.py` `_publish` serves mark operations including terminal completion.
- `src/coga/git.py` `_guard` and `_build_tree` call `_hash_blob`; the former may write a candidate blob during provenance checks before tree construction. `_hash_blob` uses `_run` with `hash-object -w --path=<rel> --stdin`; `_git_env` preserves inherited Git environment overrides. A temporary `GIT_INDEX_FILE` used by publication does not relocate the object database.
- `src/coga/cli.py` `main` calls `_sweep_coga_state`, which invokes `src/coga/git.py` `sync_coga_state`. That wrapper retries dirty Coga-root state under the subject `Sync coga state`. This explains the second error without a second workflow transition. `src/coga/cli.py` `_should_sweep_coga_state` excludes `run publish-state`.
- `src/coga/publish_state.py` `_publish_state`, called by `run_publish_state_recipe`, validates named regular files, fetches configured control, then calls `src/coga/git.py` `publish` over `coga_root_paths` with `require_paths`. It does not call lifecycle advancement. `src/coga/runner.py` `_record_failure` may append a `Recipe Failure` blackboard note on failure in an inherited task session; that is not a second transition.
- `src/coga/recurring_runner.py` `_sync_recurring_create`, `_sync_recurring_create_paths`, and `_adopt_control_period` each emit sync-failure text and call `_append_sync_failure`. The latter preserves a caller-provided failure sink and conditionally appends an audit note. Adoption can restore a peer's task, so generic messages there must not promise that a newly created local task survived. `src/coga/commands/delete.py` `delete` and `src/coga/commands/recurring.py` `promote` catch publication failures with stderr-only messages; preserve those policies when sharing presentation.

### Contract references (cited, not attached)

Read `coga/internals/state-publication/publish` (`docs/contexts/coga/internals/state-publication/publish/SKILL.md`), especially “Best-effort versus strict”, and `coga/internals/state-publication/sweep` (`docs/contexts/coga/internals/state-publication/sweep/SKILL.md`), especially “Strict publication on demand”. These leaves now own the details formerly referenced through the parent topic. Read `coga/sync` (`docs/contexts/coga/sync/SKILL.md`) for the keep-the-write rule; `coga/testing` (`docs/contexts/coga/testing/SKILL.md`) for “Restricted sandboxes” and interpreter isolation; and `dev/checkouts` (`docs/contexts/dev/checkouts/SKILL.md`) for “Hand off from the branch”. Existing sandbox documentation is guidance, not evidence of the original session's actual policy.

<!-- coga:blackboard -->

## Design investigation — 2026-10-14

- Design only: no source changes, branch, or PR. Initial checkout was clean on `main`. Spec is under Description/Context so it composes into later steps.
- Real-Git reproduction passed under `.venv/bin/python` (Python 3.12.12), Git 2.43.0, uid 1000. Used an inline disposable experiment with `PYTHONPATH=/home/n/Code/coga/src:/home/n/Code/coga/tests`, `tests/conftest.py` `init_git_repo`, and `tests/test_git.py` `_ticket_text`; subprocess CLI calls used the same interpreter and scrubbed inherited launch/Git variables. Initial ambient `python3.12` attempt failed before the experiment because `tomlkit` was absent; use the checkout venv.
- Reproduction layout: `/tmp/coga-object-write-design-qxi0m1ms/repo` with ordinary `.git`, a bare local origin, and `GIT_OBJECT_DIRECTORY=/tmp/coga-object-write-design-qxi0m1ms/restricted objects` chmod 0555. `GIT_ALTERNATE_OBJECT_DIRECTORIES` pointed to the repo's existing `.git/objects` for reads. `git rev-parse --path-format=absolute --git-path objects` returned the restricted directory, while `--git-common-dir` returned the repo's `.git`. The denied write destination was the override directory; uid 1000 lacked its write bit. Git reported `insufficient permission for adding an object to repository database`, not EROFS. This demonstrates the same split between writable ticket and unwritable object store, without attributing the original failure to a specific sandbox policy.
- `python -m coga.cli bump demo` exited 0, printed step 2 (review), emitted exactly two sync failures (task and sweep), retained local step 2, left origin at step 1, and recorded exactly one `advanced to step 2` audit entry.
- Restored scratch-directory permissions and removed the injected object overrides. `python -m coga.cli run publish-state coga/tasks/demo.md coga/log.md` exited 0 and confirmed publication to origin/main. A second identical invocation exited 0 with `already on origin/main`. Both kept the ticket bytes unchanged and origin's transition entry count at one. A linked checkout probe resolved its object directory to the primary repo's `.git/objects`. Temporary repositories were cleaned up; no live permissions or configuration were changed.
- Design choice: existing recovery is sufficient; enrich the shared object-write error and sync presentation. Preserve two attempts, strict callers, audit sinks, and uncertainty semantics. No evidence supports a Coga path-integration fix or a claim about the original Codex version/configuration. Implementation must add durable automated regressions; this experiment is design evidence, not the completed fix.

## Design verification

- `coga validate --task fix-git-sync-read-only-errors-after-successful-tra --json`: 1 OK, no issues.
- `git diff --check`: passed.
- Read-only `compose.compose_prompt` check: acceptance criteria, proposed shape, out of scope, verified context, evidence and open questions are all included. Ticket frontmatter matches HEAD byte-for-byte before the workflow transition.
- No source/test changes; the real-Git experiment above is the behavioral evidence for this design.

## Open Questions

None blocking the proposed implementation. The original session's exact denied path and policy remain unknown; the ticket explicitly accepts synthetic reproduction, and the observed mechanism plus verified recovery establishes the bounded design without that attribution.
