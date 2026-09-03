---
slug: cloning-a-coga-repo-has-no-setup-path
title: Cloning a coga repo has no setup path
status: draft
owner: nicktoper
human: nick
agent: claude
assignee: claude
contexts:
  - coga/cli
  - coga/codebase
skills: []
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
secrets: null
step: 1 (implement)
---

## Description

Cloning a repo that already has Coga committed leaves you with no supported way
to set the machine-local half up. `coga init` is the only command that writes
any of it, and it refuses an already-initialized repo before it ever looks at
`--user`.

Reproduced on a fresh clone of a separate repo (`multiply`), on coga 0.3.1:

```
$ coga ticket v1/updater/2-binary-hosting
No `user` set in coga.local.toml — coga needs your name and will not guess it.
Add `user = "<name>"` to .../coga/coga.local.toml (for example, `user = "marc"`);
the file is gitignored, so every teammate's clone sets its own. For a fresh repo
that has not been initialized yet, run `coga init --user <name>`.

$ coga init --user nicktoper
.../coga already exists — this repo is already initialized.
To upgrade the CLI, use the installer that owns it: `uv tool upgrade coga` ...
If .../coga is broken or partial, fix the cause or remove the dir, then re-run
`coga init`.
To remove Coga from this repo entirely, run `coga uninstall` from inside ...
```

The `--user nicktoper` was accepted by the parser and silently dropped. The
only working remedy is to hand-write a gitignored file that no command
mentions as *the* answer for an already-initialized repo.

Make `coga init --user NAME` idempotent for exactly this case: on a repo that
is already initialized, do the machine-local half and exit 0, instead of
refusing. Keep refusing everything else.

## Context

### This is already the documented intent

`_require_user_name` in `src/coga/commands/init.py` states it outright:

> `coga init --user NAME` is the one blessed way to set the name, and because
> init writes `user` before anything reads config it still works on a bare
> clone.

It does not work on a bare clone. `_do_init` checks `coga_os.exists()` and
`sys.exit(2)`s several hundred lines *before* it reaches
`_require_user_name(user)`. The docstring describes behavior the ordering
prevents. This ticket makes the code match the claim; it is not a new carve-out
in a strict refusal.

### What a clone is actually missing

Everything `coga init` writes that the coga-managed `.gitignore` blocks never
arrives with the clone. Verified on the `multiply` clone — all four absent:

| Path | Written by | Self-heals? |
| --- | --- | --- |
| `coga/coga.local.toml` | `render_local_toml` | no — hard-blocks every command reading `current_user` |
| `.claude/skills/coga`, `.codex/skills/coga` | init's agent-symlink wiring | no — agent CLIs can't see the Coga skill view |
| `coga/.agent-skills/` | init **and** `coga launch` | yes, on first launch |
| `.coga/` (vendored CLI + venv) | init's vendoring step | no, but only matters for the vendored-CLI path |

So `user` is the symptom that bites first, not the whole gap. Scope this
ticket at the three that don't self-heal, and treat `.agent-skills/` as
already covered.

`.coga/` is the one to think about rather than reflexively include. A clone
whose operator has their own `coga` (uv tool / pip) does not need the vendored
copy, and vendoring is the slowest part of init. Decide explicitly and say so
in the ticket's blackboard: either vendor it for parity with a fresh init, or
skip it and have the success message name `.coga/` as absent-by-design with
the command that would create it. Do not leave it unstated.

### Shape

In `_do_init`, the initialized-repo branch (the one that currently prints
"repo is already initialized") splits on whether the machine-local half is
present:

- **Machine-local setup missing and `--user NAME` given** — write
  `coga.local.toml` via the existing `render_local_toml`, wire the agent
  symlinks, report what was created, exit 0.
- **Machine-local setup missing and no `--user`** — fail loud, but with the
  *right* remedy: tell them to re-run with `--user NAME`. Today they get the
  upgrade/uninstall message, which is the wrong menu entirely.
- **`coga.local.toml` already has a non-empty `user`** — keep today's refusal
  verbatim. This is the genuine "you meant to upgrade the CLI" case and its
  message is correct; the existing test asserting those remedies must keep
  passing for it.

Details that decide correctness:

1. **Never overwrite an existing `coga.local.toml`.** A file with other keys
   and an empty/absent `user` must be edited in place, not replaced with the
   template — `render_local_toml` renders the whole template, so calling it on
   an existing file destroys machine-local overrides. The `multiply` case is
   file-absent, which is the easy half; the file-present-userless half is the
   one to get right.
2. **Reuse `_clean_user_name`.** It is documented as the single source of
   truth for a valid `user` value. The new path validates through it, not with
   a second rule.
3. **Symlink wiring must be idempotent** — an existing correct symlink is a
   no-op, not an error. Check the current wiring helper before assuming it is.
4. **Do not touch the committed tree.** This path writes only gitignored
   machine-local state, so it makes no commit. Fresh init commits `coga/`;
   this must not, and must not stage anything either.
5. **Leave the `coga.toml`-missing branch alone.** That refusal ("does not
   look like an initialized Coga repo") is about a broken/partial dir and is
   unrelated.

### Also fix the message that sent the operator down the dead end

`load_config` in `src/coga/config.py` ends its missing-`user` error with "For a
fresh repo that has not been initialized yet, run `coga init --user <name>`."
That sentence is what got run, twice. Once init handles the initialized case,
the qualifier is wrong — drop "that has not been initialized yet" so the
pointer is unconditional and correct for both.

The surrounding comment block in `load_config` also says existing repos
"recover by creating or editing `coga.local.toml`" — update it to name the
command.

### Considered and rejected: a separate `coga setup` verb

A distinct verb reads cleaner than overloading init, but `coga/cli` states the
posture directly: *"There is no separate `coga setup` command — initialize the
repo with `coga init`, then run `coga build`."* Adding one contradicts shipped
documentation and gives operators two spellings for one intent. Overloading
init also matches what the operator in the report actually typed. If review
disagrees, that reversal is a docs change in `coga/cli` too — not a silent
addition.

### Docs to update in the same PR

Per `CLAUDE.md`, a behavior change updates its matching context in the same PR,
and shipped contexts exist in two copies that must stay in sync.

1. `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md` —
   its `coga init` section says "fresh scaffold; refuses if `coga/` exists".
   Document the clone case and what it writes. The "no separate `coga setup`"
   line a few lines below stays, and becomes load-bearing for the rejected
   alternative above.

   Note the asymmetry with most context edits: `coga/cli` is **package-only**.
   Checked — there is no `coga/contexts/coga/cli/SKILL.md` in this repo, so the
   packaged file is the single copy and there is no mirror to keep in sync.
   Do not create a local override to edit.
2. `README.md` — check whether it has a clone/onboarding section. If it does,
   the two-step for a teammate joining an existing repo (`git clone` →
   `coga init --user NAME`) belongs there; that is the audience for this fix.

### Tests

`tests/test_init.py::test_init_refuses_existing_coga_os` currently passes
`--user tester` against a repo with a `coga.toml` and no `coga.local.toml` —
exactly the clone shape — and asserts exit 2. It must **split**, not simply
invert:

- the refusal case keeps every existing assertion, with a
  `coga.local.toml` carrying a real `user` added to the fixture;
- a new case covers the clone shape and asserts exit 0, a written
  `coga.local.toml` containing the passed name, and the symlinks.

`test_init_does_not_misidentify_unrelated_coga_path` covers the
`coga.toml`-missing branch and must keep passing unchanged.

New coverage to add: initialized repo, no `--user` → exit non-zero naming
`--user` (not the upgrade menu); existing `coga.local.toml` with other keys and
no `user` → keys preserved, `user` added; existing `coga.local.toml` with a
`user` → refused, file untouched; re-running the clone setup twice → second run
is a clean no-op.

### Verification

`python -m pytest`, `coga validate --json`, and a manual end-to-end on a real
clone: `git clone` a Coga repo into a scratch dir, `coga init --user <name>`,
then confirm a command that needs `current_user` (e.g. `coga ticket`) runs.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Open decision for the implementer

Whether `coga init` on a clone should also vendor `.coga/`. See the
"What a clone is actually missing" table — decide, implement, and record the
reason here rather than leaving it implicit.

## Origin

Reported from a live session in a separate repo (`multiply`, a fresh clone) on
coga 0.3.1. Full transcript reproduced in `## Description`. The operator's
immediate unblock was hand-writing `coga/coga.local.toml` with one `user` line.
