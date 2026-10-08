---
name: coga/internals/git-refresh
description: How a checkout is brought level with the control branch — `git.refresh`, `fast_forward_control`, `fetch_control` — plus the read-only staleness probe behind `coga status` and the stranded-ticket-write detection used by `coga bump` and `coga open-pr`.
---

# Refreshing from control, staleness, and stranded writes

Publishing is [`coga/internals/state-publication`](../state-publication/SKILL.md);
this page is the inbound direction. State sync never copies control's Coga
state into a feature checkout: only the local control branch moves, by
fast-forward, or by *realignment* when its own local-only commits are proven
to be Coga state control already carries. Realignment never stashes,
rebases, resets hard, commits, or pushes.

## The realignment proof — `_local_control_subsumed(cfg, root, local, target)`

One deterministic guard shared by `fast_forward_control` and
`prepare_control_checkout`. Its frozen result has a `kind`, a `reason`,
`blocking` paths, the `dropped` commits (ID and subject), and the
`evidence` the verdict was decided from. It returns `ok` only when:

- `git merge-base --all local target` yields exactly one base;
- every commit in `target..local`, checked on its own (merges against every
  parent, renames off), touches only the Coga roots (`git.coga_root_paths`:
  the Coga root and the contexts root) — a commit that touched code and a
  later one that reverted it still fails;
- every path in the net `base..local` diff is already on `target`: same
  existence, mode, and bytes, or for a `merge=union` path, union-merging the
  local copy onto `target` with the merge base as the three-way base changes
  nothing.

`foreign` names the non-state commits and paths; `unpublished` lists each
state path whose content is not yet on control; `unproven` covers zero or
several merge bases, a symlink or submodule entry, and any failed Git probe,
naming what failed. Only `ok` permits a move; everything else fails closed.

## `fast_forward_control(cfg, root, new, *, staged=None)`

The only code that moves the local control ref, used after a publish and
inside `refresh`.

- Ancestry is checked first. When local control is ahead or diverged, the
  invoking checkout is first checked for an in-progress merge, rebase,
  cherry-pick, revert, or bisect (the same markers preparation uses); one
  present, or a failed inspection, returns `False` with a finish-or-abort
  note before anything is staged, written, or moved. Then the realignment
  proof runs:
  - `ok` with this checkout holding control: the staging below, then
    `read-tree -m -u HEAD <new>` (refuses on conflicting dirty files) and an
    old-value-guarded `update-ref`. With no holder: the guarded `update-ref`
    alone. One stderr line names the dropped commits and says they remain in
    the reflog. Returns `True`.
  - `ok` with control held by another worktree: left alone with a note.
  - `foreign`: left alone; the note names the commits and
    `git pull --rebase --autostash <remote> <control>` and push.
  - `unpublished`: left alone; the note lists the paths and suggests
    `git pull --rebase --autostash <remote> <control>` on control, then
    retrying the command, whose sweep publishes the rebased state.
  - `unproven`: left alone; the note says what could not be proved, with no
    rebase prescribed.
- When this checkout holds the branch, each just-published file still equal
  to the bytes `publish` read is written to its landed bytes (the union result
  for the log) and staged, so the move is not refused by the edit it carries.
  A file a peer changed meanwhile stays dirty for the next sweep.
- Another worktree holding the branch is fast-forwarded with
  `merge --ff-only` there; with no holder the ref moves by `update-ref` under
  an old-value guard.
- A `False` publish (control already held the tree) fast-forwards only the
  publishing control checkout itself, so its dirty-but-equal files come clean.

## `refresh(cfg) -> bool`

Fetches `+refs/heads/<control>:refs/remotes/<remote>/<control>`, then runs
`fast_forward_control` when HEAD is the control branch: a fast-forward, or a
realignment over local commits of state control already carries. It never
publishes: state committed by hand but missing from control is left for the
next sweep or the operator.

- `True`: level, or nothing to do — git disabled, no remote, control branch
  absent, or a **feature or detached checkout**. Those get the fetch and no
  file moves: they are stale by design for tickets other checkouts advance,
  and their own published ticket stays dirty.
