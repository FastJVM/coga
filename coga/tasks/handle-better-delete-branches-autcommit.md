---
slug: handle-better-delete-branches-autcommit
title: handle better delete branches + autcommit
status: draft
mode: llm
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
  - dev/code
skills: []
workflow: code/with-review
secrets: null
---

## Description

Make `relay retire` delete the finished ticket's git branch — both the local
branch and its `origin` counterpart — as part of wrapping up a `done` ticket.
Local and remote branches currently accumulate (~32 local, ~21 remote in this
repo) because nothing prunes them after a ticket finishes. `retire` is the
right home: it already direct-deletes the done task — a bare `tasks/<slug>.md`
file *or* a `tasks/<slug>/` directory (don't assume the directory form; this
very ticket is the bare-file form) — and at retire time the ticket still
exists, so its recorded branch name is still readable — no cron, no
orphan-matching guesswork.

This deliberately **overrides** the current note in
`src/relay/commands/retire.py` that says *"Branch hygiene (local prune,
stale-branch sweep) is a Dream concern, not retire's."* That punt is exactly
why the branches piled up. Retire becomes the lifecycle event that disposes of
the branch alongside the task directory. Update that comment to match the new
behavior.

**What gets deleted:** only the branch recorded for *this* ticket (read from
its blackboard `## Dev` section — see Context), never `main` / the control
branch, never an unrelated branch.

**Safety gate.** Gate the **remote** delete on the linked PR actually being
merged: reuse the `gh pr view` MERGED check that `src/relay/autoclose.py`
already uses (parse the `pr:` line under `## Dev`). Do **not** gate on
ancestry/`git merge-base --is-ancestor` — a squash-merged PR (GitHub's common
default) leaves the branch tip *not* an ancestor of `main` even though the work
landed, which would wrongly skip it. For the **local** delete, prefer
`git branch -d` (refuses if unmerged) and fall back to logging the tip SHA on a
forced delete so it's recoverable from the reflog. If the branch has unmerged
work and no merged PR, skip it and report rather than force-deleting silently.

Out of scope: the **autocommit** half of the original title — a separate `main`
issue, its own future ticket (see Proposal on the blackboard). Also out of
scope: a one-time cleanup of the ~32 branches that already accumulated before
this change (noted as a Proposal — retire-time deletion only handles tickets
retired from here on).

## Context

`relay retire` lives in `src/relay/commands/retire.py`. Read its current flow:
it validates the task is `status: done`, runs the `retro/done-ticket` skill,
and either opens a knowledge PR or direct-deletes the task via `relay delete`.
The task may be a bare `tasks/<slug>.md` file or a `tasks/<slug>/ticket.md`
directory — `relay delete` already handles both forms; the branch deletion must
work for both too. Branch deletion hooks into this wrap-up. Decide where in the
flow it belongs (after retro confirms the ticket is truly finished; before the
task file/dir — and thus the blackboard `## Dev` `branch:` line — is removed).

Branch → ticket link: the `code/with-review` flow records `branch:`,
`worktree:`, and `pr:` lines under a `## Dev` heading on the ticket blackboard.
The `dev/code` context defines this convention. `src/relay/autoclose.py`
already parses `pr:` from that section (`_DEV_SECTION` / `_PR_LINE_RE`) and
runs the `gh pr view` merged check — copy both the parsing and the merge check.

**Parsing caveat (real trap):** the `branch:` line is written inconsistently
across existing tickets — `branch: my-branch`, `- branch: \`my-branch\``,
``branch: `my-branch` ``. A naive `^\s*branch:\s*(\S+)$` regex will capture the
backticks or miss the list-item form, then `git branch -d <wrong-name>` no-ops
or mis-targets. Normalize: tolerate a leading `- ` and strip surrounding
backticks/whitespace before using the name.

Tests: add `pytest` coverage following `tests/` patterns for retire and
autoclose. Cover the squash-merge case (PR merged but tip not an ancestor of
`main`) and the unmerged-no-PR skip case explicitly. If you touch any shipped
template under `relay-os/`, keep the packaged
`src/relay/resources/templates/relay-os/` copy in sync (see CLAUDE.md).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: retire-deletes-branch
worktree: (none — committed from the primary checkout)
pr: https://github.com/FastJVM/relay/pull/443

## Implementation

Done in the primary checkout (interactive, draft ticket — no workflow step
running, so nothing to `bump`). Branch deletion runs **synchronously in
`relay retire` before the retro task is launched**: that's the only clean hook,
because retire launches the retro pass as a detached agent session that deletes
the task dir, and retire.py can't re-read state after. At that point the source
ticket still exists, so its `## Dev` `branch:`/`pr:` lines are readable.

