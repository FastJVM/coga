---
title: Fix coga git sync failures that leave main diverged from origin
status: in_progress
owner: nicktoper
contexts:
- coga/state-publication
- coga-dev/internals/state-publication
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
step: 2 (evaluate-design)
agent: claude
launch_generation: pending:a8b5269f-a0ec-43f9-bcf6-1f7facc92741
---

## Description

Coga's automatic git sync keeps failing in the Multiply checkout
(`~/Code/multiply`), and on 2026-09-29 a failure left local `main` diverged
from `origin/main`, forcing a manual reset. Diagnose each failure class
against the **current** Coga revision, fix what is fixable in code, and record
an explicit decision for the rest, so sync either succeeds or fails loudly
with a remedy and never leaves `main` diverged. Do not assume Coga's sandbox
makes `.git` read-only: on the owner's machine `.git` is read-write, so a
"Read-only file system" error comes from whatever sandbox the failing process
ran in, and that process has to be identified.

The design investigation (2026-11-04, evidence in `## Context` → "Findings")
found that almost every failure came from Codex's sandbox, not from Coga. The
EROFS classes and almost every DNS failure were `coga bump` / sweep commands
run inside a Codex session whose effective sandbox had no network and a
read-only `.git`. Those failures stopped on 2026-10-14 when the owner widened
the machine-wide `/etc/codex/requirements.toml` profile. The 2026-09-29
divergence was an agent's hand `git commit` of state, not a Coga commit, and
#948 already realigns that shape. One code defect remains: publication writes
its temporary Git index files to `$TMPDIR`, so a full `/tmp` fails the publish
(10-27). This ticket fixes that, adds the missing regression tests for the
incident shape, and records the per-class decisions.

### Per-class disposition

Counts are from the 2026-11-04 recount: 259 lines (68 Aug, 159 Sep, 32 Oct).
"After" means after 2026-10-15, once the widened Codex profile was in force.

| Class | Count (window) | After | Disposition |
| --- | --- | --- | --- |
| DNS: `git fetch` / push → `Could not resolve host` | 155 (08-14 → 10-13) | 0 | **Fixed by owner config, already applied.** Codex sessions ran `workspace-write` with `network_access:false` (session `turn_context`, e.g. 09-22). The October push failures sit inside `launch_agent=codex` windows. `/etc/codex/requirements.toml` profile `multiply-full` now sets `network.enabled = true`. A minority (about 27, mostly 08-19 and early Sep) could not be tied to a Codex window. They all predate #848 and nothing similar has been seen since, so they are **accepted**: current code reports the error loudly, and the next command's sweep retries. |
| EROFS: `git hash-object` → `unable to create temporary file` | 77 (09-22 → 10-14) | 0 | **Fixed by owner config, already applied.** Every instance sits inside a Codex session, including those labeled `[agent:claude]` / `[human:nicktoper]`; see "Actor labels". Codex's `workspace-write` keeps `.git` read-only under its writable roots. The `requirements.toml` edit on 10-14 (~21:10 PDT, `"/home/n/Code" = "write"`) is the last change before failures stop. The final failure (21:11) came from a session started at 21:05 under the old policy. The fetch → `hash-object` switch on 09-22 is #848: `git._publish_locked` no longer fetches first, so `git._hash_blob` is the first `.git` write. One cause, two code paths. |
| EROFS: `git add` → `.git/index.lock` | 4 (08-26 ×3 `~/Code/codex/multiply`, 09-21 ×1 `~/Code/multiply`) | 0 | Same Codex sandbox cause; **fixed by the same owner config**. The `git add` path no longer exists after #848. |
| Rebase conflict / untracked-blocked / autostash reapply | 22 (08-19 → 09-17) | 0 | **Resolved by #848.** Current `src/coga/git.py` has no rebase or autostash sync path. The only remaining mention is the remedy string in `git._divergence_message`. |
| ENOSPC: temp index `/tmp/coga-git-index-*.lock` | 1 (10-27, in a Claude recurring session) | 1 | **Fix in code (this ticket).** `/tmp` is a tmpfs capped at about 1M inodes. Pytest `tmp_path` retention from Coga's own suite can exhaust it (see the uncommitted `pyproject.toml` edit and Open Questions). Publication should not depend on a second filesystem. Move its scratch files into the Git dir, where Git keeps its own `index.lock`. |

