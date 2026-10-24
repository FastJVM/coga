---
name: code/peer-review
description: Other-agent review of the implement step's branch diff. The configured peer reviews directly (Codex) or through `/code-review` (Claude), applies must-fix findings, freshens the branch, and prepares `## PR` before the mechanical PR-opening step.
---

# Peer-review the diff

You are running a peer-review step. You were selected as the main agent's
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
PR-opening step which follows is mechanical, and the workflow auto-chains a
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

**This is the last judgment step before the PR opens.** The next frozen step
is agent-owned, but its remit is only to run the deterministic `coga open-pr`
command and bump, so anything needing review judgment must be done *here*
before you bump:

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
