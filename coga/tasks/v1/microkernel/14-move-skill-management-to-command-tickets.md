---
title: Move skill management to command tickets
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
    checkout: control
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
    checkout: control
  - name: review-design
    skills: []
    assignee: owner
    checkout: control
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 3 (review-design)
agent: claude
contexts:
- coga-dev/microkernel
- coga-dev/packaging
- coga-dev/testing
- coga/skill-management
- coga/script-tickets
---

## Description

Move the whole `coga skill` command family out of core into one editable
stateless command ticket, so a repo can change how skills are installed,
updated and reported by editing that ticket. Today the procedure lives in
`src/coga/commands/skill.py` (211 lines, six Typer subcommands) and
`src/coga/skill_manager.py` (2,123 lines). Only three small pieces have a
second core consumer. This is the skill increment split out of
`v1/microkernel/08-residual-command-surfaces`; its "Skill increment" section is
reference material, and this ticket supersedes it where they differ.

Done means: `coga skill install|install-local|install-url|update|remove` and
`coga skill-status` run from `bootstrap/skill-manage/`, with unchanged
results apart from the deliberate differences listed below. The weekly
`skill-update` reporting job still drives the real public updater. Core keeps
only the shared roots, the protected branch contract and the patch-ID helper.

### Owner decisions (2026-11-17, attended design session)

