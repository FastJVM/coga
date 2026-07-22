---
name: code/open-pr
description: Agent step that runs `coga open-pr` to push the branch and open (or ready) the PR, then bumps. The deterministic push/open/record work lives in the command; the step gates on a recorded `pr:`, so it cannot complete without a real PR.
---

# Push and open the PR

This is an agent step, but the mechanical work — push, open (or ready) the PR,
record the URL — is done by a single deterministic command, `coga open-pr`. You
run it, confirm it recorded the PR, then bump. The *judgment* (what the PR says,
whether the branch is mergeable) belongs to the earlier implement / peer-review
steps; this step just turns the recorded branch into a PR.

(Mechanism note: `coga open-pr <slug>` is a default alias for `coga launch
bootstrap/open-pr <slug>` — a stateless script launch of the packaged open-pr
command ticket. Same spelling, same behavior; as a stateless nested script
launch it is sanctioned inside your supervised session and never touches your
session's done sentinel.)

The step declares `requires: pr`, so `coga bump` refuses to advance until a
`pr:` line is recorded under `## Dev`. That is a **data check**: skipping
`coga open-pr` and bumping anyway fails loud — the recorded artifact is the
gate, not your say-so.

## Order of operations

1. **Confirm the handoff state.** Read the machine-readable `branch:` /
   `worktree:` fields under `## Dev` on the blackboard. A trailing annotation
   must follow a backtick-delimited value or live on a separate line; bare
   values consume the whole remainder of the line. The implement / peer-review
   steps must have created the feature branch, recorded it, and left it
   committed and ahead of the base branch. If `branch:` / `worktree:` are
   missing, that is an earlier-step gap — do not improvise a branch here;
   escalate per your launch mode by asking the attending human, or by using
   `coga block` with a one-line reason in a queue run.
2. **Run `coga open-pr <slug>` from the checkout that owns the live ticket.**
   In the legacy layout where `worktree:` names a separate linked worktree,
   return to the primary control checkout first; the control-branch ticket is
   authoritative there. When `worktree:` names the primary checkout itself,
   stay in that checkout on the recorded feature branch; its ticket is the live
   copy because there is no second checkout to diverge. The command proves that
   ownership against `COGA_EXPECTED_TASK`, the anchor your outer `coga launch`
   session pins to this task. (`coga open-pr` is itself a launch, so the
   `COGA_TASK_*` variables name the open-pr command ticket, not your task.)
   This keeps an independent fallback clone behind the control-checkout gate.
   It resolves the ticket first, identifies the layout, and:
   - reads `branch:` / `worktree:` from `## Dev`,
   - commits the launcher's pending generated `coga/log.md` append in a
     single-checkout launch, then confirms the recorded checkout is on that
     branch, clean, ahead of the base
     (`[git].control_branch`, default `main`), and has no unsafe material drift
     from the latest `<remote>/<base>` (byte-identical generated task/log
     overlaps from preceding lifecycle syncs are safe; any divergent generated
     blob still fails); in the single-checkout layout, generated task/log
     commits do not count as implementation work, so at least one other
     committed path must exist,
   - pushes the branch by name (using an explicit force-with-lease when a safe
     retry follows a rebase),
   - opens the PR with `gh pr create` — or `gh pr ready` if a draft already
     exists, or reuses an already-open PR (idempotent on re-run),
   - writes `pr: <url>` back under `## Dev`; in the single-checkout layout it
     syncs that generated ticket update to the feature branch *and* the control
     branch, so the checkout stays clean, the PR contains its own linkage, and
     both tips keep identical ticket bytes for the next freshness check.

   It always operates on the recorded feature branch **by name**. For separate
   worktrees or fallback clones, keeping the command on the control checkout
   prevents writes to a stale ticket copy; for a proven primary-checkout
   feature branch, syncing the write to both branches prevents the command from
   making its own retry dirty *or* stale. It **fails loud**
   (non-zero, nothing pushed/opened) on: no usable `branch:` / `worktree:`, a
   missing worktree, the recorded checkout on the wrong branch or dirty, **no
   commits ahead of base** (the incident case — no empty PR), a stale branch,
   or a `git push` / `gh` auth failure *before* the PR exists. Once `gh` has
   opened the PR and `pr:` is on the ticket, a failing record sync is reported
   on stderr rather than raised — the recorded artifact is the gate, and the
   next bump's own publishing sync lands the same state.

   **PR title** = the ticket title. **PR body** comes, in order, from: a `## PR`
   section (blackboard first, then ticket body), else the ticket's
   `## Description`, else the title; a `Closes ticket: <slug>` line is always
   appended. So author a `## PR` section in the earlier steps if you want a
   curated summary + test plan; omitting it is fine.
3. **Bump.** Once `coga open-pr` reports the URL and `pr:` is recorded under
   `## Dev`, run `coga bump <slug>` to hand off to the next step. The bump's
   `requires: pr` gate will pass because the URL is now recorded. In the
   single-checkout layout that gate also republishes the just-committed
   post-transition ticket state to the PR branch, keeping its `step:` /
   `assignee:` copy identical to control and mergeable. When this agent session
   exits, launch also publishes its trailing usage-log commit to that already-open
   branch, so the local and PR tips do not diverge after the gated bump.

## If `coga open-pr` fails

Fix the cause and re-run it — it is idempotent:

- Missing `branch:` / `worktree:` or a torn-down worktree → an earlier step
  didn't record/keep it; escalate per your launch mode if you can't recover
  it here.
- Nothing publishable ahead of base → implement/peer-review produced no change;
  lifecycle-only task/log commits do not count in a single checkout. Build the
  requested change rather than opening a state-only PR, escalating per your
  launch mode if that needs human direction.
- Stale branch → rebase the control branch in the recorded checkout, re-run
  `python -m pytest`, and commit. Then re-run `coga open-pr` from the primary
  control checkout for a separate-worktree layout, or from the recorded primary
  checkout for a single-checkout layout. If an earlier attempt already pushed,
  the retry republishes the rewritten branch with an explicit force-with-lease.
- `git` / `gh` auth failure → follow the setup hint the command prints (fix the
  remote, load your SSH key / credential helper, `gh auth login`), then re-run.
- Dirty checkout naming only `coga/.agent-skills/` in a single-checkout layout
  → that merged skill view is regenerated by every `coga launch`, and this
  command *is* a launch, so it lands in the very checkout being published. A
  repo initialized before that ignore rule existed will hit this as a confusing
  "uncommitted changes" refusal. Add `.agent-skills/` to `coga/.gitignore`
  (`coga init` writes it inside the coga-managed block), then re-run. Do not
  commit the generated view to satisfy the gate.

## Acceptance for this step

- `coga open-pr <slug>` has been run and `pr: <url>` is recorded under `## Dev`.
- `coga bump <slug>` has advanced the workflow (its `requires: pr` gate passed).

## What this skill does NOT do

- Decide whether to merge — that's the human's job in the next step.
- Make code changes or resolve CI failures. If CI fails for a real reason,
  escalate per your launch mode — ask the attending human, or `coga block`
  in a queue run — and let the human redirect or relaunch as appropriate.
- Resolve merge conflicts with the base — the peer-review / self-qa step handles
  mergeability before this step runs.
- Edit `assignee:` by hand. The workflow's per-step `assignee:` handles the role
  rewrite on bump.
