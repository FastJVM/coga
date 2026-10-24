---
name: coga/checkouts
description: The complete checkout lifecycle — which checkout each shipped step starts in, launch's branch preparation and handoff, and which checkout to invoke Coga from; reconciliation, the launch boundary, direct chat, the manual procedure, and the sandbox clone live in its leaves.
---

# Feature checkouts

Code-ticket work runs in the checkout the session was launched from. Every
session starts from a clean, current `main`, a step that changes code works
on its feature branch, and the session ends back on `main`. Under
`coga launch` the launcher performs the branch setup and both moves; in any
other session the agent does. Ticket work creates no linked worktrees; the
one alternative checkout is the [sandbox clone fallback](sandbox-clone/SKILL.md).
Only the recurring runner's temporary control worktree and Retro's isolated
checkout (created and removed for one Retro pass) are linked worktrees; ones
left from an earlier layout are disposed of by
[coga/checkout-cleanup](../checkout-cleanup/SKILL.md).

The ticket's `## Dev` record (`branch:`, `worktree:` for a sandbox clone,
`pr:`) is the link from ticket to branch to PR. It is explicit, not inferred
from the slug, because slug conventions break whenever a PR bundles tickets,
an agent picks another branch name, or a slug is truncated. Anything that
follows the link (bump gates, `open-pr`, autoclose, retire, status views)
reads the record; a branch name need not match the slug.

`origin` and `main` stand for the configured `[git].remote` and
`[git].control_branch`; `coga/tasks/`, `coga/recurring/`, and `coga/log.md`
for the configured workspace's task, recurring, and log paths. **The Coga
roots** are the Coga root plus the configured contexts root; every eligible (unignored) file there is Coga state
that publication carries ([coga/state-publication](../state-publication/SKILL.md)).

## Leaves

- [reconciliation](reconciliation/SKILL.md) — keeping edits current with main.
- [launch-boundary](launch-boundary/SKILL.md) — preparing and returning the
  invoking checkout, refusal recovery, and exemptions.
- [chat](chat/SKILL.md) — direct chat's occupancy guard and branch.
- [manual](manual/SKILL.md) — the start, work, and end an agent performs
  when launch did not prepare the branch.
- [sandbox-clone](sandbox-clone/SKILL.md) — the sandbox clone fallback.

## Start, work, end

Main can advance during any session. Follow
[reconciliation](reconciliation/SKILL.md) for the shared freshness and conflict
policy, including documentation, ticket edits, and ad-hoc work.

### Which checkout a step starts in

Launch maps the frozen current step of a shipped workflow to its entry
checkout. It is a closed table, not a step-name heuristic:

| Workflow | Current step | Entry |
| --- | --- | --- |
| `code/design-then-implement` | `design`, `evaluate-design`, `review-design` | control |
| all four shipped code/docs workflows | `implement` | create or reuse the recorded branch |
| `code/design-then-implement`, `code/with-review`, `docs/with-review` | `peer-review` | reuse the recorded branch |
| `code/with-self-review` | `self-qa` | reuse the recorded branch |
| `code/design-then-implement`, `code/with-review`, `docs/with-review` | `open-pr` | control |
| `code/with-self-review` | `pr` | control |
| all four | owner-held `review` (an explicit assist) | reuse the recorded branch |

A row applies only when the step's instructions are the shipped ones: its
step skill, or its inline `## <step>` section, equals the packaged copy
(older frozen snapshots of the same workflows match too). Anything else — a
custom workflow, a local edit of the consumed skill or section, extra or
replaced step skills — gets **manual**: launch still prepares and returns
control, but sets up no branch and says so. Ticket-wide `skills:`,
completion gates, and roles never select entry behavior. If the ticket's
workflow or step changes on control while launch prepares, launch refuses
before spawning; retry it.

Older `code/with-review` snapshots consume an inline `peer-review` section
that delegates to `code/peer-review`. Both that section and the resolved
skill must match the packaged copies for launch to reuse the branch.

### In a launched session

An ordinary `coga launch` of an agent-held step (or an explicit assist on an
owner-held step) does this for every step it chains, after bringing the
checkout to current control (the [launch boundary](launch-boundary/SKILL.md)).
It sets `COGA_LAUNCH_RETURNS_CHECKOUT=1` only when it will return the
checkout. The prompt's **Checkout (runtime)** notice states what it observed
and did.