Files:
- `src/relay/autoclose.py` — added `parse_branch_name()` next to `parse_pr_url`.
  Regex `_BRANCH_LINE_RE` tolerates a leading `- ` list prefix; value is
  `.strip().strip("\`").strip()` so the bare / list-item / backtick-wrapped
  forms all normalize to the same plain name. Exported.
- `src/relay/branchcleanup.py` (new) — `delete_ticket_branch(cfg, root,
  blackboard_text, *, echo)`. Never touches the control branch or the
  checked-out branch. **Remote** delete (`git push origin --delete`) is gated
  solely on the linked PR being `MERGED` (reuses `autoclose.pr_state`). **Local**
  delete is gated on `git merge-base --is-ancestor <branch> HEAD` (the positive
  "did it land" signal) → `git branch -d`; the squash-merge case (not an
  ancestor but PR merged) logs the tip SHA then force-`-D`; genuinely unmerged
  with no merged PR is skipped and reported.
- `src/relay/commands/retire.py` — `_cleanup_branch()` called after the `done`
  check, before `create_task`. Best-effort: any git/gh/read failure is reported
  and swallowed, never aborts retire. Updated the docstring note that used to
  say branch hygiene was "a Dream concern, not retire's".

Key design correction (worth remembering): `git branch -d` alone is **too
loose** — it deletes a branch that's merged only into its *upstream*
(`origin/<branch>`), so a pushed branch whose PR is still open would be deleted
just for being pushed. That's why local deletion gates on ancestry into HEAD,
not on `-d`'s own merge check. The task's "gate remote on PR-merged, not
ancestry" still holds (squash-merge breaks ancestry-against-main for the remote
gate); ancestry is only used as a *positive* confirmation for the safe local
`-d`, with PR-merged as the fallback authorization for the squash case.

Tests (all green; full suite 899 passed / 1 skipped):
- `tests/test_branchcleanup.py` (new, real temp git repo + bare origin):
  clean-merge deletes local+remote, squash-merge force-deletes local & logs
  tip SHA, unmerged-no-PR skip, PR-open skip, never-deletes-`main`, no-branch
  noop, checked-out-branch left in place.
- `tests/test_autoclose.py` — `parse_branch_name` across bare / list-item /
  backtick / empty / missing forms.
- `tests/test_retire.py` — integration: branch pruned before launch.

No shipped-template (`relay-os/`) edits, so no `src/relay/resources/templates/`
sync needed. Left the `retro/done-ticket` skill's "do not delete branches"
prohibition untouched — still correct, since the *command* deletes, not the agent.

## Evaluator review

_Note: this review was written against an earlier design (a standalone
recurring `branch-sweep`). The ticket has since pivoted to doing the deletion
inside `relay retire`, which resolves the review's two main concerns — the
retire/timing race and the orphan-matching problem — because the `branch:` line
is still present at retire time. The parsing-inconsistency and squash-merge
findings still apply and are now folded into the Description/Context above._

