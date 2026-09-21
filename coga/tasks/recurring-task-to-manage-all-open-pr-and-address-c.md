---
title: recurring task to manage all open pr and address commtns
status: draft
owner: nicktoper
agent: claude
workflow: code/with-review
---

## Description

Add a daily recurring task that sweeps every open PR on this repo and
addresses its review comments: for each unresolved inline review thread and
each unanswered top-level PR comment, apply the requested fix on the PR branch,
verify, push under an exact lease, and reply on the thread. Never merge a PR,
never resolve a thread, never touch a ticket's workflow — the human still owns
the review gate. Comments from any author count, including bot and
`/code-review` comments.

Today this only happens when the owner launches `coga launch <slug>` by hand
against one ticket's `review` step (the `code/address-pr-comments` skill).
With ten-plus PRs open at a time, comments sit unaddressed until someone
remembers. The sweep makes "comments get addressed within a day" a property
of the repo instead of a chore.

Ship it in the exact shape `resolve-conflicts` already has:

1. A stateless command ticket `bootstrap/address-pr-comments` (live
   `coga/bootstrap/address-pr-comments/ticket.md` and its packaged twin under
   `src/coga/resources/templates/coga/bootstrap/`) that sweeps all open PRs,
   or one PR when a selector is passed.
2. A default alias `address-pr-comments = "launch bootstrap/address-pr-comments"`
   in `aliases.DEFAULT_ALIASES`, so `coga address-pr-comments [PR]` works on
   demand. Do not add it to `coga.toml`.
3. A recurring template `coga/recurring/address-pr-comments/ticket.md` (and
   packaged twin) with `delegate: bootstrap/address-pr-comments` and
   `schedule: "0 7 * * *"` — daily at 7am, before `resolve-conflicts` fires
   at 8am on Mondays.
4. Tests mirroring the existing `resolve-conflicts` coverage in
   `tests/test_aliases.py`, `tests/test_validate.py`, `tests/test_packaging.py`
   (twins are derived automatically — just make both copies byte-identical),
   plus the docs/context touchpoints listed under Context.

Done looks like: `coga validate --json` is clean, `python -m pytest` passes,
`coga address-pr-comments 855` runs against a real open PR and prints one
report line, and `coga recurring launch address-pr-comments` drives the
period task to `done` through the delegate.

## Context

**Model to copy.** `coga/bootstrap/resolve-conflicts/ticket.md` and
`coga/recurring/resolve-conflicts/ticket.md` are the exact precedent: a
stateless command ticket owns the operation, the recurring template owns only
the schedule and a frozen `delegate:` field. Mirror their structure section
for section (Description → Scope → Run order → Restore and cleanup → Report),
including the `## Launch arguments` selector contract (`[]` = all open PRs,
`[PR]` = one PR, anything else = print usage and stop) and the paginated
`gh pr list --state open --limit 10000` enumeration. The template's own
blackboard stays stateless, like `resolve-conflicts`'.

**Mechanics to reuse.** `coga/skills/code/address-pr-comments/SKILL.md`
already holds the per-PR mechanics and must stay the single owner of them:
the `reviewThreads` GraphQL query with pagination, the
`addPullRequestReviewThreadReply` mutation, the command-unique private fetch
ref (`refs/coga/address-pr-comments/<unique-token>`) that proves the remote
head, the `git merge-base --is-ancestor` proof before a
`--force-with-lease=refs/heads/<branch>:<verified-remote-oid>` push, and the
fork-head-repository check. The bootstrap ticket should cite that skill by
path for those steps rather than restating them. What differs from the skill,
and what the bootstrap ticket must spell out itself:

- The skill reads `branch:` / `worktree:` / `pr:` from one ticket's `## Dev`
  block. The sweep instead starts from the PR (`gh pr view --json
  headRefName,headRefOid,headRepository,headRepositoryOwner,baseRefName,
  state,mergeable`) and selects a worktree the way `resolve-conflicts` does:
  reuse the branch's existing worktree only if it is clean, has no
  merge/rebase in progress, and its HEAD equals the observed head OID;
  otherwise fetch `refs/pull/<n>/head` into a temporary detached worktree
  created by this run and removed afterwards. Never touch the `main`
  checkout. Report `skipped-dirty` rather than stash or reset.
- **Top-level PR comments are in scope** (the skill covers inline threads
  only). Read them with `gh api repos/<owner>/<repo>/issues/<n>/comments`
  (paginated) and PR reviews with a non-empty body from
  `gh api repos/<owner>/<repo>/pulls/<n>/reviews`. A top-level comment is
  "addressed" once a reply from the agent quoting or referencing it exists
  later in the same comment list; reply with
  `gh api repos/<owner>/<repo>/issues/<n>/comments -f body=...`. There is
  no resolution state for these, so the re-run guard is the existing-reply
  check — define it precisely so a daily sweep never double-replies.
- Comments needing a human answer (ambiguous, contradictory, scope-expanding)
  get one reply saying so and are reported as `needs-human`; the sweep is
  unattended, so there is no one to ask. `coga block` is not available
  either — the target is stateless.
- Only PRs targeting `main`. A PR with another base is reported and skipped.
- A PR that GitHub reports `CONFLICTING` is reported `conflicting` and
  skipped — rebasing is `resolve-conflicts`' job, and a fix pushed onto a
  conflicting head would just be rebased again on Monday.

**Report contract.** One stdout line per PR as soon as its outcome is known,
`PR #<n> <head-ref> — <status> — <detail>`, with a fixed status vocabulary
(suggested: `addressed`, `no-comments`, `needs-human`, `skipped-dirty`,
`conflicting`, `verify-failed`, `push-failed`, `skipped-base`), then a single
`coga slack` roll-up at the end, exactly as `resolve-conflicts` does. The
Slack line is the only cross-run record; nothing is written to any ticket.

**Gate the skill already enforces, restated for the sweep:** never merge,
never delete a branch, never call `resolveReviewThread`, never `coga bump` /
`coga mark` on the PR's owning ticket. `autoclose-merged` closes tickets after
the human merges.

**Verification before push.** Same rule as `resolve-conflicts` step 6: if the
fix touches `src/` or `tests/`, run `python -m pytest` in the worktree; a
failure is `verify-failed` and the worktree is restored to its recorded
original OID. Docs-only fixes need no pytest run.

**Cited, not attached — `coga/recurring`**
(`coga/contexts/coga/recurring/SKILL.md`). It is large relative to the rest
of the prompt and this ticket needs three facts from it; read these sections
before touching the template: `Dropping a new recurring task` (a new template
fires retroactively on its first sweep — for a daily schedule that just means
it runs today, so no `_` parking is needed), `Extend recurring with a
task-specific workflow` (the `delegate:` constraint: a period may not carry
both `ticket.py` and `delegate:`, and a headless sweep refuses an agent-backed
template before the period task exists), and `The creation contract`.

**Cited, not attached — `coga/extension-model`**
(`coga/contexts/coga/extension-model/SKILL.md`). Two facts: a stateless
command ticket is a bootstrap target launched in place, and a default alias
is how it earns a top-level spelling. Its prose names `resolve-conflicts` as
"the shipped agent-backed form" — add `address-pr-comments` beside it in the
same PR, and update the alias lists in `docs/cli-extension-audit.md` (the
alias table and the two enumerations of default aliases) and any
`docs/development.md` mention. `aliases.DEFAULT_ALIASES`'s comment block
explains `resolve-conflicts`; extend it for the new alias.

**Out of scope.** Merging approved PRs, rebasing conflicting PRs
(`resolve-conflicts`), pre-PR branches, PRs on other repos, and changing the
`code/address-pr-comments` skill's owner-gate semantics.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