- `True` as well after realigning a control checkout whose local-only
  commits the proof accepted.
- `False`: a control checkout that could not be brought level (local commits
  the proof refused, an in-progress Git operation, a holder in another
  worktree, or a dirty file control changed), or a git failure, which is
  also appended to `coga/log.md` as `refresh failed`. The reason is the
  `[git]` note already on stderr; callers point to it rather than add a
  second remedy.

`refresh` is not a readiness proof: a feature or detached checkout returns
`True` without moving. The launch checkout boundary uses the separate
`prepare_control_checkout` below.

Callers: exempt `coga launch` teardown and its between-children recheck in recurring
runs (bails when a refresh after a preceding child fails or the admitted
remote has vanished), and the recurring scan's pre-scan catch-up
(`recurring_runner`), whose stale-control path exits
`STALE_CONTROL_EXIT_CODE` (75) so the CLI sweep does not publish the state it
left dirty. Admission details are `coga/internals/recurring-admission`.

## `prepare_control_checkout(cfg, *, require_remote_control=False)`

Confined to the invoking checkout, and never implemented with
`fast_forward_control`, which may move another holder: it fetches and pins
the remote control commit, proves every change is already published Coga
state, then restores or removes those paths, switches HEAD to the control
branch, and fast-forwards it with `merge --ff-only`. When local control is
ahead or diverged, the realignment proof decides: `ok` (its evidence,
union-attribute decisions included, is part of the re-observed plan) moves
control to the pinned commit with `read-tree -m -u HEAD <pinned>` and a
guarded `update-ref` when HEAD is control, or the guarded `update-ref` then
the ordinary `switch` from another branch, naming the dropped commits on
stderr and writing nothing to `coga/log.md`; any other verdict refuses with
the diagnostics and remedy above (from a feature branch, the
`unpublished` remedy says to switch to control before pulling). The result is
`CheckoutPreparation`: `prepared`, `exempt` (Git disabled, not a checkout,
no remote, or no remote control branch unless `require_remote_control`),
`refused` (nothing but the remote-tracking ref changed), or `failed` (where
it stopped after mutation began). Its only caller is the launch checkout
boundary. The rules it enforces are owned by
[dev/checkouts](../../../dev/checkouts/SKILL.md).

`fetch_control(cfg, root)` fetches and returns the commit to read control from
(the tracking ref, or local control with no remote); megalaunch and the
recurring gate read control's exact ticket through
`tree_bytes(root, fetch_control(cfg, root), rel)`. `known_control_revision`
is the same answer without a fetch.

## Staleness warning — `stale_coga_task_rels`

`coga status` stays no-network: it compares the working tree with the local
remote-tracking ref only. A task path is stale when control's copy is further
along in status rank (`draft` < `active` < `in_progress` < `done`/`canceled`)
or, at equal rank, in step, or when control has the ticket and the checkout
does not. Any git failure returns `[]` (fail-open). The fix is to work from a
refreshed control checkout, or take control's copy with
`git checkout <remote>/<control> -- <path>`.

## Stranded ticket writes

A **stranded** write is ticket content committed on a feature branch that
control never received — distinct from ordinary staleness.
`github_preflight.stranded_task_state_paths(control_ref, branch_ref, paths,
cwd=<toplevel>)` marks a path stranded when the branch changed it since the
merge base and no commit on control's side of the fork carried the branch
tip's exact blob; a path the branch deleted is stranded while control still
has it. A bump run from a feature checkout commits there and lands identical
bytes on control, so that branch is merely behind, not stranded. `None` means
unknown; callers stay silent rather than read it as "nothing stranded".

Both callers pass only the ticket they act on, never all of `tasks/**`, since
a branch may legitimately edit other tickets:

- `coga bump` (`commands/bump.py` `_warn_stranded_task_state`) warns on
  stderr, one step early, when the ticket's recorded `## Dev` branch is not
  the current checkout.
- `coga open-pr` uses it to word its freshness refusal: inspect a stranded
  copy before dropping it, or drop a copy control already absorbed, then bring
  control in with a merge rather than a rebase (`coga/internals/pr-publication`).
