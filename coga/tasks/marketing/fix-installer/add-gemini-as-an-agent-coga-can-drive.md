---
title: Add Gemini as an agent coga can drive
status: in_progress
owner: zach
contexts:
- coga-dev/principles
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
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
step: 2 (evaluate-design)
agent: claude
launch_generation: f8a587ce-19bf-4f97-a04e-dec0d1f89a4d
---

## Description

Coga drives `claude` and `codex` today. Nico wants Gemini as a third agent
type. Add supported Gemini CLI configuration and the install, discovery, and
peer-routing integration needed to run a task through its intended handoff.

The design survey recommends proceeding: official `@google/gemini-cli`
**0.66.0** supports the required interactive prompt and shell-to-supervisor
transport. A local offline probe exercised the actual CLI, shell tool, and
Coga supervisor successfully. It used synthetic model responses; an
authenticated task and publication smoke remains a release requirement.
Missing optional features below are degradations, not grounds to defer core
execution. If implementation discovers a concrete core incompatibility,
record its version, reproducer, and reopening condition in the standing owner
and return the decision to the owner; do not silently ship a partial handoff.

### Acceptance criteria

- [ ] A repo can declare `[agents.gemini]` using the proposed configuration,
      select `agent: gemini`, and launch an interactive task with the complete
      composed prompt. Normal and oversized file-pointer prompts work; the
      agent reads the pointer before acting.
- [ ] An authenticated Gemini CLI run in a disposable repo reaches an actual
      `coga bump` to its intended next role, publishes the transition, credits
      `agent:gemini`, and releases the supervisor with a matching done signal.
      Record CLI version, auth method (never credentials), effective sandbox,
      Git transport, and the resulting step. Synthetic responses and a zero
      process exit alone do not satisfy this check.
- [ ] The shipped three-agent configuration has explicit valid peers and
      preserves Claude↔Codex review. Gemini defaults to Claude as its peer.
      Two-agent subsets resolve each other; single-agent subsets contain no
      dangling peers and retain the existing explicit peer-workflow failure
      and `code/with-self-review` guidance. No change to peer inference.
- [ ] Gemini joins `dependencies.AGENT_CLIS`, init's labels and installation
      choices. Setup offers `brew install gemini-cli` on macOS or
      `npm install -g @google/gemini-cli`, then bare `gemini` for login, under
      the existing consent rules. Non-interactive init installs nothing.
- [ ] Fresh init creates a missing `GEMINI.md` from the existing guide template
      and preserves an existing file. Clone setup and launch refresh make
      local and bundled Coga skills discoverable by Gemini, including nested
      refs and local overrides, without overwriting user skills/settings.
      A trusted-workspace `gemini skills list` demonstrates real discovery.
- [ ] Generated Gemini links are ignored, refreshed idempotently, and removed
      when their Coga skills disappear. Empty-repo detection recognizes init's
      Gemini artifacts. Uninstall removes only Coga-owned links, preserves
      other `.gemini` content, and applies existing unchanged/edited guide
      removal/backup rules to `GEMINI.md`.
- [ ] `analyze = "-p {prompt}"` produces a one-shot command without interactive
      launch arguments. In an authenticated, trusted workspace it returns text
      and exits; missing trust/auth fails visibly rather than opening a REPL.
- [ ] User docs and packaged comments state the tested version, required
      setup, and optional limits: no CLI session-name flag, positional
      discussion fallback, and unknown token usage despite a pinned session
      ID. Canonical topics and their packaged twins agree.
- [ ] Relevant automated tests and the full suite pass; a seeded fixture
      covers Gemini prompt/config routing without replacing all two-agent
      regression coverage. Record exact verification commands and the live
      smoke receipt in the implementation handoff.

### Proposed shape

**1. Use the existing configuration and launch contract.** Add this table to
`src/coga/resources/templates/coga/coga.toml`, documenting 0.66.0 as the
verified baseline, without changing this repo's live config:

```toml
[agents.gemini]
cli = "gemini"
file = "GEMINI.md"
mode = "local"
session_id_flag = "--session-id"
analyze = "-p {prompt}"
peer = "claude"
```

Leave `name_flag`, `discussion`, and `launch_args` unset. In a TTY, 0.66.0
accepts `gemini --session-id <uuid> <prompt>` interactively. Its `-i` option
also exists, but `launch_args = "--prompt-interactive"` would put the
value-taking flag before Coga's inserted session-ID arguments. Avoid that
combination. Do not add a Gemini branch to the generic argv builder, a new
config key, an agent plugin, or automatic permission/trust bypass flags.
Keep `recurring_autofix.DEFAULT_ANALYZE_TEMPLATES` unchanged: the explicit
`analyze` setting supplies the one-shot form, including for absolute CLI paths.
Discussion launches use the existing positional fallback, with authoring's
kickoff appended; verify the combined prompt is preserved, while documenting
that the human's first message no longer determines the session title.

