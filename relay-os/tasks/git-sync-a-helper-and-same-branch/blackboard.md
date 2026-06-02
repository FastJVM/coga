The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: git-sync-a
worktree: ../relay-git-sync-a
pr: https://github.com/FastJVM/relay/pull/262
commit: f0422dc (pushed to origin/git-sync-a)

## Open PR done (claude, 2026-06-01)
Branch pushed to origin; PR #262 opened against main.
No CI configured in repo (.github/workflows/ absent) → no automated green check;
noted in PR body. PR body calls out the deliberate auto-push-to-main carve-out
and the crash-loud failure mode for the human reviewer.

## Peer review done (codex, 2026-06-02)
Status: peer-review step complete, committed on `git-sync-a`, NOT pushed/no PR.

Review tool:
- Initial `codex review --base main` completed and found 3 must-fix items.
- A final rerun after fixes failed because Codex auth refresh token was revoked
  (`401 Unauthorized`); this was after the required review completed, so I
  verified locally instead of panicking.

Findings addressed:
- P1: `git commit -m` could sweep unrelated pre-staged files into the
  task-state commit. Fixed by checking staged changes for the task pathspec and
  committing with `git commit --only ... -- <task-dir>`.
- P2: `rev-parse --show-toplevel` treated all failures as "not a git repo".
  Fixed so only the explicit non-git error is a soft no-op; other failures
  crash loud and append `log.md`.
- P2: `relay/sync` context still described Slack only. Updated live and
  packaged `relay/sync` contexts with the git sync contract, same-branch
  limitation, deferred sites, narrow pathspec scope, config, and failure model.

Verification:
- `PYTHONPATH=src python -m pytest -q tests/test_git.py` -> 16 passed.
- `PYTHONPATH=src python -m pytest -q` -> 500 passed, 1 skipped, 1 pre-existing
  failure (`tests/test_packaging.py::test_package_force_includes_relay_resources`,
  KeyError on missing `force-include`).
- `git diff --check` -> clean.
- `PYTHONPATH=/home/n/Code/relay-git-sync-a/src python -m relay.cli validate --json`
  from `example/` -> clean.
- `relay validate --json` against the primary checkout with branch code still
  reports existing task warnings plus pre-existing `split-context-to-doc...`
  `missing-step`; not caused by this change.

## Implement done (claude, 2026-06-01)
Status: implement step complete, committed on `git-sync-a`, NOT pushed/no PR.

Delivered:
- `src/relay/git.py` — `GitError` + `sync_task_state(cfg, task_path, *, message)`.
  Resolves toplevel via `git rev-parse --show-toplevel`; same-branch commit+push;
  feature-branch / not-a-repo / disabled / nothing-staged = soft no-op;
  control-branch op failure = crash-loud (GitError → stderr + log.md → typer.Exit(1)).
- `config.py` — `[git]` parsing: `git_enabled` (local-over-shared), `git_remote`,
  `git_control_branch` (defaults true/origin/main) + validation.
- Wiring (module-attr `git.sync_task_state` so the conftest stub has one patch
  point): mark.py x4 finalizers, bump.advance_step, create.py, retire.py,
  recurring.py (both scaffold posts).
- Tests: `tests/conftest.py` got autouse `_stub_git` (no-op by default, mirrors
  `_stub_slack`), a `real_git` opt-out fixture, and the reusable real-git
  `git_repo` fixture (working tree + bare origin, laid out like the live repo —
  B/C reuse it). `tests/test_git.py` covers config parsing + every sync branch
  incl. crash-loud push + CLI integration (draft→active→bump land on origin).
- `relay.toml` live + packaged template: documented `[git]` block.

Verification: `python -m pytest` → 499 passed, 1 pre-existing unrelated failure
(`test_packaging::test_package_force_includes_relay_resources` — KeyError on
`pyproject [tool.hatch...force-include]`; fails identically on `main`, untouched
by this change). `relay validate --json` on example/ fixture → clean.