Divergence (incident 09-29): **covered by #948**. Coga's `publish` never
commits on the checked-out branch: it uses `commit-tree` on the control base
and moves local control only through `fast_forward_control`. So a failed
in-session sync cannot itself become a later local commit. The incident's
ahead commit `94da4bda` was a hand commit of state-only files ("Decide
title-only tickets…", Co-Authored-By Claude). An ad-hoc probe on current
`main` ran a failed offline publish, then a hand commit of the retained state,
then a later sync: `main` realigned level with origin, and stderr said so.
With a non-state file in the hand commit, the state still landed, `main` was
left untouched, and stderr named `git pull --rebase --autostash origin main`.
No test pins this chained shape yet, so this ticket adds it.

Moving publication out of the sandbox (question 3): **not needed; no
follow-up ticket.** The outer `coga launch` process already republishes
after the session exits. The 10-14 21:11 in-session failure landed on control
at 21:23:09 as `Sync coga state before checkout return` (Multiply `ca306ba3`).
In-sandbox failures cost noise and a short window of non-durability, not
state.

### Acceptance criteria

- [ ] `git._build_tree`, `git._write_published` and `git._merge_union_bytes`
      create no files under `tempfile.gettempdir()`. Their scratch files live
      in the checkout's own Git dir (`git rev-parse --absolute-git-dir`, which
      is per-worktree for a linked worktree) and are removed on success and on
      failure.
- [ ] New test in `tests/test_git.py`: with `tempfile.tempdir` pointed at a
      path that does not exist (or is not writable), `git.publish` of a ticket
      edit and of a `merge=union` log edit both succeed. Afterwards no
      `coga-git-index-*` or `coga-union-merge-*` entries are left in the Git
      dir.
- [ ] New test, in the "realigning a state-only divergence" block of
      `tests/test_git.py`: an offline `sync_task_state` (exits normally, file
      stays dirty), then a hand commit of the retained ticket and log on
      `main`, then the remote is restored, a peer advances control, and
      `sync_coga_state` runs. Assert that control holds the ticket and the
      `sync failed` log line, `main` equals the origin tip, the tree is clean,
      and stderr contains `realigned local 'main' to origin/main`.
- [ ] Companion test: the same chain, with the hand commit also touching a
      non-state file. Assert that control holds the ticket, `main` still points
      at the hand commit, and stderr names `git pull --rebase --autostash
      origin main`.
- [ ] `docs/contexts/coga-dev/internals/state-publication/SKILL.md` records
      the durable decisions in a short section: scratch files in the Git dir
      and why; in-sandbox publication failures are healed by the launch's
      checkout return and exit sweep, so no deferred-publication state; the
      Codex-sandbox diagnosis pointer to `coga/sandboxes`.
- [ ] `docs/contexts/coga/sandboxes/SKILL.md` ("Codex sandbox grant") says that
      a missing grant shows up in `coga/log.md` as `[git] sync failed` with
      `Could not resolve host` or `git hash-object … Read-only file system`.
      It also says that a machine-level `/etc/codex/requirements.toml`
      permission profile can supply the same grant. Keep the packaged twin
      byte-identical if one exists (`tests/test_packaging.py`).
- [ ] `python -m pytest tests/test_git.py tests/test_packaging.py` passes, then
      the full suite.
- [ ] Owner-run check at the final `review` gate (not the agent's job): with
      the PR build active in Multiply, one launched Codex session and one
      launched Claude session each finish a step with no new `[git] sync
      failed` line. The owner attaches the `coga/log.md` excerpt to the PR,
      with each session's sandbox/network settings (for Codex, the
      `sandbox_policy` from its session file). Note: Multiply's `coga` is a uv
      **editable** install of `~/Code/coga/src`, so "installing the PR build"
      means checking out the PR branch in `~/Code/coga`.