**2. Preserve peer routing when there are three agents.** Add explicit
`peer = "codex"` to the packaged Claude table and `peer = "claude"` to Codex.
Keep Claude as the default and preserve table order. For an existing repo
adding Gemini, document setting peers for every main-agent type that uses
`other-agent`; a wheel upgrade does not rewrite team configuration.
Also document adding a missing `GEMINI.md` deliberately (it can import an
existing `AGENTS.md` with `@AGENTS.md`). Re-running init after `user` is
already set is refused today, so do not present that as an upgrade recipe.

Coordinate with `v1/20-ask-which-agents-to-enable-during-coga-init`, currently
in owner `review-design`. When its proposed `_disable_unchosen_agents` lands,
filtering out a table must also comment out any surviving `peer` whose target
was removed. Retain valid peers; absent peers use the existing two-agent
inference. Parse-back comparison must allow exactly table removal plus these
peer removals. Own this compatibility adjustment here if the picker is already
on main; otherwise leave this requirement in the handoff for the sibling.
Test all seven non-empty subsets, plus empty and canceled selection when that
picker exists. Do not ship a selected subset that fails config load because
of a packaged peer pointing at a disabled agent.

**3. Extend the existing installer data.** In `src/coga/dependencies.py`, add
`gemini` to `AGENT_CLIS` after Codex and add a `Dependency` with the official
installation URL, `required_at_init=False`,
`packages={"brew": ("gemini-cli",), "npm": ("@google/gemini-cli",)}`, and
`login=()`. This is a brew formula, not a cask. Add the `Gemini CLI` display
label in `src/coga/commands/init.py` `_AGENT_LABELS`. Reuse
`src/coga/agent_cli_setup.py` `installer_argv` and `offer_agent_cli`; update
its two-agent/cask-only explanatory wording. Account for all enabled agents
in init's next steps without reimplementing the sibling's picker. npm's
package engine requires Node >=20; retain vendor-managed authentication.

**4. Add real skill discovery, not just a directory name.** Add `GEMINI.md`
to init's `_AGENT_GUIDE_FILES` and `GEMINI.md`/`.gemini` to `_INIT_IGNORE`.
Keep missing-only guide writes and existing clone behavior; do not modify a
user's Gemini `settings.json` to rename its instruction file.

Gemini's one-level scanner cannot consume `.gemini/skills/coga` pointing at
the nested `coga/.agent-skills/` tree. Extend the shared skill-view machinery
in `src/coga/agent_skills.py` with a narrow synchronization helper, consumed
by init's `_link_skills_for_agents` and launch's
`_refresh_agent_skills_for_launch`. Create an immediate-child symlink for
each effective skill, such as `.gemini/skills/coga-code%2Fdesign` pointing to
`coga/.agent-skills/code/design`. Use an injective encoding of the complete
ref for link names; use relative targets when possible and retain the
existing cross-drive absolute-target fallback. Derive refs from the merged
local-over-bundled view, not a second independent resolver. Preserve skill
files and sibling attachments through the directory links.

Only replace/prune a managed-prefix symlink when its lexical target belongs
to this installation's generated view; check ownership without following the
view's leaf symlink outside that directory. Existing files, foreign symlinks,
and unrelated `.gemini` data remain untouched and conflicts are reported.
Gemini sanitizes `/` in metadata names to `-`; detect collisions such as
`foo/bar` versus `foo-bar` and report/skip ambiguous entries rather than
silently selecting one. Do not rename canonical Coga refs. Respect the
adopting root for nested init and refresh newly added/removed skills at
launch. Claude/Codex keep their existing directory links.

Update `src/coga/commands/update.py` `_HOST_GITIGNORE_BODY` for the managed
Gemini link namespace. Extend `src/coga/commands/uninstall.py` `_build_plan`
using the same ownership rule, before deleting `coga/`; its existing
`_remove_skill_link` can unlink planned entries and prune empty parents.
Adding `.gemini` to uninstall's fixed single-link tuple alone is insufficient.
Add Gemini machine-local directories to packaging's exclusion coverage where
applicable; do not package generated views or local Gemini settings.

