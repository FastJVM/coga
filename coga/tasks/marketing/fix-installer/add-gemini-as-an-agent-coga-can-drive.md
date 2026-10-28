---
title: Add Gemini as an agent coga can drive
status: active
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
step: 1 (design)
agent: claude
---

## Description

Coga drives `claude` and `codex` today. Nico wants Gemini as a third agent
type. Find out what Gemini's CLI actually supports, then either add it or say
why it cannot be added yet.

Done when: a repo can declare `[agents.gemini]` in `coga.toml` and run a Coga
task through its intended handoff, with unsupported optional features
documented, or a versioned capability survey identifies a concrete
incompatibility preventing core task execution and the owner accepts deferral
at `review-design`.

## Context

### What "adding an agent" requires

An agent type is a `[agents.*]` table. `cli` and `file` are the only required
keys, so a minimal Gemini table is trivial. The cost is in the optional keys,
each of which exists because a specific coga feature needs it:

- `name_flag` — sets the session display name. Claude uses `-n`.
- `session_id_flag` — pins a transcript ID; Claude uses `--session-id`.
  It does not provide usage parsing by itself: `usage.parser_key_for_cli`
  and `usage.parse_session` support only Claude and Codex, so Gemini usage
  currently records `unknown` regardless of this flag. Codex's
  `usage._parse_codex_session` attributes usage without a session-ID flag.
  Coga reports tokens; decide during design whether Gemini parsing belongs
  in this ticket or remains a documented limitation.
- `discussion` — injects the composed prompt as system context so the human's
  first message titles the session. Claude uses `--append-system-prompt
  {prompt}`; Codex uses `-c developer_instructions={prompt}`.
- `launch_args` — per-CLI workarounds. Codex needs `--no-daemon` so the
  `COGA_*` launch variables reach the agent.
- `analyze` — the non-interactive one-shot form the recurring autofix loop
  uses. `recurring_autofix.DEFAULT_ANALYZE_TEMPLATES` hardcodes `claude: "-p
  {prompt}"` and `codex: "exec {prompt}"`. An unknown CLI with no `analyze`
  override skips autofix loudly rather than guessing, because a bare prompt to
  an unknown CLI opens an interactive REPL nobody can drive.

First verify core execution: `launch.build_agent_command` appends the composed
prompt after `launch_args`. Confirm the chosen Gemini invocation enters an
interactive session, receives the task, and preserves `COGA_*` in agent-run
commands so the workflow handoff can reach Coga's supervisor.

Then survey four optional capabilities against `gemini --help`: does it have a
session-name flag, a deterministic session-id flag, a system-prompt injection
flag, and a non-interactive one-shot mode? Record the CLI version and evidence
for supported behavior and missing features. Missing optional flags alone do
not justify deferral; distinguish feature degradation from a core execution
blocker. Gemini was unavailable in the authoring environment, so these
capabilities still need investigation in the design step.

### Adding a third agent breaks zero-config peer review

`bump.resolve_other_agent` resolves the `other-agent` workflow role as "the
single configured type that is not the ticket's main agent", and raises when
`len(others) != 1`. Two configured agents need no `peer` key. With three,
each main-agent type used by a workflow containing `other-agent` needs
`peer = "<type>"` in its `[agents.*]` table or that handoff fails.

The error message already names the fix, so this is a documentation and
default-config problem, not a code bug. Decide whether the packaged
`coga.toml` should ship explicit `peer` values once a third agent exists.

### Also needs

- `dependencies.AGENT_CLIS` is `("claude", "codex")`; a Gemini entry needs
  `packages` (brew/npm) and `login` so `agent_cli_setup.offer_agent_cli` can
  install and authenticate it.
- `init._AGENT_LABELS` maps slugs to display names and needs a Gemini row.
- `init._AGENT_SKILL_DIRS` and `_AGENT_GUIDE_FILES` decide which skill
  symlinks and root instruction files init writes. Find out which directory
  Gemini reads skills from and which instruction file it looks for.
  Inspect the corresponding generated ignore rules and empty-repo detection;
  `commands.uninstall._AGENT_SKILL_DIRS` independently lists directories to
  clean up, while uninstall imports init's guide-file list.

### Scope note

Sibling of `v1/20-ask-which-agents-to-enable-during-coga-init`,
which makes `coga init` ask which agents to enable. That ticket does not block
on this one: its picker lists whatever `AGENT_CLIS` holds, so Gemini joins the
list for free once added here. Nico thinks this is easy; Zach's recorded
caution is that what Nico calls easy usually is not, which is why the
`gemini --help` survey comes before any commitment to ship it.
Coordinate packaged peer defaults with that sibling's agent selections.

### Documentation and design references

These topics are cited rather than attached. Read the named sections and
update any changed contract in its owner, with packaged twins kept in sync:

- `coga/init`, `docs/contexts/coga/init/SKILL.md`: "Fresh repo" and
  "Instruction files and skill discovery"; `coga/install`,
  `docs/contexts/coga/install/SKILL.md`: "Prerequisites". These are editing
  targets: they describe the existing two-agent setup. Their packaged twins
  live under `src/coga/resources/templates/coga/bootstrap/contexts/`.
- `coga-dev/internals/agent-spawn`,
  `docs/contexts/coga-dev/internals/agent-spawn/SKILL.md`: "Per-caller
  parameters" and "The supervisor" for prompt delivery and `COGA_*` handoffs;
  `coga-dev/internals/agent-config`,
  `docs/contexts/coga-dev/internals/agent-config/SKILL.md`: "Shared/local
  merge" and "`peer` resolution" for agent configuration.
- `coga-dev/internals/activity-capture`,
  `docs/contexts/coga-dev/internals/activity-capture/SKILL.md`: "Provider
  matching — never by file mtime" for the usage limitation above.

If Gemini is deferred, record the reason and what would reopen the decision
in the standing owning topic as well as this ticket; tickets can be retired.

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

The blackboard is a notepad to be written to often as the human and agent works through a task.