**1. Description clarity — strong.** A cold agent can start. The deliverable (Python sweep + script workflow + script skill + recurring ticket), the model to copy (`autoclose-merged`), the trigger (`status: done`), and the explicit out-of-scope split (autocommit → separate ticket) are all stated. The factual claims I spot-checked hold up: the `retire.py` branch-hygiene note exists (lines 48-49: "Branch hygiene ... is a Dream concern, not retire's"), and the branch counts are accurate (32 local, 20 remote vs. the ticket's "~32 / ~21").

**2. Workflow fit — there is a real mismatch.** The ticket frontmatter says `workflow: code/with-review` and `autonomy: interactive`, but the body says the *deliverable* "runs unattended (`autonomy: auto`, no agent)." Those two `autonomy` values describe different things — the ticket's own build workflow vs. the recurring task being built — and that's fine, but it's worth making explicit so no one mistakes the recurring ticket's mode. The bigger fit question: `autoclose-merged` (the named model) was itself built and shipped; if that work went through `code/with-review`, this matches. The work is genuinely code-shaped (new module + tests + templates + a PR), so `code/with-review` is appropriate. No change needed, just confirm the interactive/auto distinction is understood.

**3. Contexts — appropriate, with one fix.** `dev/code` is directly relevant and load-bearing: the sweep depends on the `## Dev` → `branch:` convention it defines, so attaching the full context (not just a copied fact) is correct here because the implementer needs the convention's nuances (multi-ticket PRs, "update in place," forward-compat). `relay/recurring` is the right home for the recurring-task shape. **Missing:** nothing about keeping the packaged template copy in sync is in `## Context` as a hard checklist item beyond a passing mention — and I confirmed `src/relay/resources/templates/relay-os/recurring/` and `.../workflows/` both ship `autoclose-merged`, so the new `branch-sweep` recurring + workflow **must** be added in both trees. That's a concrete, easy-to-miss fact; consider promoting it to a checklist line rather than the prose aside it currently is.

**4. Scope — reasonable and well-bounded.** One coherent deliverable. The autocommit half is correctly carved off into a Proposal and a future ticket. This is a single ticket's worth of work modeled 1:1 on an existing sibling. No bundling.

**5. Assumptions to question before launch — this is where the real risk lives.**

- **The branch→ticket link is fragile in practice.** The ticket assumes the sweep reads `branch:` under `## Dev` "the same way" `autoclose.py` reads `pr:`. But `autoclose.py` only parses `pr:`, not `branch:` — that parser does not exist yet. More importantly, I grepped existing tickets and the `branch:` line is **not** written in one consistent shape: I found `branch: optioninfo-timeouts`, `- branch: \`first-run-no-slack\``, and `branch: \`drop-debug-all\``. A naive `^\s*branch:\s*(\S+)$` regex (mirroring `_PR_LINE_RE`) will capture a backtick-wrapped name or miss the `- branch:` list form, and then `git branch -d <wrong-name>` either no-ops or, worse, the resolved name doesn't match git's actual ref. The implementer must normalize (strip backticks, tolerate the list-item prefix) or the gate silently never fires. Flag this explicitly.

- **The retire/timing race is the load-bearing open question, and the ticket correctly raises it but understates the consequence.** `relay retire` direct-deletes the done task directory (retire.py: "Retro direct-deletes the task via `relay delete`"). So "iterate done tickets that still exist and delete their recorded branch" will **systematically miss every branch whose ticket was already retired** — which is the common path. The "iterate actual git branches, match back to a done/merged ticket" approach is more robust but needs a definition of "match back" once the ticket is gone (slug-name heuristic? the very convention `dev/code` says is unreliable?). This should arguably be resolved before launch, not "during implementation," because it determines whether the feature works at all for the majority of branches.

- **The safety gate ("ticket is `done`") is sound in principle but has a gap:** a branch with *no* matching ticket at all (orphaned, hand-named, or ticket retired) is exactly the accumulation the ticket wants to clean up, yet "ticket is done" can't authorize deleting it because there's no ticket to check. The gate as written only cleans branches whose ticket is both done *and still present* — a small subset. Decide explicitly what happens to ticket-less branches (leave them? that's most of the 32).

- **The unmerged-commit guard is under-specified and the ticket admits it ("decide the exact guard during implementation").** "Commits not contained in the control branch" is the right idea, but: (a) it must compare against the *remote* `origin/main` after a fetch, not a possibly-stale local `main`, or it will wrongly believe work is unmerged; (b) a squash-merged PR (the common GitHub default) leaves the branch tip *not* an ancestor of `main` even though the work landed — so `git merge-base --is-ancestor` will report "unmerged" and skip every squash-merged branch, defeating the sweep. The fallback ("log tip SHA so it's recoverable from reflog") is weaker than it sounds for the **remote** branch: deleting `origin/<branch>` is not protected by your local reflog. Recommend: for remote deletion, gate on PR-merged state (reuse `autoclose.py`'s `gh pr view` MERGED check) rather than ancestry, since squash-merge makes ancestry unreliable.

**Bottom line:** Clear, well-scoped, correctly split ticket with accurate grounding. Two things should be pinned down *before* launch rather than deferred: (1) the iterate-tickets-vs-iterate-branches decision, because retire's direct-delete makes the "tickets that still exist" path miss most branches; and (2) the unmerged-commit guard, because naive ancestry checks break on squash-merges in both directions (false "safe" and false "unmerged"). The `branch:` parsing inconsistency is a concrete implementation trap worth calling out in `## Context`.

## Proposals

- **Autocommit recurring task (separate ticket).** The original title bundled
  "+ autcommit". Per the human, this is a distinct `main` issue and should be
  its own recurring-task ticket, not part of this change. File separately.

- **One-time backlog cleanup.** Retire-time deletion only prunes branches for
  tickets retired from here on. ~32 local / ~21 remote branches already
  accumulated. Consider a one-off manual prune (or a single throwaway sweep
  gated on `gh pr view` MERGED) to clear the existing backlog after this ships.