### Proposed shape

1. **`src/coga/git.py` — scratch location.** Add one private helper, e.g.
   `_scratch_dir(root: Path) -> Path`, that returns
   `Path(run_git(root, "rev-parse", "--absolute-git-dir").strip())`.
   - In `_build_tree` and `_write_published`, replace
     `tempfile.mkstemp(prefix="coga-git-index-")` with
     `tempfile.mkstemp(prefix="coga-git-index-", dir=_scratch_dir(root))`.
     Keep the existing close/unlink/`finally` cleanup, since Git creates
     `<index>.lock` beside the index path.
   - Give `_merge_union_bytes` a keyword `scratch: Path` and use
     `tempfile.TemporaryDirectory(prefix="coga-union-merge-", dir=scratch)`.
     Thread it from its two callers, `_build_tree` and `_published_proof`,
     both of which have `root`.
   - Resolve the dir once per publish attempt if that is cheap. Do not cache
     it across calls or processes.
2. **`tests/test_git.py`** — the three tests above. Reuse the `_seed_ticket`,
   `_ticket_text`, `_hand_commit`, `_head`, `_origin_tip`, `_dirty`, `_control`
   helpers and `git_repo.push_competing_commit`. The offline step follows
   `test_offline_publish_leaves_the_write_dirty_and_the_sweep_retries_it`
   (`remote set-url` to a missing path).
3. **Docs** — the two topic edits above. Keep them short, and cite this
   ticket's findings rather than restating the per-class table.
4. Do not touch realignment (`_local_control_subsumed`, `_realign_control`,
   `fast_forward_control`), provenance, or log union semantics.

### Out of scope

- Any pending-publication / deferred-retry state or supervisor-side
  publication change; per the findings above, it is not needed.
- A launch-time check that warns when a Codex session lacks the grant. Dream's
  preflight already covers that; propose a separate ticket if the owner wants
  one.
