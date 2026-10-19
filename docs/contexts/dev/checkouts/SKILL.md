---
name: dev/checkouts
description: The complete checkout lifecycle — which checkout each shipped step starts in, launch's branch preparation and handoff, the manual start/work/end procedure, chat preparation, and which checkout to invoke Coga from; reconciliation, the launch boundary, and the sandbox clone live in its leaves.
---

# Feature checkouts

Code-ticket work runs in the checkout the session was launched from. There are
no linked worktrees and no control checkouts for ticket work: every session
starts from a clean, current `main`, a step that changes code works on its
feature branch, and the session ends back on `main`. Under `coga launch` the
launcher performs the branch setup and both moves; in any other session the
agent does. Linked worktrees left over from an
earlier layout are still disposed of by `coga retire` and autoclose
([dev/checkout-cleanup](../checkout-cleanup/SKILL.md)); nothing creates new ones
for ticket work. Two owner-accepted exceptions create linked worktrees: the
recurring runner's temporary linked control worktree for a parked checkout
([coga/internals/recurring-temp-worktrees](../../coga/internals/recurring-temp-worktrees/SKILL.md)),
and Retro's dedicated isolated checkout, which the `retro/done-ticket` skill
and `coga retire`'s task prompt create and remove for one Retro pass, so
Retro runs while the operator keeps working in the main tree (owner decision,
2026-10-14). Revisit either decision if those worktrees leak or become
operator-visible noise.
The one alternative checkout for ticket work is the [sandbox clone fallback](sandbox-clone/SKILL.md).

`origin` and `main` stand for the configured `[git].remote` and
`[git].control_branch`; `coga/tasks/`, `coga/recurring/`, and `coga/log.md`
for the configured workspace's task, recurring, and log paths. **The Coga
roots** are the Coga root plus the configured contexts root
(`git.coga_root_paths`); every eligible (unignored) file there is Coga state
that publication carries ([coga/internals/state-publication](../../coga/internals/state-publication/SKILL.md)).

## Leaves

- [dev/checkouts/reconciliation](reconciliation/SKILL.md) — keeping all agent
  edits current with main while preserving unique work.
- [dev/checkouts/launch-boundary](launch-boundary/SKILL.md) — how ordinary
  ticket launches and chat/orientation prepare and return the invoking
  checkout, how to investigate refusals, and which launches skip it.
- [dev/checkouts/chat](chat/SKILL.md) — direct chat's occupancy guard and
  its session-owned branch preparation.
- [dev/checkouts/manual](manual/SKILL.md) — the start check, work, and
  end-of-step return an agent performs itself when launch did not prepare
  the branch, and publishing pre-branch ticket edits.
- [dev/checkouts/sandbox-clone](sandbox-clone/SKILL.md) — the sandbox clone
  fallback, recovery from a first sandbox refusal, and seeding what a fresh
  checkout lacks.

## Start, work, end

Main can advance during any session. Follow
[reconciliation](reconciliation/SKILL.md) for the shared freshness and conflict
policy, including documentation, ticket edits, and ad-hoc work.

### Which checkout a step starts in

`checkout_policy.select_checkout_policy` maps the frozen current step of a
shipped workflow to its entry checkout. It is a closed table, not a step-name
heuristic:

| Workflow | Current step | Entry |
| --- | --- | --- |
| `code/design-then-implement` | `design`, `evaluate-design`, `review-design` | control |
| all four shipped code/docs workflows | `implement` | create or reuse the recorded branch |
| `code/with-review`, `docs/with-review` | `peer-review` | reuse the recorded branch |
| `code/with-self-review` | `self-qa` | reuse the recorded branch |
| `code/design-then-implement`, `code/with-review`, `docs/with-review` | `open-pr` | control |
| `code/with-self-review` | `pr` | control |
| all four | owner-held `review` (an explicit assist) | reuse the recorded branch |

A row applies only when the step's instructions are the shipped ones: the
named step skill (`code/design`, `code/review-design`, `code/implement`,
`code/self-qa`, `code/open-pr`, `code/address-pr-comments`) resolves to bytes
equal to the packaged copy, or the inline step's live `## <step>` section
equals the packaged section. Older frozen snapshots without
`evaluate-design` or `requires:`, and the older empty-skills `review` that
consumes the live inline section, match the same rows. Anything else — a
custom workflow, a local edit of the consumed skill or section, extra or
replaced step skills — gets **manual**: launch still prepares and returns
control, but sets up no branch and says so. Ticket-wide `skills:`,
completion gates, and roles never select entry behavior.

### In a launched session

An ordinary `coga launch` of an agent-held step (or an explicit assist on an
owner-held step) runs this for every step it chains, from a fresh control
read: publish routine state and prepare control (the [launch
boundary](launch-boundary/SKILL.md)), routing and refusing preflights,
activation, the launch audit on control, then branch preparation, final
composition from control, the switch, and spawn. It sets
`COGA_LAUNCH_RETURNS_CHECKOUT=1` only when it will return the checkout. The
prompt's **Checkout (runtime)** notice states what it observed and did.

