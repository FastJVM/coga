---
title: Address PR review comments
agent: claude
---

## Description

Command ticket for the `address-pr-comments` verb. It sweeps open pull
requests on this repository, applies the fix each unresolved review thread and
each unanswered top-level PR comment asks for, verifies the result, pushes it
only through an explicit lease, and replies on the thread or comment. It never
merges, never resolves a thread, and never touches the PR's owning ticket: the
human still owns the review gate.

`coga address-pr-comments` is a default alias for
`coga launch bootstrap/address-pr-comments`. Pass one PR number or URL to scope
the run, for example `coga address-pr-comments 631`; omit it to sweep every
open PR. The optional selector arrives in the composed prompt's
`## Launch arguments` JSON array.

This target is stateless: do not create a task per run, edit this ticket, write
results to any ticket blackboard, or run `coga bump` / `coga mark`. Print the
per-PR report, post its roll-up through `coga slack`, then exit the agent
session.

### Mechanics: reuse the skill, not its attended conduct

`coga/skills/code/address-pr-comments/SKILL.md` is the single owner of the
per-PR mechanics. Apply these sections of it as written, substituting the
worktree selected below for the skill's recorded checkout:

- **§2 Read every unresolved review thread** — the paginated `reviewThreads`
  GraphQL query and the rule that an outdated thread is still read.
- **§3 Apply, verify, commit, and push** — the command-unique private fetch
  ref under `refs/coga/address-pr-comments/<unique-token>`, the
  `<verified-remote-oid>` equal-to-`headRefOid` proof, the
  `git merge-base --is-ancestor <verified-remote-oid> HEAD` ancestor proof,
  and the exact `--force-with-lease=refs/heads/<head-ref>:<verified-remote-oid>`
  push followed by the post-push `headRefOid == HEAD` check.
- **§4 Reply without resolving** — the `addPullRequestReviewThreadReply`
  mutation, the re-read before replying, and the ban on `resolveReviewThread`.

The skill's **§1 and its attended-assist conduct do not apply** as a whole
here. Retain only §1 items 3–5 for publication-destination validation and the
private-ref fetch proof, with the sweep-specific refusal handling below; its
ticket linkage, checkout alignment, and human escalation do not apply. Resolve
the remaining contradictions in favour of this ticket:

- There is no ticket `## Dev` block to read. The sweep starts from the PR
  itself (step 1 below), never from a `branch:` / `worktree:` / `pr:` line.
- There is no `git branch --show-current == branch:` check. A temporary
  detached worktree has no current branch; it pushes
  `HEAD:refs/heads/<head-ref>` under the same exact lease.
- There is no attending human. Nothing here asks and waits; a request that
  needs a human answer gets one reply saying so (step 5) and is reported as
  `needs-human`. `coga block` is not available either: this target is
  stateless and has no ticket to park.
- Opposite to the skill, `coga slack --task bootstrap/address-pr-comments`
  **is** the completion signal. It emits the bootstrap done sentinel (the
  `BootstrapRef` branch of `commands/slack.py`) that completes a delegated
  recurring period. The skill's "do not use `coga slack` as a completion
  signal" rule is about an ordinary ticket on its `review` step, not this
  command ticket.

### Scope and accepted limitation

The target set is **open PRs only**, targeting `main`. With no selector,
enumerate it with `gh pr list --state open --limit 10000`; the default
30-result limit is not a complete sweep. If that returns exactly 10,000 rows,
treat the result as truncated and finish enumeration with paginated `gh api`
calls before changing anything. With one selector, resolve that PR with
`gh pr view` and require it to be open. Do not enumerate worktrees, ticket
`branch:` lines, or branches that lack an open PR; pre-PR branches and PRs on
other repositories are out of scope.

Read the `## Launch arguments` JSON array exactly when the section is present;
an absent section means the launch had no positional arguments:

- no section (equivalent to `[]`) means all open PRs.
- `[PR]` means only that PR number or URL.
- Any other arity is invalid: print
  `usage: coga address-pr-comments [PR]`, make no changes, and stop the run.

Comments from **every author** count — the owner, teammates, bots, and
`/code-review` output alike. The only thing that takes a comment out of scope
is the sweep's own marker (step 3).

Rebasing is not this command's job. A PR GitHub reports `CONFLICTING` is
reported `conflicting` and skipped: `resolve-conflicts` rebases it on its own
schedule, and a fix pushed onto a conflicting head would only be rebased again.