PR-description note for later steps / reviewer:
- Auto-push of task state straight to `main` is a DELIBERATE exception to the
  PR-review flow (task state is not code). Call this out in the PR and confirm
  no conflict with the automerge post-merge hook.
- Failure mode = crash-loud was the owner's call (see above). Reviewer can still
  weigh warn-and-continue.
- A dedicated `relay/git` context (parallel to `relay/sync`) could be a
  follow-up; for now the durable explanation lives in git.py's docstring + the
  `[git]` config block.

## Implement notes (claude, 2026-06-01)

Decision settled with owner (nick) in interactive session:
- **Git failure mode on the control branch = crash-loud (like Slack).** A
  failed commit/push raises `GitError`, which `sync_task_state` catches at the
  boundary to write stderr + append `log.md`, then `raise typer.Exit(1)`.
  Mirrors `slack.post`'s `RequestException → stderr + log + typer.Exit(1)`.
- **Deliberate carve-out:** "not a git repo" (HEAD has no `.git` toplevel) is a
  soft no-op + single stderr line, NOT a crash. Without this, every command run
  in a non-git `relay-os/` checkout (incl. the entire existing test suite,
  which runs in non-git tmp dirs with git enabled by default) would crash. The
  real opt-out stays `[git].enabled = false`.

Design:
- `src/relay/git.py` — `GitError` + `sync_task_state(cfg, task_path, *, message)`.
  Resolves git toplevel via `git rev-parse --show-toplevel` (cwd=task_path).
  Branch check via `--abbrev-ref HEAD`. On control branch: `git add -- <task
  dir>`, skip if nothing staged, else commit + `git push <remote> <branch>`.
  On a feature branch: soft no-op + warning (ticket B owns cross-branch).
  Public signature is shaped so B can slot the cross-branch path in without
  reworking call sites.
- Config: `[git]` table → `git_enabled` (local-override like slack, default
  true), `git_remote` (default "origin"), `git_control_branch` (default "main").
- Wired after `slack.post` in the logic-layer finalizers: `mark.py` (mark_done,
  mark_active, mark_in_progress, mark_paused — covers `relay mark` + automerge
  auto-bump), `bump.advance_step`; and the `commands/` scaffolds: `create.py`,
  `retire.py`, `recurring.py` (both scaffold posts). Commit message style:
  `Ticket: <slug> — <transition>`.
- Real-git test fixture: `git init` tmp repo + bare `origin`, run command,
  assert task files committed + pushed. Reusable for B/C.

## Bootstrap notes (nick + claude, 2026-06-01)

Scope decided in interview:
- **Always-on, no opt-out flag** (git analogue of Slack sync).
- **Both creation AND updates** in scope (create/draft/ticket, mark, bump,
  panic, recurring, + the file writes they make).
- Workflow: `code/with-review`. Contexts: `relay/sync`, `relay/codebase`,
  `dev/code` (added after evaluator flagged the checkout-boundary gap).

RESOLVED with owner (nick), 2026-06-01:
- (1) Branch model — owner chose the HEAVIER path on purpose: task-state /
  control-plane files ALWAYS sync to `main` even when HEAD is a feature
  branch (land on main AND the branch). Core intent = differentiate ticket
  state (control plane → always main, no PR) from feature code (branch +
  PR). Added a "## The control-plane / feature split" block to the ticket.
  Implementation must reach main without disturbing the feature working
  tree — worktree-pinned-to-main or git plumbing (commit-tree/update-ref);
  decision left to implement step.
- (2) Auto-push to `main` bypassing PR review = intentional (control plane).
- (3) `relay panic` risk noted in ticket: scope strictly to task dir, never
  sweep worktree code. Failure-handling (crash-loud vs warn) = peer-review
  decision.

SPLIT into 3 tickets (owner decision after deep scope investigation):
- **A = THIS ticket** (`git-sync-a-helper-and-same-branch`,
  active). git.py helper + config + same-branch commit+push wiring (clean
  injection set: mark.py 4 finalizers, bump.advance_step, create/retire/
  recurring scaffolds) + real-git test fixture. On a feature branch: no-op
  + warn. Retitled. Workflow code/with-review (already frozen, on step 1).
