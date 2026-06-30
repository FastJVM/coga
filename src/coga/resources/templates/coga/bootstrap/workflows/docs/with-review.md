---
name: docs/with-review
description: Docs/markdown change implemented by one agent, then peer-reviewed for prose, accuracy, and repo↔packaged sync by the other agent before a PR is opened for the human's final review.
steps:
  - name: implement
    assignee: agent
    skills:
      - code/implement
  - name: peer-review
    assignee: other-agent
  - name: open-pr
    assignee: agent
    skills:
      - code/open-pr
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
owner/human handoff), or on `done`/`paused`/panic.

## implement

Run the `code/implement` skill — branch, feature worktree, edit, commit,
bump — the machinery is the same for a markdown change. The one
adjustment for docs-only work: there is usually no regression test to add
and `python -m pytest` covers nothing you changed, so treat the skill's
test step as **"verify what you actually changed."** Concretely:

- If you touched a shipped Coga context or template that has both a live
  copy under `coga/` and a packaged copy under
  `src/coga/resources/templates/coga/`, edit **both** in the same commit
  (CLAUDE.md's sync rule) unless the divergence is intentional and noted.
- If you changed anything `coga validate` checks (workflow/task structure),
  run `coga validate --json`.
- Run `python -m pytest` only if you actually touched code or a fixture;
  otherwise it is not required for this step.

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

Follow the `code/open-pr` skill to push and open the PR. In addition to
the blackboard `## Dev` entry, **update the ticket**: write the PR link
into `ticket.md` so the source of truth records where the change landed.
Add a `## PR` section to the ticket body (or update it if present) with
the PR URL before you `coga bump`.

After the PR is open, **resolve any merge conflicts with the base branch
before the handoff**: check that the PR is mergeable (e.g. `gh pr view
<PR#> --json mergeable,mergeStateStatus`), and if it conflicts with
`main`, merge/rebase `main` into the feature branch, resolve the
conflicts, and push so the human reviewer receives a clean, mergeable PR.
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