- **Read spelling: `coga skill-status`.** This follows the `fork`/`fork-copy`
  pattern (PR #1239): one bootstrap directory, two default aliases, and each
  alias fixes its dispatch policy and first operand. `coga skill status` is
  retired; no core `skill` adapter is kept.
- **Ref: `bootstrap/skill-manage`.** The name stays distinct from the
  `bootstrap/skills/` library and from `coga/skills/`.
- **Shared fork behavior (follows from the above).** Status and the writers
  live in the same directory and share the same `skill_manager.py`. Copying
  that one directory forks both, and a local fork can never pair stock status
  with forked update classification. No cross-ticket resolution, read-entry
  discovery or fallback to stock code is needed. The 08 design's separate
  `bootstrap/skill-status` ticket and its "resolve the effective writer
  directory" mechanism are dropped.

### Proposed shape

Package paths are relative to `src/coga/resources/templates/coga/`.

1. **Extract shared core first (no behavior change):**
   - Move `skill_manager.skills_root` and `bundled_skills_root` to
     `src/coga/paths.py`. `validate._check_shebang_executables` imports them
     from there (it lists both roots in its scan), and the moved manager does
     the same.
   - Move `skill_manager.SKILL_UPDATE_BRANCH` into `src/coga/branchsweep.py`,
     which already protects it in candidate classification and ref handling.
     Rename `branchsweep._verbatim_patch_ids` to public `verbatim_patch_ids`
     and update its two branchsweep callers. Delete the lazy-import wrapper
     `skill_manager._verbatim_patch_ids`, whose comment explains it was only
     there to break the branchsweep↔skill_manager cycle. With the manager gone
     from core, the cycle disappears.
   - Expose `git._git_env` publicly (for example `git.git_env`, keeping the
     private name as an alias or updating its core callers). The edge manager
     must not import a private core symbol (`skill_manager.run_subprocess`
     uses it for git child processes).
2. **Create `bootstrap/skill-manage/`:**
   - `skill_manager.py`: the current `skill_manager.py`, minus the extracted
     symbols, importing them from shared core. It imports only stdlib,
     third-party dependencies already declared by the package, and `coga.*`;
     never `coga.commands.*`, `coga_edge.*` or relative imports.
   - `ticket.py`: entry point with `main(argv)` and a `__main__` guard. It
     imports its sibling as `from skill_manager import ...`, as
     `recurring-promote/ticket.py` imports `promotion`. Six subcommands carry
     today's arguments, options, help and messages from `commands/skill.py`:
     `install`, `install-local`, `install-url`, `update` and `remove` (writers)
     and `status` (reader). Writers load config with `require_user=True` and
     the reader with `require_user=False`, as today. `SkillManagerError` still
     prints red on stderr and exits 2. For the exit-75 change, see
     "Deliberate differences".
   - `ticket.md`: the command contract owner. It covers the two aliases and
     why there are two, every subcommand and its exit codes, `--json`
     stdout-only output, the publication behavior of writers versus the
     reader, and the deliberate differences. It also explains customization:
     copy the whole directory (`ticket.md`, `ticket.py`, `skill_manager.py`)
     to `coga/bootstrap/skill-manage/`. That fork governs both aliases and is
     not updated by wheel upgrades; deleting it returns to stock. It names the
     `skill-update` job as a consumer of `skill update --all --json [--pr]`.
3. **Wire the default aliases in `src/coga/aliases.py`:**
   - `"skill": "launch bootstrap/skill-manage --"`
   - `"skill-status": "launch --read-only bootstrap/skill-manage -- status"`

   Remove `"skill"` from `BUILTIN_COMMANDS`, and extend the alias comment the
   way the `fork`/`fork-copy` comment does.
4. **Delete the core head:**
   - `src/coga/commands/skill.py`;
   - the `skill` entries in `cli._LAZY_COMMANDS` and `cli._GROUP_COMMANDS`;
   - `cli._SWEEPING_SKILL_SUBCOMMANDS` and the `command == "skill"` branch in
     `cli._should_sweep_coga_state`. Writers are now `launch` invocations and
     sweep as launch does; `--read-only` launch never sweeps.
   - `src/coga/skill_manager.py`.

   Leave no forwarding stub.
5. **Writer guard on `status`.** The writer path (ordinary launch) refuses
   `status` before loading config, exiting 2 with
   `use \`coga skill-status\``. Status run under ordinary launch would need a
   user and would sweep and audit, which breaks the read contract. The reader
   operand is reachable only through the `skill-status` alias or an explicit
   `launch --read-only bootstrap/skill-manage -- status`. The read-only alias
   fixes `status` as the first operand, so writer operands cannot reach a
   read-only invocation through the default spelling. A user who
   hand-types `launch --read-only bootstrap/skill-manage -- install ...` gets
   an unpublished local write. That is the cooperative contract of the launch
   topic's "Read-only command dispatch", the same as for `fork`, and
   `ticket.md` states it. `ticket.py` cannot detect its dispatch policy.
   Do not add an environment signal for it in this ticket.
6. **Exit 75 for the branch-claim refusal.** Today `commands.skill.update`
   sets `git.state_sweep_withheld` in-process when
   `assert_skill_update_branch_unclaimed` refuses. A ContextVar cannot cross
   the launch→script process boundary, so `ticket.py` must exit
   `git.RETRY_WITHOUT_SWEEP_EXIT_CODE` (75) for that refusal. Launch then
   skips teardown refresh and the end-of-command sweep. The local-dirt
   preflight `assert_skill_update_pr_preflight` and other
   `SkillManagerError`s stay at exit 2 with the ordinary sweep, as today.
7. **Reporting job (`src/coga/skill_update.py`, `runner.RECIPES["skill-update"]`)
   stays in core.** Its migration belongs to
   `v1/microkernel/04b-move-blocker-reminders-and-skill-update-to-the`.
   `build_update_command` keeps the same argv,
   `[sys.executable, "-m", "coga.cli", "skill", "update", "--all", "--json", ...]`,
   which now expands through the `skill` alias into a nested ordinary
   `coga launch bootstrap/skill-manage` inside the period's script phase.
   No core module imports or path-loads the moved code. An inner exit 75
   (branch-claim refusal) stays an ordinary failure under
   `run_update_json`'s non-zero rule. The refusal precedes every mutation, so
   no local state is retained, and the period's failure report should still
   publish. Keep the job's 0/1/2 contract and structured failures.
8. **Docs, in the same PR.** In the package user topic
   `coga/skill-management`, change the command section to the new spellings,
   link `bootstrap/skill-manage/ticket.md` as the owner of the command
   contract, and summarize rather than restate it. In the `coga/cli` index,
   replace the `skill` row with the two aliases. Fix every other live
   `coga skill status` reference: the bundled skills
   `bootstrap/skills/bootstrap/{skill-update,import,dream/scan/contract-audit,dream/scan/knowledge-scan}`,
   `bootstrap/workflows/skill-update/run.md` and
   `recurring/skill-update/ticket.md`, plus local
   `docs/contexts/coga-dev/codebase/SKILL.md`,
   `docs/contexts/coga-dev/codebase/gotchas/SKILL.md` and
   `docs/contexts/coga-dev/packaging/SKILL.md` as they apply. In local
   `coga-dev/microkernel`, close the `skill *` row of "Open command
   placements" with the receipt. Do not edit `docs/archive/**`.
9. **Tests and packaging.**
   - Add the three resources to `tests/required_package_resources.txt`. Add
     no live local copy to this repo.
   - Carry `tests/test_skill_manager.py` forward. Load the moved manager under
     one module identity that the in-process `ticket.py` entry also uses, so
     the existing roughly 200 monkeypatches still apply. For example, a
     fixture can register the sibling directory on `sys.path` and import
     `skill_manager`, then load `ticket.py` with
     `importlib.util.spec_from_file_location` under a unique name. Compare
     `tests/report_helpers.py` on the PR #1240 branch.
   - Replace in-process `CliRunner(app, ["skill", ...])` calls with the
     loaded `main(argv)`, keeping a handful of real subprocess alias-path
     tests.
   - Update `tests/test_cli.py`, which invokes `["skill", "status"]`, and
     `tests/test_branchsweep.py`, `tests/test_validate.py` and
     `tests/test_aliases.py` for the moved symbols, aliases and built-ins.

### Deliberate user-visible differences

1. `coga skill status [--check] [--json]` becomes `coga skill-status
   [--check] [--json]`. `coga skill status` exits 2 and names the new
   spelling. Status output, JSON fields and exit codes are otherwise
   unchanged.
2. Each writer invocation is an ordinary bootstrap-script launch. It
   publishes the `launched as a script (ticket.py)` and `script exited with
   code N` audit lines in `coga/log.md`, and stderr carries the
   `→ coga launch bootstrap/skill-manage -- ...` alias framing. The same
   applies to the weekly reporting job's nested call.
3. The `--pr` branch-claim refusal exits 75 instead of 2. Its sweep is
   still withheld.
4. A global `--agent` given before `skill` reaches generic launch handling
   for a script target, as for `retire` and `promote-recurring`. There is no
   skill-specific refusal.

### Acceptance criteria

- [ ] `src/coga/commands/skill.py` and `src/coga/skill_manager.py` are gone.
      No core module imports, path-loads or forwards to
      `bootstrap/skill-manage`. `cli.py` has no `skill` head, group entry or
      skill-specific sweep rule, and `aliases.BUILTIN_COMMANDS` has no
      `skill`.
- [ ] `paths.skills_root`/`bundled_skills_root`,
      `branchsweep.SKILL_UPDATE_BRANCH`, `branchsweep.verbatim_patch_ids` and a
      public git environment helper each have both their core consumer and the
      edge manager as callers. The edge files import no private (`_`-prefixed)
      `coga` symbol.
- [ ] The default aliases are `skill` → `launch bootstrap/skill-manage --` and
      `skill-status` → `launch --read-only bootstrap/skill-manage -- status`;
      `coga --help` lists both.
- [ ] Every existing `test_skill_manager` behavior still passes against the
      moved code: GitHub, URL, local and unmanaged/bundled outcomes; the
      include allowlist and pruning; source and installed digests and legacy
      repair; local adaptation and conflict classification; `--force`;
      notes; metadata-only changes; exact refs and namespace collisions; the
      gh capability preflight before writes; refusal of nested GitHub refs;
      and every JSON field and status meaning for both update and status.
- [ ] `--pr` guards keep their tests: local staged, unstaged and untracked
      preflight; a clean skills baseline; hand-pushed open-PR commit
      protection against the real push destination with ancestry and
      whitespace-sensitive patch checks; the observed remote head carried into
      the push lease; skills-only commit; original branch restored in
      `finally`; verification capture; and draft PR create/update.
- [ ] Through the real alias and launch subprocess path: (a) `coga
      skill-status --json` with no configured user, no agent and no TTY, on a
      dirty tree, prints only JSON on stdout. It leaves `git status`,
      `coga/log.md` and HEAD unchanged. (b) `coga skill status` exits 2 with
      the pointer and writes nothing. (c) One writer (`remove` or
      `install-local`) publishes its change under ordinary launch. (d) A
      branch-claim refusal exits 75 and leaves pre-existing dirt unpublished.
- [ ] The `skill-update` recurring job's `run_update_json`, run against the
      real alias path in a temp repo, gets stdout JSON its parser accepts. The
      expected launch audit lines appear in the log, and an inner refusal maps
      to the job's existing failure result.
- [ ] Local fork: an edited complete copy at `coga/bootstrap/skill-manage/`
      governs both `coga skill` and `coga skill-status` from an installed
      wheel with package resources read-only. Removing it returns to stock.
      Extend `tests/test_packaging.py` the way the promotion and report
      tickets did.
- [ ] Docs are updated as in "Proposed shape" step 8. No live
      `coga skill status` remains outside `docs/archive/**`. `coga validate
      --json` is clean.
- [ ] Verification follows `coga-dev/testing`: affected tests, the full Linux
      suite, a CLI smoke check and task validation. Receipts give the full
      revision, OS/Python, command, counts and runtime. Windows and macOS are
      deferred to release.
- [ ] The blackboard records before/after physical line counts (core, ticket
      Python, tests, docs) at named revisions. Baseline: main `00fb27186`,
      `commands/skill.py` 211 + `skill_manager.py` 2,123 = 2,334 core lines
      in scope; `skill_update.py` (434) is not counted.

### Out of scope

- Moving the reporting job (`skill_update.py`, the `skill-update` recipe):
  owned by `04b`.
- New skill sources, changes to `gh skill` overwrite policy, a plugin system,
  nested alias machinery, and an environment signal for read-only dispatch.
- A core `skill` adapter that keeps the old spelling.
- `coga fork`/`fork-copy` implementation (owned by
  `v1/microkernel/12-make-packaged-behavior-discoverable-and-editable`), and
  authoring (`v1/microkernel/13-move-ticket-authoring-to-a-command-ticket`).
- Compatibility heads for `skill status`.

## Context

### Dependencies

- `v1/microkernel/03-launch-decomposition` (PR #1233, at review, not on
  main) supplies `coga launch --read-only`. `skill-status` cannot ship before
  it merges. Start implementation from main after that merge, and check the
  landed contract in `coga/launch` "Read-only command dispatch".
- `v1/microkernel/12-make-packaged-behavior-discoverable-and-editable`
  (PR #1239) set the precedent of two aliases into one bootstrap directory.
  This ticket does not need it to merge, but if it lands first, check that
  `coga fork bootstrap/skill-manage` reports the full script as completely
  forkable.
- `v1/microkernel/06-read-report-commands-as-ticket-workflows` (PR #1240) and
  `v1/microkernel/08-residual-command-surfaces` (PR #1248) also edit
  `aliases.BUILTIN_COMMANDS`, `DEFAULT_ALIASES`, `cli.py` sweep tables,
  `coga/cli` and `coga-dev/microkernel`. Rebase over whichever lands first.
- `v1/microkernel/04b-move-blocker-reminders-and-skill-update-to-the`
  (blocked on 04) moves the reporting job. Its body says to "keep the
  distinct public skill updater ... in core". This ticket moves that updater
  to the edge, and the job keeps calling it through the public CLI, which is
  compatible. Owner, please reconcile that sentence in 04b.

### Verified code relationships (main `00fb27186`)

- Core consumers of `skill_manager` outside `commands/skill.py`:
  `validate.py` (imports `skills_root`, `bundled_skills_root`) and
  `branchsweep.py` (imports `SKILL_UPDATE_BRANCH` for candidate protection
  and ref handling). `skill_update.py` imports nothing from it.
- `skill_manager._verbatim_patch_ids` lazily imports
  `branchsweep._verbatim_patch_ids` because `branchsweep` imports
  `skill_manager`. `_drop_patches_on_control` is its only caller.
- `skill_manager` imports private `coga.git._git_env` for `run_subprocess`.
- `status_skills` and `_status_url_skill` write only to temporary
  directories (`--check` downloads into `tempfile.TemporaryDirectory`), so
  they are safe under read-only dispatch.
- `commands.skill.update` runs `assert_skill_update_pr_preflight`, then
  `assert_skill_update_branch_unclaimed` (setting `git.state_sweep_withheld`
  on refusal), then `update_skills` and `run_skill_update_pr_flow`.
- `skill_update.build_update_command` and `run_update_json` run that public
  command through `subprocess.run(capture_output=True)` and treat any
  non-zero exit as a `RuntimeError` failure. `recurring/skill-update/ticket.py`
  reaches it through `runner.run_recipe(cfg, "skill-update", [])`.
- Bootstrap script launches other than `bootstrap/orient` are exempt from
  checkout preparation (`coga/checkouts/launch-boundary`). Launch logs a
  `launched as a script` line before user code. Exit 75 skips teardown
  refresh and the sweep (`coga/script-tickets` "One deterministic phase").
- Precedents: `bootstrap/recurring-promote/{ticket.py,promotion.py}` on PR
  #1248 (sibling import, alias with trailing `--`); `bootstrap/fork`
  aliases on PR #1239; `tests/report_helpers.py` on PR #1240 (loading a
  script module for unit tests and running real alias subprocesses).

### Required reads

Package user topics under `src/coga/resources/templates/coga/bootstrap/contexts/`:
`coga/skill-management`, `coga/script-tickets`, `coga/launch`,
`coga/edge-code`, `coga/state-publication`, `coga/cli`. Local:
`docs/contexts/coga-dev/microkernel/SKILL.md`,
`docs/contexts/coga-dev/packaging/SKILL.md`,
`docs/contexts/coga-dev/testing/SKILL.md`.

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

## Design handoff — 2026-11-17

Investigated main `00fb27186` and the open sibling branches: 03 (#1233,
`--read-only` launch), 05 (#1239, `fork`/`fork-copy`), 06 (#1240, report
tickets and `recurring list` adapter), 04 (#1245) and 08 (#1248, promotion).
This step edited only this ticket; it created no branch, code or PR.

The owner settled the read spelling (`skill-status` alias; no core adapter)
and the ref (`bootstrap/skill-manage`) during this attended session. Shared
fork behavior is resolved by keeping the reader and writers in one directory,
which replaces 08's two-ticket read-entry design.

Notes for implement:

- Wait for 03 to merge.
- Exit 75 for the branch-claim refusal is a deliberate change. A ContextVar
  cannot cross the process boundary.
- The reporting job's nested launch needs a real-path test.

## Open Questions

For evaluate-design / review-design:

1. Confirm that an inner exit 75 from `skill update --pr` (branch-claim
   refusal, before any mutation) stays an ordinary failure in the
   `skill-update` job, so the period's failure report still publishes. The
   alternative is propagating 75 to withhold the period's publication, which
   would hide the failure report although nothing was retained.
2. Owner to reconcile `04b`'s "keep the public skill updater in core"
   sentence with this move. They are compatible because the job calls the
   public CLI, but the wording is now stale.

## Evaluator review

**Verdict:** Revise before implementation. The shared manager and local-first
fork fit the microkernel boundary. The specified launch behavior cannot
satisfy the dispatch and audit criteria as written. Reviewed on main
`e0e2a20fc8d1cb26e8f653d082a6cd4eaf43891f` and the open #1233 head
`0bf44d2a1ff5e5e846f29007f707c6d461cdee9e`.

### Must resolve before implementation

1. **Give the status entry a distinguishable route and settle refusal
   effects.** `cli.main` expands the two aliases before dispatch and
   `launch_script.run_script_phase` invokes the same child with the same
   `status` argv and script metadata. The child cannot accept one spelling
   and refuse the other with the proposed aliases. Even a child-side exit 2
   leaves the ordinary launch exit sweep eligible to publish pre-existing
   dirt (`cli._sweep_coga_state` and the nonzero exit branch in `cli.main`).
   Specify where the old spelling is refused and how the no-write guarantee
   is achieved, including in a dirty Git-enabled repo. A distinct reader
   operand could differentiate the two public argv paths, but would not
   establish the child's launch policy. Settle explicit invocation behavior
   as well. #1233's `coga/launch` “Read-only command dispatch” says a read-only
   entry rejects write operands, while Proposed Shape 5 deliberately allows
   an explicit read-only install to write locally.
2. **Align audit requirements with stateless launch.** On main and #1233,
   `launch_script.run_script_phase` wraps both script lifecycle audit lines
   and the initial `git.sync_log` in `if not stateless`. A nested
   `bootstrap/skill-manage` therefore emits neither line. Revise Deliberate
   Difference 2 and the recurring acceptance test to reflect existing
   behavior, or explicitly scope and justify an audit change and define its
   interaction with exit 75. Keep the stateful period's own audit distinct
   from the inner bootstrap invocation.
3. **Specify the publication guarantee for writers.** `cli._sweep_coga_state`
   is best effort and `git._publishes_from_feature` holds skills for merge
   off control (see `coga/state-publication`). The writer publication test
   should name a Git-enabled control checkout with a reachable test remote
   and verify the expected remote diff. Document that the ordinary sweep
   also considers other eligible dirt and that feature-branch skill edits
   stay local. The updater's dedicated `--pr` path has its own publication
   contract.

### Confirmed and follow-up

- Keep inner 75 as a recipe failure. `skill_update.run_update_json` raises
  for any nonzero result and `skill_update.run_skill_update_recipe`'s failure path writes the
  report and returns 2. The recurring `skill-update/ticket.py` returns that
  failure before bumping. The refusal protects the inner invocation from
  sweeping. The outer period still uses its ordinary publication policy.
  The owner should specify whether any pre-existing dirt must remain
  unpublished across the *outer* invocation as well. Verify the report on
  control through the actual period failure path, since a parser-only test
  cannot establish its publication.
- The library extractions match the production callers. The test migration
  also needs `test_init.py`'s obsolete installer monkeypatches and
  `test_packaging.py::_context_navigation_sources`'s
  `gh_skill_repo` import. The latter must still work in tests executed
  against the control tree's imports.
- Reconcile the job's “keep ... in core” instruction in 04b with the agreed
  public CLI dependency. Clarify that the old-spelling cleanup covers
  current guidance, with exceptions for the migration/refusal test and
  retained history such as the audit log. The frozen workflow routes this
  review to the owner next, and the implementation criteria are under the
  composed Description and Context sections.

## Superseded in part by plain-Git (2026-11-19)

Owner re-evaluation against `v1/use-git-like-everyone-remove-coga-s-publication-ab`.
Still valid: the move itself. Superseded: placing SKILL_UPDATE_BRANCH and the patch-ID helper in branchsweep, which is expected to be deleted (decision 1).
Do not implement the superseded part; re-scope after that design lands.
