---
title: recurring task to manage all open pr and address commtns
status: in_progress
owner: nicktoper
agent: claude
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 2 (peer-review)
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
   packaged twin) with `delegate: bootstrap/address-pr-comments`,
   `schedule: "0 7 * * *"` (daily at 7am), `owner:`, `agent:`, and **no
   `workflow:`** — see the delegation bound under Context.
4. Tests mirroring the existing `resolve-conflicts` coverage (exact test
   names under Context), plus the docs/context touchpoints listed there.

Done looks like: `coga validate --json` is clean, `python -m pytest` passes,
and `coga launch bootstrap/address-pr-comments --prompt-report` composes.
The side-effecting checks — `coga address-pr-comments <n>` against a real
open PR printing one report line, and `coga recurring launch
address-pr-comments` driving the period task to `done` through the delegate
— push commits and post GitHub replies, so the **owner runs them at the
`review` step**, not implement or peer-review.

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
already holds the per-PR mechanics and must stay the single owner of them.
The bootstrap ticket cites that skill by path and section rather than
restating: its §2 (thread read via `reviewThreads` GraphQL, paginated), §3
(private-ref head proof, ancestor proof, exact-lease push), and §4
(reply mutation, never resolve) apply. Its §1 and its attended-assist conduct
do **not** apply, and the bootstrap ticket must say so explicitly, because
an agent reading both will hit the contradictions: there is no `## Dev`
block to read, no `git branch --show-current == branch:` check (a temporary
detached worktree pushes `HEAD:refs/heads/<head-ref>` under the same lease),
no attending human to ask, and — opposite to the skill — `coga slack --task
bootstrap/address-pr-comments` **is** the completion signal: it emits the
bootstrap done sentinel (`commands/slack.py`, the `BootstrapRef` branch) that
completes the delegated period. What differs from the skill, and what the
bootstrap ticket must spell out itself:

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
  only). Read them with `gh api --paginate repos/<owner>/<repo>/issues/<n>/comments`
  and review summaries from `gh api --paginate repos/<owner>/<repo>/pulls/<n>/reviews`,
  keeping only reviews in state `CHANGES_REQUESTED` or `COMMENTED` with a
  non-empty body — `APPROVED` ("LGTM") and `DISMISSED` are not requests. A
  review summary that carries inline threads (e.g. `/code-review --comment`)
  is covered by addressing those threads; do not reply to the summary too.
  Reply with `gh api repos/<owner>/<repo>/issues/<n>/comments -f body=...`.
- **The re-run guard must be marker-based, not author-based.** The sweep
  posts through the owner's `gh` token, so its replies carry the owner's
  login and are indistinguishable by author — and since every author counts,
  an author-based guard would make the sweep answer its own reply the next
  day, forever. Rule: every reply the sweep posts (thread reply or top-level
  comment) embeds a fixed HTML-comment marker naming what it answers, e.g.
  `<!-- coga:address-pr-comments reply-to:<thread-or-comment-id> -->`.
  A comment containing the marker is never in the to-address set. A thread
  or comment is addressed iff a later marker comment references its id; a
  new non-marker comment posted after the marker re-opens it. Apply the same
  rule to inline threads (an unresolved thread whose last comment carries
  the marker is skipped) so a daily sweep does not re-analyze every
  unresolved thread on ten PRs.
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
`skipped-fork`, `skipped-base`, `conflicting`, `verify-failed`,
`push-failed`), then a single `coga slack --task bootstrap/address-pr-comments`
roll-up at the end, exactly as `resolve-conflicts` does. A PR with mixed
outcomes gets one line under a precedence rule (`needs-human` >
`verify-failed` > `push-failed` > `addressed`) with the counts in `<detail>`.
The Slack line is the only cross-run record; nothing is written to any
ticket.

**Gate the skill already enforces, restated for the sweep:** never merge,
never delete a branch, never call `resolveReviewThread`, never `coga bump` /
`coga mark` on the PR's owning ticket. `autoclose-merged` closes tickets after
the human merges.

