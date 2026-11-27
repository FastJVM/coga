---
name: code/address-pr-comments
description: Address requested PR changes while preserving the owner's review gate.
---

## 1. Verify the recorded PR and checkout

Read `branch:`, `remote:`, `base:` and `pr:` under `## Dev`. Switch to the
recorded branch if needed and stop if Git refuses. Leave unrelated edits
alone and stop if they prevent verification. Confirm the PR is open against
the recorded base and that its head repository and branch match the recorded
remote and branch. Keep the owner's review gate in place.

For the destination proof, require exactly one URL from
`git remote get-url --push --all <remote>`. Verify it identifies the PR head
repository and retain it as `<verified-push-url>`. Fetch the head directly
from that URL into a command-unique private ref under
`refs/coga/address-pr-comments/`. Require the fetched OID to equal the PR's
`headRefOid`, and before making changes require it to equal local HEAD.
Delete the private ref when the proof is finished. Ask the attending owner
about ambiguous or conflicting requests.

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

Record ticket notes in the local ticket. Report the addressed threads, pushed
commit and exact verification results to the owner. The final bump publishes
the ticket to the base. Leave the final bump and merge to the owner.
