---
name: code/address-pr-comments
description: Assist on an owner-controlled PR review by applying requested fixes, testing and pushing them, and replying to unresolved GitHub review threads without merging, resolving threads, or advancing the ticket.
---

# Address PR review comments

Use this skill only for an on-demand assist during the owner-controlled
`review` step. The human has finished leaving comments and explicitly launched
an agent with `coga launch <slug> --agent <type>`.

You may inspect the PR, run verification, prepare and push explicitly requested
fixes, and report a recommendation. Apply every must-fix review comment that is
within the ticket's scope. Ask the attending human about ambiguous, optional,
contradictory, or scope-expanding requests before changing code.

## Preserve the owner gate

The human still owns the review and merge decision.

- Do not merge the PR or delete its branch.
- Do not resolve GitHub review threads. Replying is allowed; resolution stays
  with the human.
- Do not run `coga bump`. This skill is an explicit exception to the base
  prompt's finish-a-step rule: the ticket must remain on `review`.
- Do not run `coga mark done` or otherwise advance, close, pause, cancel, or
  reassign the ticket.
- Do not use `coga slack` as a completion signal. It is non-terminal for an
  ordinary task and this attended assist ends when the human ends the session.

On the normal `in_progress` review path neither `step:` nor `status:` changes,
so the launch supervisor stops after this assist instead of chaining another
session. The existing `autoclose-merged` sweep marks the ticket done after the
human merges.

## 1. Verify the recorded PR and checkout

Read the current ticket's `## Dev` block. Require both recorded values:

```text
branch: <branch-name>
pr: <full-pr-url>
```

(`worktree:` appears only when the branch lives in a sandbox clone; work
there instead of switching in the launch checkout.) Do not infer a missing
value from the task slug or current checkout. Fail loud and ask the attending
human to repair the ticket if the linkage is missing, ambiguous, or stale.

**Recorded legacy checkout.** An older review ticket may record a linked
worktree or clone as `worktree:`. When this session already runs in that
exact checkout (`git rev-parse --show-toplevel` resolves to the recorded
`worktree:`) and HEAD is on the recorded `branch:`, launch recognized it as
the assist checkout and already fast-forwarded it to the verified PR head.
Work there: skip steps 1 and 2 below and the end-of-step return to `main`,
and stay on the recorded branch. Launch has already published its audit to
control, so dirty Coga state in that checkout (`coga/log.md`, task files,
recurring state) is expected; leave it unstaged and never commit it with a
fix. Any other dirt still stops the assist. A recorded `worktree:` that is
not the current checkout, or a current checkout on another branch, gets no
such exception: ask the attending human.

Confirm `gh auth status` succeeds. Then, in the launch checkout:

1. Run the `dev/checkouts` start check: HEAD on `main`, a clean tree (Coga
   state included), and `git merge --ff-only origin/main` after a fetch. If
   it fails, stop and ask the attending human; do not stash, commit, or
   switch past another ticket's work.
2. `git switch <branch-name>` and verify `git status --short` is still clean.
   Do not absorb unrelated local changes or stage `coga/log.md` with a fix.
   From here until you return to `main`, edit code only: ticket and
   blackboard edits made on the branch are not published.
3. Read `[git].remote` from `coga.toml` (default `origin`) and use that configured
   remote to resolve the publication destination with
   `git remote get-url --push --all <configured-remote>`. Require exactly one
   non-empty result and call it `<verified-push-url>`. Stop if there are zero or
   multiple results: Git can partially update a multi-push remote, so it cannot
   preserve the assist's exact-tip transaction.
4. Use `gh pr view <pr-url> --json ...` to read `state`, `url`,
   `headRefName`, `headRefOid`, `headRepository`, and
   `headRepositoryOwner`. Require an open PR whose head ref matches `branch:`.
   Construct the actual PR head repository as
   `<headRepositoryOwner.login>/<headRepository.name>` and require the
   `<verified-push-url>` to identify that same GitHub repository. A same-named
   branch in the base repository is not the PR head when the PR comes from a
   fork, and a separate fetch URL does not authorize lifecycle pushes to the
   wrong repository.
5. Create a fresh, command-unique `<assist-fetch-ref>` under
   `refs/coga/address-pr-comments/<unique-token>`; never reuse it for another
   fetch. Fetch the branch directly from `<verified-push-url>`, resolve the
   fetched OID, then delete the private ref:

   ```text
   git fetch --no-write-fetch-head <verified-push-url> refs/heads/<branch-name>:<assist-fetch-ref>
   git rev-parse <assist-fetch-ref>
   git update-ref -d <assist-fetch-ref>
   ```

   Record the resolved value before deletion as `<verified-remote-oid>` and
   require it to equal the PR's reported `headRefOid`. Always delete the private
   ref after recording the OID, including on a mismatch or later failure.
   Do not read `FETCH_HEAD`: it is shared by concurrent fetches in the checkout
   and can be replaced between commands. Fast-forward the local checkout from
   the exact recorded OID when it is merely behind. If it is ahead unexpectedly
   or diverged, ask the human before rewriting published history.

Stay on the recorded branch until the replies are posted. Inspect another ref
with read-only Git commands rather than checking it out.

Extract the base repository owner, repository name, and PR number from the
recorded PR URL. The URL identifies the base repository even when the PR comes
from a fork.

