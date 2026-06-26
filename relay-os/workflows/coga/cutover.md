---
name: coga/cutover
description: Post-merge cutover from the `relay` CLI to `coga` after the rename PR (#454) lands. Owner reinstalls + switches every invocation to `coga`, an agent verifies no `relay-os/` resurrected and the suite is green, then the owner closes the rename ticket and fans out to the sibling branches + host-repo migration.
steps:
  - name: cutover
    assignee: owner
  - name: verify
    assignee: agent
  - name: fan-out
    assignee: owner
---

## cutover

Cut every actor that runs the CLI over to `coga`. Order matters — a
pre-rename `relay` push between the merge and the reinstall re-creates a
stray `relay-os/` on the fresh `coga` main.

- Pull the renamed `main`, then reinstall so the `coga` command exists:
  `pip install -e .` (editable) or `pipx install --force .`. The old
  `relay` console script `ImportError`s after the pull — its `src/relay`
  target is gone — which is the forcing function to reinstall.
- Switch every `relay …` invocation to `coga …`: the `relay()` shell
  function wrapper in your shell profile (rename it to `coga()` or delete
  it), plus any scripts, recurring-job triggers, and aliases.
- Every machine/person that runs the CLI (you, Nick, any other host) does
  the same pull + reinstall + invocation switch. There is no central
  registry — it is per-checkout.
- Until everyone has reinstalled, nobody launches or bumps with the old
  `relay`. Once you have reinstalled, use `coga` for everything from here;
  finish this step with `coga bump <slug>`.

## verify

Confirm the cutover is clean, then hand back to the owner.

- `coga --help` works and the old `relay` command is gone/reinstalled.
- `main` contains only `coga/` — no `relay-os/` resurrected
  (`git ls-files | grep -c '^relay-os/'` returns 0).
- Full suite green (`python -m pytest`).
- Write the results to the blackboard, then `coga bump <slug>`. If
  `relay-os/` came back or the suite fails, `coga panic` with the
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
