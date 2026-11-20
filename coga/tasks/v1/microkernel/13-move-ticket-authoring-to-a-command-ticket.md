---
title: Move ticket authoring to a command ticket
status: in_progress
owner: nicktoper
contexts:
- coga-dev/microkernel
- coga-dev/testing
- coga-dev/packaging
- coga/edge-code
- coga/script-tickets
- coga/tickets/authoring
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
---

## Description

Move the guided authoring procedure (`coga ticket`) out of the core command
heads and into an editable stateless command ticket, `bootstrap/ticket`. A repo
should be able to change how tickets are drafted and interviewed by forking
that ticket, without a Coga change. Today the procedure is split across
`src/coga/commands/ticket.py` (Typer head, target selection, picker, readiness
and the session), `src/coga/authoring.py` (interviewer precedence, snapshot,
finalization and megalaunch's adapter) and `src/coga/commands/create.py`
(`create_draft`, `_split_create_path`). `src/coga/cli.py` also carries two
authoring-only keyword seams for megalaunch. `src/coga/launch.py` special-cases
the `bootstrap/ticket` name twice. All of that is authoring policy in core.

This is the authoring increment split out of
`v1/microkernel/08-residual-command-surfaces`. Its "Authoring increment"
section and the evaluator's finding 1 are reference material; this ticket
supersedes them where they differ. The dependency
`v1/microkernel/03-launch-decomposition` is merged (PR #1233), and megalaunch
has already moved to `coga_edge.megalaunch`. This ticket therefore rewires that
edge caller and does not touch core queue code.

Done means that `coga ticket [target] [--agent X | --pick-agent]` and
megalaunch's picked-draft pass run one packaged command ticket. They keep the
same interviewer precedence, readiness, scrubbed single child session,
validation and guarded finalization, apart from the deliberate differences
listed below. A legacy local `bootstrap/ticket` override fails loudly instead
of silently becoming an agent launch. Core keeps only shared machinery.

### Decisions this spec proposes (owner confirms at review-design)

These resolve "migration of existing `bootstrap/ticket` overrides and bare
launch semantics before code". Each one is also an Open Question on the
blackboard, with alternatives listed there.

1. **Placement: a wheel-owned edge module plus a package shim.** The
   implementation is a new self-contained `src/coga_edge/authoring.py`. The
   package ships `bootstrap/ticket/ticket.py` as a shim
   (`from coga_edge.authoring import main` / `sys.exit(main(sys.argv[1:]))`),
   the same pattern as `bootstrap/megalaunch` and `bootstrap/slack`. The
   resource-sibling layout (`bootstrap/ticket/{ticket.py,authoring.py}`) is
   rejected for this ticket for one reason. The install-wide default
   interviewer is `bootstrap/ticket`'s `agent:` (precedence term 5), and
   `config.py` refuses `[authoring]` in `coga.toml` and tells users to set it
   on a local `coga/bootstrap/ticket/ticket.md`. Under the shim layout, that
   override is `ticket.md` plus the two-line stock shim, and it keeps receiving
   wheel fixes. Under the sibling layout, changing one agent name would need a
   full procedure fork. A full fork copies the module over `ticket.py`, as for
   slack (`coga/edge-code`).
2. **Install-level default agent is unchanged.** Term 5 is still the effective
   `bootstrap/ticket/ticket.md` `agent:`. The precedence chain in
   `authoring.resolve_authoring_agent` is unchanged, and so is the rule that
   the choice is never written to the target.
3. **Legacy override fails loudly.** This is a generic rule with no `ticket`
   name check. `tasks.resolve_bootstrap` raises `BootstrapOverrideError` when
   the local `coga/bootstrap/<name>/` wins but has no `ticket.py` while the
   packaged `bootstrap/<name>/` has one. The message names the missing file
   and gives both remedies: copy the stock shim beside the local `ticket.md`,
   or delete the override. Because the error is raised at resolution, launch,
   help and `coga validate` all refuse or report it, and nothing falls back to
   an agent session. A repo that followed the old "add a local ticket.md to
   change the agent" advice gets an actionable exit 2 on its next `coga ticket`.
4. **`coga launch bootstrap/ticket` becomes the authoring command.** The new
   `ticket` default alias is `launch bootstrap/ticket --`. Bare
   `coga launch bootstrap/ticket` is the empty interview with finalization,
   exactly like bare `coga ticket`. It is no longer an agent session without
   finalization. Operands after `--` reach the script (`-- <target>`,
   `-- --agent X`, `-- --pick-agent`). Launch's own `--agent` placed before
   the target is meaningless for a stateless script target, because one phase
   runs and no agent phase follows. Proposed: generic launch refuses `--agent`
   for a bootstrap target with a `ticket.py`, before any effect (exit 2), and
   says to pass it after `--`. This must be verified against current behavior
   and is Open Question 3.
5. **Megalaunch picks the existing-target mode through an environment
   variable, not a public flag.** `coga_edge.megalaunch` runs
   `[sys.executable, "-c", "from coga.cli import main; main()", "launch",
   "bootstrap/ticket", "--", <qualified slug>, "--agent", <name>]` with
   `COGA_AUTHORING_EXISTING_TARGET=1` set. It calls launch directly rather
   than the `ticket` alias, so a user alias cannot reroute it. It keeps today's
   clearing of task, supervisor and expected-identity variables. The script
   reads and pops that variable, so the interviewer never sees it. This keeps
   the contract in `coga/tickets/authoring` that the adapter "adds no ...
   public flag".

### Proposed shape

Work in this order. Each stage leaves the suite green.

1. **Extract shared core (no behavior change).**
   - Move `commands.create.create_draft` and `_split_create_path` into the
     existing `src/coga/create.py`, as public `create_draft` and
     `split_create_path`. `create_draft` must raise a typed error
     (`CreateDraftError(ValueError)` or similar) instead of calling
     `typer`/`sys.exit`. It keeps validation, `create_task`, the
     `"<slug>: created (draft)"` echo responsibility (returned or printed by
     callers) and `git.sync_task_state` publication. `commands/create.py`
     becomes a thin head that maps the error to red stderr and exit 2, with
     messages unchanged. Update `tests/test_create.py`
     (`_split_create_path` test).
   - Expose `git._index_modes` publicly (for example `git.index_modes`, with
     core callers updated). The edge finalizer must not import a private core
     symbol. `authoring.snapshot_authoring_files` uses it today.
   - Shrink `src/coga/authoring.py` to the shared interviewer policy:
     `AUTHORING_AGENT_ENV` and `resolve_authoring_agent`. It has two edge
     consumers (the authoring module and `coga_edge.megalaunch._author_draft`),
     and edge modules may not import each other, so it stays in core. Update
     its docstring and the `config.py` comments that cite it.
2. **Create the edge implementation `src/coga_edge/authoring.py`.**
   It is self-contained: stdlib, declared dependencies and shared `coga.*`
   only, never `coga.commands.*` or another `coga_edge` module. It contains:
   - `main(argv) -> int`: the Typer/argparse parser with today's
     `target`/`--agent`/`--pick-agent` arguments, help text and messages
     from `commands.ticket.ticket`. It refuses with exit 2 before any effect
     when `COGA_SCRIPT_HELP=1` (the `coga/script-tickets` help contract). It
     reads and pops `COGA_AUTHORING_EXISTING_TARGET`.
   - Target selection moved together: the bare interview (the bootstrap ref
     itself, kickoff `Begin`), an existing qualified ref, or a unique bare
     leaf. It keeps the ambiguity refusal, the parked-directory refusal, and
     new-title creation through `coga.create.create_draft`. In existing-target
     mode it requires an exact `id_slug` match and never creates (today's
     `_resolve_or_create_target` with `existing_target_only`).
   - `_pick_authoring_agent` unchanged (TTY only, single-agent shortcut, the
     re-prompt loop and the keep-it hint).
   - **Full readiness before create.** Before `create_draft` runs, check the
     TTY (`launch.interactive_stdio_has_tty`), apply the `--pick-agent`
     answer, resolve the interviewer, and check that the agent type exists,
     that its CLI is on `PATH`, that the bootstrap prompt layers resolve, and
     that the Windows command can be represented (kickoff
     `Begin (new ticket)`). Use 03's `launch.prepare_agent_launch` with
     `discussion=True`, `kickoff=...` and an `env_transform` that returns
     `config.scrub_op_auth_env(os.environ)`. Do this only if it can be called
     without resolving the target's `secrets:`, for example on the authoring
     projection with `secrets` removed, and only if that projection does not
     change the composed prompt the interviewer needs. Otherwise compose the
     same checks from the public helpers (`interactive_stdio_has_tty`,
     `cfg.agent_type`, `shutil.which` with `agent_cli_missing_message`, and
     `launch.agent_command_refusal`). Any refusal exits 2 and leaves no draft.
     Readiness repeats against the real ref after creation. If it fails there
     (rare, since the prompt layers changed), the published draft remains and
     the exit is 2.
   - `_authoring_ticket` projection unchanged: skills forced to
     `["bootstrap/ticket"]` and `step` removed, ephemeral only.
   - One session through `launch.spawn_agent_session`, with today's arguments:
     `env=scrub_op_auth_env(os.environ)`, `discussion=True`, the kickoff
     token, `commit_log=True`, `secrets_are_scoped=False`,
     `stateless_identity=("bootstrap/ticket", <bootstrap title>)`,
     `include_blocker_preamble=False`, `actor=human:<user>` and the same
     log message. There is no supervisor chain, no bump and no recursive
     launch. Translate `ComposeError`, `AgentCliNotFound` and
     `FileNotFoundError` to exit 2, as today. A nonzero agent exit prints the
     same warning and returns `oscompat.process_exit_status(code)` without
     finalizing.
   - The finalizer moves unchanged in behavior: `AuthoringSnapshot`,
     `snapshot_authoring_state`, `snapshot_authoring_files`,
     `_authoring_files`, `changed_authoring_paths`, `authored_task_refs`,
     `support_paths`, `authoring_sync_message`, `validate_authored_task` and
     `finalize_authored`. It keeps the config reload, the changed-destination
     refusal, symlink refusal, relocated roots, mode changes, deletions,
     file-to-directory conversion, duplicate and discovery errors,
     workflow-less draft rejection, validation of the named unchanged
     target, selection of exact files by entry snapshot, and one `git.publish`
     with `require_paths`.
   - **Finalization refusal exits 75** (`git.RETRY_WITHOUT_SWEEP_EXIT_CODE`)
     and prints today's retained-edits recovery text. Launch's existing
     stateless path (`launch_script.run_script_chain` returns early on 75, and
     `launch` sets `script_retained_state` and `git.state_sweep_withheld`)
     then skips teardown refresh and the parent sweep. Do not add authoring
     logic to core for this.
3. **Package the command ticket.** Under
   `src/coga/resources/templates/coga/bootstrap/ticket/`:
   - Add a `ticket.py` shim.
   - Rewrite `ticket.md` as the command contract owner: the `coga ticket`
     alias and the `coga launch bootstrap/ticket -- ...` equivalence;
     operands; exits (0; 2 for argument or readiness refusals; the agent's
     status; 75 for retained finalization); `agent:` as the term-5 install
     default; the agent-only override (local `ticket.md` plus the stock
     shim); the full fork (module copied over `ticket.py`, plus optionally
     `coga/skills/bootstrap/ticket/`); the legacy-override refusal; and the
     megalaunch environment variable. Keep it stateless (no `status:`,
     `owner:` or `secrets:`) and keep `agent: claude`.
4. **Wire dispatch and delete the core head.**
   - In `src/coga/aliases.py`, add `"ticket": "launch bootstrap/ticket --"` to
     `DEFAULT_ALIASES`, remove `"ticket"` from `BUILTIN_COMMANDS`, add
     `"ticket"` to `_RETIRED_BUILTINS`, and extend the alias comment.
   - In `src/coga/cli.py`, remove the `"ticket"` lazy-command entry, the
     `retained_state_exit`/`existing_target_only` parameters of `main`, the
     authoring ContextVar block, and `_authored_state_retained`.
   - Delete `src/coga/commands/ticket.py` and
     `authoring.invoke_ticket_authoring`. Remove the
     `existing_target_only`/`authored_state_retained` ContextVars. Leave no
     forwarding stub.
   - In `src/coga/launch.py`, drop `"bootstrap/ticket"` from
     `DISCUSSION_BOOTSTRAP_TICKETS` and remove the `bootstrap/ticket` branch
     of `_bootstrap_kickoff`. Launch no longer spawns an agent directly on
     that target; the edge module passes `discussion`/`kickoff` itself.
     `bootstrap/orient` keeps its entry.
   - Add the generic incomplete-override check in `tasks.resolve_bootstrap`
     (decision 3) and the launch `--agent` refusal for script bootstrap
     targets (decision 4), each subject to its Open Question.
5. **Rewire megalaunch.** In `src/coga_edge/megalaunch.py`, move a private
   `_invoke_ticket_authoring` into the module (its only consumer) with the
   argv and environment from decision 5. Keep `_author_draft`'s non-prompting
   `resolve_authoring_agent` skip message and its rule that a 75 raises
   `SystemExit(75)` and stops the queue. `_author_draft` must report a
   `BootstrapOverrideError` instead of silently returning on every
   `TaskNotFoundError`.
6. **Docs, in the same PR.** Update the following:
   - Package user topics: `coga/tickets/authoring` (command ownership summary
     and link to `bootstrap/ticket/ticket.md`, the override migration, the
     changed exits, the adapter paragraph), `coga/cli` (move `ticket` from
     built-ins to the alias index), `coga/edge-code` (a "Forking the ticket
     command" section) and `edge-code/edge-code-upgrades.md` (a legacy
     `bootstrap/ticket` override migration with the exact old and new layout),
     `coga/configuration` and the `config.py` `[authoring]`-in-`coga.toml`
     error text (the local override now needs the shim), the `coga.toml`
     template comments that mention `coga ticket`, the packaged skill
     `bootstrap/skills/bootstrap/ticket/SKILL.md` (its "plumbing" paragraph
     names `coga launch bootstrap/ticket`), and any other live mention found
     by grepping `coga ticket`, `launch bootstrap/ticket`, `commands.ticket`
     and `coga.authoring`.
   - Local coga-dev topics: `coga-dev/microkernel` (close the `ticket` row of
     "Open command placements" with the receipt), `coga-dev/codebase` and its
     `gotchas`, and `coga-dev/internals/{agent-spawn,compose,state-publication,activity-capture}`
     where they cite the moved symbols.
   - Do not edit `docs/archive/**`. Summarize and link rather than restate
     the contract that `ticket.md` owns.
7. **Tests and packaging.**
   - Add `bootstrap/ticket/ticket.py` to `tests/required_package_resources.txt`.
     Add no live local copy to this repo.
   - Carry `tests/test_ticket.py` and `tests/test_authoring.py` forward
     against `coga_edge.authoring` (in-process `main(argv)` with monkeypatched
     `spawn_agent_session`, as today), and keep a handful of real subprocess
     tests through the alias and launch path.
   - Carry `tests/fixtures/authoring_cancellation.py` forward, retargeting its
     monkeypatches to the edge module.
   - Update `tests/test_megalaunch.py`, `test_cli.py`, `test_aliases.py`,
     `test_launch.py`, `test_launch_script.py`, `test_create.py`,
     `test_git.py`, `test_init.py`, `test_recurring.py`,
     `test_bootstrap_ticket_skill_template.py`, `test_packaging.py` and
     `conftest.py` where they import the moved symbols or invoke `["ticket", ...]`.

### Deliberate user-visible differences

1. `coga ticket ...` is now an alias. Stderr carries
   `→ coga launch bootstrap/ticket -- ...`, and launch prints its stateless
   script framing and writes whatever generic stateless-script audit lines it
   writes for other command tickets. These are in addition to the existing
   `ticket authoring launched (...)` line.
2. A refused guarded finalization exits **75** on the direct path. Today it
   exits 2 with the sweep withheld. Megalaunch's path already returned 75.
3. Pre-write refusals (an unrepresentable Windows agent command, missing TTY,
   CLI or agent) still exit 2 with no draft. The parent launch then runs its
   ordinary end-of-command sweep, because a script child cannot set the
   parent's in-process withhold. Today the representability refusal withheld
   the sweep. The refusal itself writes nothing.
4. Bare `coga launch bootstrap/ticket` runs the authoring command with
   finalization, not a plain agent session. Launch's own `--agent` before the
   target is refused (pending Open Question 3).
5. A local `coga/bootstrap/ticket/` without `ticket.py` is refused, as is any
   local override that drops a packaged script entry.
6. `ticket` is no longer a built-in. A user alias named `ticket` now overrides
   the default, and an alias whose expansion starts with `ticket` is refused
   as a retired built-in, with the replacement expansion named.

### Acceptance criteria

- [ ] `coga ticket`, `coga ticket "<dir/>New title"`, `coga ticket <qualified ref>`
      and `coga ticket <unique bare leaf>` run through
      `launch bootstrap/ticket -- ...` and the edge module. They have today's
      kickoff tokens and messages and the same ambiguity and parked refusals.
      `coga --help` lists `ticket` as an alias row.
- [ ] Interviewer precedence (`--agent` / `--pick-agent` answer >
      `COGA_AUTHORING_AGENT` > `[authoring] agent` > target `agent:` >
      `bootstrap/ticket` `agent:` > default agent) is unchanged. A bad
      winning term fails loudly and names its source. `--agent` together with
      `--pick-agent` is refused. The target's `agent:` bytes are unchanged
      after an interview.
- [ ] For a new title, every readiness refusal leaves no draft and no
      publication, with exit 2: no TTY (with and without `--pick-agent`), an
      unknown agent, a missing CLI, and an unrepresentable Windows command.
      Each refusal has a test.
- [ ] Exactly one `spawn_agent_session` call per invocation. Its environment
      equals `scrub_op_auth_env(os.environ)` re-derived by `apply_task_env`.
      It has no Coga secret injection (a target with `secrets:` resolves
      nothing), no `COGA_SCRIPT_TASK`, no expected-task, step, agent or assist
      identity, and no `COGA_AUTHORING_EXISTING_TARGET`. It uses
      `stateless_identity` bootstrap/ticket, no blocker preamble and no
      execution-step skill. The authoring launch audit is published before
      the session.
- [ ] A nonzero agent exit returns the agent's process status through the
      alias and launch path (POSIX test) and does not finalize.
- [ ] Finalization covers all authored tasks plus the named unchanged target,
      and preserves today's `test_authoring` cases (support paths, symlinks,
      relocation, mode, deletion, file-to-directory, duplicates, workflow-less
      draft, changed destination). It does one `git.publish` with
      `require_paths`.
- [ ] A finalization refusal, exercised through the real alias, launch and
      subprocess path rather than a mocked finalizer, exits 75. It retains the
      edits, and neither the parent teardown refresh nor its sweep publishes
      them. Assert this against a real bare remote, as the cancellation
      fixture does.
- [ ] The megalaunch picked-draft path invokes `launch bootstrap/ticket` with
      the existing-target variable. It never prompts and never creates. A
      missing slug ends the attempt. An unresolvable agent is reported and
      skipped. An ordinary failure leaves the draft for the check phase. A 75
      stops the queue with exit 75 and no further publication. There is one
      end-to-end subprocess test.
- [ ] Bare `coga launch bootstrap/ticket` runs the empty interview with
      finalization. `coga launch --agent X bootstrap/ticket` behaves as
      decided in Open Question 3, with a test.
- [ ] A local `coga/bootstrap/ticket/ticket.md` without `ticket.py` makes
      `coga ticket`, `coga launch bootstrap/ticket` and megalaunch's authoring
      pass refuse or report with the remedy, and no agent starts. A local
      `ticket.md` plus the stock shim changes the term-5 default and runs
      the installed implementation. A local full fork (module copied to
      `ticket.py`) runs from a read-only installed wheel. These cases are
      tested in `test_packaging.py`, as promotion's are.
- [ ] Core contains no `commands/ticket.py`, `invoke_ticket_authoring`,
      finalizer, authoring ContextVars, `cli.main` authoring parameters, or
      `bootstrap/ticket` name special cases in launch. No core module imports
      or path-loads `coga_edge.authoring`. `coga_edge.authoring` imports no
      private core symbol and no other `coga_edge` module. `coga.create`
      serves both `coga create` and authoring.
- [ ] Docs in step 6 are updated in the same PR, and the `ticket` row of
      `coga-dev/microkernel` "Open command placements" is closed with its
      receipt.
- [ ] Receipts: the affected tests, the full Linux suite, a CLI smoke check
      (`coga --help`, `coga ticket --help`) and `coga validate --json`. Each
      records the full revision, OS and Python, the command, counts and the
      runtime. Native Windows and macOS checks are deferred to release.
      Before/after physical lines are recorded for core, edge and ticket
      Python, at named revisions, against the baseline in `## Context`.

### Out of scope

- Any change to interview content, the `bootstrap/ticket` SKILL.md procedure
  (beyond the plumbing sentence), the kickoff tokens or the precedence chain.
- Moving `coga create` out of core, and changing `create_task`.
- Skill management (`v1/microkernel/14-move-skill-management-to-command-tickets`),
  promotion (done under 08), and queue policy beyond the `_author_draft` call
  site.
- A generic plugin or dispatch mechanism, nested aliases, or a public
  existing-target flag.
- Making `[authoring]` legal in `coga.toml`, which is Open Question 1's
  alternative and not the proposal.
- The discover/copy command (`v1/microkernel/05-...`). It should list
  `coga_edge.authoring` among `bootstrap/ticket`'s complete-copy sources once
  both land. Note that to its owner and do not build it here.

## Context

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

### Verified code relationships (main `fa737ac17`)

- `commands.ticket.ticket` resolves the bootstrap ref with
  `tasks.resolve_bootstrap(cfg, "ticket")`. On a new title it calls
  `before_create`, which picks and resolves the agent and runs only
  `_preflight_authoring_command` (Windows representability), before
  `commands.create.create_draft`. TTY, agent type and CLI presence are checked
  later, in `_run_authoring_session`, after the draft exists. That is the gap
  this spec closes.
- `_run_authoring_session` calls `authoring.snapshot_authoring_state` before
  `launch.spawn_agent_session(... env=scrub_op_auth_env(os.environ),
  commit_log=True, secrets_are_scoped=False, stateless_identity=...,
  include_blocker_preamble=False)`. It calls `authoring.finalize_authored` only
  on agent exit 0. On `AuthoringError`/`TaskValidationError` it sets
  `git.state_sweep_withheld` and `authored_state_retained`, then exits 2.
- `cli.main(retained_state_exit=True, existing_target_only=True)` is called
  only by `authoring.invoke_ticket_authoring`, which is called only by
  `coga_edge.megalaunch._author_draft`. It maps a retained authoring refusal
  to 75 after the sweep is skipped.
- `coga_edge.megalaunch` imports `invoke_ticket_authoring` and
  `resolve_authoring_agent` from `coga.authoring` at module level.
  `resolve_authoring_agent` has no other production caller besides
  `commands.ticket`.
- `launch_script.run_script_phase` runs a stateless, non-read-only
  `ticket.py` with `process_relay.run_foreground_child` (inherited stdio, so
  the interview keeps its TTY, and `defer_interrupt=True`). Its environment
  clears `COGA_SUPERVISED` and the expected identity, and sets
  `COGA_SCRIPT_TASK`. `spawn_agent_session` re-derives task environment
  through `task_env.apply_task_env`, which clears the `TASK_ENV_KEYS`
  namespace including `COGA_SCRIPT_TASK`.
- `run_script_chain` returns early on 75 for stateless targets.
  `launch.launch` then sets `script_retained_state` and
  `git.state_sweep_withheld`, so the generic retained-state path already
  exists (the evaluator's note on 08).
- `launch.prepare_agent_launch` is 03's public readiness pass. It covers the
  agent type, the CLI on `PATH`, prompt layers, secrets (through
  `build_launch_env(cfg, ticket.secrets)`) and the command refusal, and it has
  an `env_transform` hook. TTY is separate (`interactive_stdio_has_tty`).
- `tasks.resolve_bootstrap` picks the local directory as a whole whenever a
  local `ticket.md` is a valid entry, and raises `BootstrapOverrideError` (a
  `TaskNotFoundError`) for an unusable local override. It does not compare
  script entries with the packaged copy today.
- `config.py` refuses `[authoring]` in shared `coga.toml` and directs users
  to a local `coga/bootstrap/ticket/ticket.md` `agent:`. That is the override
  population decision 3 migrates.
- `launch.DISCUSSION_BOOTSTRAP_TICKETS` and `_bootstrap_kickoff` name
  `bootstrap/ticket`. They matter only when launch spawns an agent directly
  on that target, which stops once it has a `ticket.py`.
- Precedents: `bootstrap/slack` and `bootstrap/megalaunch` (a shim plus a
  `coga_edge` module, documented in `coga/edge-code`), and
  `bootstrap/recurring-promote` (a resource sibling, from 08's PR #1248).

### Baseline (main `fa737ac17`, physical lines)

`commands/ticket.py` 432; `authoring.py` 394 (`resolve_authoring_agent` 59,
`finalize_authored` 94, `invoke_ticket_authoring` 26); `commands/create.py`
175 (`create_draft` 64, `_split_create_path` 15). Most lines relocate. The
expected core reduction is roughly the ticket head, the finalizer, the
adapter and the `cli.main` seams. The new edge module and tests offset it.
No savings are claimed before receipts.

### Required reads

`coga-dev/microkernel` (rule and the open-placement row),
`coga/script-tickets` (help, interrupts, streams), `coga/edge-code` (shim and
fork rules), `coga/tickets/authoring` (the current contract),
`coga/state-publication` and `coga-dev/packaging`. Source design:
`coga/tasks/v1/microkernel/08-residual-command-surfaces.md` ("Authoring
increment" and the evaluator review's finding 1). The sibling
`14-move-skill-management-to-command-tickets` makes parallel choices for exits and
aliases. Keep the deliberate-difference wording consistent with it.

<!-- coga:blackboard -->

## Design handoff — 2026-11-19

Design step only. I edited this ticket and nothing else: no branch, code or PR.
I investigated main at `fa737ac17` (`git rev-list --left-right --count
HEAD...origin/main` gave `0 0` after fetch). 03-launch-decomposition is merged
(PR #1233), and megalaunch already lives in `coga_edge.megalaunch`, so the
queue call site to change is in the edge module. The spec's decisions 1–5
answer the source evaluator's finding 1 (a–d). They wait on owner
confirmation below.

## Open Questions

For the owner at review-design. Each has a recommendation in the Description.

1. **Placement.** Should the authoring module be `coga_edge.authoring` with a
   package shim at `bootstrap/ticket/ticket.py` (recommended)? The
   alternative is the resource-sibling layout
   `bootstrap/ticket/{ticket.py,authoring.py}` that skill-manage and
   recurring-promote use. The shim keeps the term-5 override cheap: a local
   `ticket.md` plus the stock shim keeps getting wheel fixes. The sibling
   layout makes an agent-only override a full fork, unless we also make
   `[authoring] agent` legal in `coga.toml` and drop term 5. That would be a
   precedence and config change.
2. **Legacy override refusal scope.** Should the incomplete-override rule be
   generic in `tasks.resolve_bootstrap` (recommended)? It applies to any
   local bootstrap override that drops a packaged `ticket.py`, including
   slack, megalaunch and recurring-promote. Or should it be narrower, either
   at launch classification only or as a `coga validate` warning only? The
   generic rule also blocks someone who deliberately replaces a packaged
   script command with an agent-only local ticket.
3. **Launch `--agent` before a stateless script target.** Should launch
   refuse it with exit 2 (recommended)? As I read `launch.py`, it is
   validated only when agent work follows, which never happens for a
   stateless script, so it is silently ignored today for `retire`, `slack`
   and `promote-recurring` too. The implementer should confirm this. The
   alternatives are to accept silent ignoring (skill-manage's choice: "no
   skill-specific refusal") or to forward it to the script. Forwarding needs
   a new launch-to-script contract.
4. **Existing-target signal.** Is the `COGA_AUTHORING_EXISTING_TARGET=1`
   environment variable acceptable (recommended, since it keeps "no public
   flag")? The alternative is a documented `--existing` operand.
5. **Exit changes.** Do you accept that the direct `coga ticket`
   finalization refusal moves from 2 to 75? Do you accept that the Windows
   representability refusal still exits 2 but no longer withholds the
   parent's ordinary sweep, since a script child cannot set it?

## Evaluator review

**Verdict: revise before implementation.** The edge module and stock shim
fit the microkernel boundary and preserve a lightweight default-agent
override. The refusal, exit-code and dispatch contracts need decisions in
the ticket body. Reviewed on control at
`1ec3f098dd10ea9839490c6f98c73eb082eb56b6`. Production and test sources
match the stated baseline. The frozen workflow routes this review to the
owner and all implementation requirements are under composed sections.

### Must resolve before implementation

1. **Define the publication guarantee for refusal.** The new-title
   acceptance criterion promises “no publication” on exit 2, while
   Deliberate Difference 3 explicitly allows the ordinary sweep.
   `cli._should_sweep_coga_state` and the nonzero-exit handling in
   `cli.main` allow publication of eligible entry dirt on a failed ordinary
   launch. The proposed outer `--agent` refusal has the same distinction.
   Specify whether refusal means no draft or interview audit from this
   attempt, with incidental settlement and sweep still allowed, or no
   publication even with dirty entry state. Test the chosen policy against
   a Git-enabled control checkout with unrelated eligible dirt.
2. **Resolve agent exit 75 versus retained finalization.**
   `commands.ticket._run_authoring_session` currently forwards the
   interviewer process status and `cli.main` uses a separate retained-state
   marker for the queue adapter. After the move, `launch_script.run_script_chain`
   and `megalaunch._author_draft` treat any 75 as retained state. An agent
   that returns 75 would stop the queue and suppress settlement and sweep
   despite finalization never running. Decide whether to reserve 75 and
   translate that agent status, or accept the queue stop as a deliberate
   difference. Test agent exit 75 separately from a real finalizer refusal.
3. **Settle explicit read-only launch.** Once the shim ships,
   `coga launch --read-only bootstrap/ticket` becomes executable.
   `launch.launch` checks only bootstrap identity and a script entry, and
   `launch_script.run_script_phase` passes the same task environment to
   both forms. `COGA_SCRIPT_HELP` identifies help only. The proposed child
   can create and publish despite the read-only invocation. This conflicts
   with the “Read-only command dispatch” contract in `coga/launch`.
   Specify how authoring refuses that route before effects and test empty
   and new-title invocations. If a generic discriminator is needed, account
   for it explicitly in the scope.
4. **Complete the incomplete-override policy at every boundary.** A
   resolver check alone does not provide all the promised outcomes.
   `validate.py` resolves bootstrap targets referenced by delegates but
   does not enumerate unreferenced bootstrap overrides. Help catches
   `TaskNotFoundError` and falls through to ordinary launch, where user
   config can fail before the override remedy appears. More importantly,
   `run_script_phase` catches that base exception during re-resolution
   and returns `ran=False`, which `_classify_script_handoff` can turn into
   an agent handoff. Specify the validation entry point and require help
   and script re-resolution to preserve the actionable override refusal.
   Test an unreferenced legacy override and an override becoming invalid
   after initial classification. The remedy should say “restore the
   packaged script entry” for commands that ship a full implementation or
   resource siblings. “Copy the stock shim” fits authoring specifically.

### Confirmed and follow-up

- I confirmed the premise of Open Question 3 in the ordinary launch
  path. A successful stateless script returns in
  `_run_initial_script` before `_prepare_agent` consumes the override.
  Decide whether a generic refusal also applies when trailing script help
  runs first, since `launch.launch` handles that before classification.
- `launch_script.run_script_phase` omits startup and exit audit lines for
  stateless targets. Deliberate Difference 1 can state that directly.
  The interview's own audit still goes through
  `spawn_agent_session` with `commit_log=True`.
- Make the pre-create prompt check concrete. In the fallback listed in
  Proposed Shape 2, TTY, agent lookup, CLI lookup and command planning
  alone cannot detect missing prompt layers. Use an explicit secret-free
  projected prompt check, define which layers a prospective draft can
  check, and exercise an unresolved prompt layer before create. Verify
  that the real-ref check and spawn use the projected authoring prompt
  without consulting the target's secret declarations.
- The cancellation fixture installs its observer patches in the same
  interpreter as the current head. Retargeting imports alone leaves the
  new shim subprocess uninstrumented. Keep the subprocess-local
  cancellation and publication observations, plus a parent-independent
  bare-remote check through the real alias. Existing launch-script tests
  already isolate the generic retained-state teardown behavior.
- The exact picked-slug check, shared interviewer resolver, draft creation
  extraction and full-copy fork are coherent. Define the stage boundaries
  so the old head keeps its finalizer and adapter imports until their
  callers move, consistent with the requirement that every stage stays
  green.

## Superseded in part by plain-Git (2026-11-19)

Owner re-evaluation against `v1/03-use-git-like-everyone-remove-coga-s-publication-ab`.
Still valid: moving coga ticket authoring to the edge. Superseded: guarded finalization, the single git.publish over an entry snapshot, and exit 75 on refusal (decisions 1, 3, 4).
Do not implement the superseded part; re-scope after that design lands.