### Run order

1. **Preflight and enumerate.** Start from the repository root. Confirm
   `git` and `gh` can read the repository (`gh auth status`), then run
   `git fetch origin main`. Query PR metadata with
   `gh pr view <n> --json number,url,state,baseRefName,headRefName,headRefOid,headRepository,headRepositoryOwner,isCrossRepository,mergeable`
   (in sweep mode, from the complete/paginated `gh pr list --state open
   --limit 10000` result described above). Process PRs sequentially and keep
   each observed head OID for its push lease. Report and skip before reading
   any comment:
   - base other than `main` → `skipped-base` with the base named;
   - `mergeable` is `CONFLICTING` → `conflicting`; if it is `UNKNOWN`, retry
     the read a small, bounded number of times and report `conflicting` if it
     stays unknown;
   - head repository other than this repository (a fork) → `skipped-fork`.
     Resolving a writable fork remote is not attempted.

   Before reading comments or changing files, apply the skill's §1 items 3–5
   to this PR: read the configured `[git].remote` (default `origin`), require
   `git remote get-url --push --all <configured-remote>` to return exactly one
   non-empty URL, and require that URL to identify the PR head repository
   `<headRepositoryOwner.login>/<headRepository.name>`. Record it as
   `<verified-push-url>`. Fetch the head branch directly from that URL through
   a fresh private ref and require its OID to equal the observed `headRefOid`.
   A missing, multiple, or mismatched destination, or a failed head proof, is
   `push-failed`: report the reason and skip this PR without changes or replies.
   Do not fast-forward or otherwise align an existing checkout here; step 4
   owns worktree selection.
2. **Inventory what needs addressing.** Three sources, all paginated:
   - Inline threads: the skill's §2 `reviewThreads` query. Keep threads whose
     `isResolved` is false.
   - Top-level PR comments:
     `gh api --paginate repos/<owner>/<repo>/issues/<n>/comments`.
   - Review summaries:
     `gh api --paginate repos/<owner>/<repo>/pulls/<n>/reviews`, keeping only
     reviews in state `CHANGES_REQUESTED` or `COMMENTED` with a non-empty
     body. `APPROVED` ("LGTM") and `DISMISSED` are not requests. A review
     summary that carries inline threads (for example `/code-review
     --comment`) is covered by addressing those threads; do not also reply to
     the summary.

   `<owner>/<repo>` and `<n>` come from the PR URL; the URL identifies the base
   repository. If a thread itself has more than 100 comments, fetch the rest
   before acting; never silently truncate the review.
3. **Apply the marker-based re-run guard.** The sweep posts through the
   owner's `gh` token, so its replies carry the owner's login and are
   indistinguishable by author — and since every author counts, an
   author-based guard would answer its own reply the next day, forever. The
   guard is therefore a fixed HTML-comment marker embedded in every reply the
   sweep posts, naming what it answers:

   `<!-- coga:address-pr-comments reply-to:<thread-or-comment-id> -->`

   For a thread the id is the thread's GraphQL node id; for a top-level
   comment or review summary it is that comment's or review's REST `id`. The
   rules, applied identically to threads, top-level comments, and review
   summaries:
   - A comment containing the marker is never in the to-address set.
   - An item is **addressed** iff a later comment carries a marker
     referencing its id: for a thread, its last comment carries the marker
     `reply-to:<thread-id>`; for a top-level comment or review summary, a
     later top-level comment carries `reply-to:<that-id>`.
   - A new non-marker comment posted after the marker re-opens the item: a
     thread whose last comment is not a marker reply, or a top-level comment
     newer than the marker that answered its predecessor, is back in the
     to-address set.

   Skipped items are not re-read or re-analyzed. A PR with nothing left in
   the to-address set is `no-comments`.
4. **Select a safe worktree.** Inspect `git worktree list --porcelain`.
   Never touch the `main` checkout. If the PR's head branch already has a
   worktree, use it only when it is clean, has no merge/rebase/cherry-pick in
   progress, and its HEAD exactly matches the observed head OID. Otherwise
   report `skipped-dirty`; never stash, reset, or overwrite that work. When no
   worktree owns the branch, fetch `refs/pull/<n>/head`, confirm the fetched
   OID still matches the observed head OID, and create a temporary detached
   worktree at that OID. Remove only worktrees created by this run. Record
   the original head OID before any change.
