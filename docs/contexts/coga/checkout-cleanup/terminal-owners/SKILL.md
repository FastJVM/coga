---
name: coga/checkout-cleanup/terminal-owners
description: When a branch whose PR closed without merging may be deleted — terminal-ticket ownership, durable branch debt in the worklist, the authorization gates, and which passes run the cleanup.
---

# Terminal owners and closed PRs

Part of [coga/checkout-cleanup](../SKILL.md).

A branch whose PR was closed without merging may be deleted, but only when
its ticket finished. Every branch-sweep pass applies
the rule: the daily autoclose pass, the weekly retry, and the restricted pass
retire and autoclose run for a disposed ticket.

**Ownership.** A ticket owns a branch only through a `## Dev` `branch:` line
(a ticket may record several). An open `retires.md` entry also
counts, because autoclose records it for a ticket it closed and that ticket
may since be gone. An entry whose recorded `owner` is another clone does not
count. A surviving ticket cannot bypass this with its own branch lines:
when it records `worktree:`, that path must be a readable primary or linked
checkout of this repository. A foreign or unavailable recorded checkout
grants no terminal-ticket deletion authority here and is reported.
When disposal itself has just proved and removed a same-repository linked
worktree, it carries that exact path's proof into its restricted branch pass.
That successful removal does not revoke the surviving ticket's ownership;
an already-missing path or a path recreated as a foreign checkout gets no such
exception. All other deletion gates are still checked.
The owner must be `done` or `canceled`. These never count as ownership: a closed PR
on its own, a prose or attachment mention, a fenced or indented code example,
and a ticket or worklist that
cannot be read.

**Durable branch debt.** Worklist entries retain additional owned branches
in an optional `branches` list beside the primary `branch`. Autoclose records
that list even when checkout disposal was skipped. The entry stays open until
every recorded local branch is gone in its owning repository and the existing
worktree gate clears. This keeps secondary branch ownership and retries alive
after the first branch or the ticket disappears. Remote leftovers retain the
existing best-effort sweep policy. Field syntax is documented in the
`coga/autoclose/sweep` invocation skill.

**Authorization.** A closed, unmerged PR for a terminal-owned branch vouches
for it the way a merged PR does. The
existing gates still apply:

- No live ticket in this workspace mentions the branch, and no live ticket in
  any workspace of the Git checkout records it. One
  terminal owner and one live claimant means the branch stays. Every recorded
  branch counts, including secondary branches on recurring period tickets.
- No PR for the head is open.
- The remote ref still equals the closed PR's exact head. A remote moved past
  that head is kept and reported, even when the local ref goes.
- Every local commit beyond the closed head, other than a patch-equivalent
  copy, touches only Coga task/log state. A source commit added after the PR
  closed keeps the ref and names the paths, because that work was never
  reviewed.
- Divergent tips follow the
  [archive rule](../branch-sweep/SKILL.md). GitHub keeps
  `refs/pull/<number>/head` for closed PRs as well as merged ones.
- The control branch, the checked-out branch, the shared skill-update branch
  and worktree-pinned branches stay protected.

A terminal-owned branch with no merged or closed PR is reported for a human
decision, never inferred.

**When it runs.** `coga mark done`, `coga mark canceled` and a final-step
`coga bump` delete nothing and make no network call. A checkout therefore
never disappears beneath the session that finished the ticket. Cleanup
happens at `coga retire`, at the autoclose disposal of a ticket it closes,
and at the next daily clone-scoped branch sweep in the clone holding the
branch (or `coga run branch-sweep`).
A refusal is visible in that pass's `## Branch Sweep` or retire report and is
retried on every later pass while an owner record exists. A canceled ticket
deleted before any pass ran leaves no owner record: its branch is then kept
and reported as having no vouching PR, the safe failure.