1. **Entry.** For a create step with no `branch:`, launch creates one
   (`coga/<task>-<hex>`) at control and publishes it as `branch:` under
   `## Dev` before switching. Otherwise it reuses the first
   recorded `branch:`: a local ref as is (a behind one fast-forwards to its
   remote; ahead or diverged commits are kept and reported), or one created
   from its remote tip. It refuses — on control, starting nothing — a
   recorded branch absent everywhere, a reuse step with no branch (unless
   `## Already satisfied` evidence exists: the agent then verifies from
   control), a branch committing ticket intent control lacks ([stranded
   ticket writes](#stranded-ticket-writes)), one held by another worktree,
   or ignored files the switch would overwrite. After switching it projects
   only this ticket from control, unstaged: the session's only entry dirt.
2. **Work.** Commit only code: stage paths by name, never `git add -A` or
   `commit -a`. Never stage, commit, or restore the projected ticket. A
   context, skill, or workflow edit that belongs to the code PR (a canonical
   topic with a packaged twin, say) is committed with it before any sweeping
   Coga command runs in this checkout; left dirty, the sweep publishes it.
   To rebase, first copy the ticket outside the repo and verify the copy,
   restore it from HEAD (delete it if HEAD lacks it), rebase, then write the
   copy back unstaged and compare bytes. Test, commit, rebase onto
   `origin/main`, push.
3. **Hand off from the branch.** Write the handoff in the projected ticket,
   then run `coga bump` last; it publishes the ticket and log. Launch
   returns the checkout to a clean `main` afterwards. A bump that prints
   `[git] sync failed` or `sync refused` left the handoff unpublished, and
   launch's return will refuse over it; say so rather than discarding it.
   The bump itself was recorded, so never bump again to publish it: after a
   `sync failed`, once Git access is restored, run the `coga run
   publish-state` recovery the report prints
   ([recovery](../state-publication/SKILL.md#recovering-a-failed-publication)).
   After a `sync refused` (control's ticket changed meanwhile), preserve the
   handoff and reconcile it onto control's copy
   ([reconciliation](reconciliation/SKILL.md)). An unused prepared branch
   needs no commit or PR when the work proves already satisfied.

A control step sees `main`; publication (`coga open-pr`) reads and pushes the
branch by name from there. A step that must exceptionally change code from
control — a docs publication fix — follows the [manual procedure](manual/SKILL.md).
A preparation failure exits 75 naming the stage and where the checkout
stands; it never rolls back, and the next launch retries the same branch
name. A recorded `worktree:` (a sandbox clone) keeps this primary on control
and names the clone, which must exist on the recorded branch; see
[sandbox-clone](sandbox-clone/SKILL.md).

### Manual or API sessions, megalaunch picks, and exempt checkouts

Without the witness, and before editing in a manual-policy step, the agent
performs the start check, branch work, and end-of-step return itself, and
publishes its pre-branch ticket edits explicitly:
[coga/checkouts/manual](manual/SKILL.md).

The recorded human assist runs on its recorded PR branch under
[coga/human-assist](../human-assist/SKILL.md).

### Direct chat

`coga chat` runs the `prepare-checkout` command its notice names before its
first edit; [coga/checkouts/chat](chat/SKILL.md) owns that contract.

Launch never changes directory: the session runs where `coga launch` was
invoked, and launch never follows a recorded `worktree:`.

## Which checkout you invoke Coga from

- **Mutating commands publish from wherever they run.** The exit sweep
  publishes every dirty file under the Coga roots, plus eligible committed
  state there (only routine task, log, and recurring state from a feature
  branch), to control, even after a config failure. Write deliberate ticket
  prose and knowledge edits on `main`; commit a knowledge edit that belongs
  to a code PR before running a sweeping command on its branch. Committed
  `coga/recurring/` changes on a feature branch are still adopted onto
  control by the next sweep, ahead of the code PR, and re-adopted after a
  revert: make such a template also work under current control code, or
  keep it out of the Coga roots until the code lands. Which invocations
  sweep is owned by
  [coga/state-publication](../state-publication/SKILL.md#when-coga-publishes).
- **`coga launch <target> --prompt-report` regenerates `.agent-skills/`.**
  It skips the state sweep. For a write-free view call
  `compose.compose_prompt_report` or `compose.compose_prompt` directly.
- **Launch and megalaunch compose from the invoking checkout.** An ordinary
  ticket launch or direct chat brings it to fresh control first (the [launch
  boundary](launch-boundary/SKILL.md)). Run megalaunch and exempt launches
  only from a control checkout freshly synced to `origin/<control>`; a stale
  one re-dispatches merged work.

## Stranded ticket writes

A ticket write committed on the feature branch strands there: control keeps
rewriting the same file at every transition. `open-pr`'s freshness gate
refuses it and `bump` warns about it on stderr. In a sandbox clone an
uncommitted ticket edit surfaces as `coga open-pr`'s "Recorded worktree has
uncommitted changes" refusal, which names this ticket's file separately.
The comparison is one-directional; a branch copy control already absorbed is
silent. Uncommitted blackboard prose left in another checkout is not
detected; publish it before switching away.

Repair: inspect the branch copy, preserve anything still needed in the primary
ticket, then restore the merge base's copy on the branch and commit:

```sh
git restore --staged --worktree --source=$(git merge-base <control> <branch>) -- <path>
```

Do not rebase to fix it, and do not restore control's copy (it goes stale at
the next transition). A dirty task/log hunk in a sandbox clone is a duplicate
only after its content is preserved in the primary ticket or verified in the
authoritative log; discard only confirmed duplicates, never commit or stash
them to pass the clean-tree gate, and never hand-edit `coga/log.md`.
This ticket's own file is never implementation diff: control has already
rewritten it, so a branch commit of it is an overlapping stranded write. Move
an intentional authored-body change to the live ticket in the primary
checkout and discard the clone's copy. `ticket.py` and attachments under
`coga/tasks/` can be implementation work and stay in the diff.
