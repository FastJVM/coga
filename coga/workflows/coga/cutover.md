---
name: coga/cutover
description: Post-merge cutover from the `relay` CLI to `coga` after the rename PR (#454) lands. Owner reinstalls + switches every invocation to `coga`, an agent verifies no `relay-os/` resurrected and the suite is green, then the owner closes the rename ticket and fans out to the sibling branches + host-repo migration.
steps:
  - name: cutover
    assignee: agent
  - name: verify
    assignee: agent
  - name: fan-out
    assignee: owner
---

## cutover

Cut every actor that runs the CLI over to `coga`. Order matters — a
pre-rename `relay` push between the merge and the reinstall re-creates a
stray `relay-os/` on the fresh `coga` main.

Drive this interactively with the present human: the reinstall and shell
changes happen on their machine(s), so walk them through each action and
confirm it's done rather than running it yourself. Bump only once they
confirm every checkout is reinstalled and on `coga`.

- Pull the renamed `main`, then reinstall so the `coga` command exists:
  `pip install -e .` (editable) or `pipx install --force .`. The old
  `relay` console script `ImportError`s after the pull — its `src/relay`
  target is gone — which is the forcing function to reinstall.
- Switch every `relay …` invocation to `coga …`: the `relay()` shell
  function wrapper in your shell profile (rename it to `coga()` or delete
  it), plus any scripts, recurring-job triggers, and aliases.
- **Coordinate every other host before bumping** — there is no central
  registry, so each machine cuts over itself. For the boss (Nick) and any
  other host that runs the CLI, run this handshake and don't proceed until
  it closes:
  1. Ping them that `main` is renamed and the old `relay` is now dead.
  2. They `git pull` the renamed `main`, reinstall (`pip install -e .` or
     `pipx install --force .`), and rename/delete their `relay()` shell
     wrapper.
  3. They confirm back that `coga --help` works and `relay` is gone.
  4. Mark that host done on the blackboard.
- Nobody launches or bumps with the old `relay` until every host has
  confirmed — a stray pre-rename push resurrects `relay-os/`. Once you've
  reinstalled, use `coga` for everything here; `coga bump <slug>` only
  after you and Nick (and any other host) have each confirmed.

## verify

Confirm the cutover is clean, then hand back to the owner.

- `coga --help` works and the old `relay` command is gone/reinstalled.
- `main` contains only `coga/` — no `relay-os/` resurrected
  (`git ls-files | grep -c '^relay-os/'` returns 0).
- Full suite green (`python -m pytest`).
- Write the results to the blackboard, then `coga bump <slug>`. If
  `relay-os/` came back or the suite fails, `coga block` with the
  specifics instead of bumping.

## fan-out

Owner wraps up the transition.

- `coga mark done rename-relay-to-coga` — close the rename ticket with the
  new CLI.
- Rebase/merge the ~15 sibling worktree branches (`relay-ci`, `relay-pkg`,
  `relay-init`, `remove-shim-concept`, …) onto the renamed `main`; each
  conflicts across the whole rename surface.
- Kick off the host-repo migration: the ~8–10 Desktop repos still on
  `relay-os/` + `relay.toml` (the `migrate-to-coga.sh` work tracked in
  `coga-rename-follow-ups-post-repo-rename`).
- `coga mark done <slug>` this ticket when the transition is complete.
