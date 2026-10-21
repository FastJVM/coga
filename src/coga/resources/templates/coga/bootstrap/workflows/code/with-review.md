---
name: code/with-review
description: Code change implemented by the main agent, then reviewed by its configured peer before a PR is opened for the human's final review.
steps:
  - name: implement
    assignee: agent
    requires: branch
    skills:
      - code/implement
  - name: peer-review
    assignee: other-agent
  - name: open-pr
    assignee: agent
    requires: pr
    skills:
      - code/open-pr
  - name: review
    assignee: owner
    skills:
      - code/address-pr-comments
---

A step that declares `skills:` does **not** compose the `## <step>` section
below: Coga builds that step-specific layer from the declared skill files, and
the inline section is never read by the launched agent. The base prompt,
contexts, ticket-level skills, ticket body, and blackboard still compose
normally. Agent instructions therefore belong in the step's skills. Sections
here for a skilled step are human-facing framing only. Skill-less steps *do*
compose their section, so those bodies are load-bearing.

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
owner/human handoff), or on a terminal (`done`/`canceled`), `paused`, or
`blocked` state.

## implement

Agent step, owned by the `code/implement` skill. Launch creates or reuses the
recorded branch before the agent starts (`coga/checkouts`). The step declares
`requires: branch`, so `coga bump` refuses to advance until `branch:` is
recorded under `## Dev` in the ticket copy of the checkout the bump runs from.

## peer-review

You are running the peer-review step. You were selected as the main agent's
configured peer, but peer selection alone does not prove independent
authorship: an explicit launch override can make the same agent implement and
review a change, so do not assume you did not write this diff.

Review the change in this fresh peer-review session:

- **Claude**: run the `/code-review` slash command (default effort —
  *not* `ultra`) against the branch diff vs `main`.
- **Codex**: you are already the reviewer. Read the branch diff against its
  base (usually `main`), inspect the affected code and contracts, and complete
  the review yourself. Do not start another `codex review`, `codex exec`, or
  interactive Codex through your shell tools. Coga's supervisor handles the
  handoff between fresh agent sessions; a child CLI would instead nest inside
  this session's command sandbox. See `coga/sandboxes`, "Restricted sandboxes",
  for the runtime limitation. Direct review satisfies this step; preserve
  actual reviewer identity and independence rather than inferring either from
  the configured peer.

Launch starts this step on the recorded branch, with this ticket projected
unstaged from control as the only entry dirt (the **Checkout (runtime)**
notice says so; otherwise follow `coga/checkouts` yourself). Review the diff
against its base (`git diff main...HEAD`, `git log main..HEAD`). To apply
must-fix findings (skip nits), re-run `python -m pytest`, commit (e.g.
`peer-review: apply review findings`), and push. Write `## Peer review` and
`## PR` in the live ticket and run `coga bump <slug>` last; launch returns
the checkout (a manual session first returns to `main` per
`coga/checkouts`).

**Complete the review before you bump.** Finish a direct review and record
that it **completed**, its findings, and the head/base it covered. If a review
tool was invoked, wait for it to **return** before bumping. A review that has been
*started* is not a review that has returned. This step owns that wait: the
`open-pr` step which follows is mechanical, and the workflow auto-chains a
fresh agent the moment you bump, so nothing downstream can hold an in-flight
review open. Record the outcome under `## Peer review` on the blackboard —
which review form ran, that it **completed** (direct) or **returned** (tool),
and what it found — because a fresh
session cannot otherwise distinguish a returned review from one still running,
and that note is the only evidence that crosses the session boundary. If you
cannot wait, escalate per your launch mode rather than bumping. If findings imply a design rethink, write to the
blackboard and escalate per your launch mode — ask the attending human,
or `coga block` in a queue run. Escalate the same way if your review tool
isn't on PATH.

**A green suite is not the whole review when the diff touches a surface tests
cannot reach.** A raw-terminal loop, a pager, a TTY prompt, a rendered Slack
message: the tests cover the pure function underneath and never the thing a
human sees, and the megalaunch picker shipped a cursor that scrolled off-screen
with every test green. Drive such a surface yourself in a real terminal at the
sizes that matter, and record what you tried and saw under `## Peer review` —
that record is the gate. If the terminal cannot be driven from this session,
escalate per your launch mode instead of bumping on tests alone.

**This is the last judgment step before the PR opens.** The next `open-pr` step
is agent-owned, but its remit is only to run the deterministic command and bump,
so anything needing review judgment must be done *here* before you bump:

- **Make the branch fresh, not just conflict-free.** Don't wait for a
  conflict: run `git fetch origin main && git rebase FETCH_HEAD` on the
  feature branch unconditionally, preserving the projected ticket as
  `coga/checkouts` describes, resolve whatever surfaces, re-run
  `python -m pytest`, commit, and push with `--force-with-lease`. `coga
  open-pr` refuses unsafe material drift,
  and the next step is intentionally mechanical — this step is the last one
  that makes rebase decisions. If a conflict needs a call you can't make,
  escalate per your launch mode — ask the attending human, or `coga block`
  in a queue run.
- **Prepare the PR presentation after the final fixes and rebase.** A review
  receipt covers only the head/base it read: rebasing or committing fixes
  afterwards leaves it historical and forces `deep`. Freshen the branch (previous
  bullet) before the review when you can, and re-review the final head if
  fixes or a later rebase moved it, or record the receipt as covering the older
  revision. Read
  [coga/pr-publication/preparation](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/pr-publication/preparation/SKILL.md),
  “Presentation and review-depth rubric” and “Preparation record”. Refresh
  `## PR` with the actual title, advisory recommendation and rationale,
  implementation/deviations/limitations, reasons for every current diff path,
  and exact check/review receipts. Preserve actual implementing identities;
  record who really reviewed, whether it was independent or self-review, that
  it completed or returned, and the head/base it covered. An override or peer configuration
  does not prove independence. Explain omissions; never re-stamp stale results
  after fixes. The workflow's existing tests and review obligations still apply.

Leave the branch committed and pushed with commits ahead of `main`; `coga
open-pr` refuses to publish an empty branch.

## open-pr

Agent step, owned by the `code/open-pr` skill: `coga open-pr <slug>` pushes the
recorded branch, opens (or readies) the PR, and writes `pr:` back under
`## Dev`. It declares `requires: pr`, so `coga bump` holds the step until that
line exists.

The command is deterministic and has no judgment of its own, which is why the
preceding `peer-review` step is the one that authors the PR body and rebases the
branch.

## review

Owner-controlled gate. The human reviews the open PR on GitHub; the peer-review
pass has already applied its must-fix findings, so the diff is the post-review
state. The human decides whether to edit, request changes, push fixes, or merge.
An agent launched to assist here runs the `code/address-pr-comments` skill,
which carries the do-not-merge and do-not-bump rules for that assist.

After the human merges, the `autoclose-merged` recurring sweep marks the task
`done` on its next run (≤24h); `coga bump` closes it immediately.

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