1. **Entry.** For a create step with no `branch:`, launch reserves one name
   (`coga/<task>-<hex>`), creates it at control without switching, writes
   `branch:` into `## Dev`, publishes the ticket strictly, and re-proves a
   clean control carrying that linkage. Otherwise it reuses the first
   recorded `branch:`: a local ref as is (a behind one fast-forwards to its
   remote; ahead or diverged commits are kept and reported), or one created
   from its remote tip. It refuses — on control, starting nothing — a
   recorded branch absent everywhere, a reuse step with no branch (unless
   `## Already satisfied` evidence exists: the agent then verifies from
   control), a branch committing ticket intent control lacks ([stranded
   ticket writes](#stranded-ticket-writes)), one held by another worktree,
   or ignored files the switch would overwrite. After switching it projects
   only this ticket from that control revision, unstaged, and records its
   blob as this worktree's publication provenance
   ([git-regressions](../../coga/internals/git-regressions/SKILL.md#the-provenance-check)).
   That projected ticket is the session's only entry dirt.
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
   ([sweep](../../coga/internals/state-publication/sweep/SKILL.md#recovering-a-failed-publication)).
   After a `sync refused` (control's ticket changed meanwhile), preserve the
   handoff and reconcile it onto control's copy
   ([reconciliation](reconciliation/SKILL.md)). An unused prepared branch
   needs no commit or PR when the work proves already satisfied.

A control step sees `main`; publication (`coga open-pr`) reads and pushes the
branch by name from there. A step that must exceptionally change code from
control — a docs publication fix — follows the [manual procedure](manual/SKILL.md). A
preparation failure exits 75 naming the stage and where the checkout stands;
it withholds the sweep, never rolls back, and keeps the reservation so the
next launch retries the same branch name. A recorded `worktree:` (a sandbox
clone) keeps this primary on control and names the clone, which must exist on
the recorded branch; see [sandbox-clone](sandbox-clone/SKILL.md), which also
owns the first sandbox refusal after launch switched.

### Manual or API sessions, megalaunch picks, and exempt checkouts

Without the witness, and before editing in a manual-policy step, the agent
performs the start check, branch work, and end-of-step return itself, and
publishes its pre-branch ticket edits explicitly:
[dev/checkouts/manual](manual/SKILL.md).

The recorded human assist keeps its own rules: it runs on its recorded PR
branch in that checkout under
[coga/internals/human-assist](../../coga/internals/human-assist/SKILL.md).

### Direct chat

`coga chat` starts on a clean, current `main` and may stay discussion-only.
Before its first edit the agent runs the exact `coga run prepare-checkout
--session <id>` its notice names, which creates or reuses that chat's one
branch through the same mechanics; launch returns the checkout when the chat
ends. The contract is [dev/checkouts/chat](chat/SKILL.md).

**Launch never changes directory.** `repl_supervisor.run_with_done_marker`
takes no `cwd` and `src/coga/` has no `os.chdir`: the session inherits the
cwd `coga launch` was typed in, and the launch boundary moves only that
checkout's HEAD. It never follows a recorded `worktree:`.

## Which checkout you invoke Coga from

- **Mutating commands publish from wherever they run.** The exit sweep
  (`sync_coga_state`) publishes every dirty file under the Coga roots, plus
  eligible committed state there (only routine task, log, and recurring
  state from a feature branch), to control, even after a config failure.
  Write deliberate ticket prose and knowledge edits on `main`; commit a
  knowledge edit that belongs to a code PR before running a sweeping command
  on its branch. Committing does not hold back recurring templates: committed
  `coga/recurring/` changes on a feature branch are adopted onto control by the
  next sweep (for example a `coga create` there), ahead of the code PR they
  depend on, and every later command on the branch re-adopts them, so a revert
  on control does not stick. This shipped `scope: clone` templates to main
  before the runner understood `scope:`. Make a template change that depends on
  unmerged code also work under the current control code (that fix made the
  `ticket.py` shims bump `COGA_TASK_SLUG` when set, so old code ran them as
  one-step periods), or keep the edit out of the Coga roots until the code
  lands. Leaving it uncommitted is not enough: the sweep publishes every dirty
  file there too. Which
  invocations sweep is owned by
  [coga/sync](../../coga/sync/SKILL.md).
- **`coga launch <target> --prompt-report` writes.** It sweeps like any launch
  and regenerates `.agent-skills/`. For a write-free view call
  `compose.compose_prompt_report` or `compose.compose_prompt` directly.
- **Launch and megalaunch compose from the invoking checkout.** An ordinary
  ticket launch or direct chat/orientation brings it to a fresh control checkout first (the [launch
  boundary](launch-boundary/SKILL.md)). Run megalaunch and exempt launches only from a control
  checkout freshly synced to `origin/<control>`; a stale one re-dispatches
  merged work.

## Stranded ticket writes

A ticket write committed on the feature branch strands there: control keeps
rewriting the same file at every transition. `open-pr`'s freshness gate
refuses it and `bump` warns about it on stderr. In a sandbox clone an
uncommitted ticket edit surfaces as `coga open-pr`'s "Recorded worktree has
uncommitted changes" refusal, which names this ticket's file separately.
The comparison is one-directional; a branch copy control already absorbed is
silent.

Decision (2026-10-06, owner): do not add a general cross-checkout detector for
uncommitted blackboard prose. The remaining working-memory loss is rare and
low stakes; missing checkout pointers, independent clones, detached worktrees,
and normal control-ahead divergence make reliable detection disproportionate.
Revisit if concrete lost-note incidents justify the complexity. Any future
comparison should report content the control copy lacks, without automatically
merging or overwriting either copy.

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
