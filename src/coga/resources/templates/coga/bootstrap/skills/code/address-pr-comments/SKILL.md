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

Because neither `step:` nor `status:` changes, the launch supervisor stops
after this assist instead of chaining another session. The existing
`autoclose-merged` sweep marks the ticket done after the human merges.

## 1. Verify the recorded PR and checkout

Read the current ticket's `## Dev` block. Require all three recorded values:

```text
branch: <branch-name>
worktree: <path>
pr: <full-pr-url>
```

Do not infer a missing value from the task slug or current checkout. Fail loud
and ask the attending human to repair the ticket if the linkage is missing,
ambiguous, or stale.

Confirm `gh auth status` succeeds. In the recorded worktree:

1. Verify `git branch --show-current` equals `branch:`.
2. Verify `git status --short` is clean before starting. Do not absorb unrelated
   local changes.
3. Run `gh pr view <pr-url> --json state,url,headRefName` and require an open PR
   whose head ref matches `branch:`.
4. Fetch the remote branch and make sure the local checkout is not behind or
   diverged. A normal fast-forward is fine; ask the human before rewriting
   published history.

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

Run:

```text
python -m pytest
```

Do not push with failing tests. Commit the requested fixes on the recorded
branch with a short factual subject. Then push normally:

```text
git push origin HEAD:<branch-name>
```

Never force-push during this assist. If the push is rejected because the remote
moved, fetch and reconcile with the attending human instead of overwriting it.

## 4. Reply without resolving

Reply only after the fix commit is successfully on the PR branch. Add one
concise reply to every unresolved thread in the inventory, saying what changed
(or why the current code already satisfies it), naming the commit when useful,
and reporting the verification result.

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

Finish by giving the attending human a compact list of addressed threads, the
pushed commit, the exact test result, and anything that still needs their
judgment. Then stop naturally with the ticket still `in_progress` on `review`.
