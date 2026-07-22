---
name: docs/with-review
description: Docs/markdown change implemented by one agent, then peer-reviewed for prose, accuracy, and repo↔packaged sync by the other agent before a PR is opened for the human's final review.
steps:
  - name: implement
    assignee: agent
  - name: peer-review
    assignee: other-agent
  - name: open-pr
    assignee: agent
  - name: review
    assignee: owner
---

## When to use this instead of code/with-review

Pick `docs/with-review` for **docs-only** tickets — README/spec edits,
context and skill bodies, markdown templates, vision/architecture docs —
where the change ships no code. It is the same branch → review → PR → owner
shape as `code/with-review`, but the `peer-review` step reviews **prose,
accuracy, and cross-copy sync** instead of running `/code-review` on a code
diff plus `python -m pytest`, which evaluators have repeatedly flagged as
value-light on markdown-only diffs.

If the ticket touches real code (even alongside docs), use
`code/with-review` instead — its diff review and test run earn their keep
there.

## Peer review by the other agent

The `implement` step runs under the ticket's `agent:` (the author). The
`peer-review` step declares `assignee: other-agent`, which resolves to
the configured `[agents.*]` type that is *not* the author — so a change
written by Claude is reviewed by Codex, and one written by Codex is
reviewed by Claude. The flip is automatic: `coga bump` rewrites
`assignee:` to the peer when it enters `peer-review`, and `open-pr`
flips back to the author.

`other-agent` needs exactly two agent types configured to be
unambiguous. With one type, or three or more, the bump fails loud rather
than guessing — fix `coga.toml` or the ticket's `agent:` if you hit
that.

The `coga launch` supervisor auto-chains across these agent boundaries:
when a bump rotates `assignee:` from one agent to another (author →
peer → author), it relaunches the *next* agent as a fresh process under
the same supervisor — claude's REPL exits and codex's starts, or vice
versa. Each step is a clean session with a freshly composed prompt; it
only returns control to the human at the final `review` step (an
owner/human handoff), or on a terminal (`done`/`canceled`), `paused`, or panic
state.

## implement

Implement the docs change on a feature branch, commit it, and stop before
push/PR. The mechanics match a code task, but the verification bar is
docs-oriented: prove the changed markdown, workflow, context, or template is
accurate and reachable rather than running tests that cover nothing.

1. **Read the ticket and context.** Confirm this is actually docs-only. If
   the ticket touches real code, write that mismatch to the blackboard and
   `coga panic` so the task can move to `code/with-review`.
2. **Create a feature worktree.** From the primary checkout on `main`,
   create a feature branch in a separate worktree outside the repo
   directory, for example:
   `git worktree add ../coga-<branch-name> -b <branch-name> main`.
   Return to the primary checkout and write `branch: <branch-name>` and
   `worktree: <path>` under `## Dev` on the blackboard.
3. **Edit in the feature worktree.** Keep the diff scoped to the ticket; no
   opportunistic rewrites. If you find adjacent cleanup, note it on the
   blackboard for a follow-up instead of folding it in.
4. **Keep shipped copies in sync.** If you touched a shipped Coga context or
   template that has both a live copy under `coga/` and a packaged copy under
   `src/coga/resources/templates/coga/`, edit **both** in the same commit
   unless the divergence is intentional and noted.
5. **Verify what changed.** Choose the checks that exercise the actual docs
   surface:

   - If you changed workflow/task structure, run `coga validate --json`
     or a task-scoped validation if repo-wide validation has unrelated drift.
   - If you changed packaged resources, run the relevant packaging/resource
     test.
   - Run `python -m pytest` only if you actually touched code or a fixture.
     A pure prose edit does not require the full suite.

6. **Commit.** Use a short factual subject and mention the ticket slug in the
   body. Leave the feature worktree clean.
7. **Bump from the primary checkout.** Run `coga bump <slug>` only after the
   blackboard is current. If you cannot reach a clean committed state, write
   the blocker to the blackboard and `coga panic`.

## peer-review

You are the *other* agent — you did not write this change. This is a
docs change, so review the **content**, not a code diff. Read the changed
markdown vs `main` (`git diff main -- '*.md'` plus any non-markdown docs
the ticket names) and check:

- **Accuracy** — do the claims match how the system actually behaves?
  Commands, paths, flags, and references should be real. Spot-check
  anything load-bearing against the source it describes.
- **Clarity & scope** — is it clear to the intended reader, and scoped to
  the ticket (no opportunistic rewrites that bloat the diff)?
- **Links & references** — internal links, file paths, and cross-doc
  references resolve; no dangling pointers to renamed/removed things.
- **Cross-copy sync** — if the change edits a Coga context or template
  with both a `coga/` copy and a `src/coga/resources/templates/coga/`
  copy, confirm both were updated (or the divergence is deliberate and
  documented). This is the most common docs-only miss.
- **Tests** — run `python -m pytest` **only if** the change actually
  touched code or a fixture; a pure prose edit does not need it.

From the feature worktree on the recorded branch, apply must-fix findings,
skip nits, commit (e.g. `peer-review: apply review findings`), then
`coga bump <slug>` from the primary checkout. If the change reads as wrong
in premise (documents behavior that doesn't exist, or contradicts a
canonical context), write to the blackboard and `coga panic` instead of
patching around it.

## open-pr

Push the reviewed branch and open the PR. This step is still docs-oriented,
but it owns the same publication and handoff guarantees as a code PR.

1. **Find the feature worktree.** Read `branch:` and `worktree:` under
   `## Dev` on the blackboard. Change into that worktree, confirm it is on
   the recorded branch, and confirm the working tree is clean.
2. **Push** the branch from the feature worktree.
3. **Open the PR** with `gh pr create`. If a draft PR already exists, mark it
   ready instead. Title = ticket title. Body = short summary + "Closes
   ticket: `<slug>`" + a one-line verification plan.
4. **Record the URL in durable task state.** From the primary checkout, add
   `pr: <url>` under `## Dev` on the blackboard. Also add or update a `## PR`
   section in the ticket body with the PR URL before you bump.

After the PR is open, **resolve any merge conflicts with the base branch
before the handoff**: check that the PR is mergeable (e.g. `gh pr view
<PR#> --json mergeable,mergeStateStatus`), and if it conflicts with
`main`, merge/rebase `main` into the feature branch, resolve the
conflicts, and push so the human reviewer receives a clean, mergeable PR.
If conflict resolution touches code or fixtures, run `python -m pytest`;
otherwise re-run the docs-specific verification that applies to the changed
files.
Only then `coga bump` to hand off to the owner. If a conflict needs a
judgment call you can't make, write it to the blackboard and `coga panic`
instead of bumping.

## review

Human reviews the open PR on GitHub. The peer-review pass has already
applied its must-fix findings to the branch, so the diff you see is the
post-review state.

This is an owner-controlled gate. If an agent is launched or asked to
assist during this step, it may inspect the PR, run verification, prepare
or push explicitly requested fixes, and report a recommendation. It must
not merge the PR, delete the branch, run
`coga mark done`, or otherwise advance/close the task unless the human
explicitly says to do that for this PR.

The human owner decides whether to edit, request changes, push fixes, or
merge. After the human merges, the `autoclose-merged` recurring sweep
marks the task `done` on its next run (≤24h); to close it immediately,
run `coga mark done`.
