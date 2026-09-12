---
title: Cloning a coga repo has no setup path
status: in_progress
owner: nicktoper
agent: claude
contexts:
- coga/cli
- coga/codebase
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
step: 4 (review)
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

## Dev

pr: https://github.com/FastJVM/coga/pull/788
branch: init-clone-setup
worktree: /home/n/Code/claude/coga-init-clone-setup
(separate linked worktree off `main`; primary checkout stays on `main` and runs `coga bump`)

## Implement (step 1) — done

Commit `16e275f6` on `init-clone-setup` (rebased on `origin/main` `ffeb1e5b`,
nothing new came in).

**Decision — `.coga/` vendoring: moot, not skipped.** Current `main`'s init
installs no software ("Init installs no software" in `coga/cli`; `_do_init`
has no venv/vendoring step, only stale "slow clone/venv" comments). The
ticket's four-row table describes 0.3.1. On this tree a clone is missing
three things — `coga.local.toml`, the `.claude/.codex` skill symlinks, and
`.agent-skills/` — and the new path creates all three (`_link_skills_for_agents`
calls `refresh_agent_skill_view`, so the self-healing one is covered too).
The success message therefore does not mention `.coga/`; there is no command
that would create it.

**What changed.** `src/coga/commands/init.py`: `_do_init`'s initialized branch
now calls `_setup_initialized_clone`, which reads `coga.local.toml` through
`tomllib` (`_local_toml_user`, same non-empty test `load_config` applies) and
splits three ways — user set → refusal verbatim (`test_init_refuses_existing_coga_os`
still asserts every remedy, now with a `user` in the fixture); user unset +
`--user` → `_require_user_name` (so `_clean_user_name` is the single rule) →
`_write_local_user` (absent file: `render_local_toml`; present file: replace
the first top-level `user = ...` line or append one, preserving other keys
and comments) → `_link_skills_for_agents` (already idempotent; re-checked) →
exit 0; user unset, no `--user` → exit 2 naming `--user NAME`. An unparseable
existing `coga.local.toml` is refused, not guessed at. No git staging or
commit; `ensure_host_gitignore` deliberately not called on this path because
it can modify the tracked `.gitignore`. `coga.toml`-missing branch untouched.
`src/coga/config.py`: message now ends "Run `coga init --user <name>` to write
it."; comment names the command for both shapes.

**Docs.** Packaged `coga/cli` context `coga init` section (package-only, no
live twin — verified again), `docs/getting-started.md` "Joining a repo" (the
`echo > coga.local.toml` hack replaced by `git clone` → `coga init --user`),
`docs/reference.md` init section, README install paragraph. The "no separate
`coga setup`" line in the context is unchanged.

**Tests.** `tests/test_init.py`: refusal test split as specified plus clone
setup, idempotent rerun, no-`--user`, invalid name, in-place edit (both the
`user = ""` template shape and a file with no `user` line), unparseable file.
`tests/test_config.py::test_missing_user_fails_loud` updated to assert the
unconditional pointer and the absence of "fresh repo".

**Verification.** `PYTHONPATH=$PWD/src python3.12 -m pytest`: 2440 passed,
1 failed — `test_packaging.py::test_wheel_includes_bootstrap_batteries`, the
documented no-`hatchling` environment noise (bare python3.12); re-run with the
repo `.venv` interpreter that has hatchling: 11/11 packaging tests pass.
`coga validate --json`: 28 warnings, all pre-existing (stale in_progress,
unfrozen v2 drafts, oversized blackboards). Manual end-to-end on a real
`git clone` of this repo in the scratchpad: no `coga.local.toml`/symlinks/
`.agent-skills` → `coga create` hits the missing-user error with the new
pointer → `coga init` (no flag) exits 2 naming `--user NAME` → `coga init
--user nicktoper` exits 0, writes all three, `git status` clean,
`load_config().current_user == "nicktoper"` → rerun with any name exits 2
with the upgrade/uninstall refusal.

**For review.** Two judgment calls worth a look: (1) `_write_local_user`'s
in-place edit is a regex on the first `^user\s*=` line rather than a TOML
re-serialize — chosen to keep comments; a `user` key inside a table would not
match, which is the right outcome since `load_config` reads top-level `user`.
(2) On the clone path a `--user` that is *given* when `user` is already set is
refused rather than treated as "change my name" — the ticket asked for the
refusal verbatim and the file untouched; editing `coga.local.toml` by hand
remains the way to rename.

