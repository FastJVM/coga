---
slug: handle-better-delete-branches-autcommit
title: handle better delete branches + autcommit
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
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

**Follow-ups (out of scope for this ticket):**
- **Autocommit recurring task.** The original title bundled "+ autcommit" — a
  distinct `main` issue that should be its own recurring-task ticket. File
  separately.
- **One-time backlog cleanup.** Retire-time deletion only prunes branches for
  tickets retired from here on; ~32 local / ~21 remote branches already
  accumulated. Consider a one-off manual prune (or a single throwaway sweep
  gated on `gh pr view` MERGED) to clear the existing backlog.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: retire-deletes-branch
worktree: (none — committed from the primary checkout)
pr: https://github.com/FastJVM/relay/pull/443

## Production notes

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