- Mis-reporting a post-push `_write_published` failure as "Git publication
  failed" even though the commit landed. The next sync heals it (`tree ==
  base` → fast-forward). Moving scratch into the Git dir removes the observed
  trigger; a broader fix would be its own ticket.
- Editing Multiply's config, `/etc/codex/requirements.toml`, or any
  `coga.toml` / `coga.local.toml`. Those are owner actions (Open Questions).

## Context

### Incident (2026-09-29)

Evidence comes from Multiply (`~/Code/multiply`, its `coga/log.md`), a
consumer repo; the fix lands here in Coga. Local `main` was 1 ahead / 5
behind `origin/main` with uncommitted `coga/log.md` and ticket edits, all of
which had already reached origin through separate sync commits; the working
tree was byte-identical to `origin/main`. Fixed by hand with
`git branch backup/main-94da4bda HEAD && git reset origin/main`. The
`backup/main-94da4bda` branch still exists in Multiply as a repro artifact;
after #948 it reproduces an already-handled case.

**Already fixed since:** PR #948 (`f7fde464b`, merged 2026-10-05) made
`git.fast_forward_control` realign local control when
`git._local_control_subsumed` proves every local-only commit is Coga state
control already carries (`git._realign_control`); otherwise
`git._divergence_message` refuses with a `git pull --rebase --autostash`
remedy. Tests: `tests/test_git.py` ("hand commit was realigned away", the
"realigning a state-only divergence" block). Do not add another realignment
path; reuse this one.

### Findings (design step, 2026-11-04)

Recount: `grep "\[git\] sync failed" ~/Code/multiply/coga/log.md` → 259
lines. The ticket's earlier 263 predates a log trim. Per class: DNS 155,
`hash-object` EROFS 77, `index.lock` EROFS 4, rebase/autostash 22 (18 rebase
+ 4 "could not reapply local changes"), ENOSPC 1. The `[coga]` slug is the
repo-wide sweep; other slugs are ticket-scoped syncs.

- **Version.** `~/.local/bin/coga` is a uv tool with
  `requirements = [{ name = "coga", editable = "/home/n/Code/coga" }]`,
  installed 2026-10-15. It reports `0.4.1` from `pyproject.toml`, but runs
  whatever `~/Code/coga/src` holds at that moment. Release tags therefore say
  nothing about which code produced a given line. The 09-22 switch to
  `hash-object` failures came the morning after #848 merged (09-21 20:31),
  which fits an editable install tracking `main`.
- **Which process.** Each failure was matched to its enclosing session: a
  `launched (… agent=X)` line, then the failure, then that session's usage
  record `"cli":"X"`. All EROFS failures sit in `cli=codex` windows; most DNS
  failures do too. Codex session files (`~/.codex/sessions/<date>/*.jsonl`,
  `turn_context.sandbox_policy`) show the effective policy:
  - 2026-09-22: `{"type":"workspace-write","network_access":false}` with no
    extra writable roots.
  - From 2026-10-16:
    `writable_roots:["/home/n/.codex","/home/n/Code","/home/n/Code/coga/.git","/tmp"], network_access:true`.

  The source is root-owned `/etc/codex/requirements.toml`, profile
  `multiply-full`, written for Multiply's harness confinement. Its backups
  show the 10-14 evening edit replacing `":workspace_roots" = "write"` with
  `"/home/n/Code" = "write"`. Neither `~/.codex/config.toml` nor
  `~/Code/multiply/.codex/config.toml` sets a sandbox; Multiply has no
  `.codex/config.toml` grant. Claude Code's user settings set only
  `permissions.defaultMode = "auto"`, and the one post-#848 Claude-session
  failure is the ENOSPC.
- **Actor labels.** `[agent:claude] advanced … → codex` inside a Codex
  session reflects the missing `launch_args = "--no-daemon"` in Multiply's
  `[agents.codex]`. Codex's shared app-server daemon drops the `COGA_*` launch
  env, so bumps get credited to a stale or human actor; the shipped template's
  comment documents this. This affects audit attribution, not sync.
- **After the profile change.** Between 10-15 and 11-04 Multiply ran 20
  Codex launches (13+ on tickets) with in-session bumps, and no sync failure
  except the single 10-27 ENOSPC.
- **ENOSPC.** `/tmp` is tmpfs (32G, 1,048,576 inodes). The uncommitted
  `pyproject.toml` edit in `~/Code/coga` (`tmp_path_retention_policy =
  "failed"`, "passing runs otherwise exhaust /tmp inodes") points at Coga's
  own test runs as the filler. Temp index sites: `git._build_tree`,
  `git._write_published` (`tempfile.mkstemp(prefix="coga-git-index-")`), and
  `git._merge_union_bytes` (`TemporaryDirectory(prefix="coga-union-merge-")`).
  The failing call was `git rm --cached` against the temp index inside
  `_build_tree`, before any push.
- **Publish order.** `git._publish_locked` builds on the remote-tracking ref
  (`_control_base`) and fetches only when it is missing or a push is
  rejected. So in a sandbox, `_hash_blob` (first object write) fails before
  any network call, and with `.git` writable but network off, `_push` fails.

### Code pointers

- `git.sync_task_state`, `git.publish` → `git._publish_locked` and its
  `hash-object` call; `git.ObjectWriteError`, raised from `git._hash_blob`.
- Scratch sites to change: `git._build_tree`, `git._write_published`,
  `git._merge_union_bytes` (callers `_build_tree`, `_published_proof`).
- Existing tests to model on: `test_offline_publish_leaves_the_write_dirty_and_the_sweep_retries_it`,
  `test_sweep_publishes_a_hand_committed_ticket_from_a_clean_control_checkout`,
  `test_prepare_refuses_a_local_commit_touching_state_and_code`,
  `test_erofs_hash_failure_keeps_git_stderr_and_the_location`.
- `git.py` writes `sync failed: …` under the `git` tag through
  `git.record_sync_failure` and `git.sync_failure_report`. Literal
  `[git] sync failed` sites: `recurring_runner.py`,
  `commands/recurring.py`. `mark.py`, `commands/mark.py` and `authoring.py`
  catch `git.GitError` and report through `git.py`'s helper.

### Cited, not attached

- `coga-dev/internals/git-refresh` (`docs/contexts/coga-dev/internals/git-refresh/SKILL.md`):
  read "The realignment proof", "`fast_forward_control`" and "`refresh`".
  Attach it only if the design changes realignment.
- `coga/checkouts/sandbox-clone` and `coga/checkouts/launch-boundary`
  (`docs/contexts/coga/checkouts/`): the sandbox and checkout boundary, for
  question 1.
- `coga-dev/internals/git-regressions` and `coga-dev/internals/spool-merge`:
  only if the fix touches the provenance check or the `log.md` union merge.

### Related

- Multiline Git stderr breaking log lines was fixed in #985
  (`keep-multiline-audit-messages-on-one-log-line`).
- Unsourced counts relayed on 2026-10-07 (no checkout or query) were dropped;
  the recount above supersedes them.
- Previous ref: `fix-coga-git-sync-failures-that-leave-main-diverge` (renamed
  2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design handoff (2026-11-04, claude)

- Spec is under `## Description` (per-class disposition, acceptance
  criteria, proposed shape, out of scope); evidence is under `## Context` →
  "Findings". Code change is small: move publication scratch files from
  `$TMPDIR` into the Git dir, plus two incident-shape regression tests and two
  doc touch-ups.
- Both incident-shape tests were probed ad hoc against current `main`
  (throwaway file, deleted) and pass as specified: the state-only hand commit
  realigns; the mixed hand commit refuses loudly with the `git pull --rebase
  --autostash origin main` remedy while the state still lands. They are
  regression pins, not fixes.
- The uncommitted `pyproject.toml` edit in `~/Code/coga`'s main checkout
  (`tmp_path_retention_policy = "failed"`) pre-dates this session and was
  left untouched. See Open Question 3.

## Open Questions

1. **Keep relying on `/etc/codex/requirements.toml` for Coga's Codex sandbox
   grant?** The DNS/EROFS classes are fixed only because the Multiply
   harness's machine-wide `multiply-full` profile grants network plus
   `/home/n/Code` write. If that file is reverted or narrowed, the failures
   come back. Options: (a) accept the dependency (recommended; nothing to
   do), or (b) also add the documented project grant in
   `~/Code/multiply/.codex/config.toml` (`coga/sandboxes` → "Codex sandbox
   grant", `writable_roots = [<git common dir>]`, `network_access = true`) so
   Coga does not depend on the harness file.
2. **Add `launch_args = "--no-daemon"` to Multiply's `[agents.codex]`** (in
   `coga/coga.toml`, or per machine in `coga.local.toml`)? It does not affect
   sync, but without it in-Codex bumps get misattributed
   (`[agent:claude]` / `[human:nicktoper]`) and the done sentinel can miss.
   Owner edit; agents may not touch these files.
3. **The uncommitted `pyproject.toml` `tmp_path_retention_policy = "failed"`
   edit** — likely what exhausted `/tmp` inodes on 10-27. Should `implement`
   carry it into this PR as the root-cause half of the ENOSPC disposition, or
   is it someone's separate in-flight change?
4. **Editable install in Multiply.** Multiply runs live `~/Code/coga/src`, so
   any branch checked out in `~/Code/coga`, including an agent's work in
   progress, changes Multiply's Coga mid-flight. Fine for dogfooding, but it
   makes version-vs-failure attribution impossible. Keep it, or pin a built
   wheel? (It doesn't block this ticket; it affects how the final review-gate
   check is run.)