**Verification before push.** Same rule as `resolve-conflicts` step 6: if the
fix touches `src/` or `tests/`, run `python -m pytest` in the worktree; a
failure is `verify-failed` and the worktree is restored to its recorded
original OID. Docs-only fixes need no pytest run.

**Cited, not attached — `coga/recurring`**
(`coga/contexts/coga/recurring/SKILL.md`). Only a few identifiable facts
govern the template, all copied here; nothing else in the implement step
reads the rest. Read these sections before touching the template:

- The `delegate` bullet under `## A recurring task is a ticket-format
  directory` — **a delegated period is bounded to one agent step**: the
  template's resolved workflow must be exactly one step explicitly
  `assignee: agent` with no `requires:`. Omit `workflow:` so it gets the
  default `direct/body`; naming `code/with-review` (this ticket's workflow)
  on the template is refused as `unbounded-delegated-workflow`. Same bullet:
  a period may not carry both `ticket.py` and `delegate:`
  (`conflicting-delegate-script`), and the target must itself be agent-backed
  (`script-backed-delegate-target`).
- `## Gotchas` — declare `delegate:`; never shell out to a nested
  `coga launch` from the template body.
- `## Dropping a new recurring task` — a new template fires retroactively on
  its first sweep; for a daily schedule that just means it runs once on the
  next sweep, so no `_` parking is needed.
- **Headless sweeps skip this template.** A delegating template is in the
  agent-backed admission class, so a cron-driven `coga recurring` refuses it
  (with a warning) before the period task exists; it runs only under an
  attended sweep or an explicit `coga recurring launch address-pr-comments`.
  "Comments addressed within a day" therefore means "within a day of the next
  attended sweep", and every attended sweep on a new day opens one agent
  session that inspects every open PR. Owner accepted this cost at authoring.

**Cited, not attached — `coga/extension-model`**
(`coga/contexts/coga/extension-model/SKILL.md`). Two facts: a stateless
command ticket is a bootstrap target launched in place, and a default alias
is how it earns a top-level spelling. Its prose names `resolve-conflicts` as
"the shipped agent-backed form" — add `address-pr-comments` beside it in the
same PR, and update the alias lists in `docs/cli-extension-audit.md` (the
alias table and the two enumerations of default aliases) and any
`docs/development.md` mention. `aliases.DEFAULT_ALIASES`'s comment block
explains `resolve-conflicts`; extend it for the new alias.

**Tests to mirror.** `tests/test_packaging.py::EXPECTED_BOOTSTRAP_RESOURCES`
is a wheel-inclusion allowlist — add both new packaged paths (bootstrap and
recurring `ticket.md`); twin byte-identity is derived automatically. Add a
sibling of
`test_packaging.py::test_resolve_conflicts_recurring_wrapper_replaces_stale_worktree_sweep`
(asserts `delegate:`, no `ticket.py`, no `coga mark done`, no nested
`coga <alias> --agent` in the wrapper body), a sibling of
`test_aliases.py::test_resolve_conflicts_is_default_alias_for_agent_command_ticket`
and its selector-carrying twin, and extend or parametrize
`test_validate.py::test_validate_accepts_recurring_delegate_to_shipped_bootstrap`.

**Out of scope.** Merging approved PRs, rebasing conflicting PRs
(`resolve-conflicts`), pre-PR branches, PRs on other repos, and changing the
`code/address-pr-comments` skill's owner-gate semantics.

<!-- coga:blackboard -->

## Dev

branch: address-pr-comments-sweep
worktree: /home/n/Code/coga-address-pr-comments

## Plan (implement, attended)

Layout: separate linked worktree from `origin/main`; `## Dev` recorded on the
primary checkout, which is where `coga bump` runs.

Deliverables, all mirrored on `resolve-conflicts`:
- `bootstrap/address-pr-comments/ticket.md` live + packaged (byte-identical).
- `recurring/address-pr-comments/ticket.md` live + packaged, `delegate:` +
  daily schedule, no `workflow:`.
- `aliases.DEFAULT_ALIASES["address-pr-comments"]` + comment block.
- Tests: `EXPECTED_BOOTSTRAP_RESOURCES`, wrapper-shape sibling, two alias
  siblings, parametrized validate delegate test.
- Docs/contexts: `docs/cli-extension-audit.md`, `docs/development.md`,
  `coga/extension-model` (live + packaged), plus `coga/sync` template
  accounting (owner agreed to this one extra touchpoint).

## Implement — done (2026-09-20)

Commits on `address-pr-comments-sweep` (rebased on `origin/main` a5420200):
- `7fbbf98c` Add address-pr-comments command ticket and daily recurring sweep
- `e00a76c9` Account for address-pr-comments in docs and contexts

What landed:
- `coga/bootstrap/address-pr-comments/ticket.md` + packaged twin. Mirrors
  `resolve-conflicts` section for section. Cites skill §2/§3/§4 by path;
  states explicitly that §1 and the attended conduct do not apply (no
  `## Dev`, no `branch --show-current` check, no human to ask, no
  `coga block`, and `coga slack --task bootstrap/address-pr-comments` IS the
  completion signal). Spells out: PR-first `gh pr view` fields, three
  comment sources (threads / issue comments / reviews with the
  APPROVED+DISMISSED exclusion and the "summary covered by its threads"
  rule), the marker `<!-- coga:address-pr-comments reply-to:<id> -->`
  guard with re-open rule, worktree selection, `needs-human`, base/
  conflicting/fork skips, verify gate, lease push, nine status tokens and
  the mixed-outcome precedence.
- `coga/recurring/address-pr-comments/ticket.md` + packaged twin:
  `schedule: "0 7 * * *"`, `delegate:`, `owner: nicktoper`, `agent: claude`,
  no `workflow:` (comment in frontmatter says why).
- `aliases.DEFAULT_ALIASES["address-pr-comments"]` + comment block.
- Tests: `EXPECTED_BOOTSTRAP_RESOURCES` (+2), new
  `test_address_pr_comments_recurring_wrapper_delegates_to_command_ticket`,
  `test_address_pr_comments_is_default_alias_for_agent_command_ticket`,
  `test_default_address_pr_comments_alias_carries_optional_pr`, and
  `test_validate_accepts_recurring_delegate_to_shipped_bootstrap` is now
  parametrized over both delegates.
- Docs/contexts: `docs/cli-extension-audit.md` (alias table, recurring
  table, both enumerations, "ships nine", inventories),
  `docs/development.md` (second local override), `coga/extension-model`
  and `coga/sync` contexts (live + packaged twins).

Verification (in the feature worktree, own `.venv` via
`uv venv --python 3.12` + `uv pip install -e ".[test]"`):
- `python -m pytest` → 2661 passed.
- `coga validate --json` → same issue set as `main` (4 pre-existing
  `unsynthesized-draft-blackboard` errors on unrelated draft tickets); zero
  issues mention address-pr-comments.
- `coga launch bootstrap/address-pr-comments --prompt-report` composes
  (~5.1k tokens; task_description 12.8 KiB).

Decisions / flags for review:
- `owner: nicktoper` is in the recurring template because the ticket asked
  for `owner:`; no other packaged recurring template carries one and
  `coga.toml` already defaults `owner`. It ships in the wheel — drop the
  line at review if that is unwanted (twins must stay byte-identical).
- Fork PRs are `skipped-fork` outright; the sweep never resolves a fork
  push remote. Same posture as `resolve-conflicts`' "origin only".
- `docs/development.md` line-range cite `tasks.py:302-312` became a symbol
  cite (`resolve_bootstrap`) while the sentence was being edited.
- The feature worktree carries a seeded 0600 `coga/coga.local.toml`
  (gitignored) for the prompt-report check; remove it when the worktree is
  retired.

Not done here (owner runs at `review`, side-effecting): `coga
address-pr-comments <n>` against a real open PR; `coga recurring launch
address-pr-comments` end to end.
