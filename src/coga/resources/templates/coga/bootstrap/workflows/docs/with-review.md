---
name: docs/with-review
description: Docs/markdown change implemented by one agent, then peer-reviewed for prose, accuracy, and repo↔packaged sync by the other agent before a PR is opened for the human's final review.
steps:
  - name: implement
    assignee: agent
    requires: branch
  - name: peer-review
    assignee: other-agent
  - name: open-pr
    assignee: agent
    requires: pr
  - name: review
    assignee: owner
    skills:
      - code/address-pr-comments
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

The `implement` step derives its operator from the ticket's `agent:` main-agent
choice. The `peer-review` step declares `assignee: other-agent`, which resolves
to that main agent's configured peer. `coga bump` advances `step:` and the next
operator is derived from the frozen role; it never writes an assignment.
`open-pr` declares `agent` and routes back to the same main-agent choice.

With two configured agent types, `other-agent` infers the only peer with no
extra config. With three or more, set `peer = "<type>"` on the main agent's
`[agents.<type>]` table; the mapping is one-directional, so each main agent that
uses this workflow needs its own peer. An absent or ambiguous peer fails loud
rather than guessing.

An explicit launch override changes the executing agent without changing the
stored main agent or its peer. It can therefore make the same agent implement
and review a change. Peer selection alone does not prove independent authorship.

The `coga launch` supervisor auto-chains across these agent boundaries:
when a bump changes the derived operator (main → peer → main),
it launches the *next* agent as a fresh process under
the same supervisor — claude's REPL exits and codex's starts, or vice
versa. Each step is a clean session with a freshly composed prompt; it
only returns control to the human at the final `review` step (an
owner/human handoff), or on a terminal (`done`/`canceled`), `paused`, or blocked
state.

## implement

Implement the docs change on a feature branch in the launch checkout,
commit and push it, and hand off; stop before the PR. Under `coga launch`
the branch is already created or reused and launch returns the checkout
after you bump; the **Checkout (runtime)** notice says so. Otherwise follow
`coga/checkouts` yourself — no linked worktrees. The mechanics match a code
task, but the verification bar is
docs-oriented: prove the changed markdown, workflow, context, or template is
accurate and reachable rather than running tests that cover nothing.

1. **Read the ticket and context.** Confirm this is actually docs-only. If
   the ticket touches real code, write that mismatch to the blackboard and
   escalate per your launch mode — ask the attending human, or `coga block`
   in a queue run — so the task can move to `code/with-review`.
2. **Confirm the checkout.** On a prepared branch the only entry dirt is
   this ticket, projected unstaged from control: write notes and the
   handoff there, and never stage or commit it. A notice reporting kept
   local commits means reconcile per `coga/checkouts/reconciliation` before
   pushing; anything unexpected means stop and escalate per your launch
   mode. With no prepared branch, perform the `coga/checkouts` manual start
   check and branch setup. A read-only `.git` uses the
   sandbox clone fallback in `coga/checkouts/sandbox-clone`; seed each clone,
   on creation and on resume, with
   `python /resolved/code/implement/seed_local_config.py /primary/repo/coga /feature/repo`.
3. **Edit on the feature branch.** Keep the diff scoped to the ticket; no
   opportunistic rewrites. Edit docs only while on the branch — note
   adjacent cleanup for a follow-up and write it to the blackboard with the
   handoff (step 7).
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

6. **Commit and push.** Use a short factual subject and mention the
   ticket slug in the body, rebase onto fetched `origin/main` as
   `coga/checkouts` describes, then push the branch. A manual session then
   runs the `coga/checkouts` end-of-step return.
7. **Hand off and bump.** Write the handoff in the live ticket, confirm
   `## Dev` records `branch:`, then run `coga bump <slug>` last. If
   you cannot reach a clean committed state, write the blocker to the
   blackboard and escalate per your launch mode — ask the attending human,
   or `coga block` in a queue run.

## peer-review

You are running the peer-review step for a docs change. You were selected as
the main agent's configured peer, but peer selection alone does not prove
independent authorship: an explicit launch override can make the same agent
implement and review a change, so do not assume you did not write this diff.