**5. Prove execution before polishing optional features.** Add focused cases
in `tests/test_launch.py` for configured argv, discussion+kickoff, large
prompt delivery, and supervised handoff; in `tests/test_recurring_autofix.py`
for the explicit Gemini analyze template; and in `tests/test_config.py`,
`tests/test_commands.py`, and `tests/test_validate.py` for three-agent peers
and ambiguity. Retain the generic unknown-provider usage behavior in
`tests/test_usage.py` rather than implementing a parser.

Extend `tests/test_agent_cli_setup.py` (its fake installer currently treats
anything other than Codex as Claude), `tests/test_init.py` skill-view and
clone cases, `tests/test_uninstall.py`, and `tests/test_packaging.py` for the
new lifecycle. Use the vendor scanner in a manual versioned discovery smoke;
CI tests must not download Gemini or require vendor credentials. Preserve
existing two-agent fixtures and add a representative Gemini configuration
case under `tests/fixtures/seeded-repo/` or its related fixture helpers.

**6. Update the durable owners in the implementation PR.** The packaged
config comments own agent key usage. `coga/init` owns instruction-file and
skill discovery, `coga/install` owns installation/authentication prerequisites,
`coga/uninstall` owns cleanup, `coga/sandboxes` owns the environment/Git-access
caveats below, and `coga/usage` owns the user-visible unknown-usage limit.
Update the corresponding `docs/contexts/coga/<topic>/SKILL.md` and
`src/coga/resources/templates/coga/bootstrap/contexts/coga/<topic>/SKILL.md`
together. Update affected implementation facts in the local-only
`coga-dev/internals/{agent-spawn,agent-config,activity-capture}` and
`coga-dev/packaging` topics; do not ship those development topics. Link to
owning facts instead of duplicating a capability specification across topics.

### Out of scope

- A Gemini transcript/token parser, pricing, or session resume integration.
  Keep unknown usage honest even though the CLI can pin a session ID.
- A system-prompt-file wrapper, vendor system-prompt replacement, or simulated
  session naming to conceal unsupported optional argv.
- New agent schemas, launch backends, MCP/ACP integration, or a plugin registry.
- The sibling's general agent-selection UI or changes to peer inference and
  single-agent workflow policy beyond compatibility with the added defaults.
- Native Windows agent sessions, remote/container sandbox certification, or
  automatic changes to operator permissions, credentials, and trust settings.

## Context

### Versioned capability survey