5. **Decide each item, then fix.** For every item in the to-address set,
   decide whether it needs a code change, is already satisfied by the current
   head, or needs a human answer. A request that is ambiguous, contradictory,
   optional in a way that changes the PR's intent, or scope-expanding gets no
   code change: it receives exactly one marker reply saying what decision the
   human has to make, and counts toward `needs-human`. For the rest, make the
   smallest coherent changes that satisfy them; keep unrelated cleanup out of
   the diff. Commit on the selected worktree with a short factual subject.
   Do not stage `coga/log.md` or any `coga/tasks/**` file.
6. **Verify before push.** Re-read `git diff <original-head-oid>...HEAD` and
   confirm it implements only the requested fixes. If the changed paths
   include anything under `src/` or `tests/`, run `python -m pytest` in the
   worktree. A failed or unavailable required test is `verify-failed`: do not
   push, and restore the worktree to its recorded original OID. Docs-only
   fixes need no pytest run; verify their factual claims, links, and
   live/packaged twins instead. Diff review and the conditional test are a
   mandatory gate; never push first and verify afterward.
7. **Push with the observed lease.** Follow the skill's §3 exactly: refresh
   the PR's `state`, base, head repository, `headRefName`, and `headRefOid`
   immediately before pushing and require it to remain open against `main`
   on the same branch and repository. Repeat the single-push-URL and repository
   identity checks from step 1 in the selected worktree, requiring the URL to
   remain `<verified-push-url>`; fetch the head directly from that URL through
   a fresh private ref and require
   `<verified-remote-oid>` to equal the fresh `headRefOid` and the recorded
   original OID; prove ancestry with `git merge-base --is-ancestor`; then
   `git push --force-with-lease=refs/heads/<head-ref>:<verified-remote-oid> <verified-push-url> HEAD:refs/heads/<head-ref>`
   and require the post-push `headRefOid` to equal `git rev-parse HEAD`. If
   the destination changed, the head moved, or the lease rejects, do not
   weaken or retry it: restore
   local state and report `push-failed` with the reason. When no item needed
   a file change, there is nothing to push; run the skill's no-change proof
   instead, including the same destination checks and fetch from
   `<verified-push-url>`, so reply evidence describes the PR's current head.
8. **Reply without resolving.** Only after the applicable post-push or
   no-change proof succeeds. Threads: the skill's §4 mutation. Top-level
   comments and review summaries:
   `gh api repos/<owner>/<repo>/issues/<n>/comments -f body=<reply>`. Every
   reply embeds the step 3 marker for the item it answers, says what changed
   (or why the current head already satisfies it) naming the commit when
   useful, and reports the verification result. Re-read the item immediately
   before replying so a retry does not post twice. Never call
   `resolveReviewThread` or any UI/API action that resolves a conversation.

### Restore and cleanup

A PR that is not successfully pushed must be left as it was found. If a fix
was committed in an existing worktree but verification or push then failed,
restore its recorded original OID only because the worktree was proven clean
before the run. For a temporary detached worktree, remove it through
`git worktree remove` and then remove its now-empty temporary parent. Never
delete a pre-existing worktree or branch. Never touch, rebase, or push `main`.
Always delete the private fetch ref after recording its OID, including on a
mismatch or later failure.

Never merge a PR, never delete its branch, never resolve a thread, and never
run `coga bump` or `coga mark` on the PR's owning ticket. `autoclose-merged`
closes tickets after the human merges.

### Report

Print exactly one concise stdout line per selected PR as soon as its outcome is
known:

`PR #<number> <head-ref> — <status> — <detail>`

Use these status tokens exactly:

- `addressed`
- `no-comments`
- `needs-human`
- `skipped-dirty`
- `skipped-fork`
- `skipped-base`
- `conflicting`
- `verify-failed`
- `push-failed`

A PR with mixed item outcomes gets one line under the precedence
`needs-human` > `verify-failed` > `push-failed` > `addressed`, with the
per-outcome counts in `<detail>` (for example `2 addressed, 1 needs-human`).

After all PRs, post one compact count roll-up (and the PR numbers needing human
attention) with the command below. This must be the final action: a successful
bootstrap-target FYI also signals the stateless launch supervisor that the
command is complete.

`coga slack --task bootstrap/address-pr-comments --message "<one-line roll-up>"`

A Slack failure is a command failure and must be surfaced. The Slack line is
the only cross-run record: do not persist the per-PR lines or roll-up in this
command ticket or in any other task file.
