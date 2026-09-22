---
name: coga/internals/git-refresh
description: How a checkout is brought level with the control branch — `git.refresh`, `fast_forward_control`, `fetch_control` — plus the read-only staleness probe behind `coga status` and the stranded-ticket-write detection used by `coga bump` and `coga open-pr`.
---

# Refreshing from control, staleness, and stranded writes

Publishing is [`coga/internals/state-publication`](../state-publication/SKILL.md);
this page is the inbound direction. State sync never copies control's Coga
state into a feature checkout: only the local control branch moves, and only
by fast-forward.

## `fast_forward_control(cfg, root, new, *, staged=None)`

The only code that moves the local control ref, used after a publish and
inside `refresh`.

- Ancestry is checked first. A local control that is ahead or diverged
  (unpushed human commits) is left alone, nothing is staged, and one stderr
  line names `git pull --rebase <remote> <control>`. Returns `False`.
- When this checkout holds the branch, each just-published file still equal
  to the bytes `publish` read is written to its landed bytes (the union result
  for the log) and staged, so `merge --ff-only` is not refused by the edit it
  carries. A file a peer changed meanwhile stays dirty for the next sweep.
- Another worktree holding the branch is fast-forwarded with
  `merge --ff-only` there; with no holder the ref moves by `update-ref` under
  an old-value guard.
- A `False` publish (control already held the tree) fast-forwards only the
  publishing control checkout itself, so its dirty-but-equal files come clean.

## `refresh(cfg) -> bool`

Fetches `+refs/heads/<control>:refs/remotes/<remote>/<control>`, then
fast-forwards when HEAD is the control branch.

- `True`: level, or nothing to do — git disabled, no remote, control branch
  absent, or a **feature or detached checkout**. Those get the fetch and no
  file moves: they are stale by design for tickets other checkouts advance,
  and their own published ticket stays dirty.
- `False`: a control checkout that could not be brought level (ahead,
  diverged, or blocked by a dirty file control changed), or a git failure,
  which is also appended to `coga/log.md` as `refresh failed`.

Callers: `coga launch` teardown and its between-children recheck in recurring
runs (bails when a refresh after a preceding child fails or the admitted
remote has vanished), and the recurring scan's pre-scan catch-up
(`recurring_runner`), whose stale-control path exits
`STALE_CONTROL_EXIT_CODE` (75) so the CLI sweep does not publish the state it
left dirty. Admission details are `coga/internals/recurring-admission`.

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