Surveyed 2026-10-28 (America/Los_Angeles), with Node v24.13.0 on Linux.
`npm view @google/gemini-cli version engines dist.tarball --json` returned
0.66.0 and Node >=20; an isolated npm execution reported `gemini --version`
as `0.66.0`. Actual `--help` and package behavior take precedence over a
moving web cheatsheet. Source artifact:
[official npm package 0.66.0](https://registry.npmjs.org/@google/gemini-cli/-/gemini-cli-0.66.0.tgz).

| Capability | 0.66.0 evidence and design consequence |
| --- | --- |
| Interactive task | Positional prompts enter the REPL with TTY stdin/stdout; `--prompt-interactive` is also supported. Use the positional form. |
| Session display name | No naming flag in actual `--help`. Leave `name_flag` unset. |
| Deterministic new ID | `--session-id` starts a new session with a supplied UUID; distinct from `--resume`. Set `session_id_flag`. |
| System-context injection | No inline system-prompt flag in help. `GEMINI_SYSTEM_MD` is a file-based replacement of Gemini's core instructions, not Coga's discussion argv contract. Use positional fallback. |
| One-shot analysis | `--prompt`/`-p` is headless; the trusted scratch probe returned output and exited 0. An untrusted scratch invocation exited 55 with a trust remedy. |
| Instruction file | Default is `GEMINI.md`; custom names are operator settings, not an integration dependency. |
| Skills | `.gemini/skills/` is a workspace location; only the root and immediate children are scanned. Direct skill-directory symlinks were discovered. |
| Usage | Gemini's UUID support does not add a Coga parser; session activity remains recorded with unknown provider usage. |

Google's [CLI reference](https://geminicli.com/docs/cli/cli-reference/),
[installation guide](https://geminicli.com/docs/get-started/installation/),
[authentication guide](https://geminicli.com/docs/get-started/authentication/),
[GEMINI.md guide](https://geminicli.com/docs/cli/gemini-md/),
[skills guide](https://geminicli.com/docs/cli/skills/), and
[system-prompt guide](https://geminicli.com/docs/cli/system-prompt/) support
setup and optional-feature interpretation. Login starts with bare `gemini`;
there is no need to invent a `gemini login` subcommand.

In Gemini's versioned source, `packages/cli/src/config/config.ts`
`parseArguments` maps a positional query to `promptInteractive` in a terminal;
`loadCliConfig` passes it into interactive configuration. The local CLI's
`resolveSessionId` in `packages/cli/src/gemini.tsx` accepts the new UUID.
`packages/core/src/skills/skillLoader.ts` `loadSkillsFromDir` uses the patterns
`SKILL.md` and `*/SKILL.md`, and `loadSkillFromFile` sanitizes the metadata
name. These are source symbols visible in the published bundle, not inferred
from a similarly named flag.

### Execution proof and remaining boundary

An isolated PTY probe ran the real 0.66.0 CLI with a fixed synthetic response
from its testing-only `--fake-responses-non-strict` facility. The transcript
contains the supplied initial prompt and UUID. Gemini's real
`run_shell_command` invoked Coga's `emit_done_marker("survey/probe")`; the
real `run_with_done_marker` returned exit 0, `kind="done"`,
`done_signalled=true`. The command wrote its environment receipt and signaled
only the disposable probe sentinel; all inherited Coga session variables
were replaced or removed. The probe alone used explicit scratch-workspace
trust and tool auto-approval flags; neither belongs in the shipped defaults.
This proves interactive delivery and the shell/supervisor transport, not
model compliance, paid-service access, lifecycle publication, or a full task.
No real credentials or model requests were used.

In the vendor bundle, `packages/core/src/services/shellExecutionService.ts`
`ShellExecutionService.prepareExecution` takes the current environment through
`sanitizeEnvironment` before spawning the shell. Both pipe and PTY-requested
shell probes preserved `COGA_SUPERVISED`, `COGA_EXPECTED_TASK`,
`COGA_EXPECTED_STEP`, `COGA_EXPECTED_AGENT`, `COGA_TASK_SLUG`, and
`COGA_DONE_SENTINEL`, including with ordinary variable redaction enabled.
No Codex-style daemon flag is needed for this tested local path.

Do not overgeneralize that proof: the vendor's
`packages/core/src/services/environmentSanitization.ts` `sanitizeEnvironment`
and `shouldRedactEnvironmentVariable` use a stricter allowlist under
`GITHUB_SHA`/`SURFACE=Github`; ordinary redaction can also remove secret-like
variables used by commands. `ShellExecutionService.prepareExecution` adds
Git overrides including an empty `credential.helper` and disables prompting,
so HTTPS publication depending on a credential helper needs an independently
working authentication route. The implementation smoke must check publication
from inside the Gemini shell, not infer it from host access. Document these
operator requirements without silently disabling vendor protections.

### Coga code relationships

- `src/coga/config.py` `AgentType` and `_parse_agents` already accept all
  proposed keys, merge local/shared keys, and reject self/unknown peers.
  The required `file` field describes discovery; launch does not read it.
- `src/coga/launch.py` `spawn_agent_session` calls `build_agent_command`,
  appends authoring's optional kickoff, and runs the shared supervisor.
  `_argv_prompt` replaces an oversized argument with a prompt-file pointer.
  `_discussion_template` has no Gemini built-in, so it falls back to the
  normal prompt path. `src/coga/repl_supervisor.py` `emit_done_marker` and
  `run_with_done_marker` communicate through the matching task-slug sentinel.
- `src/coga/bump.py` `resolve_other_agent` reads explicit live peers first;
  otherwise it requires exactly one other configured type. Configuring three
  tables alone is insufficient even for an unchanged Claude/Codex ticket.
- `src/coga/recurring_autofix.py` `build_analyze_command` prefers
  `AgentType.analyze` to its known-CLI defaults and never appends `launch_args`.
  `src/coga/usage.py` `parser_key_for_cli` and `parse_session` only implement
  Claude/Codex usage; a session-ID flag alone does not change that.
- `src/coga/commands/init.py` `_link_skills_for_agents` and
  `src/coga/launch.py` `_refresh_agent_skills_for_launch` both consume
  `src/coga/agent_skills.py` `refresh_agent_skill_view`. That function merges
  bundled then local refs and preserves nested paths. These are the two real
  consumers for shared Gemini projection support; core must not import an
  executable from a skill or ticket directory.
- `src/coga/commands/uninstall.py` `_build_plan` currently uses its own
  `_AGENT_SKILL_DIRS` and imports init's `_AGENT_GUIDE_FILES`.
  `tests/test_packaging.py` `INTENTIONALLY_DIVERGENT_TWINS` already exempts the
  live `coga/coga.toml` as real team config; do not copy the new seed over it.

### Required topic reads and sibling coordination

These topics are cited rather than attached. Read `coga/init`,
`docs/contexts/coga/init/SKILL.md`, "Fresh repo" and "Instruction files and
skill discovery"; `coga/install`, `docs/contexts/coga/install/SKILL.md`,
"Prerequisites"; `coga/uninstall`, `docs/contexts/coga/uninstall/SKILL.md`,
"What it removes"; and `coga/sandboxes`,
`docs/contexts/coga/sandboxes/SKILL.md`, "Restricted sandboxes" before editing
their contracts. Read `coga-dev/internals/agent-spawn`,
`docs/contexts/coga-dev/internals/agent-spawn/SKILL.md`, "Per-caller parameters"
and "The supervisor"; `coga-dev/internals/agent-config`,
`docs/contexts/coga-dev/internals/agent-config/SKILL.md`, "Shared/local merge"
and "`peer` resolution"; and `coga-dev/internals/activity-capture`,
`docs/contexts/coga-dev/internals/activity-capture/SKILL.md`, "Provider matching
— never by file mtime". Read `coga-dev/packaging`,
`docs/contexts/coga-dev/packaging/SKILL.md`, "Canonical copies and twins", for
exclusions and twin enforcement.

The sibling `coga/tasks/v1/20-ask-which-agents-to-enable-during-coga-init.md`
plans to list `AGENT_CLIS` and comment unselected tables, but its current spec
predates active peer defaults. Recheck its status and landed code at
implementation time. This design does not make its picker a prerequisite for
Gemini support; whichever change lands second must preserve the subset rules
above. Root guide/skill wiring remains independent of agent selection, as
that sibling deliberately specifies.

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

## Design handoff

Recommend proceeding with the integration specified above. No feature branch,
code change, live config edit, or PR was created by this design step.
The proposal awaits independent evaluation and owner review.

Key findings: 0.66.0 accepts an interactive positional prompt and a new
session UUID; a trailing `--prompt-interactive` in `launch_args` must not be
combined with Coga's intervening session flag. Gemini requires immediate
skill-directory links rather than the current nested view link. Three-agent
peer defaults must survive the init sibling's subset filtering. Usage stays
unknown; discussion uses a first-user-prompt fallback. Native Git helper
suppression makes publication a separate live-smoke requirement.

## Evidence and checks

- Survey: official `@google/gemini-cli@0.66.0`, Node v24.13.0, Linux,
  2026-10-28 local date. Commands included
  `npm view @google/gemini-cli version engines dist.tarball --json` and
  `npm exec --cache /tmp/coga-gemini-survey-cache --yes --package @google/gemini-cli@0.66.0 -- gemini --version`.
  Actual `--help` was read from that package, with `GEMINI_CLI_HOME` pointed
  at a temporary profile. No global Gemini installation was made.
- Vendor scanner probe: nested `skills/coga -> view` found zero skills;
  immediate `skills/coga-code-probe -> view/code/probe` found `code-probe`.
  Pipe and PTY-requested shell execution preserved all six tested Coga
  variables, even with ordinary environment redaction enabled.
- Offline interactive transport:
  `PYTHONPATH=/home/n/Code/coga/src /home/n/.local/share/uv/tools/coga/bin/python /tmp/coga-gemini-supervisor-probe.py`
  ran with a TTY. Result: exit 0, `kind=done`, `done_signalled=true`.
  Transcript verified the initial prompt and requested UUID. Local receipts:
  `/tmp/coga-gemini-pty-b6mu7_co/{result.json,handoff-env.json,terminal.txt}`
  and its isolated `profile/.gemini/tmp/.../chats/` transcript. These are
  disposable local reproduction aids; the version, method, results, and
  limitations are recorded durably above.
- Offline one-shot: `-p` produced the synthetic output marker and exit 0
  with scratch trust supplied. Without trust it exited 55, naming the setup
  remedy. Neither probe used real credentials or called a model service.
- Existing Coga `build_agent_command` produced
  `gemini --session-id <uuid> <prompt>`; `build_analyze_command` produced
  `gemini -p <prompt>` without a code change.
- `git diff --check`: passed. `coga validate --json`: exit 0, 101 OK,
  no errors and no issue on this ticket; 16 existing warnings on other
  tickets (large blackboards/unfrozen workflows).
- Reconciled against `origin/main` at `2335559ec` after preserving and
  verifying a ticket backup; remote changes were documentation only. Read
  the updated `coga-dev/principles`; the proposal still fits. Ticket
  frontmatter and the embedded guide were preserved byte-for-byte.

## Open Questions

No unresolved product question prevents design evaluation. The proposed
peer defaults and optional-feature scope are for owner review, not approval
by this design author. The authenticated end-to-end task/publication smoke
has **not** run and remains an explicit implementation acceptance gate; the
offline transport success does not waive it.