## 2. Read every unresolved review thread

Use `gh api graphql`; `gh pr view --comments` is not a substitute because it
does not expose inline review-thread resolution state.

Query `reviewThreads` from the PR's base repository, including the thread ID,
resolution/outdated state, file and line, and all comments:

```graphql
query(
  $owner: String!,
  $repo: String!,
  $number: Int!,
  $cursor: String
) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      reviewThreads(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          originalLine
          comments(first: 100) {
            pageInfo { hasNextPage endCursor }
            nodes {
              id
              body
              url
              createdAt
              author { login }
            }
          }
        }
      }
    }
  }
}
```

Pass that query and typed variables to `gh api graphql`, for example with
`-F owner=<owner> -F repo=<repo> -F number=<number>`. Omit `cursor` on the
first request, then pass each `endCursor` until `hasNextPage` is false. If a
thread itself has more than 100 comments, fetch the remaining comments before
acting; never silently truncate the review.

The concrete call shape is:

```text
gh api graphql -F owner=<owner> -F repo=<repo> -F number=<number> -f query='<query-above>'
```

Add `-F cursor=<end-cursor>` on subsequent pages.

Keep only threads where `isResolved` is false, but do not discard an outdated
thread without reading it: the requested behavior may still be missing from
the current file. Inventory each thread and decide whether it needs a code
change, is already satisfied, or needs a human answer. Check existing replies
so a rerun does not duplicate work or responses.

## 3. Apply, verify, commit, and push

Make the smallest coherent changes that satisfy the must-fix threads. Keep
unrelated cleanup out of the diff. For a thread already satisfied by the
current branch, collect concrete file/commit evidence instead of manufacturing
another change.

Choose verification from the changed files and the repository's documented
checks. For code or fixture changes in a Python project, run `python -m pytest`;
in other projects, run the documented suite for that surface. For docs-only
changes, verify factual claims, links, and live/packaged copies. Run targeted
packaging, workflow, or composition checks when those contracts changed.
A pure prose edit does not require pytest or a Python test installation.
Record the exact checks and results; do not continue with failing required
checks. Then choose the path that matches the inventory:

- **At least one thread required a file change.** Commit the requested fixes on
  the recorded branch with a short factual subject. Immediately before pushing,
  re-read the PR's `state`, head repository, `headRefName`, and `headRefOid`;
  require the PR to remain open with the same repository and branch. Repeat the
  command-scoped verification sequence above with a new unique private ref,
  record it as `<verified-remote-oid>`, and require that OID to equal the fresh
  `headRefOid`. Prove the local fix is a fast-forward descendant with
  `git merge-base --is-ancestor <verified-remote-oid> HEAD`, then publish under
  an exact lease:

```text
git push --force-with-lease=refs/heads/<branch-name>:<verified-remote-oid> <verified-push-url> HEAD:refs/heads/<branch-name>
```

  The lease is a compare-and-swap guard, not permission to rewrite history:
  never run it unless the ancestor proof succeeded, and never use another
  force option. If the branch was deleted, the PR closed, or the remote moved,
  this exact lease must reject instead of recreating or overwriting the branch;
  fetch and reconcile with the attending human. After the push, re-run
  `gh pr view <pr-url> --json headRefOid` and require the reported OID to equal
  `git rev-parse HEAD`.
- **Every thread is already satisfied.** Do not manufacture a commit and do not
  push. Re-require the PR to be open, repeat the command-scoped fetch with a new
  unique private ref, and re-read the PR's `headRefOid`; require the recorded
  fetched OID, that reported OID, and `git rev-parse HEAD` to be identical. This
  proves the file/commit evidence you are about to cite describes the PR's
  current head.

Do not reply to threads until the applicable post-push or no-change proof
succeeds.

## 4. Reply without resolving

Reply only after the applicable head proof succeeds. Add one concise reply to
every unresolved thread in the inventory, saying what changed (or why the
current code already satisfies it), naming the commit when useful, and
reporting the verification result.

Use the thread's GraphQL node ID with this mutation:

```graphql
mutation($threadId: ID!, $body: String!) {
  addPullRequestReviewThreadReply(
    input: {
      pullRequestReviewThreadId: $threadId
      body: $body
    }
  ) {
    comment { id url }
  }
}
```

Invoke it with `gh api graphql` and typed `threadId` / `body` variables. Re-read
the thread immediately before replying so a retry does not post the same reply
twice. Do not call `resolveReviewThread` or use any UI/API action that resolves
the conversation.

The concrete call shape is:

```text
gh api graphql -F threadId=<thread-node-id> -f body='<reply>' -f query='<mutation-above>'
```

In a recorded legacy checkout, finish on the recorded branch and leave the
launch-published Coga state as it is. Otherwise, finish by running the
`dev/checkouts` end-of-step return: discard dirty Coga state only after
proving it already matches `origin/main`, `git switch main`, and
`git merge --ff-only origin/main`. If anything dirty is unpublished or
outside Coga state, stop and ask instead of discarding it.
Then give the attending human a compact list of addressed
threads, the pushed commit, the exact test result, and anything that still
needs their judgment, and stop naturally with the ticket still `in_progress`
on `review`. The launch supervisor publishes its trailing usage-log line to
control during teardown; do not add a completion commit or signal to imitate
it.