- **B** = `git-sync-b-cross-branch-to-main` (draft).
  Cross-branch land-on-main mechanism (plumbing vs worktree, CAS update-ref,
  locking — none exists today, non-fast-forward retry, offline, nesting).
  Workflow code/design-then-implement (has a real design decision). Depends
  on A merged. Highest-risk piece.
- **C** = `git-sync-c-panic-and-ticket-auth` (draft).
  Bespoke sites A skipped: relay panic (blackboard-only, riskiest — never
  sweep feature worktree) + relay ticket authoring (external agent edits,
  commit after session at commands/ticket.py:204). Workflow code/with-review.
  Depends on A.

Investigation that drove the split: ~5-6 clean logic-layer injection points
(80%) + 2-3 bespoke; cross-branch mechanism + locking + edge matrix is the
disproportionate risk; no git.py / no git abstraction / no locking / git
fully mocked in tests today; Config knows nothing about git. See the second
investigation agent's report (in session) for file:line detail.

## Evaluator review

I have everything I need. The repo already has an explicit "checkout boundary" model that directly answers the branch question, and the ticket missed it. Here is my evaluation.

---

## Evaluation: `git-sync-a-helper-and-same-branch`

### 1. Is the Description clear enough to start cold?
Mostly yes. The Description states the problem (CLI mutates files + posts Slack but does no git, so the repo drifts) and the goal (auto-commit changed task files to `main` and push, always-on) clearly. A cold agent would understand the intent. The `## Context` is unusually rich and does most of the heavy lifting — call sites, helper factoring, commit scoping, message style are all spelled out. The one thing missing from the Description proper is *why now / what triggered this* relative to the existing checkout-boundary model (see #5), but the work is startable.

### 2. Does `code/with-review` fit?
Yes, good fit. This is genuine `src/relay/` Python work (new `git.py` helper + wiring into ~7 call sites + tests + fixture), and the ticket itself flags the "higher review bar." A peer review of git-push-on-every-state-change is exactly the kind of design decision that benefits from the other-agent pass. No mismatch. The workflow's own implement step ("branch + feature worktree, commit there, do not push") is well-suited.

### 3. Are the attached contexts right? Anything missing?
- `relay/codebase` — relevant and appropriately scoped (source layout, test/validate commands, the two-halves distinction). Good.
- `relay/sync` — relevant *as an analogy* (the ticket explicitly models git-sync on Slack-sync: same call sites, write-local-first ordering, crash-loud philosophy). Fine to attach. It is broad, but the ticket already copied the load-bearing specifics into `## Context` (the "Callers that post" list, the write-then-post ordering), so it is not relying on the agent to re-derive them. Good practice.
- **Missing context — this is the significant gap.** The ticket does NOT attach or reference `relay-os/contexts/dev/code/SKILL.md`, which contains a "## Checkout boundary" section that *directly governs the central open question*. It already states the policy:
  > "Treat the primary repo checkout as the Relay control-plane checkout. Keep it on `main` when possible. Do code changes in a feature worktree outside the primary checkout, then return to the primary checkout for blackboard updates, `relay bump`, `relay slack`, and `relay panic`. ... If task-state changes need to be committed, commit them separately from the code PR."

  The ticket frames "commit to main regardless of branch" as an unresolved design question to settle in the blackboard, when the project already has a documented model that answers it: task-state mutations are expected to run *from the primary checkout, which is on `main`*. This context should be attached (and the relevant fact arguably copied into `## Context`), because it reframes the whole "branch behavior" question.

### 4. Is the scope reasonable?
Borderline but defensible. Given the human's explicit choices (always-on, no flag, both creation + updates), the work is one coherent change: a shared `git.py` helper + wiring into the same call-site set that already posts to Slack + tests + fixture. That is one ticket's worth of *mechanism*. Two things inflate it into possible multi-ticket territory:
- The **failure-handling policy** (crash-loud vs warn-and-continue, behavior offline / no remote / non-fast-forward) is genuinely undecided and could itself be a design ticket. The ticket punts it to "weigh with the peer reviewer," which is reasonable for `with-review` but means the implement step starts without a settled contract.
- The **branch/main decision** (see #5) is architecturally large enough that, if it lands on "commit to a detached main ref/worktree regardless of current branch," that is a substantial subsystem on its own.

If both open questions resolve toward the *simple* answer (commit on current checkout, which is normally `main`; crash loud like Slack), scope is one ticket. If they resolve toward the *ambitious* answer (cross-branch commit-to-main machinery), this is 2-3 tickets and should be split.

### 5. Assumptions to question before launch — especially the branch behavior
This is the ticket's weakest point and it correctly flags it as the KEY open question, but it under-weights how problematic the title's framing is:

- **"Commit to main regardless of current branch" is not sane as literally stated in a normal git checkout.** You cannot commit to `main` while `HEAD` is on `rename-workflow-to-playbook` without either (a) checking out main (destroys/stashes the agent's in-progress feature work — unacceptable mid-session), (b) a separate worktree/detached-ref commit + push to `origin/main` (real but heavy machinery, and pushing straight to `main` bypasses the very PR-review flow this repo is built around), or (c) committing task files onto whatever branch is current (contradicts the title). All three have sharp edges.

- **The repo already resolves this a different way.** Per `dev/code`'s checkout boundary, task-state commands are *supposed to run from the primary checkout on `main`*, with code changes isolated in a feature worktree. Under that model, "commit the changed task files and push" naturally means "commit on the current branch, which by convention is `main`" — no cross-branch machinery needed. The ticket's framing fights an architecture problem that the contexts already solved by convention. **Before launch, the human should decide whether relay should enforce/assume the checkout-boundary model (commit on current branch, document that task-state commands belong on the control-plane checkout) rather than build branch-spanning commit-to-main plumbing.**

- **Auto-pushing to `main` collides with the PR-review culture.** Every other code change in this repo goes through `code/with-review` → PR → human merge. Auto-committing-and-pushing task files straight to `main` on every `mark`/`bump` is a deliberate exception to that. It is probably the right exception (task state is not code), but it should be an explicit, acknowledged decision, not a side effect — and it interacts badly with the `automerge` post-merge hook and any session running inside a feature worktree.

- **Call-site precision.** The `## Context` says to wire into `commands/create.py`, `commands/mark.py`, `commands/bump.py`, etc., mirroring "the call sites that call `slack.post`." Heads-up for the implementer: several of those commands post via the *logic modules* `relay/mark.py` and `relay/bump.py`, not the `commands/` files (and `automerge`/`auto_bump_merged` posts through `mark_done`). The "wire it where Slack is posted" instruction is right, but the actual injection points are partly in `mark.py`/`bump.py`, not only under `commands/`. Also note `commands/retire.py` posts to Slack and is in scope by the "same set as Slack" rule but is not named in the ticket's list — worth confirming whether `retire` is intentionally excluded.

- **`commands/panic.py` in scope?** The ticket lists `relay panic` as a call site, but `panic` is a distress signal mid-work, frequently *inside a feature worktree with uncommitted code*. Auto-committing-and-pushing during a panic is exactly when the "commit to main regardless of branch" assumption is most dangerous. Worth singling out.

### Bottom line
Solid, well-researched ticket with an above-average `## Context`. Two pre-launch actions recommended: (1) **attach `relay/dev/code` (or copy its "Checkout boundary" paragraph into `## Context`)** — it already answers the central open question and the ticket currently treats that question as open; (2) **the human should pre-settle the branch model and the auto-push-to-`main`-vs-PR-flow tension** rather than leaving "commit to main regardless of current branch" as an implement-step decision, because the literal title behavior is either unsafe (checkout main mid-session) or heavyweight (worktree/detached-ref push that bypasses review). Failure-handling can reasonably stay a peer-review decision. Scope is one ticket *if* both open questions resolve toward the simple answer; flag for splitting if cross-branch commit machinery is chosen.