## Peer review

`codex review --base main` **returned** (exit 0) from the recorded feature
worktree. It found two P2 issues: the regex editor corrupts valid TOML or sets
`user` inside a table, and persisting the name before skill wiring makes a
failed/interrupted setup refuse retries. Independent reproductions confirmed
both. No design reversal was needed.

The attending human approved TOMLKit as a runtime dependency. The corrections
use it to edit only the root `user`, preserve nested keys/comments, and check
the rendered TOML with `tomllib` before writing. Skill wiring now precedes the
config write; exceptions and obstructed links leave the previous config intact
and permit a retry after repair. Regression coverage includes varied TOML key
spellings, multiline values, interrupts, partial wiring, and a real clone with
unrelated staged/unstaged work. The packaged CLI context (no live twin) and
getting-started guide document the recovery behavior.

`git fetch origin main` and `git rebase FETCH_HEAD` completed without conflicts
onto `48083942`; implementation commit is now `e110359e`. Review fixes are in
commit `237aadd5` (`peer-review: preserve clone config and allow setup retries`).
The final fetch/rebase found no newer base changes. The feature branch is clean
with two product commits ahead of `main`.

**Verification:**

- `PYTHONPATH=/home/n/Code/claude/coga-init-clone-setup/src /home/n/Code/claude/coga/.venv/bin/python -m pytest -q` — **2457 passed**, including all packaging checks. Initial failures were two incomplete new agent fixtures (missing required `file`), corrected before this passing run.
- `PYTHONPATH=/home/n/Code/claude/coga-init-clone-setup/src /home/n/Code/claude/coga/.venv/bin/python -m coga.cli validate --json` — 5 errors and 23 warnings. Re-running the same validator against the same feature-worktree task files with `PYTHONPATH=/home/n/Code/claude/coga/src` produced the identical `(kind, task, severity)` set: pre-existing missing `coga/digest/flush`, four unsynthesized v2 draft blackboards, and existing warnings. No task-model regression.
- `PYTHONPATH=/home/n/Code/claude/coga-init-clone-setup/src /home/n/Code/claude/coga/.venv/bin/python -m coga.cli validate --task cloning-a-coga-repo-has-no-setup-path --json` from the primary checkout — clean.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/n/Code/claude/coga-init-clone-setup/src /home/n/Code/claude/coga/.venv/bin/python /tmp/coga_clone_setup_e2e.py` — passed on real clone `/tmp/coga-clone-setup-e2e-74k90o09/clone`: missing-name remedy, setup, correct agent links, unchanged HEAD/index and clean working tree after init, unchanged repeat refusal, then `coga create` produced a draft owned by `clone-check`. All Git publication used a disposable local bare remote.
- `git diff --check` — clean. Packaged `coga/cli` still has no live twin; no override was created.

## PR

Cloning a repo with committed Coga files now has a supported setup path:
`coga init --user NAME` creates the gitignored local config, generated skill
view, and Claude Code/Codex discovery links without staging or committing
project files. TOMLKit preserves existing settings and comments when adding the
root user. Skill wiring completes before saving the name, so failed or
interrupted setup can be retried after repair. Repos that already name a user
keep the existing refusal and upgrade remedies.

Updates the missing-user diagnostic, README, getting-started guide, reference,
and packaged CLI context. Adds coverage for clone setup, TOML preservation,
retry behavior, and unchanged Git state with unrelated work staged.

Test plan: `PYTHONPATH=/home/n/Code/claude/coga-init-clone-setup/src /home/n/Code/claude/coga/.venv/bin/python -m pytest -q` (2457 passed); `PYTHONPATH=/home/n/Code/claude/coga-init-clone-setup/src /home/n/Code/claude/coga/.venv/bin/python -m coga.cli validate --task cloning-a-coga-repo-has-no-setup-path --json` (clean, primary checkout); `PYTHONPATH=/home/n/Code/claude/coga-init-clone-setup/src /home/n/Code/claude/coga/.venv/bin/python -m coga.cli validate --json` (5 existing errors/23 warnings, identical to main); real-clone `coga init --user clone-check` then `coga create "Clone setup smoke check"` (passed).

## Origin

Reported from a live session in a separate repo (`multiply`, a fresh clone) on
coga 0.3.1. Full transcript reproduced in `## Description`. The operator's
immediate unblock was hand-writing `coga/coga.local.toml` with one `user` line.
