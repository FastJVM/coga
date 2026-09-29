# `coga/tasks/_v2/` — the v2 wish list

A parked directory (see `coga/tickets`): Coga never lists, launches,
validates, or scans anything here. `ls` and git are the way to browse it.

## What this is

A wish list of things someone wanted at some point, not a backlog. Each file
is a dated wish, not a spec. Files may be stale, name surfaces that no longer
exist, or contradict each other and `main` — that is fine. Nobody reconciles,
adjudicates, or cancels them while they sit here, and no verdict is ever due.
Do not "fix" a draft here to match the current repo.

Capture a wish with `coga create "_v2/<title>"`; a bare title is enough, and
`--description` is optional. Delete a wish that is no longer wanted with
`git rm`.

## Pulling a wish forward

Only through an explicit human decision. Then:

1. Run the premise check below against current `main`.
2. `git mv` the file out of `_v2/` into `coga/tasks/` (or `coga create` a
   fresh ticket that cites it), rewrite it against the current shape, and give
   it a workflow. From that point it is an ordinary ticket: it must pass
   `coga validate` and is visible to `coga status` and Dream.

### The premise check

The problem statement usually survives; the proposed implementation often
does not, because the surfaces it names keep moving. Four questions, in order:

1. **Does the subject still exist?** If what the wish asks you to build,
   document, or remove is already gone, drop it (`git rm`) instead of writing
   prose about a removed design.
2. **Do the surfaces it names still resolve?** Check every command, path, and
   field it names against current `main`, starting with the table below.
3. **Does the wish carry the substance it depends on?** A wish that points
   at another ticket's blackboard or body for its requirements may have lost
   them: that ticket can be retired and deleted. Recover the missing substance
   from git history with the
   [retired-task recipe in `coga/tickets`](../../../docs/contexts/coga/tickets/SKILL.md#where-tasks-live-and-how-they-are-named)
   (it covers the pre-rename `relay-os/tasks/` too) and inline it; never
   repoint the citation at a different live ticket. Citations kept only for
   provenance are fine.
4. **Has something else already delivered it?** Compare the target surface
   on current `main` with the wish's acceptance criterion, not its title. If
   it already ships, drop the wish; if only part shipped, pull forward only
   the remainder.

### Known-stale surfaces (the pre-rename cohort)

Most of this directory predates the `relay` → `coga` rename, and 46 of its
drafts still say `relay`. **The rename is not a find-and-replace.** Some names
carried over, some changed meaning, and some were deleted outright — so
mechanically rewriting `relay` to `coga` produces confident, wrong
instructions. Check each occurrence against this table:

| As written in a draft | Status today |
| --- | --- |
| `src/relay/` | Renamed — now `src/coga/`. |
| `relay-os/contexts/…` | Renamed — now `coga/contexts/…`. |
| `relay-os/workflows/<name>.md` | Check repo-local `coga/workflows/<name>.md` first; if absent, check `src/coga/resources/templates/coga/bootstrap/workflows/<name>.md`. This repo's `code/*` workflows are packaged-only: `coga/workflows/code/` does not exist. |
| `relay launch`, `relay recurring`, `relay status`, `relay bump` | Renamed — the `coga` equivalents exist. |
| `relay draft` | **Gone.** Ticket creation is `coga create` (raw draft) or `coga ticket` (authoring skill). |
| `relay panic` | **Replaced.** Use `coga block --task <slug> --reason "…"` for unresolved input; it records the ask, marks the task blocked, notifies the owner, and ends the session. |
| `mode:` ticket frontmatter (`script` / `auto` / `interactive`) | **Gone.** There is no `mode` or `recipe:` field. A directory-form ticket's exact sibling `ticket.py` is its headless deterministic half; without that file, launch selects the agent path. See `coga/script-tickets`. |
| Child `mode: script` tasks driven by a parent task | **Gone.** Put a ticket-owned deterministic phase in that selected ticket's exact sibling `ticket.py`, or invoke a stable package command explicitly through `coga run`; do not rebuild child-task mode orchestration. |
| `[secrets]` bulk-inject config block | **Gone.** Secrets are per-ticket `secrets:` frontmatter holding `op://vault/item/field` refs; see `coga/secrets`. |

This table is a starting point, not a guarantee of completeness — it was built
from the surfaces actually present in these drafts as of 2026-08-13. Treat any
other `relay`-era name the same way: verify it against `main` before acting on
it.