Review the **content**. Launch starts this step on the recorded branch (the
notice says so; otherwise follow `coga/checkouts`). Read the changed markdown
against its base (`git diff main...HEAD -- '*.md'` plus any non-markdown docs
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

Record the outcome under `## Peer review` on the blackboard, and refresh the
`## PR` preparation record there
([coga/pr-publication/preparation](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/pr-publication/preparation/SKILL.md),
“Preparation record”) so the `open-pr` step has evidence to format.

Apply must-fix findings (skip nits) on the branch, commit (e.g.
`peer-review: apply review findings`), and push. Write your notes in the
live ticket and run `coga bump <slug>` last (a manual session first returns
to `main` per `coga/checkouts`). If the change reads as wrong
in premise (documents behavior that doesn't exist, or contradicts a
canonical context), write to the blackboard and escalate per your launch mode
— ask the attending human, or `coga block` in a queue run — instead of patching
around it.

## open-pr

Push the reviewed branch and open the PR. This step is still docs-oriented,
but it owns the same publication and handoff guarantees as a code PR, and
declares `requires: pr`, so `coga bump` holds it until `pr:` is recorded.

1. **Find the branch.** This step runs from a clean, current `main` (the
   notice says whether launch prepared it; otherwise perform the
   `coga/checkouts` manual start check). Read `branch:` under `## Dev` on the
   blackboard (and `worktree:`, present only for a sandbox clone). Confirm
   the branch has commits ahead of `main`.
2. **Run `coga open-pr <slug>` from `main`.** It pushes the recorded branch
   by name, opens the PR (or readies a draft, or refreshes an open one),
   formats the blackboard `## PR` preparation record into the body, and
   writes `pr: <url>` under `## Dev` on the blackboard
   ([coga/pr-publication](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/pr-publication/SKILL.md)).
   Do not add a `## PR` section to the ticket body, and never hand-open the
   PR with `gh pr create` to route around a refusal without explicit human
   approval.

After the PR is open, **resolve any merge conflicts with the base branch
before the handoff**: check that the PR is mergeable (e.g. `gh pr view
<PR#> --json mergeable,mergeStateStatus`), and if it conflicts with
`main`, resolve it on the feature branch with the `coga/checkouts/manual`
procedure — switch, merge or rebase `main`, resolve, push, and return to a
clean `main` before writing any ticket notes — so the human reviewer
receives a clean, mergeable PR.
If conflict resolution touches code or fixtures, run `python -m pytest`;
otherwise re-run the docs-specific verification that applies to the changed
files. A resolution push moves the head the PR body describes: refresh the
`## PR` preparation record — new check receipts, and the review receipt
marked as covering the pre-resolution revision — then rerun
`coga open-pr <slug>` from `main` after the final push so the body matches
the head the owner reviews.
Only then `coga bump` to hand off to the owner. If a conflict needs a
judgment call you can't make, write it to the blackboard and escalate per your
launch mode — ask the attending human, or `coga block` in a queue run — instead
of bumping.

## review

Human reviews the open PR on GitHub. The peer-review pass has already
applied its must-fix findings to the branch, so the diff you see is the
post-review state.

This is an owner-controlled gate. The step freezes `code/address-pr-comments`
(the same skill `code/with-review` freezes), so an agent launched or asked to
assist here composes that skill rather than this section: it reads the PR's
review threads, may run verification and prepare or push explicitly requested
fixes, replies without resolving, and reports a recommendation. It must not
merge the PR, delete the branch, run `coga bump` or `coga mark done`, or
otherwise advance/close the task unless the human explicitly says to do that
for this PR.

The human owner decides whether to edit, request changes, push fixes, or
merge. After the human merges, the `autoclose-merged` recurring sweep
marks the task `done` on its next run (≤24h); to close it immediately,
run `coga bump`.

`done` is not the end of the ticket. When the sweep closes it, the sweep also
disposes of the feature branch (and any leftover recorded worktree) recorded
under `## Dev`, but only what the shared checkout proofs show is safe to
remove; a `coga bump` close disposes of nothing. The closing act is still the
owner's — once the ticket is `done`, run `coga retire <slug>`. Retire runs the
same proofs on whatever checkout remains, then deletes the done ticket with no
agent: its learning already landed with the merged PR. The packaged
`bootstrap/retire/ticket.md` owns that procedure, and the
`coga/checkout-cleanup` context owns what the shared proofs prove, preserve,
and record for later sweeps.
